-- Keyspace for ECG real-time streaming
CREATE KEYSPACE IF NOT EXISTS spark_streams
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

-- Real-time wearable patient alerts & telemetry sink
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
