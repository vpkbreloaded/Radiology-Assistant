"""
AI-Powered Professional Radiology Reporting Assistant
Version 6.3 - Web-based Voice Input & Modern UI
"""

import streamlit as st
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import re
import json
import os
import datetime
import hashlib
import pandas as pd
from collections import defaultdict
import tempfile
from pathlib import Path

# ===== OPTIONAL IMPORTS WITH FALLBACKS =====
PLOTLY_AVAILABLE = False
try:
    import plotly.graph_objects as go
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    pass

DICOM_AVAILABLE = False
try:
    import pydicom
    from pydicom.errors import InvalidDicomError
    DICOM_AVAILABLE = True
except ImportError:
    pass

# ===== CONFIGURATION =====
CONFIG_FILE = "radiology_config.json"
HISTORY_FILE = "report_history.json"
TEMPLATES_FILE = "saved_templates.json"
UPLOADED_TEMPLATES_DIR = "uploaded_templates"
EXPORT_DIR = "exported_reports"
AUDIT_LOG_FILE = "audit_logs.json"

os.makedirs(UPLOADED_TEMPLATES_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)

# ===== DIFFERENTIAL DIAGNOSIS DATABASE =====
DIFFERENTIAL_DATABASE = {
    "brain_lesion_enhancing": [
        {"diagnosis": "Meningioma", "confidence": "High", "features": "Dural-based, homogeneous enhancement", "modality": "MRI", "urgency": "Non-urgent"},
        {"diagnosis": "Metastasis", "confidence": "High", "features": "Multiple, at gray-white junction", "modality": "MRI", "urgency": "Urgent"},
        {"diagnosis": "Glioblastoma", "confidence": "Medium", "features": "Irregular rim enhancement", "modality": "MRI", "urgency": "Urgent"}
    ],
    "white_matter": [
        {"diagnosis": "Microvascular ischemia", "confidence": "High", "features": "Periventricular, punctate", "modality": "MRI", "urgency": "Non-urgent"},
        {"diagnosis": "Multiple Sclerosis", "confidence": "Medium", "features": "Ovoid, perivenular", "modality": "MRI", "urgency": "Non-urgent"}
    ],
    "stroke": [
        {"diagnosis": "Ischemic infarct", "confidence": "High", "features": "Vascular territory, DWI bright", "modality": "MRI/CT", "urgency": "Urgent"},
        {"diagnosis": "Venous infarct", "confidence": "Medium", "features": "Hemorrhagic, non-arterial", "modality": "MRI/CT", "urgency": "Urgent"}
    ],
    "spinal_lesion": [
        {"diagnosis": "Disc herniation", "confidence": "High", "features": "Disc material extrusion", "modality": "MRI", "urgency": "Non-urgent"},
        {"diagnosis": "Metastasis", "confidence": "Medium", "features": "Vertebral body destruction", "modality": "MRI", "urgency": "Urgent"}
    ],
    "lung_nodule": [
        {"diagnosis": "Primary lung cancer", "confidence": "Medium", "features": "Spiculated, >2cm", "modality": "CT", "urgency": "Urgent"},
        {"diagnosis": "Metastasis", "confidence": "Medium", "features": "Multiple, peripheral", "modality": "CT", "urgency": "Urgent"}
    ],
    "liver_lesion": [
        {"diagnosis": "Hemangioma", "confidence": "High", "features": "Peripheral nodular enhancement", "modality": "MRI/CT", "urgency": "Non-urgent"},
        {"diagnosis": "Metastasis", "confidence": "Medium", "features": "Multiple, ring enhancement", "modality": "MRI/CT", "urgency": "Urgent"}
    ]
}

# ===== WEB-BASED VOICE RECOGNITION =====
def get_voice_input_javascript():
    """Returns JavaScript for browser-based voice recognition"""
    return """
    <script>
    // Voice recognition using browser's Web Speech API
    let recognition;
    let isListening = false;
    
    function initVoiceRecognition() {
        if ('webkitSpeechRecognition' in window) {
            recognition = new webkitSpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = 'en-US';
            
            recognition.onresult = function(event) {
                const transcript = event.results[0][0].transcript;
                window.parent.postMessage({
                    type: 'STREAMLIT_VOICE_RESULT',
                    data: transcript
                }, '*');
            };
            
            recognition.onerror = function(event) {
                window.parent.postMessage({
                    type: 'STREAMLIT_VOICE_ERROR',
                    data: event.error
                }, '*');
            };
            
            recognition.onend = function() {
                isListening = false;
                updateButtonState();
            };
            
            console.log("Voice recognition initialized");
        } else {
            console.error("Web Speech API not supported");
            window.parent.postMessage({
                type: 'STREAMLIT_VOICE_ERROR',
                data: 'Voice recognition not supported in this browser'
            }, '*');
        }
    }
    
    function startListening() {
        if (recognition && !isListening) {
            try {
                recognition.start();
                isListening = true;
                updateButtonState();
                return true;
            } catch (error) {
                console.error("Error starting recognition:", error);
                return false;
            }
        }
        return false;
    }
    
    function stopListening() {
        if (recognition && isListening) {
            try {
                recognition.stop();
                isListening = false;
                updateButtonState();
                return true;
            } catch (error) {
                console.error("Error stopping recognition:", error);
                return false;
            }
        }
        return false;
    }
    
    function updateButtonState() {
        const startBtn = document.getElementById('voiceStartBtn');
        const stopBtn = document.getElementById('voiceStopBtn');
        const status = document.getElementById('voiceStatus');
        
        if (startBtn && stopBtn && status) {
            if (isListening) {
                startBtn.disabled = true;
                stopBtn.disabled = false;
                status.textContent = "🎤 Listening... Speak now";
                status.className = "recording";
            } else {
                startBtn.disabled = false;
                stopBtn.disabled = true;
                status.textContent = "🎤 Ready to record";
                status.className = "";
            }
        }
    }
    
    // Initialize on load
    window.addEventListener('load', initVoiceRecognition);
    
    // Handle messages from Streamlit
    window.addEventListener('message', function(event) {
        if (event.data.type === 'STREAMLIT_VOICE_START') {
            startListening();
        } else if (event.data.type === 'STREAMLIT_VOICE_STOP') {
            stopListening();
        }
    });
    </script>
    """

# ===== ANALYTICS DASHBOARD CLASS =====
class AnalyticsDashboard:
    def __init__(self):
        self.metrics = {
            "turnaround_time": [],
            "report_length": [],
            "template_usage": defaultdict(int),
            "critical_findings_count": 0,
            "modality_usage": defaultdict(int),
            "user_productivity": defaultdict(int)
        }
    
    def update_metrics(self, report_data):
        """Update metrics with new report data"""
        report_length = len(report_data.get('report', ''))
        self.metrics["report_length"].append(report_length)
        
        modality = report_data.get('technique_info', {}).get('modality', 'Unknown')
        self.metrics["modality_usage"][modality] += 1
        
        user = report_data.get('created_by', 'unknown')
        self.metrics["user_productivity"][user] += 1
        
        templates_used = report_data.get('templates_used', [])
        if isinstance(templates_used, str) and templates_used != "None":
            self.metrics["template_usage"][templates_used] += 1
        elif isinstance(templates_used, list):
            for template in templates_used:
                self.metrics["template_usage"][template] += 1
        
        report_text = report_data.get('report', '').lower()
        critical_keywords = ["hemorrhage", "stroke", "infarct", "herniation", "compression", "rupture", "abscess"]
        if any(keyword in report_text for keyword in critical_keywords):
            self.metrics["critical_findings_count"] += 1

# ===== QUALITY ASSURANCE CLASS =====
class QualityAssurance:
    def __init__(self):
        self.quality_metrics = {
            "required_sections": ["FINDINGS", "IMPRESSION"],
            "recommended_sections": ["TECHNIQUE", "CLINICAL HISTORY", "COMPARISON"],
            "min_findings_length": 50,
            "max_findings_length": 2000,
            "ambiguous_terms": ["possible", "likely", "suggestive of", "cannot exclude", "may represent", "probably"],
            "forbidden_terms": ["normal", "unremarkable"]
        }
    
    def audit_report(self, report_text):
        """Audit report for quality metrics"""
        audit_results = {
            "score": 100,
            "warnings": [],
            "suggestions": [],
            "missing_sections": [],
            "strengths": []
        }
        
        for section in self.quality_metrics["required_sections"]:
            if section not in report_text.upper():
                audit_results["missing_sections"].append(section)
                audit_results["score"] -= 20
                audit_results["warnings"].append(f"Missing required section: {section}")
        
        findings_match = re.search(r'FINDINGS:(.*?)(?=\n\n[A-Z]+:|$)', report_text, re.DOTALL | re.IGNORECASE)
        if findings_match:
            findings_text = findings_match.group(1).strip()
            
            if len(findings_text) < self.quality_metrics["min_findings_length"]:
                audit_results["warnings"].append(f"Findings section is brief ({len(findings_text)} chars)")
                audit_results["score"] -= 10
                audit_results["suggestions"].append("Consider adding more descriptive details")
            elif len(findings_text) > self.quality_metrics["max_findings_length"]:
                audit_results["warnings"].append(f"Findings section is verbose ({len(findings_text)} chars)")
                audit_results["score"] -= 5
                audit_results["suggestions"].append("Consider being more concise")
            else:
                audit_results["strengths"].append("Findings section has appropriate length")
            
            for term in self.quality_metrics["ambiguous_terms"]:
                if term in findings_text.lower():
                    audit_results["suggestions"].append(f"Consider clarifying ambiguous term: '{term}'")
                    audit_results["score"] -= 3
            
            for term in self.quality_metrics["forbidden_terms"]:
                if term in findings_text.lower() and len(findings_text) < 100:
                    audit_results["warnings"].append(f"Avoid vague term: '{term}' without supporting details")
                    audit_results["score"] -= 5
        
        if "COMPARISON" in report_text.upper():
            audit_results["strengths"].append("Includes comparison with prior studies")
            audit_results["score"] += 10
        
        if "DIFFERENTIAL" in report_text.upper():
            audit_results["strengths"].append("Includes differential diagnosis")
            audit_results["score"] += 5
        
        audit_results["score"] = max(0, min(100, audit_results["score"]))
        
        if audit_results["score"] >= 90:
            audit_results["grade"] = "Excellent"
        elif audit_results["score"] >= 75:
            audit_results["grade"] = "Good"
        elif audit_results["score"] >= 60:
            audit_results["grade"] = "Fair"
        else:
            audit_results["grade"] = "Needs Improvement"
        
        return audit_results

# ===== TEMPLATE SYSTEM =====
class TemplateSystem:
    def __init__(self):
        self.templates = {}
        self.load_templates()
    
    def load_templates(self):
        if os.path.exists(TEMPLATES_FILE):
            try:
                with open(TEMPLATES_FILE, 'r') as f:
                    self.templates = json.load(f)
            except:
                self.templates = {}
    
    def save_templates(self):
        try:
            with open(TEMPLATES_FILE, 'w') as f:
                json.dump(self.templates, f, indent=2)
        except:
            pass
    
    def add_template(self, name, content, template_type="findings"):
        self.templates[name] = {
            "content": content,
            "type": template_type,
            "created_by": st.session_state.get('current_user', 'unknown'),
            "created_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "used_count": 0
        }
        self.save_templates()

# ===== HELPER FUNCTIONS =====
def generate_differential_diagnosis(text, modality_filter=None):
    if not text:
        return []
    
    text_lower = text.lower()
    results = []
    
    if any(word in text_lower for word in ["enhanc", "mass", "tumor", "neoplasm", "gadolinium"]):
        results.extend(DIFFERENTIAL_DATABASE["brain_lesion_enhancing"])
    
    if any(word in text_lower for word in ["white matter", "flair", "hyperintensity", "msa", "demyelinating"]):
        results.extend(DIFFERENTIAL_DATABASE["white_matter"])
    
    if any(word in text_lower for word in ["stroke", "infarct", "ischemi", "mca", "aca", "pca"]):
        results.extend(DIFFERENTIAL_DATABASE["stroke"])
    
    if any(word in text_lower for word in ["spinal", "cord", "disc", "vertebral", "canal", "foraminal"]):
        results.extend(DIFFERENTIAL_DATABASE["spinal_lesion"])
    
    if any(word in text_lower for word in ["lung", "pulmonary", "nodule", "chest", "thorax", "pleural"]):
        results.extend(DIFFERENTIAL_DATABASE["lung_nodule"])
    
    if any(word in text_lower for word in ["liver", "hepatic", "lesion", "hepato", "portal"]):
        results.extend(DIFFERENTIAL_DATABASE["liver_lesion"])
    
    if modality_filter and modality_filter != "All":
        results = [r for r in results if r.get('modality') == modality_filter]
    
    seen = set()
    unique_results = []
    for r in results:
        key = r['diagnosis']
        if key not in seen:
            seen.add(key)
            unique_results.append(r)
    
    return unique_results[:6]

def create_word_document(patient_info, report_text, report_date):
    doc = Document()
    title = doc.add_heading('RADIOLOGY REPORT', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph()
    
    if patient_info and any(patient_info.values()):
        doc.add_heading('PATIENT INFORMATION', level=1)
        if patient_info.get('name'):
            doc.add_paragraph(f"Patient Name: {patient_info['name']}")
        if patient_info.get('id'):
            doc.add_paragraph(f"Patient ID: {patient_info['id']}")
        if patient_info.get('age') or patient_info.get('sex'):
            doc.add_paragraph(f"Age/Sex: {patient_info.get('age', '')}/{patient_info.get('sex', '')}")
        if patient_info.get('history'):
            doc.add_paragraph(f"Clinical History: {patient_info['history']}")
        doc.add_paragraph(f"Report Date: {report_date if report_date else datetime.datetime.now().strftime('%Y-%m-%d')}")
    
    doc.add_paragraph()
    lines = report_text.split('\n')
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            doc.add_paragraph()
            continue
        if line_stripped.endswith(':') and line_stripped[:-1].replace(' ', '').isupper():
            heading_text = line_stripped[:-1]
            doc.add_heading(heading_text, level=1)
        else:
            doc.add_paragraph(line_stripped)
    
    doc.add_page_break()
    doc.add_heading('REPORT DETAILS', level=1)
    p = doc.add_paragraph()
    p.add_run(f"Generated by: {st.session_state.get('current_user', 'Unknown')}\n")
    p.add_run(f"Generation date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return doc

# ===== INITIALIZE SESSION STATE =====
def init_session_state():
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.users = {
            "admin": {"password": hashlib.sha256("admin123".encode()).hexdigest(), "role": "admin"},
            "neuro": {"password": hashlib.sha256("neuro123".encode()).hexdigest(), "role": "radiologist"},
            "body": {"password": hashlib.sha256("body123".encode()).hexdigest(), "role": "radiologist"}
        }
        st.session_state.report_history = []
        st.session_state.report_draft = ""
        st.session_state.patient_info = {}
        st.session_state.ai_report = ""
        st.session_state.report_date = ""
        st.session_state.current_user = "default"
        st.session_state.logged_in = False
        st.session_state.differential_results = []
        st.session_state.template_system = TemplateSystem()
        st.session_state.technique_info = {
            "modality": "MRI",
            "contrast": "Without contrast",
            "sequences": "Standard sequences"
        }
        st.session_state.show_differential_suggestions = False
        
        # Voice recognition state
        st.session_state.voice_transcript = ""
        st.session_state.is_recording = False
        st.session_state.voice_status = "🎤 Ready to record"
        
        # Analytics and QA
        st.session_state.analytics_dashboard = AnalyticsDashboard()
        st.session_state.quality_assurance = QualityAssurance()

# ===== STREAMLIT APP =====
def main():
    # Page config with modern theme
    st.set_page_config(
        page_title="Radiology Assistant Pro",
        layout="wide",
        page_icon="🩺",
        initial_sidebar_state="collapsed"
    )
    
    # Custom CSS for modern design
    st.markdown("""
    <style>
    /* Main container */
    .main {
        padding: 0rem 1rem;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #1E3A8A;
        font-weight: 600;
    }
    
    /* Cards */
    .card {
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
        border-left: 4px solid #3B82F6;
    }
    
    /* Voice recording indicator */
    .recording {
        animation: pulse 1.5s infinite;
        color: #EF4444;
        font-weight: bold;
    }
    
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
    
    /* Buttons */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
    }
    
    /* Voice input specific */
    .voice-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    /* Status indicators */
    .status-ready { color: #10B981; }
    .status-listening { color: #EF4444; }
    .status-error { color: #F59E0B; }
    </style>
    """, unsafe_allow_html=True)
    
    # Inject JavaScript for voice recognition
    st.markdown(get_voice_input_javascript(), unsafe_allow_html=True)
    
    # Initialize session state
    init_session_state()
    
    # ===== LOGIN SYSTEM =====
    if not st.session_state.logged_in:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.container():
                st.markdown("<h1 style='text-align: center;'>🔐 Radiology Assistant Pro</h1>", unsafe_allow_html=True)
                
                with st.container(border=True):
                    st.subheader("Login")
                    username = st.text_input("Username", key="login_user")
                    password = st.text_input("Password", type="password", key="login_pass")
                    
                    if st.button("Login", type="primary", use_container_width=True):
                        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
                        if username in st.session_state.users:
                            if st.session_state.users[username]["password"] == hashed_pw:
                                st.session_state.logged_in = True
                                st.session_state.current_user = username
                                st.success(f"Welcome, {username}!")
                                st.rerun()
                            else:
                                st.error("Invalid password")
                        else:
                            st.error("User not found")
                    
                    st.info("**Demo accounts:** admin/admin123 | neuro/neuro123 | body/body123")
        
        return
    
    # ===== MAIN APPLICATION =====
    
    # Top Header with User Info
    col_header1, col_header2, col_header3 = st.columns([3, 1, 1])
    with col_header1:
        st.markdown(f"# 🏥 Radiology Assistant Pro")
        st.markdown(f"**Welcome, Dr. {st.session_state.current_user}!**")
    
    with col_header2:
        if st.button("📊 Dashboard", use_container_width=True):
            st.session_state.show_analytics = not st.session_state.get('show_analytics', False)
            st.rerun()
    
    with col_header3:
        if st.button("🚪 Logout", use_container_width=True, type="secondary"):
            st.session_state.logged_in = False
            st.rerun()
    
    # Main Layout: Sidebar + Two Main Columns
    col_sidebar, col_main1, col_main2 = st.columns([1, 2, 2])
    
    # ===== LEFT SIDEBAR: REPORT CREATION & PATIENT DATA =====
    with col_sidebar:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("### 📋 Report Setup")
        
        # Quick Patient Info
        with st.expander("👤 Patient Information", expanded=True):
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                p_name = st.text_input("Name", value=st.session_state.patient_info.get('name', ''), key="pat_name")
                p_age = st.text_input("Age", value=st.session_state.patient_info.get('age', ''), key="pat_age")
            with col_p2:
                p_id = st.text_input("ID", value=st.session_state.patient_info.get('id', ''), key="pat_id")
                p_sex = st.selectbox("Sex", ["", "M", "F", "Other"], 
                                    index=["", "M", "F", "Other"].index(st.session_state.patient_info.get('sex', '')) 
                                    if st.session_state.patient_info.get('sex') in ["", "M", "F", "Other"] else 0,
                                    key="pat_sex")
            
            p_history = st.text_area("Clinical History", value=st.session_state.patient_info.get('history', ''), 
                                    height=60, key="pat_history", placeholder="Enter clinical history...")
            
            if st.button("💾 Save Patient", use_container_width=True, key="save_patient"):
                st.session_state.patient_info = {
                    "name": p_name, "id": p_id, "age": p_age, 
                    "sex": p_sex, "history": p_history
                }
                st.success("Patient info saved!")
        
        # Technique Details
        with st.expander("🔬 Imaging Details", expanded=True):
            modality = st.selectbox(
                "Modality",
                ["MRI", "CT", "Ultrasound", "X-ray", "PET-CT"],
                key="modality_select",
                index=0
            )
            
            contrast = st.selectbox(
                "Contrast",
                ["Without contrast", "With contrast", "With and without contrast"],
                key="contrast_select",
                index=0
            )
            
            sequences = st.text_area(
                "Protocol Details",
                value=st.session_state.technique_info.get('sequences', ''),
                height=80,
                key="sequences_input",
                placeholder="e.g., T1, T2, FLAIR, DWI sequences"
            )
            
            if st.button("💾 Save Technique", use_container_width=True, key="save_tech"):
                st.session_state.technique_info = {
                    "modality": modality,
                    "contrast": contrast,
                    "sequences": sequences if sequences else "Standard protocol"
                }
                st.success("Technique saved!")
        
        # Voice Input Section
        st.markdown("---")
        st.markdown("### 🎤 Voice Dictation")
        
        # Voice status display
        voice_status_display = st.empty()
        with voice_status_display.container():
            status_class = "status-listening" if st.session_state.is_recording else "status-ready"
            st.markdown(f"<div class='{status_class}'>{st.session_state.voice_status}</div>", unsafe_allow_html=True)
        
        # Voice controls
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            if st.button("🎤 Start", key="voice_start", use_container_width=True, disabled=st.session_state.is_recording):
                # Trigger JavaScript to start recording
                js_code = """
                <script>
                window.postMessage({type: 'STREAMLIT_VOICE_START'}, '*');
                </script>
                """
                st.components.v1.html(js_code, height=0)
                st.session_state.is_recording = True
                st.session_state.voice_status = "🎤 Listening... Speak now"
                st.rerun()
        
        with col_v2:
            if st.button("⏹️ Stop", key="voice_stop", use_container_width=True, disabled=not st.session_state.is_recording):
                # Trigger JavaScript to stop recording
                js_code = """
                <script>
                window.postMessage({type: 'STREAMLIT_VOICE_STOP'}, '*');
                </script>
                """
                st.components.v1.html(js_code, height=0)
                st.session_state.is_recording = False
                st.session_state.voice_status = "⏹️ Processing..."
                st.rerun()
        
        # Manual text input for voice (fallback)
        st.markdown("---")
        st.markdown("### 📝 Manual Entry")
        manual_text = st.text_area("Or type voice transcript:", height=100, key="manual_voice", 
                                  placeholder="Type or paste voice transcript here...")
        
        if st.button("📥 Add to Draft", key="add_manual_voice", use_container_width=True) and manual_text:
            st.session_state.report_draft += f"\n{manual_text}"
            st.success("Text added to draft!")
            st.rerun()
        
        # Quick Templates
        st.markdown("---")
        st.markdown("### 📑 Quick Templates")
        
        templates = {
            "Normal Brain MRI": "FINDINGS:\nNormal study. No acute intracranial hemorrhage, mass effect, or territorial infarct. Ventricles and sulci are normal.",
            "White Matter Changes": "FINDINGS:\nScattered punctate FLAIR hyperintensities in the periventricular white matter, consistent with chronic microvascular ischemic changes.",
            "Disc Herniation": "FINDINGS:\nDisc bulge/protrusion causing mild neural foraminal narrowing without significant cord compression."
        }
        
        selected_template = st.selectbox("Choose template", ["Select..."] + list(templates.keys()))
        if selected_template != "Select..." and st.button("📥 Insert Template", use_container_width=True):
            st.session_state.report_draft += f"\n\n{templates[selected_template]}"
            st.success(f"Added {selected_template} template!")
            st.rerun()
        
        # Quick Actions
        st.markdown("---")
        st.markdown("### ⚡ Quick Actions")
        
        col_q1, col_q2 = st.columns(2)
        with col_q1:
            if st.button("🧹 Clear All", use_container_width=True):
                st.session_state.report_draft = ""
                st.session_state.ai_report = ""
                st.rerun()
        
        with col_q2:
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # ===== MAIN COLUMN 1: REPORT DRAFTING =====
    with col_main1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("## ✍️ Report Drafting")
        
        # Voice transcription display
        if st.session_state.is_recording:
            with st.container(border=True):
                st.markdown("### 🎤 **Live Recording Active**")
                st.markdown("**Speak clearly into your microphone...**")
                st.progress(70)
                st.info("Your speech will be transcribed when you click 'Stop'")
        
        # JavaScript message handler for voice results
        js_handler = """
        <script>
        // Handle voice results from the page
        window.addEventListener('message', function(event) {
            if (event.data.type === 'STREAMLIT_VOICE_RESULT') {
                // Send the transcript back to Streamlit
                const data = {transcript: event.data.data};
                window.parent.postMessage({
                    type: 'streamlit:setComponentValue',
                    value: JSON.stringify(data)
                }, '*');
            }
        });
        </script>
        """
        st.components.v1.html(js_handler, height=0)
        
        # Create a custom component to receive voice data
        if 'voice_data' not in st.session_state:
            st.session_state.voice_data = ""
        
        # Check for incoming voice data
        voice_input = st.text_input("Voice input (hidden)", value=st.session_state.voice_data, 
                                   key="voice_input_hidden", label_visibility="collapsed")
        
        if voice_input and voice_input != st.session_state.voice_data:
            try:
                data = json.loads(voice_input)
                if 'transcript' in data:
                    transcript = data['transcript']
                    st.session_state.report_draft += f"\n{transcript}"
                    st.session_state.voice_status = f"✅ Transcribed: {transcript[:50]}..."
                    st.session_state.voice_data = voice_input
                    st.success("Voice transcript added to draft!")
                    st.rerun()
            except:
                pass
        
        # Main text editor with enhanced features
        tab1, tab2, tab3 = st.tabs(["📝 Editor", "🧠 AI Assist", "🔍 Preview"])
        
        with tab1:
            # Enhanced text area with formatting options
            col_editor1, col_editor2 = st.columns([3, 1])
            with col_editor1:
                st.markdown("**Report Content:**")
            
            with col_editor2:
                if st.button("📋 Format Headings", key="format_btn", use_container_width=True):
                    # Auto-format common headings
                    text = st.session_state.report_draft
                    sections = ["FINDINGS", "IMPRESSION", "TECHNIQUE", "CLINICAL HISTORY", "DIFFERENTIAL DIAGNOSIS"]
                    for section in sections:
                        if section.lower() in text.lower() and f"{section}:" not in text:
                            text = re.sub(fr'\b{section}\b', f'{section}:', text, flags=re.IGNORECASE)
                    st.session_state.report_draft = text
                    st.success("Headings formatted!")
            
            draft_text = st.text_area(
                "Type or dictate your report:",
                value=st.session_state.report_draft,
                height=400,
                key="draft_input",
                label_visibility="collapsed",
                placeholder="Start typing your report here...\n\nUse voice dictation for hands-free input.\n\nTip: Start sections with headings like 'FINDINGS:' or 'IMPRESSION:'"
            )
            st.session_state.report_draft = draft_text
            
            # Quick formatting buttons
            col_fmt1, col_fmt2, col_fmt3, col_fmt4 = st.columns(4)
            with col_fmt1:
                if st.button("📋 Copy", use_container_width=True):
                    st.session_state.clipboard = draft_text
                    st.success("Copied to clipboard!")
            with col_fmt2:
                if st.button("📝 Clear", use_container_width=True):
                    st.session_state.report_draft = ""
                    st.rerun()
            with col_fmt3:
                if st.button("💾 Save Draft", use_container_width=True):
                    # Save draft to temporary file
                    temp_file = f"draft_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    with open(temp_file, 'w') as f:
                        f.write(draft_text)
                    st.success(f"Draft saved as {temp_file}")
            with col_fmt4:
                if st.button("📤 Load Draft", use_container_width=True):
                    st.info("Use the 'Load' button in history section")
        
        with tab2:
            # AI Assistance features
            st.markdown("### 🧠 AI Assistant")
            
            col_ai1, col_ai2 = st.columns(2)
            with col_ai1:
                if st.button("🔍 Generate Differentials", use_container_width=True):
                    if st.session_state.report_draft:
                        current_modality = st.session_state.technique_info.get('modality', 'All')
                        st.session_state.differential_results = generate_differential_diagnosis(
                            st.session_state.report_draft, 
                            current_modality
                        )
                        st.session_state.show_differential_suggestions = True
                        st.success("Differential diagnosis generated!")
                        st.rerun()
                    else:
                        st.warning("Please enter findings first")
            
            with col_ai2:
                if st.button("✨ Improve Language", use_container_width=True):
                    # Simple language improvement
                    if st.session_state.report_draft:
                        text = st.session_state.report_draft
                        # Replace vague terms
                        improvements = {
                            "normal": "unremarkable",
                            "big": "enlarged",
                            "small": "diminished",
                            "looks like": "consistent with",
                            "maybe": "potentially"
                        }
                        for old, new in improvements.items():
                            if old in text.lower():
                                text = re.sub(rf'\b{old}\b', new, text, flags=re.IGNORECASE)
                        st.session_state.report_draft = text
                        st.success("Language improved!")
                    else:
                        st.warning("No text to improve")
            
            # Show differential suggestions if available
            if st.session_state.show_differential_suggestions and st.session_state.differential_results:
                st.markdown("### 📋 Differential Suggestions")
                for dx in st.session_state.differential_results:
                    with st.container(border=True):
                        col_dx1, col_dx2 = st.columns([3, 1])
                        with col_dx1:
                            urgency = "🔴" if dx.get('urgency') == "Urgent" else "🟢"
                            st.markdown(f"**{dx['diagnosis']}** {urgency}")
                            st.caption(f"*{dx['features']}*")
                            st.caption(f"Confidence: {dx.get('confidence')} | Modality: {dx.get('modality')}")
                        with col_dx2:
                            if st.button("➕ Add", key=f"add_{dx['diagnosis']}"):
                                dx_text = f"\n- {dx['diagnosis']}: {dx['features']}"
                                if "DIFFERENTIAL DIAGNOSIS:" in st.session_state.report_draft:
                                    st.session_state.report_draft += dx_text
                                else:
                                    st.session_state.report_draft += f"\n\nDIFFERENTIAL DIAGNOSIS:{dx_text}"
                                st.success(f"Added {dx['diagnosis']}")
                                st.rerun()
        
        with tab3:
            # Draft preview
            st.markdown("### 👁️ Draft Preview")
            if st.session_state.report_draft:
                st.text_area(
                    "Preview:",
                    value=st.session_state.report_draft,
                    height=350,
                    key="draft_preview",
                    label_visibility="collapsed"
                )
            else:
                st.info("No draft content to preview")
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # ===== MAIN COLUMN 2: FINAL REPORT =====
    with col_main2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("## 📄 Final Report")
        
        # Report generation and preview
        col_gen1, col_gen2 = st.columns([2, 1])
        with col_gen1:
            if st.button("🤖 Generate Full Report", type="primary", use_container_width=True):
                if st.session_state.report_draft:
                    formatted_report = ""
                    
                    # Add patient info if available
                    if st.session_state.patient_info and any(st.session_state.patient_info.values()):
                        formatted_report += "**PATIENT INFORMATION:**\n"
                        if st.session_state.patient_info.get('name'):
                            formatted_report += f"Name: {st.session_state.patient_info['name']}\n"
                        if st.session_state.patient_info.get('id'):
                            formatted_report += f"ID: {st.session_state.patient_info['id']}\n"
                        if st.session_state.patient_info.get('age') or st.session_state.patient_info.get('sex'):
                            formatted_report += f"Age/Sex: {st.session_state.patient_info.get('age', '')}/{st.session_state.patient_info.get('sex', '')}\n"
                        if st.session_state.patient_info.get('history'):
                            formatted_report += f"Clinical History: {st.session_state.patient_info['history']}\n"
                        formatted_report += "\n"
                    
                    # Add technique
                    formatted_report += "**TECHNIQUE:**\n"
                    tech_info = st.session_state.technique_info
                    formatted_report += f"Modality: {tech_info.get('modality', 'Not specified')}\n"
                    formatted_report += f"Contrast: {tech_info.get('contrast', 'Without contrast')}\n"
                    if tech_info.get('sequences'):
                        formatted_report += f"Protocol: {tech_info['sequences']}\n"
                    formatted_report += "\n"
                    
                    # Add findings
                    formatted_report += st.session_state.report_draft
                    
                    # Ensure impression exists
                    if "IMPRESSION:" not in formatted_report and "IMPRESSION" not in formatted_report:
                        formatted_report += "\n\n**IMPRESSION:**\nFindings as described. Clinical correlation recommended."
                    
                    st.session_state.ai_report = formatted_report
                    st.session_state.report_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    st.success("✅ Report generated successfully!")
                else:
                    st.warning("Please enter findings in the draft section")
        
        with col_gen2:
            if st.button("🔍 Quality Check", use_container_width=True):
                if st.session_state.ai_report:
                    audit_results = st.session_state.quality_assurance.audit_report(st.session_state.ai_report)
                    st.session_state.quality_results = audit_results
                    st.success(f"Quality Score: {audit_results['score']}/100")
                else:
                    st.warning("Generate a report first")
        
        # Report preview
        if st.session_state.ai_report:
            st.markdown("### 📋 Report Preview")
            
            # Quality score display
            if hasattr(st.session_state, 'quality_results'):
                score = st.session_state.quality_results['score']
                grade = st.session_state.quality_results['grade']
                color = "🟢" if score >= 80 else "🟡" if score >= 60 else "🔴"
                st.metric("Quality Score", f"{color} {score}/100 ({grade})")
            
            # Report content
            with st.container(border=True, height=350):
                st.text_area(
                    "Generated Report:",
                    value=st.session_state.ai_report,
                    height=320,
                    key="report_preview",
                    label_visibility="collapsed"
                )
            
            # Export options
            st.markdown("### 📤 Export Options")
            
            col_exp1, col_exp2, col_exp3, col_exp4 = st.columns(4)
            
            with col_exp1:
                # Word document
                try:
                    doc = create_word_document(
                        patient_info=st.session_state.patient_info,
                        report_text=st.session_state.ai_report,
                        report_date=st.session_state.report_date
                    )
                    
                    buffer = BytesIO()
                    doc.save(buffer)
                    buffer.seek(0)
                    
                    patient_name = st.session_state.patient_info.get('name', 'Unknown').replace(' ', '_')
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
                    
                    st.download_button(
                        label="📄 Word",
                        data=buffer,
                        file_name=f"Report_{patient_name}_{timestamp}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                        key="download_word"
                    )
                except Exception as e:
                    st.error(f"Word export: {str(e)}")
            
            with col_exp2:
                # Text file
                txt_data = st.session_state.ai_report
                st.download_button(
                    label="📝 Text",
                    data=txt_data,
                    file_name=f"Report_{patient_name}_{timestamp}.txt",
                    mime="text/plain",
                    use_container_width=True,
                    key="download_text"
                )
            
            with col_exp3:
                # JSON export
                report_data = {
                    "metadata": {
                        "radiologist": st.session_state.current_user,
                        "date": st.session_state.report_date,
                        "patient": st.session_state.patient_info,
                        "technique": st.session_state.technique_info
                    },
                    "report": st.session_state.ai_report
                }
                
                json_data = json.dumps(report_data, indent=2)
                st.download_button(
                    label="📊 JSON",
                    data=json_data,
                    file_name=f"Report_{patient_name}_{timestamp}.json",
                    mime="application/json",
                    use_container_width=True,
                    key="download_json"
                )
            
            with col_exp4:
                # Clipboard copy
                if st.button("📋 Copy", use_container_width=True, key="copy_report"):
                    st.session_state.clipboard = st.session_state.ai_report
                    st.success("Report copied to clipboard!")
            
            # Save to history
            st.markdown("---")
            st.markdown("### 💾 Save Report")
            
            report_name = st.text_input(
                "Report Title:",
                value=f"{st.session_state.patient_info.get('name', 'Report')} - {st.session_state.report_date.split()[0]}",
                key="report_name"
            )
            
            if st.button("💾 Save to History", type="secondary", use_container_width=True):
                history_entry = {
                    "name": report_name,
                    "date": st.session_state.report_date,
                    "patient_info": st.session_state.patient_info,
                    "technique_info": st.session_state.technique_info,
                    "report": st.session_state.ai_report,
                    "created_by": st.session_state.current_user
                }
                st.session_state.report_history.append(history_entry)
                st.session_state.analytics_dashboard.update_metrics(history_entry)
                st.success("✅ Report saved to history!")
        
        else:
            # Empty state
            with st.container(border=True, height=400):
                st.markdown("""
                ### 🚀 Ready to Generate!
                
                **To create your report:**
                1. Enter patient details (optional) in sidebar
                2. Set imaging technique
                3. Draft findings using text or voice
                4. Click "Generate Full Report"
                
                **Voice dictation tips:**
                • Click 🎤 in sidebar to start recording
                • Speak clearly and naturally
                • Use headings like "Findings" and "Impression"
                • Stop recording to transcribe
                
                **Quick templates available in sidebar!**
                """)
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # ===== REPORT HISTORY SECTION =====
    st.markdown("---")
    st.markdown("## 📜 Recent Reports")
    
    if st.session_state.report_history:
        # Display last 3 reports
        recent_reports = st.session_state.report_history[-3:][::-1]
        
        for i, report in enumerate(recent_reports):
            col_hist1, col_hist2 = st.columns([3, 1])
            
            with col_hist1:
                with st.container(border=True):
                    st.markdown(f"**{report['name']}**")
                    st.caption(f"📅 {report['date']} | 👤 {report['created_by']}")
                    
                    patient_name = report['patient_info'].get('name', 'No patient data')
                    modality = report['technique_info'].get('modality', 'Unknown')
                    st.caption(f"👤 {patient_name} | 🔬 {modality}")
                    
                    # Preview snippet
                    preview = report['report'][:150] + "..." if len(report['report']) > 150 else report['report']
                    st.text(preview)
            
            with col_hist2:
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("📥 Load", key=f"load_{i}", use_container_width=True):
                        st.session_state.patient_info = report['patient_info']
                        st.session_state.technique_info = report['technique_info']
                        st.session_state.ai_report = report['report']
                        st.session_state.report_date = report['date']
                        st.success("Report loaded!")
                        st.rerun()
                
                with col_btn2:
                    if st.button("🗑️", key=f"delete_{i}", help="Delete report", use_container_width=True):
                        idx = len(st.session_state.report_history) - 1 - i
                        st.session_state.report_history.pop(idx)
                        st.warning("Report deleted!")
                        st.rerun()
    else:
        st.info("No reports in history yet. Generate and save your first report!")

# ===== RUN APPLICATION =====
if __name__ == "__main__":
    main()
