import os
import time
import logging
from typing import Optional, Dict, Any

try:
    from dotenv import load_dotenv
    # Load .env from project root
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
except ImportError:
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CardioPulse.AWSSNS")

class AWSSNSAlertDispatcher:
    """
    Enterprise Alert Dispatcher for CardioPulse IoMT Pipeline.
    Publishes real-time arrhythmia notifications to an AWS SNS Topic (Email / SMS)
    with an intelligent per-patient cooldown engine to prevent alert fatigue.
    """
    def __init__(self, cooldown_seconds: int = 600):
        self.cooldown_seconds = int(os.getenv("ALERT_COOLDOWN_SECONDS", cooldown_seconds))
        self.last_alert_times: Dict[str, float] = {}
        
        self.aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_region = os.getenv("AWS_DEFAULT_REGION", "ap-south-1")
        raw_topic = os.getenv("AWS_SNS_TOPIC_ARN")
        if raw_topic:
            parts = raw_topic.strip().strip('"').strip("'").split(":")
            self.topic_arn = ":".join(parts[:6]) if len(parts) >= 6 else raw_topic
        else:
            self.topic_arn = None
        
        self.sns_client = None
        self._init_client()

    def _init_client(self):
        """Initializes boto3 SNS client if valid AWS credentials exist."""
        if self.aws_access_key and self.aws_secret_key and self.topic_arn:
            try:
                import boto3
                self.sns_client = boto3.client(
                    "sns",
                    aws_access_key_id=self.aws_access_key,
                    aws_secret_access_key=self.aws_secret_key,
                    region_name=self.aws_region
                )
                logger.info(f"[+] AWS SNS Alert Dispatcher initialized for Topic '{self.topic_arn}' ({self.aws_region})")
            except Exception as e:
                logger.warning(f"[-] Could not initialize boto3 SNS client: {e}. Running in simulation mode.")
                self.sns_client = None
        else:
            logger.info("[*] AWS SNS credentials or Topic ARN not configured. Running in local simulation mode.")
            self.sns_client = None

    def reload_config(self):
        """Reloads .env credentials on the fly without restarting services."""
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        if os.path.exists(env_path):
            try:
                from dotenv import load_dotenv
                load_dotenv(env_path, override=True)
            except ImportError:
                pass
        self.aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_region = os.getenv("AWS_DEFAULT_REGION", "ap-south-1")
        raw_topic = os.getenv("AWS_SNS_TOPIC_ARN")
        if raw_topic:
            parts = raw_topic.strip().strip('"').strip("'").split(":")
            self.topic_arn = ":".join(parts[:6]) if len(parts) >= 6 else raw_topic
        else:
            self.topic_arn = None
        self.cooldown_seconds = int(os.getenv("ALERT_COOLDOWN_SECONDS", 600))
        self._init_client()

    def should_suppress_alert(self, patient_id: str) -> bool:
        """Enforces a per-patient cooldown window to avoid spamming the doctor's inbox."""
        now = time.time()
        last_time = self.last_alert_times.get(patient_id, 0.0)
        elapsed = now - last_time
        if elapsed < self.cooldown_seconds:
            logger.info(f"[-] Alert for {patient_id} debounced ({int(self.cooldown_seconds - elapsed)}s remaining in cooldown)")
            return True
        return False

    def send_arrhythmia_alert(
        self,
        patient_id: str,
        prediction: str,
        heart_rate_bpm: int,
        confidence: float,
        ward: str = "Cardiac ICU",
        room: str = "Room 204",
        bed: str = "BED 02",
        device_id: str = "DEV-102",
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Dispatches a high-priority clinical cardiac emergency notification via AWS SNS.
        """
        if not force and self.should_suppress_alert(patient_id):
            return {
                "status": "debounced",
                "patient_id": patient_id,
                "message": f"Alert suppressed by cooldown ({self.cooldown_seconds}s limit)"
            }

        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S EST")
        subject = f"🚨 URGENT CARDIAC ALERT: Patient {patient_id} - {prediction} ({heart_rate_bpm} BPM)"
        
        # Max subject length for SNS is 100 characters
        if len(subject) > 100:
            subject = subject[:97] + "..."

        body = f"""METROHEALTH CENTRAL CARDIAC SURVEILLANCE — EMERGENCY ALERT
======================================================================
Hospital Unit:    MetroHealth Central Acute Telemetry Center
Alert Time:       {timestamp_str}
Alert Priority:   CRITICAL CARDIAC EMERGENCY

PATIENT DETAILS:
----------------
Patient ID:       {patient_id}
Ward Location:    {ward}
Room / Bed:       {room} • {bed}
Wearable IoMT:    {device_id} (125 Hz Lead-II Ingestion)

CLINICAL TRIAGE & AI DIAGNOSIS:
-------------------------------
AI Arrhythmia:    {prediction}
Heart Rate:       {heart_rate_bpm} BPM
1D-ResNet Conf:   {confidence * 100:.2f}% (Trained on MIT-BIH EC57 Dataset)
Cassandra Status: Ingested to table 'spark_streams.ecg_patient_alerts'

REQUIRED ACTIONS:
-----------------
1. Bedside Oscilloscope: http://localhost:8000/monitor/
2. Central Ward Triage:  http://localhost:8501
3. Dispatch Rapid Response or Cardiac Code Team if indicated.
======================================================================
Automated alert from CardioPulse Distributed Streaming Pipeline.
"""

        # Update last alert timestamp
        self.last_alert_times[patient_id] = time.time()

        if self.sns_client and self.topic_arn:
            try:
                response = self.sns_client.publish(
                    TopicArn=self.topic_arn,
                    Subject=subject,
                    Message=body
                )
                message_id = response.get("MessageId", "unknown")
                logger.info(f"[+] Successfully published AWS SNS alert for {patient_id} (Message ID: {message_id})")
                return {
                    "status": "published",
                    "patient_id": patient_id,
                    "message_id": message_id,
                    "channel": "AWS SNS Topic",
                    "timestamp": timestamp_str
                }
            except Exception as e:
                logger.error(f"[-] Failed to publish to AWS SNS: {e}")
                return {
                    "status": "error",
                    "patient_id": patient_id,
                    "error": str(e)
                }
        else:
            # Simulation / Dry-run fallback
            logger.info(f"[SIMULATED AWS SNS ALERT] Subject: {subject}")
            return {
                "status": "simulated",
                "patient_id": patient_id,
                "message": "Simulated AWS SNS alert dispatched (configure .env with AWS keys for live cloud delivery)",
                "timestamp": timestamp_str,
                "subject": subject
            }

# Singleton instance
alert_dispatcher = AWSSNSAlertDispatcher()
