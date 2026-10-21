# 🫀 CardioPulse: Real-Time Wearable ECG Arrhythmia Surveillance Pipeline
### Enterprise Distributed Multi-Patient Cardiac Triage using 1D-ResNet, Apache Kafka, Spark Streaming & Cassandra

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Apache Kafka](https://img.shields.io/badge/Apache%20Kafka-Distributed%20Streaming-231F20?style=for-the-badge&logo=apache-kafka&logoColor=white)](https://kafka.apache.org)
[![Apache Spark](https://img.shields.io/badge/Apache%20Spark-Structured%20Streaming-E25A1C?style=for-the-badge&logo=apache-spark&logoColor=white)](https://spark.apache.org)
[![Apache Cassandra](https://img.shields.io/badge/Apache%20Cassandra-NoSQL%20Store-1287B1?style=for-the-badge&logo=apache-cassandra&logoColor=white)](https://cassandra.apache.org)
[![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)

---

## 📌 Overview

**CardioPulse** is an enterprise-grade distributed **Internet of Medical Things (IoMT)** data engineering and deep learning streaming platform. It continuously ingests single-lead ECG telemetry captured by remote wearable health devices (sampled at 125 Hz from the MIT-BIH Arrhythmia Database), performs sub-millisecond edge/cloud deep learning classification using a **1D-ResNet** architecture, streams telemetry through **Apache Kafka**, processes events with **Apache Spark Structured Streaming**, persists data into an **Apache Cassandra** wide-column store, and surfaces sudden arrhythmias on real-time hospital surveillance dashboards.

---

## 🏗️ System Architecture

```
+---------------------------------------------------------------------------------------------------+
|                                  Distributed System Architecture                                  |
+---------------------------------------------------------------------------------------------------+
                                                                                                    
 [ Wearable IoMT Devices ] (PAT-101, PAT-102, PAT-103, PAT-104)                                    
        |                                                                                           
        | (187-sample Lead-II window @ 125 Hz)                                                      
        v                                                                                           
 [ 1D-ResNet Deep Learning API ] <---- FastAPI Microservice (Port 8000, 97.94% Validation Accuracy)  
        |                                                                                           
        | Enriched JSON Payload (Patient ID, Heart Rate, AAMI Arrhythmia Prediction, Confidence)     
        v                                                                                           
 [ Apache Kafka Event Broker ] <------ Topic: 'ecg_telemetry' (Buffered via Zookeeper)             
        |                                                                                           
        v                                                                                           
 [ Apache Spark Streaming ] <-------- PySpark Structured Streaming Engine (Schema Parsing & Windowing)
        |                                                                                           
        v                                                                                           
 [ Apache Cassandra NoSQL ] <-------- Keyspace: 'spark_streams' | Table: 'ecg_patient_alerts'       
        |                                                                                           
        v                                                                                           
 [ Hospital Triage Dashboards ] <----- Light-Theme Central Surveillance Web Portal & Streamlit Suite
```

---

## 🔬 Clinical Classification Standard (AAMI EC57)

The system classifies each heartbeat into one of 5 standard **AAMI EC57** arrhythmia categories:

| Class ID | Label | AAMI Category | Clinical Severity | Alert Status |
| :---: | :--- | :--- | :--- | :---: |
| **0** | **Normal Beat (N)** | Normal / Bundle Branch Block | Normal cardiac rhythm | `NORMAL` |
| **1** | **Supraventricular Ectopic (S)** | Atrial premature / Nodal premature | Elevated atrial ectopic risk | `CRITICAL` |
| **2** | **Ventricular Ectopic (V)** | Premature Ventricular Contraction (PVC) | High ventricular risk / tachycardia | `CRITICAL` |
| **3** | **Fusion Beat (F)** | Fusion of ventricular and normal beat | High cardiac stress | `CRITICAL` |
| **4** | **Unknown / Paced (Q)** | Paced / Unclassifiable beat | Monitored rhythm | `NORMAL` |

---

## 📂 Unified Project Structure

```
cardiopulse/
├── frontend/                    # Hospital Central Surveillance Web Portal (Light Theme)
│   ├── index.html               # Multi-patient monitoring cockpit & top emergency alert banner
│   ├── style.css                # Clinical enterprise light theme & calibrated grid styles
│   └── app.js                   # Multi-patient telemetry stream, audio chime & triage logic
├── data/
│   └── sample_mitbih.csv        # Bundled lightweight test dataset (instant execution out-of-the-box!)
├── dl_inference_service/        # Deep Learning Microservice
│   ├── app.py                   # FastAPI service serving /predict, /health & /monitor/
│   ├── train_model.py           # 1D-ResNet architecture & training script
│   ├── models/
│   │   └── ecg_resnet1d.pt      # Pre-trained 1D-ResNet PyTorch weights (97.94% accuracy)
│   ├── Dockerfile               # Container definition for DL service
│   └── requirements.txt         # Service dependencies
├── dags/
│   └── kafka_stream.py          # Wearable sensor simulator & Kafka producer
├── script/
│   ├── entrypoint.sh            # Airflow container entrypoint
│   ├── init_cassandra.cql       # Cassandra keyspace & table schema
│   └── requirements-airflow.txt # Lightweight Airflow container requirements
├── docker-compose.yml           # Multi-container orchestration (Kafka, Spark, Cassandra, Airflow)
├── spark_stream.py              # PySpark Structured Streaming job (Kafka -> Cassandra)
├── streamlit_app.py             # Hospital Big Data analytics & Cassandra triage suite (Light Theme)
├── requirements.txt             # Comprehensive workspace Python dependencies
├── RUN_INSTRUCTIONS.md          # Step-by-step operating guide
├── .gitignore                   # Optimized ignore rules (excludes large CSVs, caches, logs)
└── LICENSE                      # Open-source MIT License
```

---

## 🖥️ Hospital Central Clinical Frontends (Light UI Theme)

1. **🏥 Central Ward Surveillance Web Portal (`http://localhost:8000/monitor/`)**:
   - **Top Emergency Alert Banner**: Automatically drops down and flashes when any patient's wearable IoT device flags an arrhythmia.
   - **Multi-Patient Surveillance Grid**: Live streaming tiles for Bed 01 (PAT-101), Bed 02 (PAT-102), Bed 03 (PAT-103), Bed 04 (PAT-104) with BPM counters and status badges.
   - **Calibrated Lead-II ECG Strip**: Standard medical grid (10 mm/mV, 25 mm/s) with dynamic alert coloring.
   - **"⚡ SIMULATE PVC ALERT" Button**: Test the acute emergency alert banner and audio chime on demand.

2. **📊 Hospital Big Data & Cassandra Suite (`http://localhost:8501`)**:
   - Connects directly to **Apache Cassandra** to query live ingested telemetry.
   - Cohort distributions, heart rate variation boxplots, model calibration histograms, and multi-patient triage audit log.

---

## 🎓 LP-2 Subject Mapping (3 Core Domains)

This project satisfies all three core engineering domains for **Laboratory Practice 2 (LP-2)**:

| Domain | Syllabus Requirement | Implementation in this Pipeline |
| :--- | :--- | :--- |
| **🧠 Deep Learning (DL)** | ResNet-1D / ConvLSTM, Heartbeat segmentation, RR interval analysis, Anomaly classification | **PyTorch 1D-ResNet** (`dl_inference_service`): 5-stage residual network validated at **97.94% accuracy** on MIT-BIH dataset; performs real-time classification across 5 AAMI EC57 arrhythmia classes. |
| **⚡ Big Data Analytics (BDA)** | Continuous Ingestion via Apache Kafka, Stream Processing (sub-second windowing, alert filtering), NoSQL storage | **Apache Kafka + Apache Spark + Cassandra**: Kafka topic `ecg_telemetry` buffers wearable ECG packets; PySpark Structured Streaming processes events in real time and writes to Cassandra table `spark_streams.ecg_patient_alerts`. |
| **☁️ Cloud Computing (CC)** | Containerized microservice architecture, Serverless/REST endpoints, Web Telemetry | **Dockerized Architecture + FastAPI + Web Monitor**: Complete multi-container distributed cluster (`docker-compose.yml`), RESTful inference microservice, and live 60 FPS ICU telehealth web monitor. |

---

## ⚡ Step-by-Step Execution Guide (All 3 Domains Active)

Follow these steps to run the complete end-to-end distributed system:

### Step 1: Start Distributed Cluster Infrastructure (Docker)
Starts Zookeeper, Kafka Broker (port 9092), Spark Master (port 9091), Spark Worker, Cassandra (port 9042), and Postgres:
```bash
docker-compose up -d
```
*Wait ~1-2 minutes for Kafka and Cassandra to become fully healthy.*

Verify running containers:
```bash
docker ps
```

---

### Step 2: Start the Deep Learning Inference Microservice (Domain 1: DL)
In a new terminal:
```bash
python -m uvicorn dl_inference_service.app:app --port 8000
```
*The 1D-ResNet classifier loads `ecg_resnet1d.pt` and serves `/predict` with sub-millisecond inference.*

---

### Step 3: Launch Apache Spark Structured Streaming (Domain 2: Big Data)
Submit the PySpark job that consumes from Kafka topic `ecg_telemetry`, validates schema, and writes directly into Cassandra table `spark_streams.ecg_patient_alerts`:

```bash
docker exec -it wearable-ecg-cloud-analytics-spark-master-1 spark-submit \
  --packages com.datastax.spark:spark-cassandra-connector_2.12:3.4.0,org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
  /tmp/spark_stream.py
```
*(Tip: Copy `spark_stream.py` to the master container using `docker cp spark_stream.py wearable-ecg-cloud-analytics-spark-master-1:/tmp/spark_stream.py` if not already present).*

---

### Step 4: Start Ingesting Wearable Telemetry to Kafka (Domain 2: Big Data)
In a new terminal:
```bash
python dags/kafka_stream.py
```
*Continuously samples 187-sample Lead-II ECG packets from `mitbih_test.csv`, queries the 1D-ResNet API, and publishes real-time enriched payloads into Kafka.*

---

### Step 5: Launch the Dashboards (Domain 3: Cloud & Web)
You can view both clinical interfaces concurrently:

1. **📊 Cloud Big Data & Cassandra Suite** (Streamlit):
   ```bash
   python -m streamlit run streamlit_app.py
   ```
   *Connects to Cassandra at `127.0.0.1:9042` and visualizes live incoming heartbeats, Lead-II waveforms, and cohort statistics.*

2. **🏥 Bedside ICU Telehealth Web Monitor** (Browser):
   Open in your browser:
   👉 **[http://localhost:8000/monitor/](http://localhost:8000/monitor/)**
   *Displays 60 FPS sweeping oscilloscope ECG trace, Web Audio pulse sound, and live vitals HUD.*

---

## 🗄️ Database Schema (Apache Cassandra)

```sql
CREATE KEYSPACE IF NOT EXISTS spark_streams
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

CREATE TABLE IF NOT EXISTS spark_streams.ecg_patient_alerts (
    patient_id text,
    timestamp text,
    alert_status text,
    class_id int,
    confidence float,
    device_id text,
    heart_rate_bpm int,
    lead_ii_signal text,
    prediction text,
    PRIMARY KEY (patient_id, timestamp)
) WITH CLUSTERING ORDER BY (timestamp ASC);
```

---

## 🧠 1D-ResNet Model Architecture

- **Stem:** 1D Conv (kernel 7, stride 1) + BatchNorm1d + ReLU
- **Residual Blocks:** 3 sequential residual stages with skip connections:
  - Block 1: 32 -> 64 channels (stride 2)
  - Block 2: 64 -> 128 channels (stride 2)
  - Block 3: 128 -> 256 channels (stride 2)
- **Classifier:** Adaptive Average Pooling 1D + Linear layer mapping to 5 classes.
- **Accuracy:** ~97.94% test set accuracy on MIT-BIH dataset.

---

## 📜 License
This project is licensed under the [MIT License](LICENSE).
