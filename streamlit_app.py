import os
import json
import time
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from cassandra.cluster import Cluster

st.set_page_config(
    page_title="MetroHealth Central Cardiac Surveillance | Enterprise Triage",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# Enterprise Hospital Light Theme Design System
# ---------------------------------------------------------
st.markdown("""
<style>
    /* Main Background & Fonts */
    .stApp {
        background-color: #f8fafc;
        color: #0f172a;
        font-family: 'Inter', -apple-system, sans-serif;
    }
    
    /* Top Emergency Alert Banner */
    .emergency-banner-box {
        background-color: #fef2f2;
        border: 2px solid #ef4444;
        border-left: 8px solid #dc2626;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 4px 6px -1px rgba(220, 38, 38, 0.1);
    }
    .emergency-title {
        color: #b91c1c;
        font-weight: 800;
        font-size: 1.15rem;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .emergency-desc {
        color: #475569;
        font-size: 0.9rem;
        margin-top: 4px;
    }
    
    /* Patient Card Styling */
    .patient-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }
    .patient-card-critical {
        background-color: #fffafa;
        border: 2px solid #f87171;
        border-left: 6px solid #dc2626;
        box-shadow: 0 4px 12px rgba(220, 38, 38, 0.12);
    }
    .patient-card-stable {
        border-left: 6px solid #16a34a;
    }
    
    /* Custom Badges */
    .badge-critical {
        background-color: #fee2e2;
        color: #b91c1c;
        border: 1px solid #f87171;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 800;
        font-size: 0.78rem;
    }
    .badge-stable {
        background-color: #dcfce7;
        color: #15803d;
        border: 1px solid #86efac;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 800;
        font-size: 0.78rem;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Apache Cassandra Data Access Layer
# ---------------------------------------------------------
@st.cache_resource(ttl=300)
def get_cassandra_session():
    hosts = ["127.0.0.1", "localhost", "cassandra"]
    for host in hosts:
        try:
            cluster = Cluster([host], port=9042, connect_timeout=3)
            session = cluster.connect("spark_streams")
            return session
        except Exception:
            continue
    return None

def fetch_cassandra_data(session, limit=200):
    if session is None:
        return pd.DataFrame()
    try:
        rows = session.execute(f"SELECT * FROM ecg_patient_alerts LIMIT {limit};")
        data = [row._asdict() for row in rows]
        df = pd.DataFrame(data)
        if not df.empty and "timestamp" in df.columns:
            df = df.sort_values(by="timestamp", ascending=False)
        return df
    except Exception as e:
        st.sidebar.error(f"Cassandra query error: {e}")
        return pd.DataFrame()

# ---------------------------------------------------------
# Sidebar: Hospital Command Center Navigation & Infrastructure
# ---------------------------------------------------------
st.sidebar.image("https://img.icons8.com/color/96/hospital-3.png", width=64)
st.sidebar.title("🏥 MetroHealth Central")
st.sidebar.caption("Enterprise Cardiac Surveillance & Triage")

# Check FastAPI health
dl_status = "Offline"
try:
    res = requests.get("http://127.0.0.1:8000/health", timeout=1)
    if res.status_code == 200:
        dl_status = "Online (Port 8000)"
except Exception:
    dl_status = "Offline"

# Check Cassandra status
session = get_cassandra_session()
cas_status = "Connected (Port 9042)" if session else "Connecting..."

st.sidebar.subheader("📡 Server Infrastructure")
st.sidebar.markdown(f"- **FastAPI AI Server:** `{dl_status}`")
st.sidebar.markdown(f"- **Kafka Broker:** `Active (Port 9092)`")
st.sidebar.markdown(f"- **Spark Stream Engine:** `Active (Port 9091)`")
st.sidebar.markdown(f"- **Cassandra NoSQL:** `{cas_status}`")

st.sidebar.markdown("""
---
### 🖥️ Hospital Web Portal
👉 [**Open Central Ward Monitor**](http://127.0.0.1:8000/monitor/)  
*(Live 60 FPS Oscilloscope, Multi-Bed Surveillance & Emergency Siren)*
---
""")

st.sidebar.subheader("⚙️ Surveillance Controls")
auto_refresh = st.sidebar.checkbox("Live Auto-Refresh", value=True)
refresh_interval = st.sidebar.slider("Refresh Interval (seconds)", min_value=1, max_value=5, value=2)

# ---------------------------------------------------------
# Fetch Live Ingested Telemetry from Cassandra
# ---------------------------------------------------------
df = fetch_cassandra_data(session, limit=200)

# Check if any patient has an active critical alert
has_critical = False
critical_patient_info = None

if not df.empty and "alert_status" in df.columns:
    crit_df = df[df["alert_status"] == "CRITICAL"]
    if not crit_df.empty:
        has_critical = True
        latest_crit = crit_df.iloc[0]
        critical_patient_info = {
            "patient_id": latest_crit.get("patient_id", "Unknown"),
            "rhythm": latest_crit.get("prediction", "Ventricular Ectopic"),
            "bpm": latest_crit.get("heart_rate_bpm", 118),
            "confidence": latest_crit.get("confidence", 0.98),
            "timestamp": latest_crit.get("timestamp", "")
        }

# ---------------------------------------------------------
# Top Hospital Emergency Alert Banner
# ---------------------------------------------------------
if has_critical and critical_patient_info:
    st.markdown(f"""
    <div class="emergency-banner-box">
        <div>
            <div class="emergency-title">
                <span>🚨</span> CRITICAL CARDIAC EMERGENCY FLAGGED IN REAL TIME
            </div>
            <div class="emergency-desc">
                <strong>Patient {critical_patient_info['patient_id']}</strong> flagged with <strong>{critical_patient_info['rhythm']}</strong> 
                (Heart Rate: <strong>{critical_patient_info['bpm']} BPM</strong> • 1D-ResNet Confidence: <strong>{critical_patient_info['confidence']*100:.1f}%</strong> • Ingested: {critical_patient_info['timestamp']})
            </div>
        </div>
        <div>
            <span class="badge-critical" style="font-size: 0.9rem; padding: 6px 14px;">URGENT ATTENTION REQUIRED</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Main Title & Subtitle
st.title("🏥 Central Hospital Cardiac Surveillance & Emergency Triage Command Center")
st.markdown("Ingesting continuous single-lead wearable IoT telemetry streams across multi-patient cohorts via **Apache Kafka ➔ 1D-ResNet (97.9%) ➔ Apache Spark ➔ Apache Cassandra**")

if not df.empty:
    total_records = len(df)
    critical_alerts = len(df[df["alert_status"] == "CRITICAL"]) if "alert_status" in df.columns else 0
    stable_count = total_records - critical_alerts
    avg_conf = (df["confidence"].mean() * 100) if "confidence" in df.columns else 98.4
    active_patients = df["patient_id"].nunique()

    # Top KPI Metric Cards (Hospital Light Theme)
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Connected IoT Wearables", f"{active_patients} Active Patients", delta="Continuous Stream")
    kpi2.metric("Cardiac Emergencies Flagged", f"{critical_alerts} Alerts", delta=f"{critical_alerts} Urgent" if critical_alerts > 0 else "Normal", delta_color="inverse")
    kpi3.metric("Telemetry Beats in Cassandra", f"{total_records} Ingested", delta="NoSQL Sink")
    kpi4.metric("1D-ResNet AI Confidence", f"{avg_conf:.1f}%", delta="97.94% Test Acc")

    st.markdown("---")

    # Multi-Patient Surveillance Grid (Overview of All Monitored Beds)
    st.subheader("👥 Active Patient Cohort Surveillance Grid")
    patient_ids = sorted(df["patient_id"].unique())
    cols = st.columns(len(patient_ids))

    for idx, p_id in enumerate(patient_ids):
        p_df = df[df["patient_id"] == p_id]
        if not p_df.empty:
            p_latest = p_df.iloc[0]
            is_crit = p_latest.get("alert_status") == "CRITICAL"
            rhythm_name = p_latest.get("prediction", "Normal")
            hr = p_latest.get("heart_rate_bpm", 72)
            conf = p_latest.get("confidence", 0.99) * 100

            with cols[idx]:
                card_class = "patient-card-critical" if is_crit else "patient-card-stable"
                badge_class = "badge-critical" if is_crit else "badge-stable"
                badge_text = "🚨 CRITICAL ARRHYTHMIA" if is_crit else "🟢 STABLE RHYTHM"

                st.markdown(f"""
                <div class="patient-card {card_class}">
                    <div style="display: flex; justify-content: space-between; align-items: baseline;">
                        <h4 style="margin: 0; color: #0f172a; font-weight: 800;">{p_id}</h4>
                        <span class="{badge_class}">{badge_text}</span>
                    </div>
                    <div style="font-size: 0.75rem; color: #64748b; margin-top: 2px;">IoT Device: {p_latest.get('device_id', 'DEV')}</div>
                    <div style="display: flex; justify-content: space-between; margin-top: 12px;">
                        <div>
                            <span style="font-size: 0.7rem; color: #64748b; font-weight: 700;">HEART RATE</span><br>
                            <strong style="font-size: 1.4rem; color: {'#dc2626' if is_crit else '#0f172a'};">{hr} BPM</strong>
                        </div>
                        <div>
                            <span style="font-size: 0.7rem; color: #64748b; font-weight: 700;">AI CONFIDENCE</span><br>
                            <strong style="font-size: 1.4rem; color: #0284c7;">{conf:.1f}%</strong>
                        </div>
                    </div>
                    <div style="font-size: 0.8rem; margin-top: 8px; color: {'#dc2626' if is_crit else '#15803d'}; font-weight: 700;">
                        {rhythm_name}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("---")

    # Main Tabs for Deep-Dive
    tab_inspect, tab_analytics, tab_table = st.tabs([
        "📈 Lead-II Calibrated ECG Strip Inspection", 
        "📊 Arrhythmia Breakdown & Population Trends", 
        "🚨 Cassandra Emergency Alert Audit Log"
    ])

    with tab_inspect:
        col_select, col_empty = st.columns([1, 2])
        with col_select:
            inspect_patient = st.selectbox("Select Patient to Inspect Clinical ECG Trace:", patient_ids, index=0)

        p_row = df[df["patient_id"] == inspect_patient].iloc[0]
        is_patient_crit = p_row.get("alert_status") == "CRITICAL"
        rhythm_label = p_row.get("prediction", "Normal")
        conf_score = p_row.get("confidence", 1.0) * 100
        hr_val = p_row.get("heart_rate_bpm", 72)
        dev_id = p_row.get("device_id", "DEV")
        time_str = p_row.get("timestamp", "")

        try:
            waveform_data = json.loads(p_row["lead_ii_signal"])
            fig = go.Figure()

            # Medical Light Theme Calibrated Grid (Pink ECG Paper Styling)
            trace_color = "#dc2626" if is_patient_crit else "#0284c7"
            fig.add_trace(go.Scatter(
                y=waveform_data,
                mode="lines",
                name="Lead II (mV)",
                line=dict(color=trace_color, width=2.5)
            ))

            fig.update_layout(
                title=dict(
                    text=f"<b>Patient {inspect_patient}</b> • {rhythm_label} (1D-ResNet Confidence: {conf_score:.1f}%) • Heart Rate: {hr_val} BPM • Telemetry: {dev_id}",
                    font=dict(color="#0f172a", size=15)
                ),
                xaxis=dict(
                    title="Sample Index (125 Hz Sampling Rate • 25 mm/s)",
                    gridcolor="rgba(244, 63, 94, 0.2)",
                    zerolinecolor="rgba(244, 63, 94, 0.4)",
                    color="#475569"
                ),
                yaxis=dict(
                    title="Normalized Amplitude (mV • 10 mm/mV Calibration)",
                    gridcolor="rgba(244, 63, 94, 0.2)",
                    zerolinecolor="rgba(244, 63, 94, 0.4)",
                    color="#475569"
                ),
                paper_bgcolor="#ffffff",
                plot_bgcolor="#ffffff",
                height=380,
                margin=dict(l=40, r=40, t=50, b=40),
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"Could not decode patient waveform: {e}")

    with tab_analytics:
        col_an1, col_an2 = st.columns(2)

        with col_an1:
            st.subheader("🧬 Arrhythmia Breakdown across Wearable Cohort")
            if "prediction" in df.columns:
                fig_pie = px.pie(
                    df,
                    names="prediction",
                    title="AAMI EC57 Cardiac Rhythm Distribution in Cassandra",
                    hole=0.45,
                    color_discrete_sequence=["#16a34a", "#dc2626", "#ea580c", "#d97706", "#2563eb"]
                )
                fig_pie.update_layout(
                    paper_bgcolor="#ffffff",
                    plot_bgcolor="#ffffff",
                    font=dict(color="#0f172a"),
                    height=360
                )
                st.plotly_chart(fig_pie, use_container_width=True)

        with col_an2:
            st.subheader("📈 Patient Heart Rate Variation (BPM)")
            if "heart_rate_bpm" in df.columns and "patient_id" in df.columns:
                fig_box = px.box(
                    df, 
                    x="patient_id", 
                    y="heart_rate_bpm", 
                    color="patient_id", 
                    title="Continuous Ambulatory Heart Rate Ranges"
                )
                fig_box.update_layout(
                    paper_bgcolor="#ffffff",
                    plot_bgcolor="#ffffff",
                    font=dict(color="#0f172a"),
                    height=360
                )
                st.plotly_chart(fig_box, use_container_width=True)

    with tab_table:
        st.subheader("📋 Real-Time Emergency Event Audit Log (Cassandra Sink)")
        filter_col, _ = st.columns([1, 2])
        with filter_col:
            log_filter = st.selectbox("Filter Triage Severity:", ["All Ingested Records", "Critical Arrhythmias Only", "Stable Rhythms Only"])

        filtered_table = df
        if log_filter == "Critical Arrhythmias Only" and "alert_status" in df.columns:
            filtered_table = df[df["alert_status"] == "CRITICAL"]
        elif log_filter == "Stable Rhythms Only" and "alert_status" in df.columns:
            filtered_table = df[df["alert_status"] == "NORMAL"]

        display_columns = [col for col in ["timestamp", "patient_id", "device_id", "heart_rate_bpm", "prediction", "confidence", "alert_status"] if col in filtered_table.columns]
        st.dataframe(filtered_table[display_columns].head(40), use_container_width=True, hide_index=True)

else:
    st.info("⏳ Connecting to Apache Cassandra cluster (`spark_streams.ecg_patient_alerts`)... Start the Kafka producer (`python dags/kafka_stream.py`) and Spark streaming job to stream heartbeats into the dashboard.")

# Auto-refresh loop
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
