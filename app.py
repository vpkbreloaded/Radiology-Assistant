import streamlit as st
from docx import Document
from io import BytesIO
import re

st.set_page_config(page_title="AI Radiology Assistant", layout="wide")

# ===== Initialize session state =====
if 'report_draft' not in st.session_state:
    st.session_state.report_draft = ""
if 'patient_info' not in st.session_state:
    st.session_state.patient_info = {}
if 'ai_report' not in st.session_state:
    st.session_state.ai_report = ""

st.title('🏥 AI-Powered Radiology Reporting Assistant')

# ===== SIDEBAR: Patient Info & Controls =====
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
    
    # Template Quick Insert
    st.header("📋 Quick Templates")
    template_options = {
        "Normal Brain MRI": "Normal study. No acute intracranial hemorrhage, mass effect, or territorial infarct. Ventricles and sulci are normal. No abnormal enhancement.",
        "White Matter Changes": "Scattered punctate FLAIR hyperintensities in the periventricular and deep white matter, consistent with chronic microvascular ischemia.",
        "Meningioma": "Extra-axial dural-based mass with homogeneous enhancement and dural tail sign. Mild vasogenic edema in the adjacent parenchyma.",
        "Acute Stroke": "Restricted diffusion in the [TERRITORY] territory consistent with acute infarct. No hemorrhage on GRE."
    }
    
    selected_template = st.selectbox("Insert common findings:", ["Select..."] + list(template_options.keys()))
    if selected_template != "Select...":
        if st.button(f"Insert '{selected_template}'"):
            current_draft = st.session_state.report_draft
            new_text = template_options[selected_template]
            st.session_state.report_draft = current_draft + "\n" + new_text if current_draft else new_text
            st.rerun()
    
    st.divider()
    if st.button("🧹 Clear All Text"):
        st.session_state.report_draft = ""
        st.session_state.ai_report = ""
        st.rerun()

# ===== MAIN AREA: Two-Column Editor =====
col1, col2 = st.columns(2)

# Column 1: Your Draft Area
with col1:
    st.header("✍️ Your Draft / Findings")
    st.caption("Type your raw observations, bullet points, or incomplete sentences here.")
    
    # Large text area for drafting
    draft_text = st.text_area(
        "Draft your report below:",
        value=st.session_state.report_draft,
        height=450,
        key="draft_input",
        label_visibility="collapsed",
        placeholder="Example findings:\n- 2.3 cm well-defined lesion in the right frontal lobe\n- Isointense on T1, enhances homogeneously\n- Minimal perilesional edema\n- Differential: Meningioma vs. Metastasis"
    )
    # Update session state as user types
    st.session_state.report_draft = draft_text

# Column 2: AI Assistant & Report
with col2:
    st.header("🤖 AI Report Assistant")
    
    # Show patient info if available
    if st.session_state.patient_info:
        patient = st.session_state.patient_info
        with st.expander("📄 Current Patient Info", expanded=True):
            st.markdown(f"**Name:** {patient['name']}  \n**ID:** {patient['id']}  \n**Age/Sex:** {patient['age']}/{patient['sex']}  \n**History:** {patient['history']}")
    
    # ===== AI GENERATION BUTTON (READY FOR API INTEGRATION) =====
    if st.button("🤖 Generate Report with AI", type="primary", use_container_width=True):
        if not st.session_state.report_draft:
            st.warning("Please enter some draft findings in the left column first.")
        else:
            # Construct the prompt for the AI
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
                # ===== IMPORTANT: API CALL PLACEHOLDER =====
                # Replace this section with actual Perplexity/DeepSeek API code
                # ------------------------------------------------------------
                # Example structure for Perplexity API (requires 'perplexityai' library):
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
                
                # TEMPORARY: Simulated AI response for testing
                ai_report = f"""**TECHNIQUE:** MRI brain without and with contrast.
**FINDINGS:** {st.session_state.report_draft[:100]}... [Full AI-generated report would appear here after API integration].
**IMPRESSION:** Findings consistent with the described observations. Clinical correlation recommended."""
                
                st.session_state.ai_report = ai_report
                st.success("Report generated!")
    
    # Display the AI-generated report
    if st.session_state.ai_report:
        st.subheader("AI-Generated Report")
        st.text_area(
            "",
            value=st.session_state.ai_report,
            height=400,
            key="ai_report_display",
            label_visibility="collapsed"
        )
        
        # Download button for the AI report
        st.download_button(
            label="📥 Download AI Report",
            data=st.session_state.ai_report,
            file_name=f"AI_Report_{st.session_state.patient_info.get('id', 'Unknown')}.txt",
            mime="text/plain",
            use_container_width=True
        )
    else:
        # Initial instructions
        st.info("👈 First, fill in patient info in the sidebar and type your draft findings in the left column.")
        st.markdown("""
        **How this works:**
        1. Enter patient details in the **sidebar**
        2. Type your findings in the **left column**
        3. Click **'Generate Report with AI'** button above
        """)

# ===== BOTTOM SECTION: Recent Drafts =====
st.divider()
st.subheader("💾 Recent Drafts")
if st.session_state.report_draft:
    st.caption("Your current draft is auto-saved. Copy it for later use:")
    st.code(st.session_state.report_draft[:500] + "..." if len(st.session_state.report_draft) > 500 else st.session_state.report_draft, language="text")
else:
    st.caption("Start typing in the left column to see your draft appear here.")
