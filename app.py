import streamlit as st
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import re
import json
import os
import datetime
import time
import pydicom
from pydicom.errors import InvalidDicomError

def extract_dicom_info(uploaded_file):
    """Extract patient and study info from a DICOM file."""
    try:
        dicom_data = pydicom.dcmread(uploaded_file, force=True)
        info = {
            "name": str(getattr(dicom_data, 'PatientName', '')),
            "id": str(getattr(dicom_data, 'PatientID', '')),
            "dob": str(getattr(dicom_data, 'PatientBirthDate', '')),
            "sex": str(getattr(dicom_data, 'PatientSex', '')),
            "study_date": str(getattr(dicom_data, 'StudyDate', '')),
            "modality": str(getattr(dicom_data, 'Modality', '')),
            "study_desc": str(getattr(dicom_data, 'StudyDescription', ''))
        }
        return info
    except InvalidDicomError:
        return None
    except Exception as e:
        st.error(f"DICOM read error: {e}")
        return None

# ===== FUNCTIONS FOR PERMANENT STORAGE =====
HISTORY_FILE = "report_history.json"
TEMPLATES_FILE = "saved_templates.json"

def save_history_to_file():
    """Save the report history to a JSON file."""
    try:
        history_to_save = []
        for entry in st.session_state.report_history:
            safe_entry = {
                "name": entry.get("name", ""),
                "date": entry.get("date", ""),
                "timestamp": entry.get("timestamp", ""),
                "patient_info": entry.get("patient_info", {}),
                "draft": entry.get("draft", ""),
                "ai_report": entry.get("ai_report", "")
            }
            history_to_save.append(safe_entry)
        
        with open(HISTORY_FILE, "w") as f:
            json.dump(history_to_save, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving history: {e}")
        return False

def load_history_from_file():
    """Load report history from JSON file."""
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r") as f:
                loaded_history = json.load(f)
            return loaded_history
    except Exception as e:
        st.error(f"Error loading history: {e}")
    return []

def save_templates_to_file():
    """Save templates with categories to JSON file."""
    try:
        with open(TEMPLATES_FILE, "w") as f:
            json.dump(st.session_state.saved_templates, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving templates: {e}")
        return False

def load_templates_from_file():
    """Load templates with categories from JSON file."""
    try:
        if os.path.exists(TEMPLATES_FILE):
            with open(TEMPLATES_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        st.error(f"Error loading templates: {e}")
    return {}

# ===== PROFESSIONAL WORD EXPORT FUNCTION =====
def create_professional_word_report(ai_report, patient_info, report_date):
    """Create a professionally formatted Word document."""
    doc = Document()
    
    # Set document margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(0.5)
        section.right_margin = Inches(0.5)
    
    # 1. HOSPITAL HEADER
    header = sections[0].header
    header_para = header.paragraphs[0]
    header_para.text = "RADIOLOGY DEPARTMENT - AI ASSISTED REPORT"
    header_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    header_para.style.font.size = Pt(10)
    header_para.style.font.color.rgb = RGBColor(100, 100, 100)
    
    # 2. MAIN TITLE
    title = doc.add_heading('RADIOLOGY REPORT', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.style.font.size = Pt(16)
    
    # 3. PATIENT INFORMATION TABLE
    doc.add_heading('PATIENT INFORMATION', level=1)
    
    table = doc.add_table(rows=5, cols=2)
    table.style = 'Light Grid'
    
    # Table headers
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "FIELD"
    hdr_cells[1].text = "INFORMATION"
    
    # Fill patient data
    data_rows = [
        ("Patient Name", patient_info.get('name', 'Not Provided')),
        ("Patient ID", patient_info.get('id', 'Not Provided')),
        ("Age / Sex", f"{patient_info.get('age', 'N/A')} / {patient_info.get('sex', 'N/A')}"),
        ("Accession #", patient_info.get('accession', 'Not Provided'))
    ]
    
    for i, (field, value) in enumerate(data_rows, 1):
        row_cells = table.rows[i].cells
        row_cells[0].text = field
        row_cells[1].text = value
    
    # 4. CLINICAL HISTORY
    if patient_info.get('history'):
        doc.add_heading('CLINICAL HISTORY', level=1)
        doc.add_paragraph(patient_info.get('history'))
    
    doc.add_paragraph()  # Spacing
    
    # 5. REPORT CONTENT
    doc.add_heading('REPORT', level=1)
    
    # Smart parsing of AI report sections
    if '**TECHNIQUE:**' in ai_report:
        # Format with proper section headings
        sections_text = ai_report.split('**')
        for section in sections_text:
            if section.endswith(':**'):
                # Section heading
                doc.add_heading(section.replace(':**', '').strip(), level=2)
            elif section.strip():
                # Section content
                # Handle bullet points
                lines = section.strip().split('\n')
                for line in lines:
                    if line.strip().startswith('-') or line.strip().startswith('*'):
                        # Bullet point
                        p = doc.add_paragraph(style='List Bullet')
                        p.add_run(line.strip().lstrip('-* '))
                    elif line.strip():
                        # Regular paragraph
                        doc.add_paragraph(line.strip())
    else:
        # Simple formatting
        lines = ai_report.split('\n')
        for line in lines:
            if line.strip():
                doc.add_paragraph(line.strip())
    
    # 6. IMPRESSION (if separate)
    if '**IMPRESSION:**' in ai_report:
        # Already handled in sections
        pass
    elif 'IMPRESSION:' in ai_report or 'Impression:' in ai_report:
        doc.add_heading('IMPRESSION', level=2)
        # Extract impression text
        impression_start = ai_report.lower().find('impression')
        if impression_start != -1:
            impression_text = ai_report[impression_start + 10:].strip()
            doc.add_paragraph(impression_text)
    
    # 7. FOOTER WITH TIMESTAMP
    footer = sections[0].footer
    footer_para = footer.paragraphs[0]
    footer_para.text = f"Report generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} | AI Radiology Assistant v1.0"
    footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer_para.style.font.size = Pt(8)
    footer_para.style.font.color.rgb = RGBColor(150, 150, 150)
    
    # 8. PAGE NUMBER
    footer.add_paragraph().alignment = WD_ALIGN_PARAGRAPH.RIGHT
    footer.paragraphs[1].text = "Page 1 of 1"
    
    return doc

# ===== STREAMLIT PAGE CONFIG =====
st.set_page_config(page_title="AI Radiology Assistant", layout="wide")

# ===== INITIALIZE SESSION STATE =====
if 'report_draft' not in st.session_state:
    st.session_state.report_draft = ""
if 'patient_info' not in st.session_state:
    st.session_state.patient_info = {}
if 'saved_templates' not in st.session_state:
    st.session_state.saved_templates = load_templates_from_file()
if 'ai_report' not in st.session_state:
    st.session_state.ai_report = ""
if 'report_history' not in st.session_state:
    st.session_state.report_history = load_history_from_file()
if 'report_date' not in st.session_state:
    st.session_state.report_date = ""
if 'report_timestamp' not in st.session_state:
    st.session_state.report_timestamp = ""
if 'last_save_time' not in st.session_state:
    st.session_state.last_save_time = datetime.datetime.now()
if 'last_saved_draft' not in st.session_state:
    st.session_state.last_saved_draft = ""
if 'template_categories' not in st.session_state:
    st.session_state.template_categories = {
        "Brain": [],
        "Spine": [],
        "Chest": [],
        "Abdomen": [],
        "MSK": [],
        "Other": []
    }
    # Load existing templates into categories
    for name, content in st.session_state.saved_templates.items():
        # Simple categorization (you can improve this)
        if any(word in name.lower() for word in ['brain', 'head', 'mri']):
            st.session_state.template_categories["Brain"].append(name)
        elif any(word in name.lower() for word in ['spine', 'vertebral']):
            st.session_state.template_categories["Spine"].append(name)
        elif any(word in name.lower() for word in ['chest', 'lung', 'thorax']):
            st.session_state.template_categories["Chest"].append(name)
        else:
            st.session_state.template_categories["Other"].append(name)

# ===== APP TITLE =====
st.title('🏥 Professional Radiology Reporting Assistant')

# ===== SIDEBAR: PATIENT INFO & TEMPLATE MANAGEMENT =====
with st.sidebar:
    st.header("🧾 Patient Information")
    
    # Patient Form
    with st.form("patient_form"):
        p_name = st.text_input("Full Name*")
        p_id = st.text_input("Patient ID*")
        p_age = st.text_input("Age")
        p_sex = st.selectbox("Sex", ["", "M", "F", "Other"])
        p_accession = st.text_input("Accession #")
        p_history = st.text_area("Clinical History", height=100)
        
        submitted = st.form_submit_button("💾 Load Patient Info")
        if submitted and p_name and p_id:
            st.session_state.patient_info = {
                "name": p_name, "id": p_id, "age": p_age,
                "sex": p_sex, "accession": p_accession,
                "history": p_history
            }
            st.success("Patient info saved!")
    
    st.divider()
    
    # ===== TEMPLATE LIBRARY WITH CATEGORIES =====
    st.header("📚 Template Library")
    
    # Category selection
    selected_category = st.selectbox(
        "Browse by category:",
        options=["All"] + list(st.session_state.template_categories.keys()),
        key="category_selector"
    )
    
    # Save Current Draft as a New Template WITH CATEGORY
    st.subheader("💾 Save Current Draft")
    
    col1, col2 = st.columns(2)
    with col1:
        new_template_name = st.text_input("Template name:")
    with col2:
        template_category = st.selectbox(
            "Category:",
            options=list(st.session_state.template_categories.keys()),
            key="new_template_category"
        )
    
    if st.button("💾 Save as New Template", key="save_button"):
        if not new_template_name:
            st.warning("Please enter a name for the template.")
        elif not st.session_state.report_draft:
            st.warning("Your draft is empty. Type something in the left column first.")
        else:
            # Save template content
            st.session_state.saved_templates[new_template_name] = st.session_state.report_draft
            
            # Add to category
            if new_template_name not in st.session_state.template_categories[template_category]:
                st.session_state.template_categories[template_category].append(new_template_name)
            
            # Save to file
            if save_templates_to_file():
                st.success(f"Template **'{new_template_name}'** saved to **{template_category}** category!")
            else:
                st.error("Template saved to session but failed to save to file.")
    
    st.divider()
    
    # ===== LOAD TEMPLATES BY CATEGORY =====
    st.subheader("📂 Load Saved Template")
    
    # Get templates based on selected category
    if selected_category == "All":
        available_templates = list(st.session_state.saved_templates.keys())
    else:
        available_templates = st.session_state.template_categories[selected_category]
    
    if available_templates:
        selected_template_name = st.selectbox(
            f"Choose from {selected_category}:",
            options=available_templates,
            key="template_selector"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Load into Draft", key="load_button"):
                if selected_template_name in st.session_state.saved_templates:
                    st.session_state.report_draft = st.session_state.saved_templates[selected_template_name]
                    st.success(f"Loaded **'{selected_template_name}'**!")
                    st.rerun()
        with col2:
            if st.button("🗑️ Delete", key="delete_button"):
                if selected_template_name in st.session_state.saved_templates:
                    # Remove from templates
                    del st.session_state.saved_templates[selected_template_name]
                    
                    # Remove from all categories
                    for category in st.session_state.template_categories:
                        if selected_template_name in st.session_state.template_categories[category]:
                            st.session_state.template_categories[category].remove(selected_template_name)
                    
                    # Save to file
                    save_templates_to_file()
                    st.warning(f"Deleted template **'{selected_template_name}'**.")
                    st.rerun()
        
        # Preview
        if selected_template_name in st.session_state.saved_templates:
            with st.expander("🔍 Preview"):
                preview_text = st.session_state.saved_templates[selected_template_name]
                st.caption(preview_text[:150] + "..." if len(preview_text) > 150 else preview_text)
    else:
        st.info(f"No templates in '{selected_category}' category yet.")
    
    st.divider()
    
    # ===== QUICK TEMPLATES =====
    st.header("⚡ Quick Insert")
    
    quick_categories = {
        "Brain MRI": {
            "Normal Brain MRI": "Normal study. No acute intracranial hemorrhage, mass effect, or territorial infarct. Ventricles and sulci are normal. No abnormal enhancement.",
            "White Matter Changes": "Scattered punctate FLAIR hyperintensities in the periventricular and deep white matter, consistent with chronic microvascular ischemia.",
            "Meningioma": "Extra-axial dural-based mass with homogeneous enhancement and dural tail sign. Mild vasogenic edema in the adjacent parenchyma.",
            "Acute Stroke": "Restricted diffusion in the [TERRITORY] territory consistent with acute infarct. No hemorrhage on GRE."
        },
        "Spine MRI": {
            "Disc Herniation": "Disc bulge/protrusion at [LEVEL] causing mild [SIDE] neural foraminal narrowing.",
            "Spinal Stenosis": "Degenerative changes with moderate central canal stenosis at [LEVEL]."
        }
    }
    
    selected_quick_category = st.selectbox("Category:", list(quick_categories.keys()))
    
    if selected_quick_category:
        selected_quick_template = st.selectbox(
            "Template:",
            ["Select..."] + list(quick_categories[selected_quick_category].keys())
        )
        
        if selected_quick_template != "Select...":
            if st.button(f"Insert '{selected_quick_template}'"):
                current_draft = st.session_state.report_draft
                new_text = quick_categories[selected_quick_category][selected_quick_template]
                separator = "\n" if current_draft else ""
                st.session_state.report_draft = current_draft + separator + new_text
                st.rerun()
    
    st.divider()
    
    # Clear All Button
    if st.button("🧹 Clear All Text (Draft & AI Report)"):
        st.session_state.report_draft = ""
        st.session_state.ai_report = ""
        st.rerun()

# ===== MAIN AREA: TWO-COLUMN EDITOR =====
col1, col2 = st.columns(2)

# Column 1: Your Draft Area WITH AUTO-SAVE
with col1:
    st.header("✍️ Your Draft / Findings")
    
    # Auto-save status indicator
    if 'last_save_time' in st.session_state:
        time_since_save = (datetime.datetime.now() - st.session_state.last_save_time).seconds
        if time_since_save < 60:
            st.caption(f"🔄 Auto-save: {time_since_save}s ago")
        elif time_since_save < 300:  # 5 minutes
            st.caption("⚡ Draft saved")
        else:
            st.caption("⏳ Draft not saved recently")
    
    st.caption("Type your raw observations, bullet points, or incomplete sentences here.")
    
    draft_text = st.text_area(
        "Draft your report below:",
        value=st.session_state.report_draft,
        height=450,
        key="draft_input",
        label_visibility="collapsed",
        placeholder="Example findings:\n- 2.3 cm well-defined lesion in the right frontal lobe\n- Isointense on T1, enhances homogeneously\n- Minimal perilesional edema\n- Differential: Meningioma vs. Metastasis"
    )
    
    # ===== AUTO-SAVE LOGIC =====
    if draft_text != st.session_state.get('last_saved_draft', ''):
        st.session_state.report_draft = draft_text
        
        # Auto-save every 30 seconds if draft has changed
        current_time = datetime.datetime.now()
        last_save = st.session_state.get('last_save_time', current_time)
        
        if (current_time - last_save).seconds > 30:  # Auto-save every 30 seconds
            st.session_state.last_saved_draft = draft_text
            st.session_state.last_save_time = current_time
            
            # Also auto-save to templates file periodically
            if 'saved_templates' in st.session_state and st.session_state.saved_templates:
                save_templates_to_file()
            
            # Show subtle success (you'll see it flash)
            st.success("💾 Draft auto-saved", icon="✅")

# Column 2: AI Assistant & Report
with col2:
    st.header("🤖 AI Report Assistant")
    
    if st.session_state.patient_info:
        patient = st.session_state.patient_info
        with st.expander("📄 Current Patient Info", expanded=True):
            st.markdown(f"**Name:** {patient['name']}  \n**ID:** {patient['id']}  \n**Age/Sex:** {patient['age']}/{patient['sex']}  \n**History:** {patient['history']}")
    
    if st.button("🤖 Generate Report with AI", type="primary", use_container_width=True):
        if not st.session_state.report_draft:
            st.warning("Please enter some draft findings in the left column first.")
        else:
            patient = st.session_state.get('patient_info', {})
            system_message = "You are an expert radiologist. Convert the following draft findings into a formal, structured radiology report."
            
            user_prompt = f"""
            PATIENT DETAILS:
            - Name: {patient.get('name', 'N/A')}
            - ID: {patient.get('id', 'N/A')}
            - Age/Sex: {patient.get('age', 'N/A')}/{patient.get('sex', 'N/A')}
            - Clinical History: {patient.get('history', 'N/A')}

            DRAFT FINDINGS:
            {st.session_state.report_draft}

            INSTRUCTIONS:
            Structure the report with: TECHNIQUE, FINDINGS, IMPRESSION.
            Use professional radiology language. Keep the impression concise.
            Do not add findings not mentioned in the draft.
            """

            with st.spinner('AI is writing the report...'):
                # ===== AI API CALL PLACEHOLDER =====
                # TEMPORARY SIMULATION - Replace with real API when ready
                ai_report = f"""**TECHNIQUE:** MRI brain without and with contrast.
**FINDINGS:** {st.session_state.report_draft[:100]}... [Full AI-generated report would appear here after API integration].
**IMPRESSION:** Findings consistent with the described observations. Clinical correlation recommended."""
                
                st.session_state.ai_report = ai_report
                # Add date and timestamp for the history
                st.session_state.report_date = datetime.datetime.now().strftime("%Y-%m-%d")
                st.session_state.report_timestamp = datetime.datetime.now().isoformat()
                st.success("Report generated!")
    
    # ===== PROFESSIONAL WORD DOWNLOAD =====
    if st.session_state.ai_report:
        st.subheader("AI-Generated Report")
        st.text_area(
            "",
            value=st.session_state.ai_report,
            height=400,
            key="ai_report_display",
            label_visibility="collapsed"
        )
        
        # Single "Download as Professional Word" button
        try:
            # Create professional Word document
            patient = st.session_state.get('patient_info', {})
            report_date = st.session_state.get('report_date', datetime.datetime.now().strftime('%Y-%m-%d'))
            
            doc = create_professional_word_report(
                st.session_state.ai_report,
                patient,
                report_date
            )
            
            # Save to bytes buffer
            doc_buffer = BytesIO()
            doc.save(doc_buffer)
            doc_buffer.seek(0)
            
            # Download button with professional label
            st.download_button(
                label="📄 Download Professional Report",
                data=doc_buffer,
                file_name=f"Rad_Report_{patient.get('id', 'Unknown')}_{report_date}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                help="Download as professionally formatted Microsoft Word document",
                use_container_width=True,
                type="primary"
            )
            
            # File info
            file_size = len(doc_buffer.getvalue()) / 1024  # KB
            st.caption(f"📦 File size: {file_size:.1f} KB | 📅 Date: {report_date}")
            
        except Exception as e:
            # Fallback to basic text if Word creation fails
            st.error(f"Professional Word creation failed: {str(e)[:100]}")
            st.download_button(
                label="📥 Download as Basic Text",
                data=st.session_state.ai_report,
                file_name=f"Report_{st.session_state.patient_info.get('id', 'Unknown')}.txt",
                mime="text/plain",
                use_container_width=True
            )
    else:
        st.info("👈 First, fill in patient info and type your draft findings.")
        st.markdown("""
        **Next Steps:**
        1. Enter patient details in the sidebar
        2. Type findings or load a template
        3. Click **'Generate Report with AI'**
        4. Download as professional Word document
        """)

# ===== REPORT HISTORY & EXPORT =====
st.divider()
st.header("📜 Report History")

# Save the current report to history
st.subheader("💾 Save Current Report")
report_to_save_name = st.text_input("Name for this report (e.g., PatientName_Date):")

if st.button("Save to History", key="save_history_button"):
    if not report_to_save_name:
        st.warning("Please enter a report name.")
    elif not st.session_state.report_draft and not st.session_state.ai_report:
        st.warning("No report content to save.")
    else:
        # Create a history entry with timestamp
        history_entry = {
            "name": report_to_save_name,
            "date": st.session_state.get("report_date", datetime.datetime.now().strftime("%Y-%m-%d")),
            "timestamp": st.session_state.get("report_timestamp", datetime.datetime.now().isoformat()),
            "patient_info": st.session_state.get("patient_info", {}),
            "draft": st.session_state.report_draft,
            "ai_report": st.session_state.ai_report
        }
        # Add to the beginning of the history list
        st.session_state.report_history.insert(0, history_entry)
        
        # Save to file
        if save_history_to_file():
            st.success(f"Report '{report_to_save_name}' saved to history!")
        else:
            st.error("Report saved to session but failed to save to file.")

st.divider()

# Browse and Load from History
st.subheader("📂 Load Past Report")

if st.session_state.report_history:
    # Create a list of report names for the dropdown
    history_options = [f"{entry['name']} ({entry.get('date', 'No date')})" for entry in st.session_state.report_history]
    
    selected_history = st.selectbox("Select a report:", options=history_options, key="history_selector")
    
    if selected_history:
        # Find the index of the selected report
        selected_index = history_options.index(selected_history)
        selected_entry = st.session_state.report_history[selected_index]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📥 Load Draft", key="load_history_draft"):
                st.session_state.report_draft = selected_entry['draft']
                st.session_state.patient_info = selected_entry['patient_info']
                st.success("Draft loaded!")
                st.rerun()
        with col2:
            if st.button("📥 Load AI Report", key="load_history_ai"):
                st.session_state.ai_report = selected_entry['ai_report']
                st.session_state.patient_info = selected_entry['patient_info']
                st.success("AI Report loaded!")
                st.rerun()
        with col3:
            if st.button("🗑️ Delete Entry", key="delete_history", type="secondary"):
                del st.session_state.report_history[selected_index]
                if save_history_to_file():
                    st.warning("Report deleted from history.")
                else:
                    st.error("Deleted from session but file save failed.")
                st.rerun()
        
        # Show a preview
        with st.expander("🔍 Preview this report"):
            st.write(f"**Patient:** {selected_entry['patient_info'].get('name', 'N/A')}")
            st.caption(f"**Saved on:** {selected_entry.get('timestamp', 'Unknown date')}")
            if selected_entry['draft']:
                st.caption("**Draft Preview:**")
                st.text(selected_entry['draft'][:150] + "..." if len(selected_entry['draft']) > 150 else selected_entry['draft'])
            if selected_entry['ai_report']:
                st.caption("**AI Report Preview:**")
                st.text(selected_entry['ai_report'][:150] + "..." if len(selected_entry['ai_report']) > 150 else selected_entry['ai_report'])

    # Add a button to clear ALL history
    st.divider()
    if st.button("🗑️ Clear ALL History", type="secondary", key="clear_all_history"):
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
        st.session_state.report_history = []
        st.warning("All history cleared!")
        st.rerun()
        
else:
    st.info("No reports in history yet. Save your first report above!")

# ===== BOTTOM SECTION =====
st.divider()
st.subheader("📊 Statistics")
col1, col2, col3 = st.columns(3)

with col1:
    total_templates = len(st.session_state.saved_templates)
    st.metric("Saved Templates", total_templates)

with col2:
    total_reports = len(st.session_state.report_history)
    st.metric("Saved Reports", total_reports)

with col3:
    draft_length = len(st.session_state.report_draft)
    st.metric("Current Draft", f"{draft_length} chars")

# Recent Drafts
st.subheader("💾 Recent Drafts")
if st.session_state.report_draft:
    st.caption("Your current draft (auto-saved):")
    st.code(st.session_state.report_draft[:300] + "..." if len(st.session_state.report_draft) > 300 else st.session_state.report_draft, language="text")
    
    # Auto-save timestamp
    if 'last_save_time' in st.session_state:
        last_save_str = st.session_state.last_save_time.strftime("%H:%M:%S")
        st.caption(f"Last auto-save: {last_save_str}")
else:
    st.caption("Start typing in the left column. Your draft will auto-save every 30 seconds.")

