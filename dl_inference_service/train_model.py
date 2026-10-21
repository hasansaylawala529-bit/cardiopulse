import os
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
import pandas as pd
from sklearn.metrics import classification_report, accuracy_score

# 1. 1D-ResNet Architecture for 187-sample Wearable ECG Beats
class ResidualBlock1D(nn.Module):
    def __init__(self, in_c, out_c, stride=1):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv1d(in_c, out_c, kernel_size=5, stride=stride, padding=2, bias=False),
            nn.BatchNorm1d(out_c),
            nn.ReLU(),
            nn.Conv1d(out_c, out_c, kernel_size=5, stride=1, padding=2, bias=False),
            nn.BatchNorm1d(out_c)
        )
        self.shortcut = nn.Sequential()
        if stride != 1 or in_c != out_c:
            self.shortcut = nn.Sequential(
                nn.Conv1d(in_c, out_c, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm1d(out_c)
            )
        self.relu = nn.ReLU()

    def forward(self, x):
        return self.relu(self.conv(x) + self.shortcut(x))

class ECGResNet1D(nn.Module):
    def __init__(self, num_classes=5):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Conv1d(1, 32, kernel_size=7, padding=3, bias=False),
            nn.BatchNorm1d(32),
            nn.ReLU()
        )
        self.block1 = ResidualBlock1D(32, 64, stride=2)
        self.block2 = ResidualBlock1D(64, 128, stride=2)
        self.block3 = ResidualBlock1D(128, 256, stride=2)
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.fc = nn.Linear(256, num_classes)

    def forward(self, x):
        x = self.stem(x)
        x = self.block1(x)
        x = self.block2(x)
        x = self.block3(x)
        x = self.pool(x).squeeze(-1)
        return self.fc(x)

if __name__ == "__main__":
    # Locate the CSVs in the root project folder
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    train_csv = os.path.join(BASE_DIR, "mitbih_train.csv")
    test_csv = os.path.join(BASE_DIR, "mitbih_test.csv")

    print(f"[1/4] Loading MIT-BIH datasets from {BASE_DIR}...")
    train_df = pd.read_csv(train_csv, header=None)
    test_df = pd.read_csv(test_csv, header=None)

    X_train = torch.tensor(train_df.iloc[:, :187].values, dtype=torch.float32).unsqueeze(1)
    y_train = torch.tensor(train_df.iloc[:, 187].values, dtype=torch.long)

    X_test = torch.tensor(test_df.iloc[:, :187].values, dtype=torch.float32).unsqueeze(1)
    y_test = torch.tensor(test_df.iloc[:, 187].values, dtype=torch.long)

    train_loader = DataLoader(TensorDataset(X_train, y_train), batch_size=128, shuffle=True)
    test_loader = DataLoader(TensorDataset(X_test, y_test), batch_size=256, shuffle=False)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[2/4] Training 1D-ResNet on {device}...")

    model = ECGResNet1D(num_classes=5).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)

    EPOCHS = 5
    for epoch in range(EPOCHS):
        model.train()
        total_loss = 0.0
        for bx, by in train_loader:
            bx, by = bx.to(device), by.to(device)
            optimizer.zero_grad()
            out = model(bx)
            loss = criterion(out, by)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        print(f"  Epoch {epoch+1}/{EPOCHS} | Loss: {total_loss/len(train_loader):.4f}")

    print("[3/4] Evaluating on Test Set...")
    model.eval()
    preds, trues = [], []
    with torch.no_grad():
        for bx, by in test_loader:
            bx = bx.to(device)
            preds.extend(torch.argmax(model(bx), dim=1).cpu().numpy())
            trues.extend(by.numpy())

    acc = accuracy_score(trues, preds)
    print(f"\n[+] Final Test Accuracy: {acc*100:.2f}%")
    print(classification_report(trues, preds, target_names=["N", "S", "V", "F", "Q"]))

    # Save weights inside dl_inference_service/models/
    model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
    os.makedirs(model_dir, exist_ok=True)
    weight_path = os.path.join(model_dir, "ecg_resnet1d.pt")
    torch.save(model.state_dict(), weight_path)
    print(f"[4/4] Saved trained model weights to: {weight_path}")