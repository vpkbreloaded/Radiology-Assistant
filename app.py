"""
AI-Powered Professional Radiology Reporting Assistant
Version 3.2 - Enhanced with User-Controlled Differentials & Improved Formatting
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
USER_FILE = "users.json"

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

# ===== TEMPLATE SYSTEM WITH HEADINGS =====
class TemplateSystem:
    """Enhanced template system with heading support."""
    
    def __init__(self):
        self.templates = {}
        self.load_templates()
    
    def load_templates(self):
        """Load templates from file."""
        if os.path.exists(TEMPLATES_FILE):
            with open(TEMPLATES_FILE, 'r') as f:
                self.templates = json.load(f)
    
    def save_templates(self):
        """Save templates to file."""
        with open(TEMPLATES_FILE, 'w') as f:
            json.dump(self.templates, f, indent=2)
    
    def add_template(self, name, content, template_type="findings"):
        """Add a new template with heading."""
        self.templates[name] = {
            "content": content,
            "type": template_type,
            "created_by": st.session_state.current_user,
            "created_date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "used_count": 0
        }
        self.save_templates()
    
    def get_template_heading(self, template_name):
        """Get heading format for a template."""
        template = self.templates.get(template_name, {})
        template_type = template.get("type", "findings")
        
        heading_map = {
            "technique": "TECHNIQUE",
            "findings": "FINDINGS",
            "impression": "IMPRESSION",
            "clinical": "CLINICAL HISTORY",
            "differential": "DIFFERENTIAL DIAGNOSIS"
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
        
        # Format with heading (no bold in final report - will be formatted in Word)
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
    text_lower = text.lower()
    results = []
    
    # Check for patterns in various categories
    if any(word in text_lower for word in ["enhanc", "mass", "tumor", "neoplasm"]):
        results.extend(DIFFERENTIAL_DATABASE["brain_lesion_enhancing"])
    
    if any(word in text_lower for word in ["white matter", "flair", "hyperintensity", "msa"]):
        results.extend(DIFFERENTIAL_DATABASE["white_matter"])
    
    if any(word in text_lower for word in ["stroke", "infarct", "ischemi", "mca"]):
        results.extend(DIFFERENTIAL_DATABASE["stroke"])
    
    if any(word in text_lower for word in ["spinal", "cord", "disc", "vertebral"]):
        results.extend(DIFFERENTIAL_DATABASE["spinal_lesion"])
    
    if any(word in text_lower for word in ["lung", "pulmonary", "nodule", "chest"]):
        results.extend(DIFFERENTIAL_DATABASE["lung_nodule"])
    
    if any(word in text_lower for word in ["liver", "hepatic", "lesion", "hepato"]):
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

def create_word_document(patient_info, report_text, report_date, include_hospital_header=False):
    """Create a Word document with proper formatting."""
    doc = Document()
    
    # Optional: Hospital header
    if include_hospital_header:
        title = doc.add_heading('RADIOLOGY REPORT', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph()  # Add spacing
    
    # Patient Information Section
    doc.add_heading('PATIENT INFORMATION', level=1)
    
    patient_table = doc.add_table(rows=4, cols=2)
    patient_table.style = 'Light Shading'
    
    # Fill patient table
    cells = patient_table.rows[0].cells
    cells[0].text = "Patient Name:"
    cells[1].text = patient_info.get('name', 'Not provided')
    
    cells = patient_table.rows[1].cells
    cells[0].text = "Patient ID:"
    cells[1].text = patient_info.get('id', 'Not provided')
    
    cells = patient_table.rows[2].cells
    cells[0].text = "Age/Sex:"
    cells[1].text = f"{patient_info.get('age', '')}/{patient_info.get('sex', '')}".strip('/')
    
    cells = patient_table.rows[3].cells
    cells[0].text = "Report Date:"
    cells[1].text = report_date if report_date else datetime.datetime.now().strftime("%Y-%m-%d")
    
    doc.add_paragraph()  # Add spacing
    
    # Parse and add report sections
    lines = report_text.split('\n')
    current_heading = None
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
            
        # Check if line is a heading (ends with colon and is uppercase)
        if line_stripped.endswith(':') and line_stripped[:-1].isupper():
            current_heading = line_stripped[:-1]  # Remove colon
            doc.add_heading(current_heading, level=1)
        elif line_stripped.startswith('**') and line_stripped.endswith('**'):
            # Bold text in markdown format
            bold_text = line_stripped.strip('**')
            p = doc.add_paragraph()
            run = p.add_run(bold_text)
            run.bold = True
        else:
            # Regular content
            doc.add_paragraph(line_stripped)
    
    # Add footer with radiologist info
    doc.add_page_break()
    doc.add_heading('RADIOLOGIST INFORMATION', level=1)
    p = doc.add_paragraph()
    p.add_run(f"Report generated by: {st.session_state.current_user}\n")
    p.add_run(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
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
            "include_hospital_header": False  # Option to include hospital name
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
        st.session_state.template_system = TemplateSystem()
        st.session_state.selected_template = ""
        st.session_state.new_template_name = ""
        st.session_state.new_template_content = ""
        st.session_state.new_template_type = "findings"
    
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
        st.title("Radiology Reporting Assistant")
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
                "Include Hospital Header in Report", 
                value=st.session_state.config.get("include_hospital_header", False)
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
        
        # ===== TEMPLATE MANAGEMENT =====
        st.divider()
        st.header("📚 Template Management")
        
        # Add New Template
        with st.expander("➕ Add New Template", expanded=False):
            st.subheader("Create New Template")
            
            st.session_state.new_template_name = st.text_input(
                "Template Name*", 
                value=st.session_state.new_template_name,
                placeholder="e.g., Normal Brain MRI Findings"
            )
            
            st.session_state.new_template_type = st.selectbox(
                "Template Type",
                ["findings", "technique", "impression", "clinical", "differential"],
                format_func=lambda x: x.upper(),
                index=0
            )
            
            st.session_state.new_template_content = st.text_area(
                "Template Content*",
                value=st.session_state.new_template_content,
                height=150,
                placeholder="Enter the template text here..."
            )
            
            if st.button("💾 Save Template", type="primary", use_container_width=True):
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
        
        # Select Template to Use
        st.divider()
        st.subheader("📋 Select Template")
        
        # Get user's templates
        user_templates = st.session_state.template_system.get_user_templates(st.session_state.current_user)
        
        if user_templates:
            template_names = list(user_templates.keys())
            
            # Create dropdown with template info
            template_options = []
            for name in template_names:
                template_data = user_templates[name]
                usage = template_data.get("used_count", 0)
                template_options.append(f"{name} ({usage} uses)")
            
            selected_template_display = st.selectbox(
                "Your Templates:",
                ["Select a template..."] + template_options,
                key="template_select_display"
            )
            
            if selected_template_display != "Select a template...":
                # Extract template name from display string
                selected_template_name = selected_template_display.split(" (")[0]
                st.session_state.selected_template = selected_template_name
                
                # Show template preview
                with st.expander("👁️ Preview Template"):
                    template_data = user_templates[selected_template_name]
                    st.caption(f"Type: {template_data['type'].upper()}")
                    st.caption(f"Created: {template_data.get('created_date', 'Unknown')}")
                    st.text(template_data['content'][:200] + "..." if len(template_data['content']) > 200 else template_data['content'])
                
                # Apply Template Button
                if st.button("📥 Insert Template", type="secondary", use_container_width=True):
                    if st.session_state.selected_template:
                        st.session_state.report_draft = st.session_state.template_system.apply_template(
                            st.session_state.selected_template,
                            st.session_state.report_draft
                        )
                        st.success(f"Template inserted with '{st.session_state.template_system.get_template_heading(st.session_state.selected_template)}' heading!")
                        st.rerun()
        else:
            st.info("No templates yet. Create your first template above!")
        
        # Quick Templates (System templates)
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
        
        # Show active template
        if st.session_state.selected_template:
            template_heading = st.session_state.template_system.get_template_heading(st.session_state.selected_template)
            st.info(f"📋 Active Template: **{st.session_state.selected_template}** (Will insert as: **{template_heading}** heading)")
        
        # Differential Diagnosis Suggestions (Separate Section)
        if st.session_state.report_draft:
            st.session_state.differential_results = generate_differential_diagnosis(st.session_state.report_draft)
            
            if st.session_state.differential_results:
                st.subheader("🧠 Differential Diagnosis Suggestions")
                st.caption("Review and manually add to report if desired:")
                
                for i, dx in enumerate(st.session_state.differential_results):
                    with st.expander(f"🔍 {dx['diagnosis']} ({dx['confidence']} confidence)", expanded=False):
                        col_dx1, col_dx2 = st.columns([3, 1])
                        with col_dx1:
                            st.write(f"**Key Features:** {dx['features']}")
                        with col_dx2:
                            # Button to add to report
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
                                st.success(f"Added {dx['diagnosis']} to report!")
                                st.rerun()
        
        # Draft text area
        draft_text = st.text_area(
            "Type your report below (templates will insert with proper headings):",
            value=st.session_state.report_draft,
            height=350,
            key="draft_input",
            label_visibility="collapsed",
            placeholder="Start typing your report here...\nOr insert templates from the sidebar.\nHeadings will be automatically formatted."
        )
        st.session_state.report_draft = draft_text
        
        # Action buttons
        col1a, col1b, col1c = st.columns(3)
        with col1a:
            if st.button("🤖 Generate Full Report", type="primary", use_container_width=True):
                if st.session_state.patient_info.get('name') and st.session_state.patient_info.get('id'):
                    # Format the draft with proper structure
                    formatted_report = ""
                    
                    # Add clinical history if available
                    if st.session_state.patient_info.get('history'):
                        formatted_report += f"CLINICAL HISTORY:\n{st.session_state.patient_info['history']}\n"
                    
                    # Add technique section (default if not present)
                    if "TECHNIQUE:" not in draft_text and "TECHNIQUE" not in draft_text:
                        formatted_report += "\nTECHNIQUE:\nStandard imaging protocol was performed.\n"
                    
                    # Add the main draft content
                    if draft_text:
                        if formatted_report:  # Add spacing if we already have content
                            formatted_report += "\n"
                        formatted_report += draft_text
                    
                    # Ensure IMPRESSION section exists
                    if "IMPRESSION:" not in formatted_report and "IMPRESSION" not in formatted_report:
                        formatted_report += "\n\nIMPRESSION:\nFindings as described above. Clinical correlation recommended."
                    
                    st.session_state.ai_report = formatted_report
                    st.session_state.report_date = datetime.datetime.now().strftime("%Y-%m-%d")
                    st.success("Report generated with proper headings!")
                else:
                    st.warning("Please enter patient information first!")
        
        with col1b:
            if st.button("🔍 Check Headings", use_container_width=True):
                headings = re.findall(r'([A-Z][A-Z\s]+):', st.session_state.report_draft)
                if headings:
                    st.info(f"Found headings: {', '.join(set(headings))}")
                else:
                    st.warning("No headings found. Use templates to add proper headings.")
        
        with col1c:
            if st.button("🧹 Clear Draft", use_container_width=True):
                st.session_state.report_draft = ""
                st.session_state.selected_template = ""
                st.rerun()
    
    with col2:
        # Generated Report Display
        st.header("📋 Final Report Preview")
        
        if st.session_state.ai_report:
            # Display patient info
            with st.container(border=True):
                st.subheader("Patient Information")
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.text(f"Name: {st.session_state.patient_info.get('name', 'N/A')}")
                    st.text(f"Age/Sex: {st.session_state.patient_info.get('age', 'N/A')}/{st.session_state.patient_info.get('sex', 'N/A')}")
                with col_info2:
                    st.text(f"ID: {st.session_state.patient_info.get('id', 'N/A')}")
                    st.text(f"Date: {st.session_state.report_date}")
            
            # Display formatted report
            st.text_area(
                "Report Content:",
                value=st.session_state.ai_report,
                height=300,
                key="report_preview",
                label_visibility="collapsed"
            )
            
            # Create Word document
            try:
                doc = create_word_document(
                    patient_info=st.session_state.patient_info,
                    report_text=st.session_state.ai_report,
                    report_date=st.session_state.report_date,
                    include_hospital_header=st.session_state.config.get("include_hospital_header", False)
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
                value=f"{st.session_state.patient_info.get('name', 'Report')}_{st.session_state.report_date}"
            )
            
            if st.button("💾 Save to History", use_container_width=True):
                history_entry = {
                    "name": report_name,
                    "date": st.session_state.report_date,
                    "patient_info": st.session_state.patient_info,
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
                2. **Add Templates** from sidebar dropdown
                   - Templates automatically insert with proper headings
                3. **Type additional findings**
                4. **Review Differential Suggestions** (appear automatically)
                   - Manually add relevant ones to report
                5. **Click 'Generate Full Report'**
                6. **Download as Word Document**
                
                **Key Features:**
                - Template headings appear below patient info
                - Differential suggestions are optional
                - Clean, professional formatting
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
                        st.success("Report loaded for viewing!")
                        st.rerun()
                
                with col_h2:
                    if st.button(f"🗑️ Delete", key=f"delete_{i}", use_container_width=True):
                        # Find the actual index (since we reversed for display)
                        actual_index = len(st.session_state.report_history) - 1 - i
                        st.session_state.report_history.pop(actual_index)
                        st.warning("Report deleted from history!")
                        st.rerun()
                
                st.caption(f"**Patient:** {report['patient_info'].get('name', 'Unknown')} | **ID:** {report['patient_info'].get('id', 'Unknown')}")
                st.caption(f"**Templates used:** {report.get('templates_used', 'None')}")
                
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
