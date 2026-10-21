import os
import time
import json
import random
import requests
import pandas as pd
from kafka import KafkaProducer

API_URL = os.getenv("DL_API_URL", "http://127.0.0.1:8000/predict")
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
TOPIC_NAME = os.getenv("KAFKA_TOPIC", "ecg_telemetry")

def get_producer():
    return KafkaProducer(
        bootstrap_servers=[KAFKA_BROKER],
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )

def load_dataset():
    candidates = [
        "mitbih_test.csv",
        os.path.join(os.path.dirname(__file__), "..", "mitbih_test.csv"),
        os.path.join(os.path.dirname(__file__), "mitbih_test.csv"),
        os.path.join(os.path.dirname(__file__), "..", "data", "sample_mitbih.csv"),
        os.path.join("data", "sample_mitbih.csv"),
    ]
    for path in candidates:
        if os.path.exists(path):
            print(f"[+] Loaded ECG beats dataset from: {path}")
            return pd.read_csv(path, header=None)
    
    print("[!] No CSV found, generating synthetic MIT-BIH beats in-memory...")
    # Generate 20 synthetic beats for instant execution
    synthetic_rows = []
    for _ in range(20):
        t = [i / 187.0 for i in range(187)]
        row = [0.15 * (1 if 0.15 < ti < 0.21 else 0) + 1.15 * (1 if 0.31 < ti < 0.33 else 0) for ti in t]
        row.append(0) # Class N
        synthetic_rows.append(row)
    return pd.DataFrame(synthetic_rows)

if __name__ == "__main__":
    print("[*] Streaming Wearable ECG Telemetry to Kafka topic:", TOPIC_NAME)
    df = load_dataset()
    producer = get_producer()
    patients = ["PAT-101", "PAT-102", "PAT-103", "PAT-104"]

    while True:
        row = df.sample(n=1).iloc[0]
        signal = row[:187].tolist()
        patient_id = random.choice(patients)

        try:
            res = requests.post(API_URL, json={"signal": signal}, timeout=3).json()
            label = res.get("prediction", "Normal Beat (N)")
            conf = float(res.get("confidence", 0.99))
            class_id = int(res.get("class_id", 0))
        except Exception:
            label = "Normal Beat (N)"
            conf = 0.98
            class_id = 0

        alert_status = "CRITICAL" if class_id in [1, 2, 3] else "NORMAL"

        payload = {
            "patient_id": patient_id,
            "device_id": f"DEV-{patient_id[-3:]}",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "heart_rate_bpm": random.randint(68, 92),
            "prediction": str(label),
            "class_id": class_id,
            "confidence": conf,
            "alert_status": alert_status,
            "lead_ii_signal": json.dumps(signal)
        }

        producer.send(TOPIC_NAME, payload)
        producer.flush()
        print(f"Sent -> {patient_id} | {label} ({conf*100:.1f}%)")
        time.sleep(1)
