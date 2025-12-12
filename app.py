"""
Radiology Reporting Assistant - WORKING VERSION
"""
import os
import sys
import streamlit as st
import openai
from dotenv import load_dotenv
from docx import Document
from io import BytesIO
import datetime
import hashlib
import json

# ===== CRITICAL: LOAD ENVIRONMENT AND INITIALIZE AI FIRST =====
print("=" * 60, file=sys.stderr)
print("INITIALIZING APPLICATION", file=sys.stderr)

# 1. Load the .env file
load_dotenv()
API_KEY = os.getenv("PERPLEXITY_API_KEY")

# 2. Validate the key is loaded
if not API_KEY:
    print("ERROR: PERPLEXITY_API_KEY not found in environment.", file=sys.stderr)
    CLIENT = None
else:
    print(f"INFO: API Key loaded successfully (starts with: {API_KEY[:10]}...)", file=sys.stderr)
    # 3. Initialize the Perplexity client using the OpenAI SDK
    try:
        CLIENT = openai.OpenAI(
            api_key=API_KEY,
            base_url="https://api.perplexity.ai"  # Correct endpoint for Perplexity
        )
        print("INFO: Perplexity AI client initialized successfully.", file=sys.stderr)
        # Optional quick connection test (silent)
        # _ = CLIENT.chat.completions.create(model="sonar", messages=[{"role": "user", "content": "test"}], max_tokens=1)
    except Exception as e:
        print(f"ERROR: Failed to initialize AI client: {e}", file=sys.stderr)
        CLIENT = None

print("=" * 60, file=sys.stderr)

# ===== TEMPLATE SYSTEM (from your original code) =====
TEMPLATES_FILE = "saved_templates.json"
class TemplateSystem:
    def __init__(self):
        self.templates = self.load_templates()
    def load_templates(self):
        if os.path.exists(TEMPLATES_FILE):
            try:
                with open(TEMPLATES_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    # ... (include other methods like save_templates, add_template, etc.)

# ===== STREAMLIT APP =====
def main():
    st.set_page_config(page_title="Radiology Reporting Assistant", layout="wide", page_icon="🏥")
    st.title("🏥 Radiology Reporting Assistant")

    # Display status at the top
    if CLIENT:
        st.success("✅ AI Assistant is ACTIVE and ready to generate reports!")
    else:
        st.error("⚠️ AI Assistant is DISABLED. Check the console/terminal for error logs.")

    # Initialize session state for user management
    if 'users' not in st.session_state:
        st.session_state.users = {
            "admin": {"password": hashlib.sha256("admin123".encode()).hexdigest(), "role": "admin"},
            "radiologist": {"password": hashlib.sha256("rad123".encode()).hexdigest(), "role": "radiologist"}
        }
        st.session_state.logged_in = False
        st.session_state.current_user = None

    # --- Login / Logout Logic ---
    if not st.session_state.logged_in:
        st.header("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            hashed_pw = hashlib.sha256(password.encode()).hexdigest()
            if username in st.session_state.users and st.session_state.users[username]["password"] == hashed_pw:
                st.session_state.logged_in = True
                st.session_state.current_user = username
                st.rerun()
            else:
                st.error("Invalid username or password")
        st.info("Use **admin / admin123** or **radiologist / rad123**")
        return  # Stop here until logged in

    # Main App (after login)
    st.write(f"Logged in as: **{st.session_state.current_user}**")
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- Main Application Columns ---
    col1, col2 = st.columns([1, 1])
    with col1:
        st.header("✍️ Input Findings")
        modality = st.selectbox("Modality", ["MRI", "CT", "X-ray", "Ultrasound", "PET-CT"])
        findings = st.text_area("Clinical Findings", height=200, placeholder="Describe the imaging findings in detail...")
        
        if st.button("🤖 Generate AI Report", type="primary", disabled=(CLIENT is None)):
            if not findings.strip():
                st.warning("Please enter findings first.")
            else:
                with st.spinner("AI is generating a structured report..."):
                    try:
                        prompt = f"""You are a senior board-certified radiologist. Generate a complete, structured radiology report based on the following information.

IMAGING TECHNIQUE: {modality}
CLINICAL FINDINGS PROVIDED: {findings}

Please structure the report with the following sections:
1. TECHNIQUE: Describe the imaging technique briefly.
2. FINDINGS: Provide a detailed, systematic description of the findings using precise radiological terminology.
3. IMPRESSION: Summarize the key conclusions and provide clinical recommendations in a numbered list.

Ensure the report is professional, concise, and ready for clinical use."""
                        
                        response = CLIENT.chat.completions.create(
                            model="sonar",
                            messages=[
                                {"role": "system", "content": "You are a expert radiologist. Always output complete, well-structured medical reports."},
                                {"role": "user", "content": prompt}
                            ],
                            max_tokens=2000
                        )
                        generated_report = response.choices[0].message.content
                        st.session_state['last_report'] = generated_report
                        st.session_state['last_modality'] = modality
                        st.success("Report generated successfully!")
                    except Exception as e:
                        st.error(f"Failed to generate report: {e}")

    with col2:
        st.header("📋 Report Output")
        if 'last_report' in st.session_state:
            st.text_area("Generated Report", st.session_state['last_report'], height=350)
            
            # Create a downloadable Word document
            doc = Document()
            doc.add_heading(f'{modality} RADIOLOGY REPORT', 0)
            for line in st.session_state['last_report'].split('\n'):
                doc.add_paragraph(line)
            
            bio = BytesIO()
            doc.save(bio)
            st.download_button(
                label="📥 Download as Word (.docx)",
                data=bio.getvalue(),
                file_name=f"Radiology_Report_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        else:
            st.info("Generate a report to see the output here.")

    # Debug Panel in Sidebar
    with st.sidebar:
        st.header("🔧 System Status")
        st.write(f"**AI Client:** {'✅ Initialized' if CLIENT else '❌ Failed'}")
        st.write(f"**API Key Present:** {'✅ Yes' if API_KEY else '❌ No'}")
        if st.button("Test Connection"):
            if CLIENT:
                try:
                    test = CLIENT.chat.completions.create(
                        model="sonar",
                        messages=[{"role": "user", "content": "Say 'OK'."}],
                        max_tokens=5
                    )
                    st.success(f"Connection Test Passed: {test.choices[0].message.content}")
                except openai.AuthenticationError:
                    st.error("Authentication Failed. The API key may be invalid or revoked.[citation:4]")
                except Exception as e:
                    st.error(f"Connection Failed: {e}")
            else:
                st.error("Client not initialized.")

if __name__ == "__main__":
    main()
