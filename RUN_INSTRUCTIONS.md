# 🚀 CardioPulse: End-to-End Execution Guide

**CardioPulse** is an enterprise-grade distributed IoMT pipeline for real-time wearable ECG arrhythmia classification, stream processing, and clinical surveillance. It integrates **PyTorch 1D-ResNet**, **Apache Kafka**, **Apache Spark Structured Streaming**, **Apache Cassandra NoSQL**, and interactive web dashboards (**FastAPI & Streamlit**).

---

## ⚠️ Important Configuration Notes

Before running the stack, note these key architectural settings:

1. **Targeted Container Startup**:
   Running `docker-compose up -d zookeeper broker cassandra spark-master spark-worker` starts only the 5 core services needed for the streaming pipeline without spinning up unnecessary background services.

2. **Cassandra Schema Initialization**:
   A fresh Cassandra container starts with no schema. Run `docker exec cassandra cqlsh -f /tmp/init_cassandra.cql` (or `//tmp/init_cassandra.cql` in Git Bash) once Cassandra is healthy to create the `spark_streams` keyspace and `ecg_patient_alerts` table.

3. **Spark Master Container & Volume Mount**:
   The master container is named `spark-master`, and `spark_stream.py` is automatically mounted into `/tmp/spark_stream.py`.

4. **Service Health & Ingestion Order**:
   Kafka broker and Cassandra require ~45–60 seconds on initial boot to initialize and pass healthchecks before starting producers and streaming consumers.

---

## 📋 The Complete Step-by-Step Execution Sequence

Open separate terminal windows in `d:\Projects\wearable-ecg-cloud-analytics`:

---

### Step 1: Start Distributed Infrastructure (Docker)
In **Terminal 1**:
```bash
docker-compose up -d zookeeper broker cassandra spark-master spark-worker
```
*Wait ~45-60 seconds for Kafka (port 9092) and Cassandra (port 9042) to initialize.*

Verify all 5 containers are running:
```bash
docker ps
```
*(You should see `zookeeper`, `broker`, `cassandra`, `spark-master`, and `spark-worker`).*

---

### Step 2: Initialize Cassandra Schema (NoSQL Sink)
In **Terminal 1** (once Cassandra is up):

> 💡 **For Git Bash (MinGW)**: Use double slash `//tmp` to prevent Git Bash from translating it to Windows temp directory:
```bash
docker exec cassandra cqlsh -f //tmp/init_cassandra.cql
```
*(In PowerShell / CMD: `docker exec cassandra cqlsh -f /tmp/init_cassandra.cql`)*

Verify the keyspace is created:
```bash
docker exec cassandra cqlsh -e "DESCRIBE KEYSPACE spark_streams;"
```

---

### Step 3: Start the PyTorch 1D-ResNet Inference Microservice (FastAPI)
In **Terminal 2**:
```bash
python dl_inference_service/app.py
```
*(Alternative: `python -m uvicorn dl_inference_service.app:app --port 8000`)*
- Loads the trained PyTorch 1D-ResNet weights (`ecg_resnet1d.pt`) validated at 98.75% accuracy.
- Serves real-time inference on `http://127.0.0.1:8000/predict`.
- Mounts the Bedside ICU Telehealth Web Monitor on `http://127.0.0.1:8000/monitor/`.

---

### Step 4: Launch Apache Spark Structured Streaming
In **Terminal 3**:
Submit the Spark job that consumes from Kafka topic `ecg_telemetry` and writes directly to Cassandra table `spark_streams.ecg_patient_alerts`:

**In Git Bash**:
```bash
docker exec -i spark-master spark-submit --packages com.datastax.spark:spark-cassandra-connector_2.12:3.4.0,org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 //tmp/spark_stream.py
```
*(In PowerShell / CMD: use `/tmp/spark_stream.py`)*

Expected terminal output:
```text
INFO:__main__:[+] Spark session initialized successfully
INFO:__main__:[+] Connected to Kafka topic 'ecg_telemetry'
INFO:__main__:[*] Streaming pipeline active: Kafka -> Spark -> Cassandra
```

---

### Step 5: Start Ingesting Wearable Telemetry to Kafka
In **Terminal 4**:
```bash
python dags/kafka_stream.py
```
- Samples real 187-sample MIT-BIH Lead-II ECG beats from `mitbih_test.csv`.
- Calls FastAPI (`http://127.0.0.1:8000/predict`) to classify each beat using the 1D-ResNet model.
- Publishes enriched patient telemetry into Kafka topic `ecg_telemetry`.

Live streaming output:
```text
Sent -> PAT-101 | Normal Beat (N) (99.8%)
Sent -> PAT-102 | Ventricular Ectopic (V) (98.4%)
```

---

### Step 6: Launch Clinical Surveillance Command Center (Streamlit)
In **Terminal 5**:
```bash
python -m streamlit run streamlit_app.py
```
Open your browser to:
👉 **[http://localhost:8501](http://localhost:8501)**

- Direct live connection to Apache Cassandra (`spark_streams.ecg_patient_alerts`).
- Calibrated medical pink grid Lead-II ECG strips (10mm/mV, 25mm/s).
- Flashing critical arrhythmia emergency alert banner.
- Multi-patient 2x2 surveillance grid with triage filtering.
- Real-time cardiac emergency audit log and deep-dive inspection modal.

*(Optional Bedside 60 FPS Oscilloscope)*:
👉 **[http://localhost:8000/monitor/](http://localhost:8000/monitor/)**

---

## 🛑 How to Stop All Services Cleanly
When you are done testing, stop the processes in reverse:
1. Press `Ctrl + C` in Terminals 5, 4, 3, and 2.
2. In Terminal 1, shut down the Docker containers:
```bash
docker-compose down
```
