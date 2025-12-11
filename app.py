"""
AI-Powered Professional Radiology Reporting Assistant
Version 4.0 - Enhanced with Template Upload, Contrast Options & Better Differential UI
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
from docx import Document as DocxDocument

# ===== CONFIGURATION =====
CONFIG_FILE = "radiology_config.json"
HISTORY_FILE = "report_history.json"
TEMPLATES_FILE = "saved_templates.json"
USER_FILE = "users.json"
UPLOADED_TEMPLATES_DIR = "uploaded_templates"

# Create directories if they don't exist
os.makedirs(UPLOADED_TEMPLATES_DIR, exist_ok=True)

# ===== DIFFERENTIAL DIAGNOSIS DATABASE =====
DIFFERENTIAL_DATABASE = {
    "brain_lesion_enhancing": [
        {"diagnosis": "Meningioma", "confidence": "High", "features": "Dural-based, homogeneous enhancement"},
        {"diagnosis": "Metastasis", "confidence": "High", "features": "Multiple, at gray-white junction"},
        {"diagnosis": "Glioblastoma", "confidence": "Medium", "features": "Irregular rim enhancement"}
    ],
    "white_matter": [
        {"diagnosis": "Microvascular ischemia", "confidence": "High", "features": "Periventricular, punctate"},
        {"diagnosis": "Multiple Sclerosis", "confidence": "Medium", "features": "Ovoid, perivenular"},
        {"diagnosis": "Vasculitis", "confidence": "Low", "features": "Multiple territories"}
    ],
    "stroke": [
        {"diagnosis": "Ischemic infarct", "confidence": "High", "features": "Vascular territory, DWI bright"},
        {"diagnosis": "Venous infarct", "confidence": "Medium", "features": "Hemorrhagic, non-arterial"}
    ],
    "spinal_lesion": [
        {"diagnosis": "Disc herniation", "confidence": "High", "features": "Disc material extrusion"},
        {"diagnosis": "Metastasis", "confidence": "Medium", "features": "Vertebral body destruction"},
        {"diagnosis": "Infection", "confidence": "Low", "features": "Epidural abscess"}
    ],
    "lung_nodule": [
        {"diagnosis": "Primary lung cancer", "confidence": "Medium", "features": "Spiculated, >2cm"},
        {"diagnosis": "Metastasis", "confidence": "Medium", "features": "Multiple, peripheral"},
        {"diagnosis": "Granuloma", "confidence": "Low", "features": "Calcified, stable"}
    ],
    "liver_lesion": [
        {"diagnosis": "Hemangioma", "confidence": "High", "features": "Peripheral nodular enhancement"},
        {"diagnosis": "Metastasis", "confidence": "Medium", "features": "Multiple, ring enhancement"},
        {"diagnosis": "HCC", "confidence": "Medium", "features": "Arterial enhancement, washout"}
    ]
}

# ===== ENHANCED TEMPLATE SYSTEM =====
class EnhancedTemplateSystem:
    """Enhanced template system with Word upload support."""
    
    def __init__(self):
        self.templates = {}
        self.uploaded_templates = {}
        self.load_templates()
    
    def load_templates(self):
        """Load templates from file."""
        if os.path.exists(TEMPLATES_FILE):
            with open(TEMPLATES_FILE, 'r') as f:
                self.templates = json.load(f)
        
        # Load uploaded templates info
        uploaded_info_file = os.path.join(UPLOADED_TEMPLATES_DIR, "uploaded_templates.json")
        if os.path.exists(uploaded_info_file):
            with open(uploaded_info_file, 'r') as f:
                self.uploaded_templates = json.load(f)
    
    def save_templates(self):
        """Save templates to file."""
        with open(TEMPLATES_FILE, 'w') as f:
            json.dump(self.templates, f, indent=2)
        
        # Save uploaded templates info
        uploaded_info_file = os.path.join(UPLOADED_TEMPLATES_DIR, "uploaded_templates.json")
        with open(uploaded_info_file, 'w') as f:
            json.dump(self.uploaded_templates, f, indent=2)
    
    def add_template(self, name, content, template_type="findings", source="manual"):
        """Add a new template."""
        self.templates[name] = {
            "content": content,
            "type": template_type,
            "created_by": st.session_state.current_user,
            "created_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "used_count": 0,
            "source": source
        }
        self.save_templates()
    
    def upload_word_template(self, file, template_name, template_type="findings"):
        """Upload and parse a Word document as template."""
        try:
            # Save uploaded file
            file_path = os.path.join(UPLOADED_TEMPLATES_DIR, f"{template_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.docx")
            with open(file_path, "wb") as f:
                f.write(file.getbuffer())
            
            # Parse Word document
            doc = DocxDocument(BytesIO(file.getvalue()))
            content = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    content.append(paragraph.text.strip())
            
            template_content = "\n".join(content)
            
            # Save template info
            self.uploaded_templates[template_name] = {
                "filename": os.path.basename(file_path),
                "type": template_type,
                "uploaded_by": st.session_state.current_user,
                "upload_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "content": template_content
            }
            
            # Also add to regular templates for easy access
            self.add_template(template_name, template_content, template_type, source="word_upload")
            
            self.save_templates()
            return True, template_content
        
        except Exception as e:
            return False, str(e)
    
    def get_template_heading(self, template_name):
        """Get heading format for a template."""
        if template_name in self.templates:
            template = self.templates[template_name]
        elif template_name in self.uploaded_templates:
            template = self.uploaded_templates[template_name]
        else:
            return template_name.upper()
        
        template_type = template.get("type", "findings")
        
        heading_map = {
            "technique": "TECHNIQUE",
            "findings": "FINDINGS",
            "impression": "IMPRESSION",
            "clinical": "CLINICAL HISTORY",
            "differential": "DIFFERENTIAL DIAGNOSIS",
            "comparison": "COMPARISON"
        }
        
        return heading_map.get(template_type, template_name.upper())
    
    def apply_template(self, template_name, current_text=""):
        """Apply a template with proper heading."""
        if template_name not in self.templates and template_name not in self.uploaded_templates:
            return current_text
        
        if template_name in self.templates:
            template = self.templates[template_name]
            content = template['content']
            # Increment usage count
            template["used_count"] = template.get("used_count", 0) + 1
        else:
            template = self.uploaded_templates[template_name]
            content = template['content']
        
        heading = self.get_template_heading(template_name)
        
        # Format with heading
        formatted_template = f"\n\n{heading.upper()}:\n{content}"
        
        if current_text:
            return current_text + formatted_template
        return formatted_template
    
    def get_user_templates(self, username):
        """Get templates created by specific user."""
        user_templates = {}
        for name, data in self.templates.items():
            if data.get("created_by") == username:
                user_templates[name] = data
        
        for name, data in self.uploaded_templates.items():
            if data.get("uploaded_by") == username:
                user_templates[name] = data
        
        return user_templates
    
    def get_all_templates(self):
        """Get all templates including uploaded ones."""
        all_templates = self.templates.copy()
        for name, data in self.uploaded_templates.items():
            if name not in all_templates:
                all_templates[name] = data
        return all_templates

def generate_differential_diagnosis(text):
    """Generate differential diagnosis based on findings."""
    text_lower = text.lower()
    results = []
    
    # Check for patterns in various categories
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
    
    # Remove duplicates
    seen = set()
    unique_results = []
    for r in results:
        key = r['diagnosis']
        if key not in seen:
            seen.add(key)
            unique_results.append(r)
    
    return unique_results[:6]  # Return top 6 suggestions

def create_word_document(patient_info, report_text, report_date, technique_info=None):
    """Create a Word document with proper formatting including patient data."""
    doc = Document()
    
    # Title
    title = doc.add_heading('RADIOLOGY REPORT', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Add spacing
    doc.add_paragraph()
    
    # PATIENT INFORMATION Section - Always included
    doc.add_heading('PATIENT INFORMATION', level=1)
    
    # Create a table for patient data
    patient_table = doc.add_table(rows=5, cols=2)
    patient_table.style = 'Light Grid'
    
    # Fill patient table
    rows_data = [
        ("Patient Name:", patient_info.get('name', 'Not provided')),
        ("Patient ID:", patient_info.get('id', 'Not provided')),
        ("Age/Sex:", f"{patient_info.get('age', 'N/A')}/{patient_info.get('sex', 'N/A')}"),
        ("Clinical History:", patient_info.get('history', 'Not provided')),
        ("Report Date:", report_date if report_date else datetime.datetime.now().strftime("%Y-%m-%d"))
    ]
    
    for i, (label, value) in enumerate(rows_data):
        cells = patient_table.rows[i].cells
        cells[0].text = label
        cells[1].text = str(value)
    
    # Add spacing
    doc.add_paragraph()
    
    # Parse and add report sections
    lines = report_text.split('\n')
    current_heading = None
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            doc.add_paragraph()  # Preserve paragraph breaks
            continue
            
        # Check if line is a heading (ends with colon and is mostly uppercase)
        if line_stripped.endswith(':') and line_stripped[:-1].replace(' ', '').isupper():
            current_heading = line_stripped[:-1]  # Remove colon
            doc.add_heading(current_heading, level=1)
        elif line_stripped.startswith('**') and line_stripped.endswith('**'):
            # Bold text in markdown format
            bold_text = line_stripped.strip('**')
            p = doc.add_paragraph()
            run = p.add_run(bold_text)
            run.bold = True
        elif line_stripped.startswith('- ') or line_stripped.startswith('* '):
            # List item
            p = doc.add_paragraph(style='List Bullet')
            p.add_run(line_stripped[2:])
        elif line_stripped[0].isdigit() and '. ' in line_stripped[:3]:
            # Numbered list
            p = doc.add_paragraph(style='List Number')
            p.add_run(line_stripped.split('. ', 1)[1])
        else:
            # Regular content
            doc.add_paragraph(line_stripped)
    
    # Add footer with radiologist info
    doc.add_page_break()
    doc.add_heading('REPORT DETAILS', level=1)
    p = doc.add_paragraph()
    p.add_run(f"Generated by: {st.session_state.current_user}\n")
    p.add_run(f"Generation date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    if technique_info:
        p.add_run(f"Contrast: {technique_info.get('contrast', 'Not specified')}\n")
    
    return doc

# ===== STREAMLIT APP =====
def main():
    # Page config
    st.set_page_config(
        page_title="Professional Radiology Assistant",
        layout="wide",
        page_icon="🏥"
    )
    
    # Initialize session state
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.config = {
            "current_user": "default",
            "include_hospital_header": True
        }
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
        st.session_state.is_finalized = False
        st.session_state.current_user = "default"
        st.session_state.logged_in = False
        st.session_state.differential_results = []
        st.session_state.template_system = EnhancedTemplateSystem()
        st.session_state.selected_template = ""
        st.session_state.new_template_name = ""
        st.session_state.new_template_content = ""
        st.session_state.new_template_type = "findings"
        st.session_state.technique_info = {
            "modality": "MRI",
            "contrast": "Without contrast",
            "sequences": "Standard sequences"
        }
        st.session_state.uploaded_template_name = ""
        st.session_state.uploaded_template_type = "findings"
        st.session_state.show_differential_suggestions = False
    
    # ===== LOGIN SYSTEM =====
    if not st.session_state.logged_in:
        st.title("🔐 Radiology Assistant - Login")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.container(border=True):
                st.subheader("Login")
                username = st.text_input("Username", key="login_user")
                password = st.text_input("Password", type="password", key="login_pass")
                
                col_login1, col_login2 = st.columns(2)
                with col_login1:
                    if st.button("Login", type="primary", use_container_width=True):
                        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
                        if username in st.session_state.users:
                            if st.session_state.users[username]["password"] == hashed_pw:
                                st.session_state.logged_in = True
                                st.session_state.current_user = username
                                st.session_state.config["current_user"] = username
                                st.success(f"Welcome, {username}!")
                                st.rerun()
                            else:
                                st.error("Invalid password")
                        else:
                            st.error("User not found")
                
                st.info("Demo accounts: admin/admin123, neuro/neuro123, body/body123")
        
        st.stop()
    
    # ===== MAIN APPLICATION =====
    config = st.session_state.config
    
    # Header
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.title("🏥 Radiology Reporting Assistant")
    with col2:
        st.markdown(f"**User:** {st.session_state.current_user}")
    with col3:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()
    
    # ===== SIDEBAR =====
    with st.sidebar:
        st.header("👤 User Panel")
        st.markdown(f"**Signed in as:** {st.session_state.current_user}")
        
        # Settings
        with st.expander("⚙️ Settings"):
            st.session_state.config["include_hospital_header"] = st.checkbox(
                "Include Hospital Header", 
                value=st.session_state.config.get("include_hospital_header", True)
            )
        
        # Patient Information
        st.divider()
        st.header("🧾 Patient Information")
        
        with st.form("patient_form"):
            p_name = st.text_input("Full Name*", value=st.session_state.patient_info.get('name', ''))
            p_id = st.text_input("Patient ID*", value=st.session_state.patient_info.get('id', ''))
            p_age = st.text_input("Age", value=st.session_state.patient_info.get('age', ''))
            p_sex = st.selectbox("Sex", ["", "M", "F", "Other"], 
                                index=["", "M", "F", "Other"].index(st.session_state.patient_info.get('sex', '')) 
                                if st.session_state.patient_info.get('sex') in ["", "M", "F", "Other"] else 0)
            p_history = st.text_area("Clinical History", value=st.session_state.patient_info.get('history', ''), height=80)
            
            submitted = st.form_submit_button("💾 Save Patient Info")
            if submitted:
                if p_name and p_id:
                    st.session_state.patient_info = {
                        "name": p_name, "id": p_id, "age": p_age, 
                        "sex": p_sex, "history": p_history
                    }
                    st.success("Patient info saved!")
                else:
                    st.warning("Please enter at least Name and ID")
        
        # ===== TECHNIQUE INFORMATION =====
        st.divider()
        st.header("🔬 Technique Details")
        
        with st.form("technique_form"):
            modality = st.selectbox(
                "Modality",
                ["MRI", "CT", "Ultrasound", "X-ray", "PET-CT", "Mammography"],
                index=0
            )
            
            contrast = st.selectbox(
                "Contrast Administration",
                ["Without contrast", "With contrast", "With and without contrast", "Not specified"],
                index=0
            )
            
            sequences = st.text_area(
                "Sequences/Protocol",
                value=st.session_state.technique_info.get('sequences', ''),
                placeholder="e.g., T1, T2, FLAIR, DWI, ADC"
            )
            
            if st.form_submit_button("💾 Save Technique"):
                st.session_state.technique_info = {
                    "modality": modality,
                    "contrast": contrast,
                    "sequences": sequences if sequences else "Standard sequences"
                }
                st.success("Technique details saved!")
        
        # ===== TEMPLATE MANAGEMENT =====
        st.divider()
        st.header("📚 Template Management")
        
        # Tab interface for templates
        tab1, tab2 = st.tabs(["➕ Add Template", "📤 Upload Template"])
        
        with tab1:
            st.subheader("Create New Template")
            
            st.session_state.new_template_name = st.text_input(
                "Template Name*", 
                value=st.session_state.new_template_name,
                placeholder="e.g., Normal Brain MRI Findings",
                key="new_template_name"
            )
            
            st.session_state.new_template_type = st.selectbox(
                "Template Type",
                ["findings", "technique", "impression", "clinical", "differential", "comparison"],
                format_func=lambda x: x.upper(),
                index=0,
                key="new_template_type"
            )
            
            st.session_state.new_template_content = st.text_area(
                "Template Content*",
                value=st.session_state.new_template_content,
                height=150,
                placeholder="Enter the template text here...",
                key="new_template_content"
            )
            
            if st.button("💾 Save Template", type="primary", use_container_width=True, key="save_template"):
                if st.session_state.new_template_name and st.session_state.new_template_content:
                    st.session_state.template_system.add_template(
                        st.session_state.new_template_name,
                        st.session_state.new_template_content,
                        st.session_state.new_template_type
                    )
                    st.success(f"Template '{st.session_state.new_template_name}' saved!")
                    st.session_state.new_template_name = ""
                    st.session_state.new_template_content = ""
                    st.rerun()
                else:
                    st.warning("Please fill in both name and content")
        
        with tab2:
            st.subheader("Upload Word Template")
            
            uploaded_file = st.file_uploader(
                "Choose a Word document (.docx)",
                type=['docx'],
                key="template_upload"
            )
            
            st.session_state.uploaded_template_name = st.text_input(
                "Template Name*",
                value=st.session_state.uploaded_template_name,
                placeholder="e.g., Hospital MRI Protocol",
                key="uploaded_name"
            )
            
            st.session_state.uploaded_template_type = st.selectbox(
                "Template Type",
                ["findings", "technique", "impression", "clinical", "differential", "comparison"],
                format_func=lambda x: x.upper(),
                index=0,
                key="uploaded_type"
            )
            
            if uploaded_file and st.session_state.uploaded_template_name:
                if st.button("📤 Upload Template", type="primary", use_container_width=True, key="upload_template"):
                    success, result = st.session_state.template_system.upload_word_template(
                        uploaded_file,
                        st.session_state.uploaded_template_name,
                        st.session_state.uploaded_template_type
                    )
                    if success:
                        st.success(f"Template '{st.session_state.uploaded_template_name}' uploaded successfully!")
                        st.session_state.uploaded_template_name = ""
                        st.rerun()
                    else:
                        st.error(f"Upload failed: {result}")
        
        # ===== SELECT TEMPLATE =====
        st.divider()
        st.subheader("📋 Available Templates")
        
        # Get user's templates
        user_templates = st.session_state.template_system.get_user_templates(st.session_state.current_user)
        
        if user_templates:
            template_names = list(user_templates.keys())
            
            # Group templates by type
            templates_by_type = defaultdict(list)
            for name in template_names:
                if name in st.session_state.template_system.templates:
                    template_data = st.session_state.template_system.templates[name]
                else:
                    template_data = st.session_state.template_system.uploaded_templates[name]
                
                template_type = template_data.get('type', 'findings')
                templates_by_type[template_type.upper()].append(name)
            
            # Display templates by type
            for template_type, names in templates_by_type.items():
                with st.expander(f"{template_type} Templates ({len(names)})", expanded=False):
                    for name in sorted(names):
                        col_temp1, col_temp2 = st.columns([3, 1])
                        with col_temp1:
                            st.write(f"**{name}**")
                        with col_temp2:
                            if st.button("📥", key=f"insert_{name}", help=f"Insert {name}"):
                                st.session_state.report_draft = st.session_state.template_system.apply_template(
                                    name,
                                    st.session_state.report_draft
                                )
                                st.success(f"Template '{name}' inserted!")
                                st.rerun()
        else:
            st.info("No templates yet. Create or upload your first template!")
        
        # Quick Templates
        st.divider()
        st.subheader("⚡ Quick Templates")
        
        quick_templates = {
            "Normal Brain MRI": "Normal study. No acute intracranial hemorrhage, mass effect, or territorial infarct. Ventricles and sulci are normal. No abnormal enhancement.",
            "White Matter Changes": "Scattered punctate FLAIR hyperintensities in the periventricular and deep white matter, consistent with chronic microvascular ischemic changes.",
            "Disc Herniation": "Disc bulge/protrusion causing mild neural foraminal narrowing without significant cord compression.",
            "Normal Chest CT": "No pulmonary nodules, consolidation, or pleural effusion. Mediastinum is unremarkable."
        }
        
        quick_selected = st.selectbox("Common Templates:", ["Select..."] + list(quick_templates.keys()))
        
        if quick_selected != "Select...":
            if st.button(f"Insert '{quick_selected}'", use_container_width=True):
                heading = "FINDINGS" if "MRI" in quick_selected or "CT" in quick_selected else "IMPRESSION"
                st.session_state.report_draft += f"\n\n{heading}:\n{quick_templates[quick_selected]}"
                st.success("Template inserted!")
                st.rerun()
    
    # ===== MAIN CONTENT =====
    col1, col2 = st.columns(2)
    
    with col1:
        # Draft Area
        st.header("✍️ Report Draft")
        
        # Show technique info
        if st.session_state.technique_info.get('contrast'):
            contrast_status = st.session_state.technique_info['contrast']
            st.info(f"**Technique:** {st.session_state.technique_info['modality']} | **Contrast:** {contrast_status}")
        
        # Differential Diagnosis Suggestions Button
        if st.session_state.report_draft:
            col_diff1, col_diff2 = st.columns([2, 1])
            with col_diff1:
                if st.button("🧠 Generate Differential Suggestions", type="secondary", use_container_width=True):
                    st.session_state.show_differential_suggestions = True
                    st.session_state.differential_results = generate_differential_diagnosis(st.session_state.report_draft)
                    st.rerun()
            
            # Show Differential Suggestions if requested
            if st.session_state.show_differential_suggestions and st.session_state.differential_results:
                st.subheader("Differential Diagnosis Suggestions")
                st.caption("Select suggestions to add to your draft (they will NOT be automatically added):")
                
                for i, dx in enumerate(st.session_state.differential_results):
                    col_dx1, col_dx2, col_dx3 = st.columns([3, 1, 1])
                    with col_dx1:
                        st.write(f"**{dx['diagnosis']}** ({dx['confidence']} confidence)")
                        st.caption(f"Features: {dx['features']}")
                    
                    with col_dx2:
                        if st.button("➕ Add", key=f"add_dx_{i}", use_container_width=True):
                            if "DIFFERENTIAL DIAGNOSIS:" not in st.session_state.report_draft:
                                dx_text = f"\n\nDIFFERENTIAL DIAGNOSIS:\n1. {dx['diagnosis']}: {dx['features']}"
                            else:
                                # Find the last line number and add new one
                                lines = st.session_state.report_draft.split('\n')
                                last_number = 1
                                for line in reversed(lines):
                                    if line.strip().startswith(tuple(str(i) for i in range(10))):
                                        try:
                                            last_number = int(line.split('.')[0]) + 1
                                            break
                                        except:
                                            pass
                                dx_text = f"\n{last_number}. {dx['diagnosis']}: {dx['features']}"
                            
                            st.session_state.report_draft += dx_text
                            st.success(f"Added {dx['diagnosis']} to draft!")
                            st.rerun()
                    
                    with col_dx3:
                        if st.button("❌", key=f"hide_dx_{i}", help="Hide this suggestion", use_container_width=True):
                            st.session_state.differential_results.pop(i)
                            st.rerun()
        
        # Draft text area
        draft_text = st.text_area(
            "Type your report below:",
            value=st.session_state.report_draft,
            height=300,
            key="draft_input",
            label_visibility="collapsed",
            placeholder="Start typing your report here...\nUse templates from the sidebar.\nHeadings will be automatically formatted."
        )
        st.session_state.report_draft = draft_text
        
        # Action buttons
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        with col_btn1:
            if st.button("🤖 Generate Full Report", type="primary", use_container_width=True):
                if st.session_state.patient_info.get('name') and st.session_state.patient_info.get('id'):
                    # Format the draft with proper structure
                    formatted_report = ""
                    
                    # Add patient info section
                    formatted_report += "PATIENT INFORMATION:\n"
                    formatted_report += f"Name: {st.session_state.patient_info.get('name', 'N/A')}\n"
                    formatted_report += f"ID: {st.session_state.patient_info.get('id', 'N/A')}\n"
                    formatted_report += f"Age/Sex: {st.session_state.patient_info.get('age', 'N/A')}/{st.session_state.patient_info.get('sex', 'N/A')}\n"
                    formatted_report += f"Clinical History: {st.session_state.patient_info.get('history', 'N/A')}\n"
                    
                    # Add technique section
                    formatted_report += "\nTECHNIQUE:\n"
                    tech_info = st.session_state.technique_info
                    formatted_report += f"Modality: {tech_info.get('modality', 'Not specified')}\n"
                    formatted_report += f"Contrast: {tech_info.get('contrast', 'Without contrast')}\n"
                    formatted_report += f"Protocol: {tech_info.get('sequences', 'Standard sequences')}\n"
                    
                    # Add the main draft content
                    if draft_text:
                        formatted_report += "\n" + draft_text
                    
                    # Ensure IMPRESSION section exists if not in draft
                    if "IMPRESSION:" not in formatted_report and "IMPRESSION" not in formatted_report:
                        formatted_report += "\n\nIMPRESSION:\nFindings as described above. Clinical correlation recommended."
                    
                    st.session_state.ai_report = formatted_report
                    st.session_state.report_date = datetime.datetime.now().strftime("%Y-%m-%d")
                    st.success("Report generated with patient data!")
                else:
                    st.warning("Please enter patient information first!")
        
        with col_btn2:
            if st.button("🔍 Check Headings", use_container_width=True):
                headings = re.findall(r'([A-Z][A-Z\s]+):', st.session_state.report_draft)
                if headings:
                    st.info(f"Found headings: {', '.join(set(headings))}")
                else:
                    st.warning("No headings found. Use templates to add proper headings.")
        
        with col_btn3:
            if st.button("🧹 Clear Draft", use_container_width=True):
                st.session_state.report_draft = ""
                st.session_state.selected_template = ""
                st.session_state.show_differential_suggestions = False
                st.rerun()
    
    with col2:
        # Generated Report Display
        st.header("📋 Final Report Preview")
        
        if st.session_state.ai_report:
            # Display preview
            st.text_area(
                "Report Content:",
                value=st.session_state.ai_report,
                height=400,
                key="report_preview",
                label_visibility="collapsed"
            )
            
            # Create Word document
            try:
                doc = create_word_document(
                    patient_info=st.session_state.patient_info,
                    report_text=st.session_state.ai_report,
                    report_date=st.session_state.report_date,
                    technique_info=st.session_state.technique_info
                )
                
                # Save to buffer
                buffer = BytesIO()
                doc.save(buffer)
                buffer.seek(0)
                
                # Download button
                patient_name = st.session_state.patient_info.get('name', 'Unknown').replace(' ', '_')
                patient_id = st.session_state.patient_info.get('id', 'Unknown')
                
                st.download_button(
                    label="📄 Download as Word Document",
                    data=buffer,
                    file_name=f"RadReport_{patient_id}_{patient_name}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                    type="primary"
                )
                
            except Exception as e:
                st.error(f"Error creating document: {str(e)}")
            
            # Save to history
            st.divider()
            st.subheader("Save Report")
            
            report_name = st.text_input(
                "Report Name:",
                value=f"{st.session_state.patient_info.get('name', 'Report')}_{st.session_state.report_date}",
                key="save_report_name"
            )
            
            if st.button("💾 Save to History", use_container_width=True, key="save_to_history"):
                history_entry = {
                    "name": report_name,
                    "date": st.session_state.report_date,
                    "patient_info": st.session_state.patient_info,
                    "technique_info": st.session_state.technique_info,
                    "report": st.session_state.ai_report,
                    "created_by": st.session_state.current_user,
                    "templates_used": st.session_state.selected_template if st.session_state.selected_template else "None"
                }
                st.session_state.report_history.append(history_entry)
                st.success("Report saved to history!")
        
        else:
            with st.container(border=True):
                st.info("""
                **How to use this system:**
                
                1. **Enter Patient Info** in sidebar
                2. **Set Technique Details** (contrast, modality)
                3. **Add Templates** from sidebar
                   - Create new templates
                   - Upload Word document templates
                4. **Type additional findings**
                5. **Generate Differential Suggestions** (optional)
                   - Manually add relevant ones to report
                6. **Click 'Generate Full Report'**
                7. **Download as Word Document**
                
                **Patient data is always included in the report.**
                """)
    
    # ===== REPORT HISTORY =====
    st.divider()
    st.header("📜 Recent Reports")
    
    if st.session_state.report_history:
        # Show last 5 reports
        for i, report in enumerate(reversed(st.session_state.report_history[-5:])):
            with st.expander(f"{report['name']} - {report['date']}", expanded=False):
                col_h1, col_h2 = st.columns([1, 1])
                with col_h1:
                    if st.button(f"📥 Load Report", key=f"load_{i}", use_container_width=True):
                        st.session_state.patient_info = report['patient_info']
                        st.session_state.ai_report = report['report']
                        st.session_state.report_date = report['date']
                        if 'technique_info' in report:
                            st.session_state.technique_info = report['technique_info']
                        st.success("Report loaded for viewing!")
                        st.rerun()
                
                with col_h2:
                    if st.button(f"🗑️ Delete", key=f"delete_{i}", use_container_width=True):
                        # Find the actual index (since we reversed for display)
                        actual_index = len(st.session_state.report_history) - 1 - i
