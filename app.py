import streamlit as st
from docx import Document
from io import BytesIO
import re
import json
import os
import datetime

# ===== FUNCTIONS FOR PERMANENT STORAGE =====
HISTORY_FILE = "report_history.json"

def save_history_to_file():
    """Save the report history to a JSON file."""
    try:
        # Convert the history to a serializable format
        history_to_save = []
        for entry in st.session_state.report_history:
            # Create a clean copy that can be saved as JSON
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

# ===== STREAMLIT PAGE CONFIG =====
st.set_page_config(page_title="AI Radiology Assistant", layout="wide")

# ===== INITIALIZE SESSION STATE =====
if 'report_draft' not in st.session_state:
    st.session_state.report_draft = ""
if 'patient_info' not in st.session_state:
    st.session_state.patient_info = {}
if 'saved_templates' not in st.session_state:
    st.session_state.saved_templates = {}
if 'ai_report' not in st.session_state:
    st.session_state.ai_report = ""
if 'report_history' not in st.session_state:
    st.session_state.report_history = load_history_from_file()

# ===== APP TITLE =====
st.title('🏥 AI-Powered Radiology Reporting Assistant')

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
    
    # ===== TEMPLATE LIBRARY =====
    st.header("📚 Template Library")
    
    # --- Save Current Draft as a New Template ---
    st.subheader("💾 Save Current Draft")
    new_template_name = st.text_input("Give this template a name:")
    
    if st.button("💾 Save as New Template", key="save_button"):
        if not new_template_name:
            st.warning("Please enter a name for the template.")
        elif not st.session_state.report_draft:
            st.warning("Your draft is empty. Type something in the left column first.")
        else:
            st.session_state.saved_templates[new_template_name] = st.session_state.report_draft
            st.success(f"Template **'{new_template_name}'** saved successfully!")
    
    st.divider()
    
    # --- Load a Saved Template ---
    st.subheader("📂 Load a Saved Template")
    
    if 'saved_templates' in st.session_state and st.session_state.saved_templates:
        template_list = list(st.session_state.saved_templates.keys())
        selected_template_name = st.selectbox("Choose a template:", options=template_list, key="template_selector")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Load into Draft", key="load_button"):
                st.session_state.report_draft = st.session_state.saved_templates[selected_template_name]
                st.success(f"Loaded **'{selected_template_name}'**!")
                st.rerun()
        with col2:
            if st.button("🗑️ Delete", key="delete_button"):
                del st.session_state.saved_templates[selected_template_name]
                st.warning(f"Deleted template **'{selected_template_name}'**.")
                st.rerun()
        
        with st.expander("Preview selected template"):
            preview_text = st.session_state.saved_templates[selected_template_name]
            st.caption(preview_text[:200] + "..." if len(preview_text) > 200 else preview_text)
    else:
        st.info("No saved templates yet. Save your first draft above!")
    
    st.divider()
    
    # ===== QUICK TEMPLATES =====
    st.header("⚡ Quick Insert")
    template_options = {
        "Normal Brain MRI": "Normal study. No acute intracranial hemorrhage, mass effect, or territorial infarct. Ventricles and sulci are normal. No abnormal enhancement.",
        "White Matter Changes": "Scattered punctate FLAIR hyperintensities in the periventricular and deep white matter, consistent with chronic microvascular ischemia.",
        "Meningioma": "Extra-axial dural-based mass with homogeneous enhancement and dural tail sign. Mild vasogenic edema in the adjacent parenchyma.",
        "Acute Stroke": "Restricted diffusion in the [TERRITORY] territory consistent with acute infarct. No hemorrhage on GRE."
    }
    
    selected_quick_template = st.selectbox("Insert common findings:", ["Select..."] + list(template_options.keys()))
    if selected_quick_template != "Select...":
        if st.button(f"Insert '{selected_quick_template}' snippet"):
            current_draft = st.session_state.report_draft
            new_text = template_options[selected_quick_template]
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

# Column 1: Your Draft Area
with col1:
    st.header("✍️ Your Draft / Findings")
    st.caption("Type your raw observations, bullet points, or incomplete sentences here.")
    
    draft_text = st.text_area(
        "Draft your report below:",
        value=st.session_state.report_draft,
        height=450,
        key="draft_input",
        label_visibility="collapsed",
        placeholder="Example findings:\n- 2.3 cm well-defined lesion in the right frontal lobe\n- Isointense on T1, enhances homogeneously\n- Minimal perilesional edema\n- Differential: Meningioma vs. Metastasis"
    )
    st.session_state.report_draft = draft_text

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
                # To use Perplexity/OpenAI, uncomment and configure the code below
                # ------------------------------------------------------------
                # Example for Perplexity:
                # from perplexity import Perplexity
                # client = Perplexity(api_key=st.secrets["PERPLEXITY_API_KEY"])
                # response = client.chat.completions.create(
                #     model="sonar-pro",
                #     messages=[
                #         {"role": "system", "content": system_message},
                #         {"role": "user", "content": user_prompt}
                #     ]
                # )
                # ai_report = response.choices[0].message.content
                # ------------------------------------------------------------
                
                # TEMPORARY SIMULATION (Delete this when using real API)
                ai_report = f"""**TECHNIQUE:** MRI brain without and with contrast.
**FINDINGS:** {st.session_state.report_draft[:100]}... [Full AI-generated report would appear here after API integration].
**IMPRESSION:** Findings consistent with the described observations. Clinical correlation recommended."""
                
                st.session_state.ai_report = ai_report
                # Add date and timestamp for the history
                st.session_state.report_date = datetime.datetime.now().strftime("%Y-%m-%d")
                st.session_state.report_timestamp = datetime.datetime.now().isoformat()
                st.success("Report generated!")
    
    if st.session_state.ai_report:
        st.subheader("AI-Generated Report")
        st.text_area(
            "",
            value=st.session_state.ai_report,
            height=400,
            key="ai_report_display",
            label_visibility="collapsed"
        )
        
        st.download_button(
            label="📥 Download AI Report",
            data=st.session_state.ai_report,
            file_name=f"AI_Report_{st.session_state.patient_info.get('id', 'Unknown')}.txt",
            mime="text/plain",
            use_container_width=True
        )
    else:
        st.info("👈 First, fill in patient info in the sidebar and type your draft findings in the left column.")
        st.markdown("""
        **How this works:**
        1. Enter patient details in the **sidebar**
        2. Type your findings in the **left column**
        3. Click **'Generate Report with AI'** button above
        """)

# ===== REPORT HISTORY & EXPORT =====
st.divider()
st.header("📜 Report History")

# --- Save the current report to history ---
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

# --- Browse and Load from History ---
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
        with st.expander("Preview this report"):
            st.write(f"**Patient:** {selected_entry['patient_info'].get('name', 'N/A')}")
            st.caption(f"**Saved on:** {selected_entry.get('timestamp', 'Unknown date')}")
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

# In your right column, where you display st.session_state.ai_report
if st.session_state.ai_report:
    st.subheader("AI-Generated Report")
    st.text_area(
        "",
        value=st.session_state.ai_report,
        height=400,
        key="ai_report_display",
        label_visibility="collapsed"
    )
    
    # === SINGLE "DOWNLOAD AS WORD" BUTTON ===
    try:
        from docx import Document
        from io import BytesIO
        
        # Create a new Word document
        doc = Document()
        
        # Add title and patient info
        doc.add_heading('RADIOLOGY REPORT', 0)
        
        patient = st.session_state.get('patient_info', {})
        if patient:
            doc.add_paragraph(f"Patient: {patient.get('name', 'N/A')}")
            doc.add_paragraph(f"Patient ID: {patient.get('id', 'N/A')}")
            doc.add_paragraph(f"Age/Sex: {patient.get('age', 'N/A')}/{patient.get('sex', 'N/A')}")
            if patient.get('accession'):
                doc.add_paragraph(f"Accession #: {patient.get('accession')}")
        
        doc.add_paragraph(f"Report Date: {st.session_state.get('report_date', 'N/A')}")
        doc.add_paragraph()  # Empty line
        
        # Add the AI report content
        # Split into paragraphs for better formatting
        report_lines = st.session_state.ai_report.split('\n')
        for line in report_lines:
            if line.strip():  # Only add non-empty lines
                doc.add_paragraph(line.strip())
        
        # Save document to a BytesIO buffer
        doc_buffer = BytesIO()
        doc.save(doc_buffer)
        doc_buffer.seek(0)  # Move to start of buffer
        
        # Single download button for Word document
        st.download_button(
            label="📄 Download Report as Word",
            data=doc_buffer,
            file_name=f"Rad_Report_{st.session_state.patient_info.get('id', 'Unknown')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            help="Download as Microsoft Word document (.docx)",
            use_container_width=True,
            type="primary"  # Makes it stand out as the main action
        )
        
    except Exception as e:
        # Fallback to text download if Word creation fails
        st.error(f"Word creation failed: {str(e)[:50]}...")
        st.download_button(
            label="📥 Download Report as Text (Fallback)",
            data=st.session_state.ai_report,
            file_name=f"Report_{st.session_state.patient_info.get('id', 'Unknown')}.txt",
            mime="text/plain",
            use_container_width=True
        )
