import os
import random
import torch
import torch.nn.functional as F
import pandas as pd
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List

try:
    from dl_inference_service.train_model import ECGResNet1D
except ImportError:
    from train_model import ECGResNet1D

app = FastAPI(
    title="Wearable ECG 1D-ResNet Cloud API & Clinical Monitor",
    description="Real-time ECG arrhythmia classification for IoMT wearables with live ICU oscilloscope telemetry.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AAMI_LABELS = {
    0: "Normal Beat (N)",
    1: "Supraventricular Ectopic (S)",
    2: "Ventricular Ectopic (V)",
    3: "Fusion Beat (F)",
    4: "Unknown / Paced (Q)"
}

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = ECGResNet1D(num_classes=5).to(device)

WEIGHT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "ecg_resnet1d.pt")
if os.path.exists(WEIGHT_PATH):
    model.load_state_dict(torch.load(WEIGHT_PATH, map_location=device))
    print(f"[+] Loaded trained weights from {WEIGHT_PATH}")
model.eval()

# Locate frontend static directory
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/monitor", StaticFiles(directory=FRONTEND_DIR, html=True), name="monitor")
    print(f"[+] Mounted Clinical Telemetry Monitor at /monitor/ from {FRONTEND_DIR}")

# Cache sample test dataset in memory for quick streaming
SAMPLE_CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mitbih_test.csv")
sample_cache_df = None
if os.path.exists(SAMPLE_CSV_PATH):
    try:
        sample_cache_df = pd.read_csv(SAMPLE_CSV_PATH, header=None, nrows=500)
        print(f"[+] Pre-loaded 500 test beats for fast telemetry streaming")
    except Exception as e:
        print(f"[-] Could not pre-cache sample beats: {e}")

class SignalInput(BaseModel):
    signal: List[float]

@app.get("/")
def root(request: Request):
    accept = request.headers.get("accept", "")
    if "text/html" in accept and os.path.exists(FRONTEND_DIR):
        return RedirectResponse(url="/monitor/")
    return {
        "status": "online",
        "model": "ECGResNet1D",
        "monitor_ui": "/monitor/",
        "docs": "/docs",
        "predict_endpoint": "/predict"
    }

@app.get("/health")
def health():
    return {"status": "online", "model": "ECGResNet1D", "device": str(device)}

@app.post("/predict")
def predict(data: SignalInput):
    x = torch.tensor(data.signal[:187], dtype=torch.float32).unsqueeze(0).unsqueeze(0).to(device)
    with torch.no_grad():
        logits = model(x)
        probs = F.softmax(logits, dim=1).squeeze(0)
        pred_id = int(torch.argmax(probs).item())
        conf = float(probs[pred_id].item())

    alert = "CRITICAL" if pred_id in [1, 2, 3] else "NORMAL"
    return {
        "prediction": AAMI_LABELS[pred_id],
        "class_id": pred_id,
        "confidence": round(conf, 4),
        "alert_status": alert
    }

@app.get("/api/sample-beat")
def get_sample_beat(type_hint: str = "any"):
    """Returns a real 187-sample beat from MIT-BIH test dataset with model prediction."""
    if sample_cache_df is not None and not sample_cache_df.empty:
        if type_hint == "pvc":
            sub_df = sample_cache_df[sample_cache_df.iloc[:, 187] == 2]
            row = sub_df.sample(n=1).iloc[0] if not sub_df.empty else sample_cache_df.sample(n=1).iloc[0]
        else:
            row = sample_cache_df.sample(n=1).iloc[0]

        signal = row.iloc[:187].tolist()
        ground_truth = int(row.iloc[187])
    else:
        # Fallback synthetic beat
        signal = [0.0] * 187
        ground_truth = 0

    # Score through model
    res = predict(SignalInput(signal=signal))
    res["signal"] = signal
    res["ground_truth"] = ground_truth
    return res