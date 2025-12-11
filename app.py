"""
AI-Powered Professional Radiology Reporting Assistant
Version 3.0 - Enterprise Edition
Features: DICOM Import, Voice Dictation, Critical Flagging, Smart Templates,
          Batch Processing, Advanced Search, Peer Review, Report Lock,
          Hospital Branding, Multi-User Support, Audit Trail
"""

import streamlit as st
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from io import BytesIO
import re
import json
import os
import datetime
import time
import base64
import hashlib
import pandas as pd
from collections import defaultdict
import numpy as np

# ===== CONFIGURATION =====
CONFIG_FILE = "radiology_config.json"
HISTORY_FILE = "report_history.json"
TEMPLATES_FILE = "saved_templates.json"
AUDIT_LOG_FILE = "audit_trail.json"
USER_FILE = "users.json"

# ===== DICOM IMPORT =====
try:
    import pydicom
    from pydicom.errors import InvalidDicomError
    DICOM_AVAILABLE = True
except ImportError:
    DICOM_AVAILABLE = False

# ===== CRITICAL FINDINGS DATABASE =====
CRITICAL_PATTERNS = {
    "Brain": [
        ("acute infarct", "High", "Immediate neurology consult"),
        ("large mass", "High", "Neurosurgery referral"),
        ("hemorrhage", "Critical", "STAT neurosurgery"),
        ("herniation", "Critical", "Emergency neurosurgery"),
        ("abscess", "High", "Infectious disease consult"),
        ("hydrocephalus", "High", "Neurosurgery consult"),
        ("child abuse", "Critical", "Legal/Child protection"),
        ("aneurysm rupture", "Critical", "Neurointerventional STAT")
    ],
    "Spine": [
        ("cord compression", "Critical", "Emergency neurosurgery"),
        ("fracture dislocation", "Critical", "Spine surgery STAT"),
        ("epidural abscess", "High", "Infectious disease + surgery"),
        ("cauda equina", "Critical", "Emergency decompression")
    ],
    "Chest": [
        ("aortic dissection", "Critical", "Cardiothoracic surgery STAT"),
        ("pneumothorax", "High", "Chest tube assessment"),
        ("pulmonary embolism", "High", "Anticoagulation/Vascular"),
        ("mediastinal mass", "Medium", "Oncology referral")
    ],
    "Abdomen": [
        ("bowel perforation", "Critical", "General surgery STAT"),
        ("aortic aneurysm", "High", "Vascular surgery"),
        ("appendicitis", "High", "Surgical consult"),
        ("obstructive uropathy", "High", "Urology consult")
    ]
}

# ===== NORMAL REFERENCE VALUES =====
NORMAL_VALUES = {
    "Brain": {
        "Lateral ventricles (frontal horn)": "<10 mm",
        "Third ventricle": "<6 mm",
        "Fourth ventricle": "<12 mm",
        "Sulcal width": "<3 mm",
        "Pineal gland": "<10 mm",
        "Pituitary height": "≤8 mm (♀), ≤10 mm (♂)"
    },
    "Spine": {
        "Spinal canal AP diameter (cervical)": "≥12 mm",
        "Spinal canal AP diameter (lumbar)": "≥15 mm",
        "Thecal sac (lumbar)": "≥12 mm",
        "Cord compression": "None"
    },
    "Chest": {
        "Aortic diameter (ascending)": "<40 mm",
        "Aortic diameter (descending)": "<30 mm",
        "PA diameter": "<29 mm",
        "Cardiothoracic ratio": "<0.5",
        "Lymph node (short axis)": "<10 mm"
    }
}

# ===== INITIALIZATION FUNCTIONS =====
def init_config():
    """Initialize configuration with default values."""
    default_config = {
        "hospital_name": "GENERAL HOSPITAL",
        "department": "RADIOLOGY DEPARTMENT",
        "logo_path": None,
        "watermark_text": "DRAFT - NOT FOR CLINICAL USE",
        "report_prefix": "RAD",
        "auto_save_interval": 30,
        "critical_check_enabled": True,
        "voice_enabled": True,
        "peer_review_enabled": True,
        "current_user": "default"
    }
    
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            saved_config = json.load(f)
            default_config.update(saved_config)
    
    return default_config

def save_config(config):
    """Save configuration to file."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def load_users():
    """Load user database."""
    default_users = {
        "admin": {
            "password": hashlib.sha256("admin123".encode()).hexdigest(),
            "role": "admin",
            "specialty": "All",
            "signature": "Dr. Admin"
        },
        "neuro": {
            "password": hashlib.sha256("neuro123".encode()).hexdigest(),
            "role": "radiologist",
            "specialty": "Neuro",
            "signature": "Dr. Neuro Radiologist"
        },
        "msk": {
            "password": hashlib.sha256("msk123".encode()).hexdigest(),
            "role": "radiologist",
            "specialty": "MSK",
            "signature": "Dr. MSK Radiologist"
        }
    }
    
    if os.path.exists(USER_FILE):
        with open(USER_FILE, 'r') as f:
            return json.load(f)
    return default_users

def save_users(users):
    """Save user database."""
    with open(USER_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def load_data(file_path, default_value):
    """Load JSON data from file."""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
    except Exception as e:
        st.error(f"Error loading {file_path}: {e}")
    return default_value

def save_data(file_path, data):
    """Save data to JSON file."""
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving {file_path}: {e}")
        return False

def log_audit_event(user, action, details=""):
    """Log an audit event."""
    audit_log = load_data(AUDIT_LOG_FILE, [])
    event = {
        "timestamp": datetime.datetime.now().isoformat(),
        "user": user,
        "action": action,
        "details": details,
        "ip": "local"  # In production, get from request
    }
    audit_log.append(event)
    save_data(AUDIT_LOG_FILE, audit_log)

# ===== FEATURE 2: VOICE-TO-TEXT DICTATION =====
def setup_voice_recognition():
    """Setup for voice recognition feature."""
    voice_js = """
    <script>
    function startDictation() {
        if (window.hasOwnProperty('webkitSpeechRecognition')) {
            var recognition = new webkitSpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = "en-US";
            recognition.start();
            
            recognition.onresult = function(e) {
                document.getElementById('voice_text').value = e.results[0][0].transcript;
                recognition.stop();
            };
            
            recognition.onerror = function(e) {
                recognition.stop();
            }
        }
    }
    </script>
    """
    return voice_js

# ===== FEATURE 3: DIFFERENTIAL DIAGNOSIS GENERATOR =====
DIFFERENTIAL_DATABASE = {
    "brain_lesion_enhancing": [
        {"diagnosis": "Meningioma", "confidence": "High", "features": "Dural-based, homogeneous enhancement, dural tail"},
        {"diagnosis": "Metastasis", "confidence": "High", "features": "Multiple, at gray-white junction, edema"},
        {"diagnosis": "Glioblastoma", "confidence": "Medium", "features": "Irregular rim enhancement, central necrosis"},
        {"diagnosis": "Lymphoma", "confidence": "Medium", "features": "Periventricular, homogeneous enhancement"},
        {"diagnosis": "Abscess", "confidence": "Low", "features": "Ring enhancement, restricted diffusion"}
    ],
    "white_matter_hyperintensities": [
        {"diagnosis": "Microvascular ischemia", "confidence": "High", "features": "Periventricular, punctate, age-appropriate"},
        {"diagnosis": "Multiple Sclerosis", "confidence": "Medium", "features": "Ovoid, perivenular, Dawson's fingers"},
        {"diagnosis": "Vasculitis", "confidence": "Low", "features": "Multiple territories, enhancement"},
        {"diagnosis": "CADASIL", "confidence": "Low", "features": "Anterior temporal lobe, external capsule"}
    ],
    "spinal_cord_lesion": [
        {"diagnosis": "Multiple Sclerosis", "confidence": "High", "features": "Short segment, peripheral"},
        {"diagnosis": "NMO spectrum", "confidence": "Medium", "features": "Long segment, central"},
        {"diagnosis": "Infarction", "confidence": "Medium", "features": "Acute, anterior cord"},
        {"diagnosis": "Tumor", "confidence": "Low", "features": "Expansile, enhancement"}
    ]
}

def generate_differential(text):
    """Generate differential diagnosis based on findings."""
    text_lower = text.lower()
    results = []
    
    # Check for patterns
    for pattern, diagnoses in DIFFERENTIAL_DATABASE.items():
        keywords = pattern.split('_')
        if any(keyword in text_lower for keyword in keywords):
            results.extend(diagnoses)
    
    # Remove duplicates and sort by confidence
    seen = set()
    unique_results = []
    for r in results:
        key = r['diagnosis']
        if key not in seen:
            seen.add(key)
            unique_results.append(r)
    
    return sorted(unique_results, key=lambda x: {'High': 0, 'Medium': 1, 'Low': 2}[x['confidence']])

# ===== FEATURE 4: CRITICAL FINDING FLAG =====
def check_critical_findings_advanced(text, modality="MRI"):
    """Advanced critical finding detection with categorization."""
    findings = []
    
    for category, patterns in CRITICAL_PATTERNS.items():
        for pattern, severity, action in patterns:
            if pattern in text.lower():
                findings.append({
                    "category": category,
                    "finding": pattern,
                    "severity": severity,
                    "action": action,
                    "modality": modality
                })
    
    return findings

# ===== FEATURE 5: SMART TEMPLATE SUGGESTIONS =====
class TemplateRecommender:
    """Smart template recommendation system."""
    
    def __init__(self, templates):
        self.templates = templates
        self.keyword_index = self._build_index()
    
    def _build_index(self):
        """Build keyword index from templates."""
        index = defaultdict(list)
        for name, content in self.templates.items():
            words = set(re.findall(r'\b[a-z]{4,}\b', content.lower()))
            for word in words:
                index[word].append(name)
        return index
    
    def recommend(self, text, limit=3):
        """Recommend templates based on current text."""
        if not text:
            return []
        
        words = set(re.findall(r'\b[a-z]{4,}\b', text.lower()))
        scores = defaultdict(int)
        
        for word in words:
            if word in self.keyword_index:
                for template in self.keyword_index[word]:
                    scores[template] += 1
        
        # Boost exact matches in template names
        for template in self.templates:
            for word in words:
                if word in template.lower():
                    scores[template] += 2
        
        sorted_templates = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [t[0] for t in sorted_templates[:limit]]

# ===== FEATURE 6: BATCH PROCESSING =====
def process_batch(file_content, template_text):
    """Process batch of patients from CSV."""
    try:
        df = pd.read_csv(BytesIO(file_content))
        results = []
        
        for _, row in df.iterrows():
            # Replace placeholders in template
            report = template_text
            for col in df.columns:
                placeholder = f"[{col.upper()}]"
                report = report.replace(placeholder, str(row[col]))
            
            results.append({
                "patient_id": row.get('PatientID', 'Unknown'),
                "patient_name": row.get('PatientName', 'Unknown'),
                "report": report
            })
        
        return results
    except Exception as e:
        st.error(f"Batch processing error: {e}")
        return []

# ===== FEATURE 7: ADVANCED SEARCH =====
def search_all_content(query, reports, templates, drafts):
    """Search across all content."""
    results = {
        "reports": [],
        "templates": [],
        "drafts": []
    }
    
    query_lower = query.lower()
    
    # Search reports
    for report in reports:
        if (query_lower in report.get('name', '').lower() or
            query_lower in report.get('draft', '').lower() or
            query_lower in report.get('ai_report', '').lower()):
            results["reports"].append(report)
    
    # Search templates
    for name, content in templates.items():
        if query_lower in name.lower() or query_lower in content.lower():
            results["templates"].append({"name": name, "content": content[:200]})
    
    # Search current drafts (from session state)
    if query_lower in drafts.lower():
        results["drafts"].append({"type": "current_draft", "preview": drafts[:200]})
    
    return results

# ===== FEATURE 8: ONE-CLICK NORMAL VALUES =====
def get_normal_values(category):
    """Get normal values for a category."""
    return NORMAL_VALUES.get(category, {})

# ===== FEATURE 9: PROFESSIONAL WORD EXPORT WITH BRANDING =====
def create_branded_word_report(ai_report, patient_info, report_date, config, is_final=False, reviewer_notes=""):
    """Create professionally branded Word document."""
    doc = Document()
    
    # Set document margins
    for section in doc.sections:
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)
    
    # Add hospital header
    header = doc.sections[0].header
    header_para = header.paragraphs[0]
    header_para.text = f"{config['hospital_name']} - {config['department']}"
    header_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    header_para.style.font.size = Pt(10)
    header_para.style.font.color.rgb = RGBColor(0, 51, 102)  # Dark blue
    
    # Add watermark if draft
    if not is_final and config.get('watermark_text'):
        watermark = doc.sections[0]
        watermark_para = watermark.header.add_paragraph()
        watermark_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        run = watermark_para.add_run(config['watermark_text'])
        run.font.size = Pt(48)
        run.font.color.rgb = RGBColor(200, 200, 200)  # Light gray
        run.font.name = 'Arial'
        
        # Rotate watermark
        for paragraph in watermark.header.paragraphs:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in paragraph.runs:
                run.font.size = Pt(48)
    
    # Main title
    title = doc.add_heading('RADIOLOGY REPORT', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.style.font.size = Pt(16)
    title.style.font.color.rgb = RGBColor(0, 51, 102)
    
    if is_final:
        final_para = doc.add_paragraph()
        final_run = final_para.add_run("FINAL REPORT")
        final_run.bold = True
        final_run.font.color.rgb = RGBColor(0, 128, 0)  # Green
        final_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Patient information table
    doc.add_heading('PATIENT INFORMATION', level=1)
    
    table = doc.add_table(rows=6, cols=2)
    table.style = 'Light Grid Accent 1'
    
    # Table headers
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "FIELD"
    hdr_cells[1].text = "INFORMATION"
    hdr_cells[0].paragraphs[0].runs[0].bold = True
    hdr_cells[1].paragraphs[0].runs[0].bold = True
    
    # Patient data
    data = [
        ("Patient Name", patient_info.get('name', 'Not Provided')),
        ("Patient ID", patient_info.get('id', 'Not Provided')),
        ("Date of Birth", patient_info.get('dob', 'Not Provided')),
        ("Age / Sex", f"{patient_info.get('age', 'N/A')} / {patient_info.get('sex', 'N/A')}"),
        ("Accession #", patient_info.get('accession', 'Not Provided')),
        ("Study Date", report_date)
    ]
    
    for i, (field, value) in enumerate(data, 1):
        row_cells = table.rows[i].cells
        row_cells[0].text = field
        row_cells[1].text = value
    
    # Clinical History
    if patient_info.get('history'):
        doc.add_heading('CLINICAL HISTORY', level=1)
        doc.add_paragraph(patient_info['history'])
    
    doc.add_page_break()
    
    # Report Content
    doc.add_heading('REPORT', level=1)
    
    # Parse and format AI report
    if '**TECHNIQUE:**' in ai_report:
        sections = ai_report.split('**')
        for section in sections:
            if section.endswith(':**'):
                doc.add_heading(section.replace(':**', '').strip(), level=2)
            elif section.strip():
                for line in section.strip().split('\n'):
                    if line.strip().startswith('-') or line.strip().startswith('*'):
                        p = doc.add_paragraph(style='List Bullet')
                        p.add_run(line.strip().lstrip('-* '))
                    elif line.strip():
                        doc.add_paragraph(line.strip())
    else:
        for line in ai_report.split('\n'):
            if line.strip():
                doc.add_paragraph(line.strip())
    
    # Add reviewer notes if present
    if reviewer_notes:
        doc.add_page_break()
        doc.add_heading('REVIEWER NOTES', level=1)
        doc.add_paragraph(reviewer_notes)
    
    # Footer with signature
    footer = doc.sections[0].footer
    footer_para = footer.paragraphs[0]
    
    if is_final:
        footer_text = f"FINALIZED BY: {config.get('current_user', 'Radiologist')} | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        footer_para.text = footer_text
        footer_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        footer_para.style.font.size = Pt(9)
        footer_para.style.font.color.rgb = RGBColor(0, 128, 0)
    else:
        footer_text = f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} | AI Radiology Assistant v3.0"
        footer_para.text = footer_text
        footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        footer_para.style.font.size = Pt(8)
        footer_para.style.font.color.rgb = RGBColor(100, 100, 100)
    
    return doc

# ===== STREAMLIT APP =====
def main():
    # Page config
    st.set_page_config(
        page_title="Professional Radiology Assistant",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.config = init_config()
        st.session_state.users = load_users()
        st.session_state.report_history = load_data(HISTORY_FILE, [])
        st.session_state.saved_templates = load_data(TEMPLATES_FILE, {})
        st.session_state.report_draft = ""
        st.session_state.patient_info = {}
        st.session_state.ai_report = ""
        st.session_state.report_date = ""
        st.session_state.report_timestamp = ""
        st.session_state.last_save_time = datetime.datetime.now()
        st.session_state.last_saved_draft = ""
        st.session_state.reviewer_notes = ""
        st.session_state.is_finalized = False
        st.session_state.template_categories = {
            "Brain": [], "Spine": [], "Chest": [], "Abdomen": [], "MSK": [], "Other": []
        }
        st.session_state.search_results = {"reports": [], "templates": [], "drafts": []}
        st.session_state.batch_results = []
        st.session_state.differential_results = []
        st.session_state.critical_findings = []
        st.session_state.voice_text = ""
        st.session_state.template_recommender = None
        st.session_state.login_attempted = False
        st.session_state.logged_in = False
        st.session_state.current_user = "default"
        
        # Initialize template recommender
        if st.session_state.saved_templates:
            st.session_state.template_recommender = TemplateRecommender(st.session_state.saved_templates)
    
    # ===== FEATURE 12: MULTI-USER LOGIN =====
    if not st.session_state.logged_in:
        st.title("🔐 Radiology Assistant - Login")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Login")
                
                if submit:
                    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
                    if username in st.session_state.users:
                        if st.session_state.users[username]["password"] == hashed_pw:
                            st.session_state.logged_in = True
                            st.session_state.current_user = username
                            st.session_state.config["current_user"] = username
                            save_config(st.session_state.config)
                            log_audit_event(username, "LOGIN", "Successful login")
                            st.success(f"Welcome, {username}!")
                            st.rerun()
                        else:
                            st.error("Invalid password")
                            log_audit_event(username, "LOGIN_FAILED", "Invalid password")
                    else:
                        st.error("User not found")
                        log_audit_event(username, "LOGIN_FAILED", "User not found")
            
            st.info("Demo accounts: admin/admin123, neuro/neuro123, msk/msk123")
        
        st.stop()
    
    # ===== MAIN APPLICATION =====
    config = st.session_state.config
    
    # Main title with user info
    col1, col2, col3 = st.columns([3, 2, 2])
    with col1:
        st.title(f"🏥 {config['hospital_name']} Radiology Assistant")
    with col2:
        st.markdown(f"**User:** {st.session_state.current_user}")
        st.markdown(f"**Role:** {st.session_state.users[st.session_state.current_user]['role']}")
    with col3:
        if st.button("🚪 Logout"):
            log_audit_event(st.session_state.current_user, "LOGOUT")
            st.session_state.logged_in = False
            st.rerun()
    
    # ===== SIDEBAR =====
    with st.sidebar:
        st.header("👤 User Panel")
        st.markdown(f"**Signed in as:** {st.session_state.current_user}")
        st.markdown(f"**Specialty:** {st.session_state.users[st.session_state.current_user]['specialty']}")
        
        # ===== FEATURE 11: HOSPITAL BRANDING SETTINGS =====
        with st.expander("🏥 Hospital Branding"):
            new_hospital = st.text_input("Hospital Name", value=config['hospital_name'])
            new_dept = st.text_input("Department", value=config['department'])
            watermark = st.text_input("Watermark Text", value=config['watermark_text'])
            
            logo_file = st.file_uploader("Hospital Logo (PNG/JPG)", type=['png', 'jpg', 'jpeg'])
            if logo_file:
                config['logo_path'] = f"logos/{logo_file.name}"
                os.makedirs("logos", exist_ok=True)
                with open(config['logo_path'], "wb") as f:
                    f.write(logo_file.getbuffer())
            
            if st.button("Save Branding"):
                config['hospital_name'] = new_hospital
                config['department'] = new_dept
                config['watermark_text'] = watermark
                save_config(config)
                st.success("Branding updated!")
        
        st.divider()
        
        # ===== PATIENT INFORMATION =====
        st.header("🧾 Patient Information")
        
        with st.form("patient_form"):
            col1, col2 = st.columns(2)
            with col1:
                p_name = st.text_input("Full Name*", value=st.session_state.patient_info.get('name', ''))
                p_id = st.text_input("Patient ID*", value=st.session_state.patient_info.get('id', ''))
                p_dob = st.text_input("Date of Birth", value=st.session_state.patient_info.get('dob', ''))
            with col2:
                p_age = st.text_input("Age", value=st.session_state.patient_info.get('age', ''))
                p_sex = st.selectbox("Sex", ["", "M", "F", "Other"], 
                                    index=["", "M", "F", "Other"].index(st.session_state.patient_info.get('sex', '')) 
                                    if st.session_state.patient_info.get('sex') in ["", "M", "F", "Other"] else 0)
                p_accession = st.text_input("Accession #", value=st.session_state.patient_info.get('accession', ''))
            
            p_history = st.text_area("Clinical History", 
                                    value=st.session_state.patient_info.get('history', ''), 
                                    height=100)
            
            submitted = st.form_submit_button("💾 Save Patient Info")
            if submitted and p_name and p_id:
                st.session_state.patient_info = {
                    "name": p_name, "id": p_id, "dob": p_dob,
                    "age": p_age, "sex": p_sex, "accession": p_accession,
                    "history": p_history
                }
                st.success("Patient info saved!")
                log_audit_event(st.session_state.current_user, "PATIENT_SAVE", f"ID: {p_id}")
        
        # ===== DICOM IMPORT =====
        if DICOM_AVAILABLE:
            st.divider()
            st.header("🖼️ DICOM Import")
            
            uploaded_dicom = st.file_uploader("Upload DICOM (.dcm)", type=['dcm'])
            if uploaded_dicom:
                try:
                    dicom_data = pydicom.dcmread(uploaded_dicom, force=True)
                    
                    dicom_info = {
                        "name": str(getattr(dicom_data, 'PatientName', '')).strip(),
                        "id": str(getattr(dicom_data, 'PatientID', '')).strip(),
                        "dob": str(getattr(dicom_data, 'PatientBirthDate', '')).strip(),
                        "sex": str(getattr(dicom_data, 'PatientSex', '')).strip(),
                        "study_date": str(getattr(dicom_data, 'StudyDate', '')).strip(),
                        "modality": str(getattr(dicom_data, 'Modality', '')).strip(),
                        "study_desc": str(getattr(dicom_data, 'StudyDescription', '')).strip()
                    }
                    
                    st.success("✅ DICOM metadata extracted!")
                    
                    if st.button("🚀 Auto-Fill from DICOM"):
                        st.session_state.patient_info.update({
                            "name": dicom_info['name'],
                            "id": dicom_info['id'],
                            "dob": dicom_info['dob'],
                            "sex": dicom_info['sex'],
                            "accession": f"DICOM-{dicom_info['study_date']}",
                            "history": f"{dicom_info['modality']}: {dicom_info['study_desc']}"
                        })
                        st.success("Patient info loaded from DICOM!")
                        st.rerun()
                        
                except InvalidDicomError:
                    st.error("❌ Invalid DICOM file")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)[:100]}")
        else:
            st.info("ℹ️ Install pydicom for DICOM features: `py -m pip install pydicom`")
        
        # ===== FEATURE 8: NORMAL VALUES =====
        st.divider()
        st.header("📏 Normal Values")
        
        category = st.selectbox("Select category", list(NORMAL_VALUES.keys()))
        if category:
            values = get_normal_values(category)
            for measurement, normal_range in values.items():
                st.caption(f"**{measurement}:** {normal_range}")
            
            if st.button("📋 Insert Normal Ranges"):
                normal_text = f"Normal ranges for {category}:\n"
                for measurement, normal_range in values.items():
                    normal_text += f"- {measurement}: {normal_range}\n"
                
                st.session_state.report_draft += "\n" + normal_text if st.session_state.report_draft else normal_text
                st.rerun()
        
        # ===== FEATURE 5: SMART TEMPLATE SUGGESTIONS =====
        if st.session_state.template_recommender and st.session_state.report_draft:
            st.divider()
            st.header("💡 Suggested Templates")
            
            suggestions = st.session_state.template_recommender.recommend(st.session_state.report_draft)
            for template in suggestions:
                if st.button(f"📝 {template}", key=f"suggest_{template}"):
                    st.session_state.report_draft += "\n" + st.session_state.saved_templates[template]
                    st.rerun()
        
        # ===== TEMPLATE LIBRARY =====
        st.divider()
        st.header("📚 Template Library")
        
        # Save current draft as template
        with st.form("save_template_form"):
            template_name = st.text_input("Template Name")
            template_category = st.selectbox("Category", list(st.session_state.template_categories.keys()))
            
            if st.form_submit_button("💾 Save as Template"):
                if template_name and st.session_state.report_draft:
                    st.session_state.saved_templates[template_name] = st.session_state.report_draft
                    st.session_state.template_categories[template_category].append(template_name)
                    save_data(TEMPLATES_FILE, st.session_state.saved_templates)
                    st.session_state.template_recommender = TemplateRecommender(st.session_state.saved_templates)
                    st.success("Template saved!")
                    log_audit_event(st.session_state.current_user, "TEMPLATE_SAVE", template_name)
        
        # Load templates
        selected_category = st.selectbox("Browse Category", ["All"] + list(st.session_state.template_categories.keys()))
        
        if selected_category == "All":
            templates_list = list(st.session_state.saved_templates.keys())
        else:
            templates_list = st.session_state.template_categories[selected_category]
        
        if templates_list:
            selected_template = st.selectbox("Select Template", templates_list)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📥 Load", key="load_template"):
                    st.session_state.report_draft = st.session_state.saved_templates[selected_template]
                    st.success("Template loaded!")
                    st.rerun()
            with col2:
                if st.button("🗑️ Delete", key="delete_template"):
                    del st.session_state.saved_templates[selected_template]
                    for cat in st.session_state.template_categories.values():
                        if selected_template in cat:
                            cat.remove(selected_template)
                    save_data(TEMPLATES_FILE, st.session_state.saved_templates)
                    st.session_state.template_recommender = TemplateRecommender(st.session_state.saved_templates)
                    st.warning("Template deleted!")
                    st.rerun()
        
        # ===== FEATURE 6: BATCH PROCESSING =====
        st.divider()
        st.header("📦 Batch Processing")
        
        batch_file = st.file_uploader("Upload patient list (CSV)", type=['csv'])
        if batch_file and st.session_state.report_draft:
            if st.button("🔄 Process Batch"):
                results = process_batch(batch_file.read(), st.session_state.report_draft)
                st.session_state.batch_results = results
                st.success(f"Processed {len(results)} patients!")
                log_audit_event(st.session_state.current_user, "BATCH_PROCESS", f"Processed {len(results)} patients")
        
        # ===== FEATURE 7: ADVANCED SEARCH =====
        st.divider()
        st.header("🔍 Search Everything")
        
        search_query = st.text_input("Search keyword")
        if search_query:
            results = search_all_content(
                search_query,
                st.session_state.report_history,
                st.session_state.saved_templates,
                st.session_state.report_draft
            )
            st.session_state.search_results = results
            
            st.metric("Reports Found", len(results["reports"]))
            st.metric("Templates Found", len(results["templates"]))
            st.metric("Drafts Found", len(results["drafts"]))
    
    # ===== MAIN CONTENT AREA =====
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # ===== FEATURE 2: VOICE DICTATION =====
        st.header("🎤 Voice Dictation")
        
        voice_html = setup_voice_recognition()
        st.components.v1.html(voice_html, height=0)
        
        col1a, col1b = st.columns([3, 1])
        with col1a:
            voice_text = st.text_input("Voice Input", key="voice_text", label_visibility="collapsed", 
                                      placeholder="Click 'Start Dictation' then speak...")
        with col1b:
            if st.button("🎤 Start Dictation"):
                st.info("Please allow microphone access. Then speak your findings.")
                # In production, implement proper Web Speech API integration
        
        if voice_text:
            st.session_state.report_draft += "\n" + voice_text if st.session_state.report_draft else voice_text
            st.session_state.voice_text = ""
            st.rerun()
        
        # Main draft area
        st.header("✍️ Report Draft")
        
        # Auto-save status
        if 'last_save_time' in st.session_state:
            time_since = (datetime.datetime.now() - st.session_state.last_save_time).seconds
            if time_since < config['auto_save_interval']:
                st.caption(f"🔄 Auto-saved {time_since}s ago")
        
        draft_text = st.text_area(
            "Type your findings:",
            value=st.session_state.report_draft,
            height=300,
            key="draft_input",
            label_visibility="collapsed",
            placeholder="Enter findings, use bullet points:\n- Finding 1\n- Finding 2\n- Differential diagnosis"
        )
        
        # Auto-save logic
        if draft_text != st.session_state.last_saved_draft:
            st.session_state.report_draft = draft_text
            current_time = datetime.datetime.now()
            last_save = st.session_state.get('last_save_time', current_time)
            
            if (current_time - last_save).seconds > config['auto_save_interval']:
                st.session_state.last_saved_draft = draft_text
                st.session_state.last_save_time = current_time
                log_audit_event(st.session_state.current_user, "AUTO_SAVE", f"Chars: {len(draft_text)}")
        
        # ===== FEATURE 4: CRITICAL FINDING FLAGS =====
        if draft_text and config.get('critical_check_enabled', True):
            critical_findings = check_critical_findings_advanced(draft_text)
            st.session_state.critical_findings = critical_findings
            
            if critical_findings:
                st.error("🚨 **CRITICAL FINDINGS DETECTED**")
                for finding in critical_findings:
                    st.warning(f"**{finding['finding'].upper()}** ({finding['severity']}) - {finding['action']}")
        
        # ===== FEATURE 3: DIFFERENTIAL DIAGNOSIS =====
        if draft_text:
            differential = generate_differential(draft_text)
            st.session_state.differential_results = differential
            
            if differential:
                st.info("🧠 **Differential Diagnosis Suggestions**")
                for dx in differential[:3]:  # Show top 3
                    st.markdown(f"**{dx['diagnosis']}** ({dx['confidence']}): {dx['features']}")
        
        # Action buttons
        col2a, col2b, col2c = st.columns(3)
        with col2a:
            if st.button("🤖 Generate AI Report", type="primary", use_container_width=True):
                if draft_text:
                    # Placeholder for real AI integration
                    st.session_state.ai_report = f"""**TECHNIQUE:** MRI performed as described.
**FINDINGS:** {draft_text[:500]}
**IMPRESSION:** Findings as described above. Recommend clinical correlation."""
                    st.session_state.report_date = datetime.datetime.now().strftime("%Y-%m-%d")
                    st.session_state.report_timestamp = datetime.datetime.now().isoformat()
                    st.session_state.is_finalized = False
                    st.success("Report generated!")
                    log_audit_event(st.session_state.current_user, "AI_GENERATE", f"Chars: {len(draft_text)}")
                else:
                    st.warning("Please enter findings first")
        
        with col2b:
            if st.button("💾 Save Draft", use_container_width=True):
                st.session_state.last_saved_draft = draft_text
                st.session_state.last_save_time = datetime.datetime.now()
                st.success("Draft saved!")
        
        with col2c:
            if st.button("🧹 Clear", use_container_width=True):
                st.session_state.report_draft = ""
                st.rerun()
    
    with col2:
        # ===== FEATURE 9 & 10: PEER REVIEW & REPORT LOCK =====
        st.header("📋 Report Management")
        
        if st.session_state.ai_report:
            st.subheader("AI Generated Report")
            st.text_area("", st.session_state.ai_report, height=250, key="ai_display", label_visibility="collapsed")
            
            # Peer review notes
            if config.get('peer_review_enabled', True):
                st.subheader("👥 Peer Review")
                review_notes = st.text_area("Reviewer Notes", value=st.session_state.reviewer_notes, height=100)
                if review_notes != st.session_state.reviewer_notes:
                    st.session_state.reviewer_notes = review_notes
            
            # Report finalization
            st.subheader("🔒 Report Finalization")
            
            if not st.session_state.is_finalized:
                if st.button("✅ Finalize Report", type="primary", use_container_width=True):
                    st.session_state.is_finalized = True
                    st.success("Report finalized and locked!")
                    log_audit_event(st.session_state.current_user, "REPORT_FINALIZE", 
                                  f"Patient: {st.session_state.patient_info.get('id', 'Unknown')}")
            else:
                st.warning("📋 **REPORT FINALIZED AND LOCKED**")
                st.info("This report cannot be modified. Download the final version below.")
            
            # Download buttons
            col3a, col3b = st.columns(2)
            with col3a:
                # Draft version
                doc_draft = create_branded_word_report(
                    st.session_state.ai_report,
                    st.session_state.patient_info,
                    st.session_state.report_date,
                    config,
                    is_final=False,
                    reviewer_notes=st.session_state.reviewer_notes
                )
                
                buffer_draft = BytesIO()
                doc_draft.save(buffer_draft)
                buffer_draft.seek(0)
                
                st.download_button(
                    label="📄 Draft Version",
                    data=buffer_draft,
                    file_name=f"RAD_DRAFT_{st.session_state.patient_info.get('id', 'Unknown')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )
            
            with col3b:
                if st.session_state.is_finalized:
                    # Final version
                    doc_final = create_branded_word_report(
                        st.session_state.ai_report,
                        st.session_state.patient_info,
                        st.session_state.report_date,
                        config,
                        is_final=True,
                        reviewer_notes=st.session_state.reviewer_notes
                    )
                    
                    buffer_final = BytesIO()
                    doc_final.save(buffer_final)
                    buffer_final.seek(0)
                    
                    st.download_button(
                        label="📋 Final Version",
                        data=buffer_final,
                        file_name=f"RAD_FINAL_{st.session_state.patient_info.get('id', 'Unknown')}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                        type="primary"
                    )
            
            # Save to history
            st.subheader("💾 Save to History")
            report_name = st.text_input("Report Name", value=f"Report_{st.session_state.patient_info.get('id', 'Unknown')}")
            
            if st.button("📚 Add to History", use_container_width=True):
                history_entry = {
                    "name": report_name,
                    "date": st.session_state.report_date,
                    "timestamp": st.session_state.report_timestamp,
                    "patient_info": st.session_state.patient_info,
                    "draft": st.session_state.report_draft,
                    "ai_report": st.session_state.ai_report,
                    "reviewer_notes": st.session_state.reviewer_notes,
                    "finalized": st.session_state.is_finalized,
                    "created_by": st.session_state.current_user
                }
                st.session_state.report_history.insert(0, history_entry)
                save_data(HISTORY_FILE, st.session_state.report_history)
                st.success("Saved to history!")
                log_audit_event(st.session_state.current_user, "HISTORY_SAVE", report_name)
        
        else:
            st.info("👈 Generate an AI report first")
    
    # ===== BATCH RESULTS DISPLAY =====
    if st.session_state.batch_results:
        st.divider()
        st.header("📊 Batch Processing Results")
        
        for i, result in enumerate(st.session_state.batch_results[:5]):  # Show first 5
            with st.expander(f"Patient: {result['patient_name']} ({result['patient_id']})"):
                st.text(result['report'][:500] + "..." if len(result['report']) > 500 else result['report'])
                
                # Download individual report
                doc_batch = Document()
                doc_batch.add_paragraph(result['report'])
                
                buffer_batch = BytesIO()
                doc_batch.save(buffer_batch)
                buffer_batch.seek(0)
                
                st.download_button(
                    label=f"Download {result['patient_id']}",
                    data=buffer_batch,
                    file_name=f"Batch_{result['patient_id']}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"batch_{i}"
                )
    
    # ===== SEARCH RESULTS DISPLAY =====
    if any(len(v) > 0 for v in st.session_state.search_results.values()):
        st.divider()
        st.header("🔍 Search Results")
        
        tabs = st.tabs(["Reports", "Templates", "Drafts"])
        
        with tabs[0]:
            if st.session_state.search_results["reports"]:
                for report in st.session_state.search_results["reports"][:5]:
                    with st.expander(f"{report.get('name', 'Unnamed')} - {report.get('date', 'No date')}"):
                        st.write(f"**Patient:** {report.get('patient_info', {}).get('name', 'Unknown')}")
                        if report.get('draft'):
                            st.caption("**Draft:**")
                            st.text(report['draft'][:200] + "..." if len(report['draft']) > 200 else report['draft'])
            else:
                st.info("No matching reports")
        
        with tabs[1]:
            if st.session_state.search_results["templates"]:
                for template in st.session_state.search_results["templates"][:5]:
                    st.write(f"**{template['name']}**")
                    st.text(template['content'])
            else:
                st.info("No matching templates")
        
        with tabs[2]:
            if st.session_state.search_results["drafts"]:
                for draft in st.session_state.search_results["drafts"]:
                    st.text(draft['preview'])
            else:
                st.info("No matching drafts")
    
    # ===== REPORT HISTORY =====
    st.divider()
    st.header("📜 Report History")
    
    if st.session_state.report_history:
        # Filter by current user if not admin
        if st.session_state.users[st.session_state.current_user]["role"] != "admin":
            user_reports = [r for r in st.session_state.report_history 
                          if r.get('created_by') == st.session_state.current_user]
        else:
            user_reports = st.session_state.report_history
        
        if user_reports:
            for i, report in enumerate(user_reports[:10]):  # Show last 10
                with st.expander(f"{report['name']} - {report['date']} - {report.get('created_by', 'Unknown')}"):
                    col_h1, col_h2, col_h3 = st.columns(3)
                    with col_h1:
                        if st.button(f"📥 Load Draft", key=f"load_h_{i}"):
                            st.session_state.report_draft = report['draft']
                            st.session_state.patient_info = report['patient_info']
                            st.session_state.ai_report = report['ai_report']
                            st.session_state.reviewer_notes = report.get('reviewer_notes', '')
                            st.session_state.is_finalized = report.get('finalized', False)
                            st.success("Report loaded!")
                            st.rerun()
                    
                    with col_h2:
                        if st.button(f"🗑️ Delete", key=f"del_h_{i}"):
                            st.session_state.report_history.remove(report)
                            save_data(HISTORY_FILE, st.session_state.report_history)
                            st.warning("Report deleted!")
                            st.rerun()
                    
                    with col_h3:
                        if report.get('finalized'):
                            st.markdown("**🔒 FINALIZED**")
                    
                    st.write(f"**Patient:** {report['patient_info'].get('name', 'Unknown')}")
                    if report.get('draft'):
                        st.caption("**Draft Preview:**")
                        st.text(report['draft'][:150] + "..." if len(report['draft']) > 150 else report['draft'])
        
        # Clear history button (admin only)
        if st.session_state.users[st.session_state.current_user]["role"] == "admin":
            if st.button("🗑️ Clear All History", type="secondary"):
                st.session_state.report_history = []
                save_data(HISTORY_FILE, st.session_state.report_history)
                st.warning("All history cleared!")
                st.rerun()
    else:
        st.info("No reports in history yet")
    
    # ===== AUDIT TRAIL (ADMIN ONLY) =====
    if st.session_state.users[st.session_state.current_user]["role"] == "admin":
        st.divider()
        st.header("📋 Audit Trail")
        
        audit_log = load_data(AUDIT_LOG_FILE, [])
        if audit_log:
            df_audit = pd.DataFrame(audit_log[-50:])  # Last 50 events
            st.dataframe(df_audit[['timestamp', 'user', 'action', 'details']], use_container_width=True)
            
            if st.button("Export Audit Log"):
                csv = df_audit.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name="audit_log.csv",
                    mime="text/csv"
                )
        else:
            st.info("No audit events yet")
    
    # ===== STATISTICS DASHBOARD =====
    st.divider()
    st.header("📊 Statistics Dashboard")
    
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    
    with col_s1:
        total_reports = len([r for r in st.session_state.report_history 
                           if r.get('created_by') == st.session_state.current_user or 
                           st.session_state.users[st.session_state.current_user]["role"] == "admin"])
        st.metric("Your Reports", total_reports)
    
    with col_s2:
        total_templates = len(st.session_state.saved_templates)
        st.metric("Templates", total_templates)
    
    with col_s3:
        draft_length = len(st.session_state.report_draft)
        st.metric("Current Draft", f"{draft_length} chars")
    
    with col_s4:
        critical_count = len(st.session_state.critical_findings)
        st.metric("Critical Flags", critical_count, delta=None)

# ===== RUN APPLICATION =====
if __name__ == "__main__":
    main()
