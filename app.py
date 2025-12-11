"""
AI-Powered Professional Radiology Reporting Assistant
Version 3.1 - With Template Headings & Differential Diagnosis
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
        
        # Format with heading
        formatted_template = f"\n\n**{heading}:**\n{template['content']}"
        
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
    
    # Check for patterns
    if any(word in text_lower for word in ["enhanc", "mass", "tumor"]):
        results.extend(DIFFERENTIAL_DATABASE["brain_lesion_enhancing"])
    
    if any(word in text_lower for word in ["white matter", "flair", "hyperintensity"]):
        results.extend(DIFFERENTIAL_DATABASE["white_matter"])
    
    if any(word in text_lower for word in ["stroke", "infarct", "ischemi"]):
        results.extend(DIFFERENTIAL_DATABASE["stroke"])
    
    if any(word in text_lower for word in ["spinal", "cord", "disc"]):
        results.extend(DIFFERENTIAL_DATABASE["spinal_lesion"])
    
    # Remove duplicates
    seen = set()
    unique_results = []
    for r in results:
        key = r['diagnosis']
        if key not in seen:
            seen.add(key)
            unique_results.append(r)
    
    return unique_results[:5]  # Return top 5

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
        st.session_state.config = {
            "hospital_name": "GENERAL HOSPITAL",
            "department": "RADIOLOGY DEPARTMENT",
            "current_user": "default"
        }
        st.session_state.users = {
            "admin": {"password": hashlib.sha256("admin123".encode()).hexdigest(), "role": "admin"},
            "neuro": {"password": hashlib.sha256("neuro123".encode()).hexdigest(), "role": "radiologist"}
        }
        st.session_state.report_history = []
        st.session_state.report_draft = ""
        st.session_state.patient_info = {}
        st.session_state.ai_report = ""
        st.session_state.report_date = ""
        st.session_state.reviewer_notes = ""
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
            if submitted and p_name and p_id:
                st.session_state.patient_info = {
                    "name": p_name, "id": p_id, "age": p_age, 
                    "sex": p_sex, "history": p_history
                }
                st.success("Patient info saved!")
        
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
            
            if st.button("💾 Save Template", type="primary"):
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
                if st.button("📥 Insert Template into Report", type="secondary", use_container_width=True):
                    if st.session_state.selected_template:
                        st.session_state.report_draft = st.session_state.template_system.apply_template(
                            st.session_state.selected_template,
                            st.session_state.report_draft
                        )
                        st.success(f"Template '{st.session_state.selected_template}' inserted!")
                        st.rerun()
        else:
            st.info("No templates yet. Create your first template above!")
        
        # Quick Templates (System templates)
        st.divider()
        st.subheader("⚡ Quick Templates")
        
        quick_templates = {
            "Normal Brain MRI": "Normal study. No acute intracranial hemorrhage, mass effect, or territorial infarct. Ventricles and sulci are normal. No abnormal enhancement.",
            "White Matter Changes": "Scattered punctate FLAIR hyperintensities in the periventricular and deep white matter, consistent with chronic microvascular ischemic changes.",
            "Disc Herniation": "Disc bulge/protrusion causing mild neural foraminal narrowing without significant cord compression."
        }
        
        quick_selected = st.selectbox("Common Templates:", ["Select..."] + list(quick_templates.keys()))
        
        if quick_selected != "Select...":
            if st.button(f"Insert '{quick_selected}'"):
                st.session_state.report_draft += f"\n\n**FINDINGS:**\n{quick_templates[quick_selected]}"
                st.success("Template inserted!")
                st.rerun()
    
    # ===== MAIN CONTENT =====
    col1, col2 = st.columns(2)
    
    with col1:
        # Draft Area
        st.header("✍️ Report Draft")
        
        # Show active template
        if st.session_state.selected_template:
            st.info(f"📋 Active Template: **{st.session_state.selected_template}**")
        
        # Differential Diagnosis Generation
        if st.session_state.report_draft:
            st.session_state.differential_results = generate_differential_diagnosis(st.session_state.report_draft)
            
            if st.session_state.differential_results:
                st.subheader("🧠 Differential Diagnosis Suggestions")
                
                for i, dx in enumerate(st.session_state.differential_results):
                    with st.expander(f"{dx['diagnosis']} ({dx['confidence']} confidence)"):
                        st.write(f"**Key Features:** {dx['features']}")
                        
                        # Button to add to report
                        if st.button(f"Add '{dx['diagnosis']}' to report", key=f"add_dx_{i}"):
                            dx_text = f"\n\n**DIFFERENTIAL DIAGNOSIS:**\n1. {dx['diagnosis']}: {dx['features']}"
                            st.session_state.report_draft += dx_text
                            st.success(f"Added {dx['diagnosis']} to report!")
                            st.rerun()
        
        # Draft text area
        draft_text = st.text_area(
            "Type your findings below (templates will appear as headings):",
            value=st.session_state.report_draft,
            height=350,
            key="draft_input",
            label_visibility="collapsed",
            placeholder="Your report will appear here...\nTemplates will be formatted with proper headings."
        )
        st.session_state.report_draft = draft_text
        
        # Action buttons
        col1a, col1b = st.columns(2)
        with col1a:
            if st.button("🤖 Generate Full Report", type="primary", use_container_width=True):
                if draft_text:
                    # Format the draft with proper structure
                    formatted_report = "**REPORT**\n\n"
                    
                    # Add patient info if available
                    if st.session_state.patient_info.get('name'):
                        formatted_report += f"**PATIENT:** {st.session_state.patient_info['name']} ({st.session_state.patient_info.get('id', 'N/A')})\n"
                    
                    # Add clinical history if available
                    if st.session_state.patient_info.get('history'):
                        formatted_report += f"\n**CLINICAL HISTORY:**\n{st.session_state.patient_info['history']}\n"
                    
                    # Add technique (default)
                    formatted_report += "\n**TECHNIQUE:**\nMRI performed with standard sequences.\n"
                    
                    # Add the main draft content
                    formatted_report += f"\n{draft_text}"
                    
                    # Add differential diagnosis if generated
                    if st.session_state.differential_results:
                        formatted_report += "\n\n**DIFFERENTIAL DIAGNOSIS:**\n"
                        for dx in st.session_state.differential_results[:3]:
                            formatted_report += f"- {dx['diagnosis']}: {dx['features']}\n"
                    
                    # Add impression
                    formatted_report += "\n**IMPRESSION:**\nFindings as described above. Clinical correlation recommended."
                    
                    st.session_state.ai_report = formatted_report
                    st.session_state.report_date = datetime.datetime.now().strftime("%Y-%m-%d")
                    st.success("Report generated with template headings!")
                else:
                    st.warning("Please enter findings first")
        
        with col1b:
            if st.button("🧹 Clear All", use_container_width=True):
                st.session_state.report_draft = ""
                st.session_state.selected_template = ""
                st.session_state.differential_results = []
                st.rerun()
    
    with col2:
        # Generated Report Display
        st.header("📋 Generated Report")
        
        if st.session_state.ai_report:
            # Display formatted report
            st.text_area(
                "Final Report Preview:",
                value=st.session_state.ai_report,
                height=400,
                key="report_preview",
                label_visibility="collapsed"
            )
            
            # Create Word document
            try:
                doc = Document()
                
                # Add title
                title = doc.add_heading('RADIOLOGY REPORT', 0)
                title.alignment = WD_ALIGN_PARAGRAPH.CENTER
                
                # Add patient info
                if st.session_state.patient_info:
                    doc.add_heading('PATIENT INFORMATION', level=1)
                    doc.add_paragraph(f"Name: {st.session_state.patient_info.get('name', 'N/A')}")
                    doc.add_paragraph(f"ID: {st.session_state.patient_info.get('id', 'N/A')}")
                    doc.add_paragraph(f"Age/Sex: {st.session_state.patient_info.get('age', 'N/A')}/{st.session_state.patient_info.get('sex', 'N/A')}")
                    doc.add_paragraph(f"Date: {st.session_state.report_date}")
                
                # Parse and add report sections
                lines = st.session_state.ai_report.split('\n')
                current_heading = None
                
                for line in lines:
                    if line.startswith('**') and line.endswith('**'):
                        # This is a heading
                        current_heading = line.strip('**')
                        doc.add_heading(current_heading, level=1)
                    elif line.strip():
                        # This is content
                        doc.add_paragraph(line.strip())
                
                # Save to buffer
                buffer = BytesIO()
                doc.save(buffer)
                buffer.seek(0)
                
                # Download button
                st.download_button(
                    label="📄 Download as Word Document",
                    data=buffer,
                    file_name=f"RAD_Report_{st.session_state.patient_info.get('id', 'Unknown')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                    type="primary"
                )
                
            except Exception as e:
                st.error(f"Error creating document: {str(e)}")
            
            # Save to history
            st.divider()
            report_name = st.text_input("Save as:", value=f"Report_{st.session_state.patient_info.get('id', 'Unknown')}")
            
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
                st.success("Saved to history!")
        
        else:
            st.info("""
            **How to use:**
            1. Enter patient info in sidebar
            2. Add templates from sidebar dropdown
            3. Type additional findings
            4. Click 'Generate Full Report'
            5. Download as Word document
            
            **Templates will appear as headings** in your final report!
            """)
    
    # ===== REPORT HISTORY =====
    st.divider()
    st.header("📜 Report History")
    
    if st.session_state.report_history:
        for i, report in enumerate(st.session_state.report_history[-5:]):  # Last 5 reports
            with st.expander(f"{report['name']} - {report['date']}"):
                col_h1, col_h2 = st.columns(2)
                with col_h1:
                    if st.button(f"📥 Load", key=f"load_{i}"):
                        st.session_state.patient_info = report['patient_info']
                        st.session_state.ai_report = report['report']
                        st.session_state.report_date = report['date']
                        st.success("Report loaded!")
                        st.rerun()
                
                with col_h2:
                    if st.button(f"🗑️ Delete", key=f"delete_{i}"):
                        st.session_state.report_history.pop(i)
                        st.warning("Report deleted!")
                        st.rerun()
                
                st.caption(f"Patient: {report['patient_info'].get('name', 'Unknown')}")
                st.caption(f"Templates used: {report.get('templates_used', 'None')}")
                st.text(report['report'][:200] + "..." if len(report['report']) > 200 else report['report'])
    else:
        st.info("No reports in history yet")

# ===== RUN APPLICATION =====
if __name__ == "__main__":
    main()
