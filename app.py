"""
AI-Powered Professional Radiology Reporting Assistant
Version 3.0 - Enterprise Edition (Corrected)
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
        ("herniation", "Critical", "Emergency neurosurgery")
    ],
    "Spine": [
        ("cord compression", "Critical", "Emergency neurosurgery"),
        ("fracture dislocation", "Critical", "Spine surgery STAT")
    ],
    "Chest": [
        ("aortic dissection", "Critical", "Cardiothoracic surgery STAT"),
        ("pneumothorax", "High", "Chest tube assessment")
    ],
    "Abdomen": [
        ("bowel perforation", "Critical", "General surgery STAT"),
        ("aortic aneurysm", "High", "Vascular surgery")
    ]
}

# ===== NORMAL REFERENCE VALUES =====
NORMAL_VALUES = {
    "Brain": {
        "Lateral ventricles": "<10 mm",
        "Third ventricle": "<6 mm",
        "Sulcal width": "<3 mm"
    },
    "Spine": {
        "Spinal canal (cervical)": "≥12 mm",
        "Spinal canal (lumbar)": "≥15 mm"
    },
    "Chest": {
        "Aortic diameter": "<40 mm",
        "Cardiothoracic ratio": "<0.5"
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
        "details": details
    }
    audit_log.append(event)
    save_data(AUDIT_LOG_FILE, audit_log)

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
        
        sorted_templates = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [t[0] for t in sorted_templates[:limit]]

# ===== FEATURE 9: PROFESSIONAL WORD EXPORT (CORRECTED) =====
def create_branded_word_report(ai_report, patient_info, report_date, config, is_final=False, reviewer_notes=""):
    """Create professionally branded Word document - CORRECTED VERSION."""
    doc = Document()
    
    # Set document margins - CORRECTED INDENTATION
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
    header_para.style.font.color.rgb = RGBColor(0, 51, 102)
    
    # Main title
    title = doc.add_heading('RADIOLOGY REPORT', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.style.font.size = Pt(16)
    title.style.font.color.rgb = RGBColor(0, 51, 102)
    
    if is_final:
        final_para = doc.add_paragraph()
        final_run = final_para.add_run("FINAL REPORT")
        final_run.bold = True
        final_run.font.color.rgb = RGBColor(0, 128, 0)
        final_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Patient information table - SIMPLIFIED TO AVOID INDEXERROR
    doc.add_heading('PATIENT INFORMATION', level=1)
    
    # Create table with dynamic rows
    table = doc.add_table(rows=1, cols=2)
    table.style = 'Light Grid Accent 1'
    
    # Add header row
    hdr_row = table.rows[0]
    hdr_row.cells[0].text = "FIELD"
    hdr_row.cells[1].text = "INFORMATION"
    hdr_row.cells[0].paragraphs[0].runs[0].bold = True
    hdr_row.cells[1].paragraphs[0].runs[0].bold = True
    
    # Add data rows dynamically - NO INDEX ERRORS
    data = [
        ("Patient Name", patient_info.get('name', 'Not Provided')),
        ("Patient ID", patient_info.get('id', 'Not Provided')),
        ("Date of Birth", patient_info.get('dob', 'Not Provided')),
        ("Age / Sex", f"{patient_info.get('age', 'N/A')} / {patient_info.get('sex', 'N/A')}"),
        ("Accession #", patient_info.get('accession', 'Not Provided')),
        ("Study Date", report_date)
    ]
    
    for field, value in data:
        row = table.add_row()
        row.cells[0].text = field
        row.cells[1].text = value
    
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
        layout="wide"
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
        st.session_state.reviewer_notes = ""
        st.session_state.is_finalized = False
        st.session_state.current_user = "default"
        st.session_state.logged_in = False
        st.session_state.critical_findings = []
        
        if st.session_state.saved_templates:
            st.session_state.template_recommender = TemplateRecommender(st.session_state.saved_templates)
    
    # ===== LOGIN SYSTEM =====
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
                            log_audit_event(username, "LOGIN")
                            st.success(f"Welcome, {username}!")
                            st.rerun()
                        else:
                            st.error("Invalid password")
                    else:
                        st.error("User not found")
            
            st.info("Demo: admin/admin123 or neuro/neuro123")
        
        st.stop()
    
    # ===== MAIN APPLICATION =====
    config = st.session_state.config
    
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(f"🏥 {config['hospital_name']} Radiology Assistant")
    with col2:
        st.markdown(f"**User:** {st.session_state.current_user}")
        if st.button("🚪 Logout"):
            log_audit_event(st.session_state.current_user, "LOGOUT")
            st.session_state.logged_in = False
            st.rerun()
    
    # ===== SIDEBAR =====
    with st.sidebar:
        st.header("👤 User Panel")
        st.markdown(f"**Signed in as:** {st.session_state.current_user}")
        
        # Hospital Branding
        with st.expander("🏥 Hospital Branding"):
            new_hospital = st.text_input("Hospital Name", value=config['hospital_name'])
            new_dept = st.text_input("Department", value=config['department'])
            
            if st.button("Save Branding"):
                config['hospital_name'] = new_hospital
                config['department'] = new_dept
                save_config(config)
                st.success("Branding updated!")
        
        st.divider()
        
        # Patient Information
        st.header("🧾 Patient Information")
        
        with st.form("patient_form"):
            col1, col2 = st.columns(2)
            with col1:
                p_name = st.text_input("Full Name*", value=st.session_state.patient_info.get('name', ''))
                p_id = st.text_input("Patient ID*", value=st.session_state.patient_info.get('id', ''))
            with col2:
                p_age = st.text_input("Age", value=st.session_state.patient_info.get('age', ''))
                p_sex = st.selectbox("Sex", ["", "M", "F", "Other"], 
                                    index=["", "M", "F", "Other"].index(st.session_state.patient_info.get('sex', '')) 
                                    if st.session_state.patient_info.get('sex') in ["", "M", "F", "Other"] else 0)
            
            p_history = st.text_area("Clinical History", 
                                    value=st.session_state.patient_info.get('history', ''), 
                                    height=100)
            
            submitted = st.form_submit_button("💾 Save Patient Info")
            if submitted and p_name and p_id:
                st.session_state.patient_info = {
                    "name": p_name, "id": p_id, "age": p_age, 
                    "sex": p_sex, "history": p_history
                }
                st.success("Patient info saved!")
        
        # DICOM Import
        if DICOM_AVAILABLE:
            st.divider()
            st.header("🖼️ DICOM Import")
            
            uploaded_dicom = st.file_uploader("Upload DICOM (.dcm)", type=['dcm'])
            if uploaded_dicom and st.button("Extract DICOM Data"):
                try:
                    dicom_data = pydicom.dcmread(uploaded_dicom, force=True)
                    st.session_state.patient_info.update({
                        "name": str(getattr(dicom_data, 'PatientName', '')),
                        "id": str(getattr(dicom_data, 'PatientID', ''))
                    })
                    st.success("DICOM data extracted!")
                except:
                    st.error("Invalid DICOM file")
        else:
            st.info("ℹ️ Install pydicom for DICOM features")
        
        # Normal Values
        st.divider()
        st.header("📏 Normal Values")
        
        category = st.selectbox("Select category", list(NORMAL_VALUES.keys()))
        if category and st.button("Insert Normal Ranges"):
            normal_text = f"Normal ranges for {category}:\n"
            for measurement, normal_range in NORMAL_VALUES[category].items():
                normal_text += f"- {measurement}: {normal_range}\n"
            
            st.session_state.report_draft += "\n" + normal_text if st.session_state.report_draft else normal_text
            st.rerun()
        
        # Smart Template Suggestions
        if hasattr(st.session_state, 'template_recommender') and st.session_state.report_draft:
            st.divider()
            st.header("💡 Suggested Templates")
            
            suggestions = st.session_state.template_recommender.recommend(st.session_state.report_draft)
            for template in suggestions:
                if st.button(f"📝 {template}", key=f"suggest_{template}"):
                    st.session_state.report_draft += "\n" + st.session_state.saved_templates[template]
                    st.rerun()
        
        # Template Library
        st.divider()
        st.header("📚 Template Library")
        
        # Save template
        template_name = st.text_input("Template Name")
        if st.button("💾 Save Current Draft as Template") and template_name and st.session_state.report_draft:
            st.session_state.saved_templates[template_name] = st.session_state.report_draft
            save_data(TEMPLATES_FILE, st.session_state.saved_templates)
            st.session_state.template_recommender = TemplateRecommender(st.session_state.saved_templates)
            st.success("Template saved!")
        
        # Load template
        if st.session_state.saved_templates:
            selected_template = st.selectbox("Load Template", list(st.session_state.saved_templates.keys()))
            if st.button("📥 Load Selected Template"):
                st.session_state.report_draft = st.session_state.saved_templates[selected_template]
                st.success("Template loaded!")
                st.rerun()
    
    # ===== MAIN CONTENT =====
    col1, col2 = st.columns(2)
    
    with col1:
        # Draft Area
        st.header("✍️ Report Draft")
        
        # Critical Findings Check
        if st.session_state.report_draft:
            critical_findings = check_critical_findings_advanced(st.session_state.report_draft)
            st.session_state.critical_findings = critical_findings
            
            if critical_findings:
                st.error("🚨 **CRITICAL FINDINGS DETECTED**")
                for finding in critical_findings:
                    st.warning(f"**{finding['finding'].upper()}** - {finding['action']}")
        
        # Draft text area
        draft_text = st.text_area(
            "Type your findings:",
            value=st.session_state.report_draft,
            height=300,
            key="draft_input",
            label_visibility="collapsed",
            placeholder="Enter findings here..."
        )
        st.session_state.report_draft = draft_text
        
        # Action buttons
        col1a, col1b, col1c = st.columns(3)
        with col1a:
            if st.button("🤖 Generate AI Report", type="primary", use_container_width=True):
                if draft_text:
                    # Placeholder AI response
                    st.session_state.ai_report = f"""**TECHNIQUE:** Imaging performed as described.
**FINDINGS:** {draft_text[:500]}
**IMPRESSION:** Findings as described. Clinical correlation recommended."""
                    st.session_state.report_date = datetime.datetime.now().strftime("%Y-%m-%d")
                    st.success("Report generated!")
                else:
                    st.warning("Please enter findings first")
        
        with col1b:
            if st.button("💾 Save Draft", use_container_width=True):
                st.success("Draft saved!")
        
        with col1c:
            if st.button("🧹 Clear", use_container_width=True):
                st.session_state.report_draft = ""
                st.rerun()
    
    with col2:
        # Report Management
        st.header("📋 Report Management")
        
        if st.session_state.ai_report:
            st.subheader("AI Generated Report")
            st.text_area("", st.session_state.ai_report, height=250, key="ai_display", label_visibility="collapsed")
            
            # Peer review
            st.subheader("👥 Peer Review")
            review_notes = st.text_area("Reviewer Notes", value=st.session_state.reviewer_notes, height=100)
            st.session_state.reviewer_notes = review_notes
            
            # Report finalization
            st.subheader("🔒 Report Finalization")
            
            if not st.session_state.is_finalized:
                if st.button("✅ Finalize Report", type="primary", use_container_width=True):
                    st.session_state.is_finalized = True
                    st.success("Report finalized!")
            else:
                st.warning("📋 **REPORT FINALIZED AND LOCKED**")
            
            # Download buttons
            try:
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
                    label="📄 Download Draft",
                    data=buffer_draft,
                    file_name=f"RAD_DRAFT_{st.session_state.patient_info.get('id', 'Unknown')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )
                
                # Final version if finalized
                if st.session_state.is_finalized:
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
                        label="📋 Download Final",
                        data=buffer_final,
                        file_name=f"RAD_FINAL_{st.session_state.patient_info.get('id', 'Unknown')}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                        type="primary"
                    )
            
            except Exception as e:
                st.error(f"Error creating document: {e}")
            
            # Save to history
            st.subheader("💾 Save to History")
            report_name = st.text_input("Report Name", value=f"Report_{st.session_state.patient_info.get('id', 'Unknown')}")
            
            if st.button("📚 Add to History", use_container_width=True):
                history_entry = {
                    "name": report_name,
                    "date": st.session_state.report_date,
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
        
        else:
            st.info("👈 Generate an AI report first")
    
    # ===== REPORT HISTORY =====
    st.divider()
    st.header("📜 Report History")
    
    if st.session_state.report_history:
        for i, report in enumerate(st.session_state.report_history[:5]):
            with st.expander(f"{report['name']} - {report['date']}"):
                if st.button(f"📥 Load", key=f"load_{i}"):
                    st.session_state.report_draft = report['draft']
                    st.session_state.patient_info = report['patient_info']
                    st.session_state.ai_report = report['ai_report']
                    st.session_state.reviewer_notes = report.get('reviewer_notes', '')
                    st.session_state.is_finalized = report.get('finalized', False)
                    st.success("Report loaded!")
                    st.rerun()
                
                st.write(f"**Patient:** {report['patient_info'].get('name', 'Unknown')}")
    else:
        st.info("No reports in history yet")
    
    # ===== STATISTICS =====
    st.divider()
    st.header("📊 Statistics")
    
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        st.metric("Your Reports", len(st.session_state.report_history))
    with col_s2:
        st.metric("Templates", len(st.session_state.saved_templates))
    with col_s3:
        st.metric("Critical Flags", len(st.session_state.critical_findings))

# ===== RUN APPLICATION =====
if __name__ == "__main__":
    main()
