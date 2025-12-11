"""
AI-Powered Professional Radiology Reporting Assistant
Version 4.1 - Fixed and Working Version
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

# ===== TEMPLATE SYSTEM =====
class TemplateSystem:
    """Template system for managing report templates."""
    
    def __init__(self):
        self.templates = {}
        self.load_templates()
    
    def load_templates(self):
        """Load templates from file."""
        if os.path.exists(TEMPLATES_FILE):
            try:
                with open(TEMPLATES_FILE, 'r') as f:
                    self.templates = json.load(f)
            except:
                self.templates = {}
    
    def save_templates(self):
        """Save templates to file."""
        try:
            with open(TEMPLATES_FILE, 'w') as f:
                json.dump(self.templates, f, indent=2)
        except:
            pass
    
    def add_template(self, name, content, template_type="findings"):
        """Add a new template."""
        self.templates[name] = {
            "content": content,
            "type": template_type,
            "created_by": st.session_state.get('current_user', 'unknown'),
            "created_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "used_count": 0
        }
        self.save_templates()
    
    def get_template_heading(self, template_name):
        """Get heading format for a template."""
        if template_name not in self.templates:
            return template_name.upper()
        
        template = self.templates[template_name]
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
        if template_name not in self.templates:
            return current_text
        
        template = self.templates[template_name]
        heading = self.get_template_heading(template_name)
        
        # Increment usage count
        template["used_count"] = template.get("used_count", 0) + 1
        self.save_templates()
        
        # Format with heading
        formatted_template = f"\n\n{heading.upper()}:\n{template['content']}"
        
        if current_text:
            return current_text + formatted_template
        return formatted_template
    
    def get_user_templates(self, username):
        """Get templates created by specific user."""
        user_templates = {}
        for name, data in self.templates.items():
            if data.get("created_by") == username:
                user_templates[name] = data
        return user_templates

def generate_differential_diagnosis(text):
    """Generate differential diagnosis based on findings."""
    if not text:
        return []
    
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
    
    return unique_results[:6]

def create_word_document(patient_info, report_text, report_date, technique_info=None):
    """Create a Word document with proper formatting including patient data."""
    doc = Document()
    
    # Title
    title = doc.add_heading('RADIOLOGY REPORT', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Add spacing
    doc.add_paragraph()
    
    # PATIENT INFORMATION Section
    doc.add_heading('PATIENT INFORMATION', level=1)
    
    # Add patient information
    doc.add_paragraph(f"Patient Name: {patient_info.get('name', 'Not provided')}")
    doc.add_paragraph(f"Patient ID: {patient_info.get('id', 'Not provided')}")
    doc.add_paragraph(f"Age/Sex: {patient_info.get('age', 'N/A')}/{patient_info.get('sex', 'N/A')}")
    doc.add_paragraph(f"Clinical History: {patient_info.get('history', 'Not provided')}")
    doc.add_paragraph(f"Report Date: {report_date if report_date else datetime.datetime.now().strftime('%Y-%m-%d')}")
    
    # Add spacing
    doc.add_paragraph()
    
    # Parse and add report sections
    lines = report_text.split('\n')
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            doc.add_paragraph()  # Preserve paragraph breaks
            continue
            
        # Check if line is a heading (ends with colon and is mostly uppercase)
        if line_stripped.endswith(':') and line_stripped[:-1].replace(' ', '').isupper():
            heading_text = line_stripped[:-1]  # Remove colon
            doc.add_heading(heading_text, level=1)
        else:
            # Regular content
            doc.add_paragraph(line_stripped)
    
    # Add footer with radiologist info
    doc.add_page_break()
    doc.add_heading('REPORT DETAILS', level=1)
    p = doc.add_paragraph()
    p.add_run(f"Generated by: {st.session_state.get('current_user', 'Unknown')}\n")
    p.add_run(f"Generation date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return doc

# ===== INITIALIZE SESSION STATE =====
def init_session_state():
    """Initialize session state variables."""
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
        st.session_state.selected_template = ""
        st.session_state.new_template_name = ""
        st.session_state.new_template_content = ""
        st.session_state.new_template_type = "findings"
        st.session_state.technique_info = {
            "modality": "MRI",
            "contrast": "Without contrast",
            "sequences": "Standard sequences"
        }
        st.session_state.show_differential_suggestions = False

# ===== STREAMLIT APP =====
def main():
    # Page config
    st.set_page_config(
        page_title="Professional Radiology Assistant",
        layout="wide",
        page_icon="🏥"
    )
    
    # Initialize session state
    init_session_state()
    
    # ===== LOGIN SYSTEM =====
    if not st.session_state.logged_in:
        st.title("🔐 Radiology Assistant - Login")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
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
                
                st.info("Demo accounts: admin/admin123, neuro/neuro123, body/body123")
        
        return
    
    # ===== MAIN APPLICATION =====
    
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
        
        # Technique Information
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
        
        # Template Management
        st.divider()
        st.header("📚 Template Management")
        
        # Add New Template
        with st.expander("➕ Add New Template", expanded=False):
            st.subheader("Create New Template")
            
            new_template_name = st.text_input(
                "Template Name*", 
                placeholder="e.g., Normal Brain MRI Findings",
                key="new_template_name_input"
            )
            
            new_template_type = st.selectbox(
                "Template Type",
                ["findings", "technique", "impression", "clinical", "differential", "comparison"],
                format_func=lambda x: x.upper(),
                index=0,
                key="new_template_type_select"
            )
            
            new_template_content = st.text_area(
                "Template Content*",
                height=150,
                placeholder="Enter the template text here...",
                key="new_template_content_area"
            )
            
            if st.button("💾 Save Template", type="primary", use_container_width=True, key="save_template_button"):
                if new_template_name and new_template_content:
                    st.session_state.template_system.add_template(
                        new_template_name,
                        new_template_content,
                        new_template_type
                    )
                    st.success(f"Template '{new_template_name}' saved!")
                    st.rerun()
                else:
                    st.warning("Please fill in both name and content")
        
        # Select Template to Use
        st.divider()
        st.subheader("📋 Available Templates")
        
        # Get user's templates
        user_templates = st.session_state.template_system.get_user_templates(st.session_state.current_user)
        
        if user_templates:
            template_names = list(user_templates.keys())
            
            # Display templates
            for name in sorted(template_names):
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
            st.info("No templates yet. Create your first template above!")
        
        # Quick Templates
        st.divider()
        st.subheader("⚡ Quick Templates")
        
        quick_templates = {
            "Normal Brain MRI": "Normal study. No acute intracranial hemorrhage, mass effect, or territorial infarct. Ventricles and sulci are normal. No abnormal enhancement.",
            "White Matter Changes": "Scattered punctate FLAIR hyperintensities in the periventricular and deep white matter, consistent with chronic microvascular ischemic changes.",
            "Disc Herniation": "Disc bulge/protrusion causing mild neural foraminal narrowing without significant cord compression.",
            "Normal Chest CT": "No pulmonary nodules, consolidation, or pleural effusion. Mediastinum is unremarkable."
        }
        
        quick_selected = st.selectbox("Common Templates:", ["Select..."] + list(quick_templates.keys()), key="quick_template_select")
        
        if quick_selected != "Select...":
            if st.button(f"Insert '{quick_selected}'", use_container_width=True, key="insert_quick_template"):
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
                if st.button("🧠 Generate Differential Suggestions", type="secondary", use_container_width=True, key="gen_diff_button"):
                    st.session_state.show_differential_suggestions = True
                    st.session_state.differential_results = generate_differential_diagnosis(st.session_state.report_draft)
                    st.rerun()
            
            # Show Differential Suggestions if requested
            if st.session_state.show_differential_suggestions and st.session_state.differential_results:
                st.subheader("Differential Diagnosis Suggestions")
                st.caption("Select suggestions to add to your draft (they will NOT be automatically added):")
                
                for i, dx in enumerate(st.session_state.differential_results):
                    col_dx1, col_dx2 = st.columns([3, 1])
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
            if st.button("🤖 Generate Full Report", type="primary", use_container_width=True, key="generate_report_button"):
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
            if st.button("🔍 Check Headings", use_container_width=True, key="check_headings_button"):
                headings = re.findall(r'([A-Z][A-Z\s]+):', st.session_state.report_draft)
                if headings:
                    st.info(f"Found headings: {', '.join(set(headings))}")
                else:
                    st.warning("No headings found. Use templates to add proper headings.")
        
        with col_btn3:
            if st.button("🧹 Clear Draft", use_container_width=True, key="clear_draft_button"):
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
                    report_date=st.session_state.report_date
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
                    type="primary",
                    key="download_report_button"
                )
                
            except Exception as e:
                st.error(f"Error creating document: {str(e)}")
            
            # Save to history
            st.divider()
            st.subheader("Save Report")
            
            report_name = st.text_input(
                "Report Name:",
                value=f"{st.session_state.patient_info.get('name', 'Report')}_{st.session_state.report_date}",
                key="save_report_name_input"
            )
            
            if st.button("💾 Save to History", use_container_width=True, key="save_history_button"):
                history_entry = {
                    "name": report_name,
                    "date": st.session_state.report_date,
                    "patient_info": st.session_state.patient_info,
                    "technique_info": st.session_state.technique_info,
                    "report": st.session_state.ai_report,
                    "created_by": st.session_state.current_user
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
                4. **Type additional findings**
                5. **Generate Differential Suggestions** (optional)
                6. **Click 'Generate Full Report'**
                7. **Download as Word Document**
                
                **Patient data is always included in the report.**
                """)
    
    # ===== REPORT HISTORY =====
    st.divider()
    st.header("📜 Recent Reports")
    
    if st.session_state.report_history:
        # Show last 5 reports
        recent_reports = st.session_state.report_history[-5:][::-1]
        for i, report in enumerate(recent_reports):
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
                    actual_index = len(st.session_state.report_history) - 1 - i
                    if st.button(f"🗑️ Delete", key=f"delete_{i}", use_container_width=True):
                        st.session_state.report_history.pop(actual_index)
                        st.warning("Report deleted from history!")
                        st.rerun()
                
                st.caption(f"**Patient:** {report['patient_info'].get('name', 'Unknown')} | **ID:** {report['patient_info'].get('id', 'Unknown')}")
                
                # Show first few lines of report
                preview = report['report'][:300]
                if len(report['report']) > 300:
                    preview += "..."
                st.text(preview)
    else:
        st.info("No reports in history yet. Generate and save your first report!")

# ===== RUN APPLICATION =====
if __name__ == "__main__":
    main()
