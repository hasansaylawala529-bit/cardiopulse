# 🚀 Wearable ECG Cloud Analytics: End-to-End System Run Guide

This project is a multi-domain distributed pipeline covering **Deep Learning**, **Big Data Analytics**, and **Cloud Computing** for **LP-2 Problem Statement 4**.

---

## 📋 The 5-Step Execution Workflow

To run the full end-to-end pipeline, open terminal windows in the project directory:

### Step 1: Start the Distributed Stack (Docker)
Spins up Zookeeper, Kafka Broker (port 9092), Spark Master & Worker (ports 9091, 7078), and Cassandra (port 9042):
```bash
docker-compose up -d
```
*Wait ~1-2 minutes for Cassandra and Kafka to become fully healthy.*

Verify running containers:
```bash
docker ps
```

---

### Step 2: Start the Deep Learning Inference Microservice (Domain 1: DL)
In **Terminal 1**:
```bash
python -m uvicorn dl_inference_service.app:app --port 8000
```
- Loads the trained PyTorch 1D-ResNet weights (`ecg_resnet1d.pt`).
- Serves real-time inference on `http://127.0.0.1:8000/predict`.
- Hosts the **Bedside ICU Telehealth Web Monitor** on `http://127.0.0.1:8000/monitor/`.

---

### Step 3: Launch Apache Spark Structured Streaming (Domain 2: Big Data)
In **Terminal 2**:
Submit the Spark streaming job that consumes from Kafka topic `ecg_telemetry` and writes directly to Cassandra table `spark_streams.ecg_patient_alerts`:

```bash
docker exec -it wearable-ecg-cloud-analytics-spark-master-1 spark-submit \
  --packages com.datastax.spark:spark-cassandra-connector_2.12:3.4.0,org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
  /tmp/spark_stream.py
```
*(Tip: Copy `spark_stream.py` to the master container using `docker cp spark_stream.py wearable-ecg-cloud-analytics-spark-master-1:/tmp/spark_stream.py` if not already present).*

---

### Step 4: Start Ingesting Wearable Telemetry to Kafka (Domain 2: Big Data)
In **Terminal 3**:
```bash
python dags/kafka_stream.py
```
- Samples 187-sample MIT-BIH Lead-II ECG packets.
- Calls the 1D-ResNet API (`http://127.0.0.1:8000/predict`) to classify each beat.
- Publishes enriched patient telemetry into Kafka topic `ecg_telemetry`.

---

### Step 5: Open the Clinical User Interfaces (Domain 3: Cloud & Web)

1. **📊 Cloud Big Data & Cassandra Suite (Streamlit)**:
   In **Terminal 4**:
   ```bash
   python -m streamlit run streamlit_app.py
   ```
   Open: **[http://localhost:8501](http://localhost:8501)**
   - Displays live incoming heartbeats from Cassandra.
   - Interactive Lead-II waveform Plotly chart.
   - Cohort distributions and real-time arrhythmia alert log.

2. **🏥 Bedside ICU Telehealth Web Monitor (FastAPI)**:
   Open in your browser:
   👉 **[http://localhost:8000/monitor/](http://localhost:8000/monitor/)**
   - 60 FPS sweeping canvas oscilloscope with phosphor glow.
   - Live vitals HUD (BPM, SpO2, NIBP, Respiration).
   - Audio pulse tone (Web Audio API) and on-demand "⚡ SIMULATE PVC" testing button.

---

## 🛑 Stopping Everything
When done, stop the Docker cluster to free memory:
```bash
docker-compose down
```
