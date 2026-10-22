/**
 * METROHEALTH CENTRAL CARDIAC SURVEILLANCE - LIGHT THEME
 * Real-time Multi-Patient Ingestion, Emergency Alert Broadcast & 1D-ResNet Clinical Triage
 */

// -------------------------------------------------------------
// Patients State Registry
// -------------------------------------------------------------
const patientsData = {
    "PAT-101": {
        id: "PAT-101",
        bed: "BED 01",
        room: "Room 101",
        ward: "Ward West",
        device: "DEV-101",
        heartRate: 72,
        rhythm: "Normal Beat (N)",
        aami: "Class N (0)",
        confidence: 0.994,
        status: "NORMAL",
        waveform: [],
        sweepX: 0,
        lastX: 0,
        lastY: 0,
        sampleIdx: 0
    },
    "PAT-102": {
        id: "PAT-102",
        bed: "BED 02 • CCU",
        room: "Room 204",
        ward: "Cardiac ICU",
        device: "DEV-102",
        heartRate: 118,
        rhythm: "Ventricular Ectopic (V)",
        aami: "Class V (2)",
        confidence: 0.982,
        status: "CRITICAL",
        waveform: [],
        sweepX: 0,
        lastX: 0,
        lastY: 0,
        sampleIdx: 0
    },
    "PAT-103": {
        id: "PAT-103",
        bed: "BED 03",
        room: "Room 108",
        ward: "Telemetry Ward",
        device: "DEV-103",
        heartRate: 78,
        rhythm: "Normal Beat (N)",
        aami: "Class N (0)",
        confidence: 0.991,
        status: "NORMAL",
        waveform: [],
        sweepX: 0,
        lastX: 0,
        lastY: 0,
        sampleIdx: 0
    },
    "PAT-104": {
        id: "PAT-104",
        bed: "BED 04",
        room: "Room 112",
        ward: "Stepdown Ward",
        device: "DEV-104",
        heartRate: 68,
        rhythm: "Normal Beat (N)",
        aami: "Class N (0)",
        confidence: 0.997,
        status: "NORMAL",
        waveform: [],
        sweepX: 0,
        lastX: 0,
        lastY: 0,
        sampleIdx: 0
    }
};

const appState = {
    soundMuted: false,
    activeFilter: "all",
    modalPatient: "PAT-102",
    auditCount: 0,
    activeEmergency: true
};

// -------------------------------------------------------------
// Web Audio Alert Chime (Hospital Medical Tone)
// -------------------------------------------------------------
class HospitalAudioAlerts {
    constructor() {
        this.ctx = null;
    }

    init() {
        if (!this.ctx) {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            this.ctx = new AudioContext();
        }
        if (this.ctx.state === "suspended") {
            this.ctx.resume();
        }
    }

    playEmergencyChime() {
        if (appState.soundMuted) return;
        this.init();
        if (!this.ctx) return;

        try {
            const now = this.ctx.currentTime;
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();

            // Urgent two-tone hospital emergency chime (960 Hz -> 720 Hz)
            osc.type = "sine";
            osc.frequency.setValueAtTime(960, now);
            osc.frequency.setValueAtTime(720, now + 0.15);

            gain.gain.setValueAtTime(0.15, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);

            osc.connect(gain);
            gain.connect(this.ctx.destination);
            osc.start(now);
            osc.stop(now + 0.35);
        } catch (e) {
            console.warn("Audio error:", e);
        }
    }
}

const hospitalAudio = new HospitalAudioAlerts();

// -------------------------------------------------------------
// Waveform Generators (MIT-BIH Shapes)
// -------------------------------------------------------------
function generateBeat(type = "normal") {
    const samples = 187;
    const wave = new Array(samples).fill(0);

    if (type === "pvc") {
        for (let i = 0; i < samples; i++) {
            const t = i / samples;
            const deepS = -1.15 * Math.exp(-Math.pow((t - 0.35) / 0.05, 2));
            const wideT = 0.45 * Math.exp(-Math.pow((t - 0.65) / 0.12, 2));
            wave[i] = deepS + wideT + (Math.random() - 0.5) * 0.02;
        }
    } else {
        for (let i = 0; i < samples; i++) {
            const t = i / samples;
            const p = 0.15 * Math.exp(-Math.pow((t - 0.18) / 0.03, 2));
            const q = -0.15 * Math.exp(-Math.pow((t - 0.28) / 0.015, 2));
            const r = 1.15 * Math.exp(-Math.pow((t - 0.32) / 0.015, 2));
            const s = -0.3 * Math.exp(-Math.pow((t - 0.36) / 0.02, 2));
            const twave = 0.28 * Math.exp(-Math.pow((t - 0.6) / 0.07, 2));
            wave[i] = p + q + r + s + twave + (Math.random() - 0.5) * 0.02;
        }
    }
    return wave;
}

// Initialize waveforms
Object.keys(patientsData).forEach(pId => {
    patientsData[pId].waveform = generateBeat(pId === "PAT-102" ? "pvc" : "normal");
});

// -------------------------------------------------------------
// Tile Canvas Oscilloscope Strip Renderer
// -------------------------------------------------------------
class TileStripRenderer {
    constructor(canvasId, patientId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext("2d");
        this.patientId = patientId;
        this.resize();
    }

    resize() {
        if (!this.canvas) return;
        const rect = this.canvas.parentElement.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        this.width = rect.width;
        this.height = rect.height;
        this.canvas.width = this.width * dpr;
        this.canvas.height = this.height * dpr;
        this.ctx.scale(dpr, dpr);
        this.midY = this.height * 0.58;
        this.yScale = this.height * 0.4;
        this.drawMedicalGrid();
    }

    drawMedicalGrid() {
        this.ctx.fillStyle = "#ffffff";
        this.ctx.fillRect(0, 0, this.width, this.height);

        // Standard medical ECG grid (subtle clinical pink / warm grey grid)
        const step = 8;
        this.ctx.lineWidth = 0.5;
        this.ctx.strokeStyle = "rgba(244, 63, 94, 0.12)";
        this.ctx.beginPath();
        for (let x = 0; x < this.width; x += step) {
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, this.height);
        }
        for (let y = 0; y < this.height; y += step) {
            this.ctx.moveTo(0, y);
            this.ctx.lineTo(this.width, y);
        }
        this.ctx.stroke();

        // Major grid (5mm ~ 40px)
        const major = 40;
        this.ctx.lineWidth = 1;
        this.ctx.strokeStyle = "rgba(244, 63, 94, 0.28)";
        this.ctx.beginPath();
        for (let x = 0; x < this.width; x += major) {
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, this.height);
        }
        for (let y = 0; y < this.height; y += major) {
            this.ctx.moveTo(0, y);
            this.ctx.lineTo(this.width, y);
        }
        this.ctx.stroke();
    }

    clearBar(x, w = 18) {
        this.ctx.save();
        this.ctx.beginPath();
        this.ctx.rect(x, 0, w, this.height);
        this.ctx.fillStyle = "#ffffff";
        this.ctx.fill();

        // Redraw minor grid
        const step = 8;
        const major = 40;
        this.ctx.lineWidth = 0.5;
        this.ctx.strokeStyle = "rgba(244, 63, 94, 0.12)";
        this.ctx.beginPath();
        const startX = Math.floor(x / step) * step;
        for (let gx = startX; gx < x + w; gx += step) {
            this.ctx.moveTo(gx, 0);
            this.ctx.lineTo(gx, this.height);
        }
        this.ctx.stroke();

        // Redraw major grid
        this.ctx.lineWidth = 1;
        this.ctx.strokeStyle = "rgba(244, 63, 94, 0.28)";
        this.ctx.beginPath();
        const startMaj = Math.floor(x / major) * major;
        for (let gx = startMaj; gx < x + w; gx += major) {
            this.ctx.moveTo(gx, 0);
            this.ctx.lineTo(gx, this.height);
        }
        this.ctx.stroke();

        // Horizontal grid
        this.ctx.lineWidth = 0.5;
        this.ctx.strokeStyle = "rgba(244, 63, 94, 0.12)";
        this.ctx.beginPath();
        for (let y = 0; y < this.height; y += step) {
            this.ctx.moveTo(x, y);
            this.ctx.lineTo(x + w, y);
        }
        this.ctx.stroke();
        this.ctx.restore();
    }

    drawStep() {
        const p = patientsData[this.patientId];
        if (!p) return;

        const pts = 2;
        for (let i = 0; i < pts; i++) {
            const sample = p.waveform[p.sampleIdx] || 0;
            const nextY = this.midY - sample * this.yScale;
            const nextX = p.sweepX;

            this.clearBar(p.sweepX, 16);

            if (p.lastX < nextX) {
                this.ctx.beginPath();
                this.ctx.moveTo(p.lastX, p.lastY);
                this.ctx.lineTo(nextX, nextY);

                if (p.status === "CRITICAL") {
                    this.ctx.strokeStyle = "#dc2626"; // Emergency red
                    this.ctx.lineWidth = 2.2;
                } else {
                    this.ctx.strokeStyle = "#0284c7"; // Clean clinical blue
                    this.ctx.lineWidth = 1.8;
                }

                this.ctx.stroke();
            }

            p.lastX = nextX;
            p.lastY = nextY;
            p.sweepX += 1.4;

            p.sampleIdx++;
            if (p.sampleIdx >= p.waveform.length) {
                p.sampleIdx = 0;
                // Periodic simulated pulse event
                onPatientCycleComplete(this.patientId);
            }

            if (p.sweepX >= this.width) {
                p.sweepX = 0;
                p.lastX = 0;
            }
        }
    }
}

const renderers = {};

// -------------------------------------------------------------
// Real-time Event Handling
// -------------------------------------------------------------
function onPatientCycleComplete(patientId) {
    const p = patientsData[patientId];
    if (!p) return;

    // Slight physiological jitter in heart rate
    if (p.status === "CRITICAL") {
        p.heartRate = Math.min(130, Math.max(105, p.heartRate + (Math.random() > 0.5 ? 2 : -2)));
        hospitalAudio.playEmergencyChime();
    } else {
        p.heartRate = Math.min(84, Math.max(64, p.heartRate + (Math.random() > 0.5 ? 1 : -1)));
    }

    const hrEl = document.getElementById(`hr-${patientId}`);
    if (hrEl) hrEl.innerText = p.heartRate;

    // If PAT-102, maintain emergency state and log event
    if (p.status === "CRITICAL") {
        checkAndShowEmergencyBanner(patientId);
    }
}

function checkAndShowEmergencyBanner(patientId) {
    const p = patientsData[patientId];
    const banner = document.getElementById("emergencyBanner");
    const pText = document.getElementById("emergencyPatientText");
    const diagText = document.getElementById("emergencyDiagnosisText");

    pText.innerText = `PATIENT ${p.id} (${p.ward} • ${p.room} • ${p.bed})`;
    diagText.innerText = `— Flagged ${p.rhythm} (${p.heartRate} BPM, ${(p.confidence * 100).toFixed(1)}% Confidence)`;
    banner.style.display = "flex";

    // Add row to audit log table if not already added recently
    if (Math.random() < 0.3) {
        addAuditLogRow(p);
    }
}

function addAuditLogRow(patient) {
    const tbody = document.getElementById("auditTableBody");
    if (!tbody) return;

    appState.auditCount++;
    document.getElementById("auditCountBadge").innerText = `${appState.auditCount} Events Recorded`;

    const tr = document.createElement("tr");
    const isCrit = patient.status === "CRITICAL";
    if (isCrit) tr.className = "row-critical";

    const now = new Date().toTimeString().split(" ")[0];

    tr.innerHTML = `
        <td><strong>${now}</strong></td>
        <td><strong>${patient.id}</strong></td>
        <td>${patient.ward} • ${patient.room}</td>
        <td><code>${patient.device}</code></td>
        <td><strong>${patient.heartRate} BPM</strong></td>
        <td>${patient.rhythm}</td>
        <td><span class="badge-tag ${isCrit ? 'tag-critical' : 'tag-stable'}">${isCrit ? '🚨 CRITICAL' : '🟢 STABLE'}</span></td>
        <td><button class="btn-inspect" onclick="openPatientModal('${patient.id}')">REVIEW</button></td>
    `;

    tbody.insertBefore(tr, tbody.firstChild);

    if (tbody.children.length > 25) {
        tbody.removeChild(tbody.lastChild);
    }
}

// -------------------------------------------------------------
// Interactive Triage Controls
// -------------------------------------------------------------
function filterPatientCards(filter) {
    appState.activeFilter = filter;
    document.querySelectorAll(".filter-pill").forEach(btn => {
        btn.classList.toggle("active", btn.getAttribute("data-filter") === filter);
    });

    Object.keys(patientsData).forEach(pId => {
        const card = document.getElementById(`card-${pId}`);
        const p = patientsData[pId];

        if (filter === "all") {
            card.style.display = "flex";
        } else if (filter === "critical") {
            card.style.display = p.status === "CRITICAL" ? "flex" : "none";
        } else if (filter === "stable") {
            card.style.display = p.status === "NORMAL" ? "flex" : "none";
        }
    });
}

function simulatePvcAlert() {
    const p102 = patientsData["PAT-102"];
    p102.status = "CRITICAL";
    p102.rhythm = "Ventricular Ectopic (V)";
    p102.aami = "Class V (2)";
    p102.heartRate = 124;
    p102.confidence = 0.988;
    p102.waveform = generateBeat("pvc");

    const card = document.getElementById("card-PAT-102");
    card.className = "patient-tile card-critical";
    
    const chip = document.getElementById("chip-PAT-102");
    chip.className = "status-chip chip-critical";
    chip.innerHTML = '<span class="chip-dot"></span><span class="chip-text">VENTRICULAR ECTOPIC</span>';

    document.getElementById("hr-PAT-102").innerText = p102.heartRate;
    document.getElementById("hr-PAT-102").className = "vital-num red-text";

    checkAndShowEmergencyBanner("PAT-102");
    hospitalAudio.playEmergencyChime();
    addAuditLogRow(p102);

    // Scroll smoothly to top banner
    window.scrollTo({ top: 0, behavior: "smooth" });
}

// -------------------------------------------------------------
// Patient Deep-Dive Modal Logic
// -------------------------------------------------------------
let modalCanvasRenderer = null;

function openPatientModal(patientId) {
    appState.modalPatient = patientId;
    const p = patientsData[patientId];
    if (!p) return;

    const modal = document.getElementById("patientModal");
    modal.style.display = "flex";

    document.getElementById("modalPatientTitle").innerText = `PATIENT ${p.id} — CLINICAL TELEMETRY DEEP-DIVE`;
    document.getElementById("modalPatientSubtitle").innerText = `${p.ward} • ${p.room} • ${p.bed} • IoT Sensor ${p.device}`;
    document.getElementById("modalRhythmTag").innerText = p.rhythm;
    document.getElementById("modalRhythmTag").className = p.status === "CRITICAL" ? "rhythm-tag" : "rhythm-tag green-sub";
    
    document.getElementById("modalPrediction").innerText = p.rhythm;
    document.getElementById("modalAamiClass").innerText = p.aami;
    document.getElementById("modalConfidence").innerText = `${(p.confidence * 100).toFixed(2)}%`;
    document.getElementById("modalHeartRate").innerText = `${p.heartRate} BPM`;

    // Render large calibrated modal canvas
    renderModalCalibratedStrip(p);
}

function closePatientModal() {
    const modal = document.getElementById("patientModal");
    modal.style.display = "none";
}

function renderModalCalibratedStrip(p) {
    const canvas = document.getElementById("modalCanvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const rect = canvas.parentElement.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;

    canvas.width = rect.width * dpr;
    canvas.height = 180 * dpr;
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = 180;
    const midY = h * 0.58;
    const yScale = h * 0.42;

    // Fill white
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, w, h);

    // Minor pink grid
    ctx.lineWidth = 0.5;
    ctx.strokeStyle = "rgba(244, 63, 94, 0.15)";
    ctx.beginPath();
    for (let x = 0; x < w; x += 10) { ctx.moveTo(x, 0); ctx.lineTo(x, h); }
    for (let y = 0; y < h; y += 10) { ctx.moveTo(0, y); ctx.lineTo(w, y); }
    ctx.stroke();

    // Major pink grid
    ctx.lineWidth = 1;
    ctx.strokeStyle = "rgba(244, 63, 94, 0.35)";
    ctx.beginPath();
    for (let x = 0; x < w; x += 50) { ctx.moveTo(x, 0); ctx.lineTo(x, h); }
    for (let y = 0; y < h; y += 50) { ctx.moveTo(0, y); ctx.lineTo(w, y); }
    ctx.stroke();

    // Draw 3 full cycles of the patient's lead-II waveform
    const fullWave = [...p.waveform, ...p.waveform, ...p.waveform];
    ctx.beginPath();
    ctx.strokeStyle = p.status === "CRITICAL" ? "#dc2626" : "#0284c7";
    ctx.lineWidth = 2.2;

    for (let i = 0; i < fullWave.length; i++) {
        const x = (i / fullWave.length) * w;
        const y = midY - fullWave[i] * yScale;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    }
    ctx.stroke();
}

function triggerCodeBlueAction() {
    alert(`🚨 CODE BLUE / RAPID RESPONSE DISPATCHED!\nEmergency Medical Team alerted for Patient ${appState.modalPatient} (${patientsData[appState.modalPatient].room}).`);
    closePatientModal();
}

// -------------------------------------------------------------
// App Initialization
// -------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
    // Initialize renderers for each patient tile
    Object.keys(patientsData).forEach(pId => {
        renderers[pId] = new TileStripRenderer(`canvas-${pId}`, pId);
    });

    // Main animation loop across all patient tiles
    function animationLoop() {
        Object.keys(renderers).forEach(pId => {
            renderers[pId].drawStep();
        });
        requestAnimationFrame(animationLoop);
    }
    requestAnimationFrame(animationLoop);

    // ---------------------------------------------------------
    // Real-Time Docker Cassandra Pipeline Polling
    // ---------------------------------------------------------
    async function pollLiveCassandraTelemetry() {
        try {
            const res = await fetch("/api/telemetry?limit=50");
            if (!res.ok) return;
            const data = await res.json();
            if (data.status !== "connected") return;

            // 1. Update status pill
            const statusEl = document.querySelector(".network-badge span:last-child");
            if (statusEl && data.stats) {
                statusEl.innerText = `IOT STREAM ACTIVE • ${data.stats.total_records} BEATS IN CASSANDRA`;
            }

            // 2. Update KPI metrics
            const kpiActive = document.getElementById("kpiActiveDevices");
            const kpiStable = document.getElementById("kpiStableCount");
            const kpiCrit = document.getElementById("kpiCriticalCount");
            if (kpiActive && data.stats) kpiActive.innerText = `${data.stats.connected_devices || 4} Devices`;
            if (kpiStable && data.stats) kpiStable.innerText = `${data.stats.stable_count} Patients`;
            if (kpiCrit && data.stats) kpiCrit.innerText = `${data.stats.critical_count} Emergency`;

            // 3. Update Patient Cards with real Cassandra data
            if (data.patients) {
                Object.keys(data.patients).forEach(pId => {
                    const rec = data.patients[pId];
                    if (!patientsData[pId]) return;

                    const p = patientsData[pId];
                    p.heartRate = rec.heart_rate_bpm || p.heartRate;
                    p.rhythm = rec.prediction || p.rhythm;
                    p.confidence = rec.confidence || p.confidence;
                    p.status = rec.alert_status || "NORMAL";
                    p.aami = `Class ${rec.prediction ? rec.prediction.charAt(0) : 'N'} (${rec.class_id || 0})`;

                    if (Array.isArray(rec.lead_ii_signal) && rec.lead_ii_signal.length > 50) {
                        p.waveform = rec.lead_ii_signal;
                    }

                    const hrEl = document.getElementById(`hr-${pId}`);
                    if (hrEl) hrEl.innerText = p.heartRate;

                    const confEl = document.getElementById(`conf-${pId}`);
                    if (confEl) confEl.innerText = `${(p.confidence * 100).toFixed(1)}%`;

                    const aamiEl = document.getElementById(`aami-${pId}`);
                    if (aamiEl) aamiEl.innerText = p.aami;

                    const badgeEl = document.getElementById(`badge-${pId}`);
                    const tileEl = document.getElementById(`tile-${pId}`);
                    const actionBtn = document.getElementById(`action-${pId}`);

                    if (p.status === "CRITICAL") {
                        if (badgeEl) {
                            badgeEl.className = "tile-badge badge-critical";
                            badgeEl.innerText = `● ${p.rhythm.toUpperCase()}`;
                        }
                        if (tileEl) tileEl.classList.add("tile-critical");
                        if (actionBtn) {
                            actionBtn.className = "btn-emergency";
                            actionBtn.innerText = "EMERGENCY REVIEW";
                        }
                    } else {
                        if (badgeEl) {
                            badgeEl.className = "tile-badge badge-stable";
                            badgeEl.innerText = `● ${p.rhythm.toUpperCase()}`;
                        }
                        if (tileEl) tileEl.classList.remove("tile-critical");
                        if (actionBtn) {
                            actionBtn.className = "btn-inspect";
                            actionBtn.innerText = "INSPECT ECG STRIP";
                        }
                    }
                });
            }

            // 4. Update Emergency Broadcast Banner
            const banner = document.getElementById("emergencyBanner");
            if (data.has_critical && data.latest_critical) {
                const lc = data.latest_critical;
                const pText = document.getElementById("emergencyPatientText");
                const diagText = document.getElementById("emergencyDiagnosisText");
                if (pText) pText.innerText = `PATIENT ${lc.patient_id} (Cardiac ICU • Room 204 • BED 02 • CCU)`;
                if (diagText) diagText.innerText = `— Flagged ${lc.prediction} (${lc.heart_rate_bpm} BPM, ${(lc.confidence * 100).toFixed(1)}% Confidence)`;
                if (banner && !appState.bannerAcknowledged) banner.style.display = "flex";
            } else if (!data.has_critical) {
                if (banner) banner.style.display = "none";
            }

            // 5. Update Audit Log Table from Cassandra
            if (Array.isArray(data.audit_log) && data.audit_log.length > 0) {
                renderAuditLogFromCassandra(data.audit_log);
            }
        } catch (e) {
            console.warn("Cassandra telemetry poll:", e);
        }
    }

    function renderAuditLogFromCassandra(records) {
        const tbody = document.getElementById("auditTableBody");
        if (!tbody) return;

        tbody.innerHTML = "";
        appState.auditCount = records.length;
        const badge = document.getElementById("auditCountBadge");
        if (badge) badge.innerText = `${records.length} Events Recorded`;

        records.forEach(rec => {
            const tr = document.createElement("tr");
            const isCrit = rec.alert_status === "CRITICAL";
            if (isCrit) tr.className = "row-critical";

            const p = patientsData[rec.patient_id] || { ward: "Ward West", room: "Room 101" };
            const timeStr = (rec.timestamp || "").split(" ")[1] || rec.timestamp || "Now";

            tr.innerHTML = `
                <td><strong>${timeStr}</strong></td>
                <td><strong>${rec.patient_id}</strong></td>
                <td>${p.ward} • ${p.room}</td>
                <td><code>${rec.device_id || 'DEV-101'}</code></td>
                <td><strong>${rec.heart_rate_bpm} BPM</strong></td>
                <td>${rec.prediction}</td>
                <td><span class="badge-tag ${isCrit ? 'tag-critical' : 'tag-stable'}">${isCrit ? '🚨 CRITICAL' : '🟢 STABLE'}</span></td>
                <td><button class="btn-inspect" onclick="openPatientModal('${rec.patient_id}')">REVIEW</button></td>
            `;
            tbody.appendChild(tr);
        });
    }

    // Run first telemetry poll immediately and then every 1.5 seconds
    pollLiveCassandraTelemetry();
    setInterval(pollLiveCassandraTelemetry, 1500);

    // Live clock
    setInterval(() => {
        const d = new Date();
        const timeStr = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        document.getElementById("hospitalClock").innerText = `${timeStr} EST`;
    }, 1000);

    // Filter pills
    document.querySelectorAll(".filter-pill").forEach(btn => {
        btn.addEventListener("click", () => {
            filterPatientCards(btn.getAttribute("data-filter"));
        });
    });

    // Sound toggle button
    const soundBtn = document.getElementById("soundToggleBtn");
    soundBtn.addEventListener("click", () => {
        appState.soundMuted = !appState.soundMuted;
        if (appState.soundMuted) {
            document.getElementById("soundIcon").innerText = "🔕";
            document.getElementById("soundLabel").innerText = "MUTED";
        } else {
            document.getElementById("soundIcon").innerText = "🔔";
            document.getElementById("soundLabel").innerText = "ALERTS ON";
            hospitalAudio.init();
        }
    });

    // Silence alert button
    document.getElementById("silenceAlertBtn").addEventListener("click", () => {
        document.getElementById("emergencyBanner").style.display = "none";
    });

    // Dispatch team button
    document.getElementById("dispatchTeamBtn").addEventListener("click", () => {
        alert("🚨 Emergency Cardiac Code Team has been dispatched to Room 204 (Bed 02)!");
        document.getElementById("emergencyBanner").style.display = "none";
    });

    // Test simulate PVC button
    document.getElementById("simPvcBtn").addEventListener("click", simulatePvcAlert);

    // Clear log view
    document.getElementById("clearAuditBtn").addEventListener("click", () => {
        document.getElementById("auditTableBody").innerHTML = "";
        appState.auditCount = 0;
        document.getElementById("auditCountBadge").innerText = "0 Events";
    });

    // Handle window resize for strip canvases
    window.addEventListener("resize", () => {
        Object.keys(renderers).forEach(pId => {
            renderers[pId].resize();
        });
    });
});
