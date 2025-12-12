"""
RADIOLOGY REPORTING ASSISTANT - GUARANTEED WORKING
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

# ===== CRITICAL: LOAD ENV AND INIT AI OUTSIDE STREAMLIT =====
print("\n" + "="*70, file=sys.stderr)
print("🚀 APPLICATION STARTUP LOG", file=sys.stderr)
print("="*70, file=sys.stderr)

# 1. Force load .env file
load_dotenv()
API_KEY = os.getenv("PERPLEXITY_API_KEY")

if API_KEY:
    print(f"✅ API Key loaded: {API_KEY[:20]}...", file=sys.stderr)
else:
    print("❌ API Key NOT loaded from .env", file=sys.stderr)
    # Emergency fallback - read directly
    try:
        with open('.env', 'r') as f:
            for line in f:
                if 'PERPLEXITY_API_KEY' in line:
                    API_KEY = line.split('=', 1)[1].strip()
                    print(f"⚠️  API Key loaded directly from file: {API_KEY[:20]}...", file=sys.stderr)
                    break
    except:
        pass

# 2. Initialize Perplexity AI client
CLIENT = None
if API_KEY:
    try:
        CLIENT = openai.OpenAI(
            api_key=API_KEY,
            base_url="https://api.perplexity.ai"
        )
        # Quick silent test
        CLIENT.chat.completions.create(
            model="sonar",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=1
        )
        print("✅ Perplexity AI client initialized successfully", file=sys.stderr)
    except Exception as e:
        print(f"❌ Failed to initialize AI client: {e}", file=sys.stderr)
        CLIENT = None
else:
    print("❌ Cannot initialize client: No API key", file=sys.stderr)

print("="*70 + "\n", file=sys.stderr)

# ===== STREAMLIT APP =====
def main():
    st.set_page_config(
        page_title="Radiology Reporting Assistant",
        layout="wide",
        page_icon="🏥"
    )
    
    # Title with status
    if CLIENT:
        st.title("🏥 Radiology Reporting Assistant 🤖")
        st.success("✅ AI Assistant is ACTIVE and READY!")
    else:
        st.title("🏥 Radiology Reporting Assistant")
        st.error("⚠️ AI Assistant is DISABLED - Check terminal logs")
    
    # Login system
    if 'users' not in st.session_state:
        st.session_state.users = {
            "admin": {"password": hashlib.sha256("admin123".encode()).hexdigest()},
            "radiologist": {"password": hashlib.sha256("rad123".encode()).hexdigest()}
        }
        st.session_state.logged_in = False
    
    # Login page
    if not st.session_state.logged_in:
        st.header("🔐 Login")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.container(border=True):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                
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
                
                st.info("Use: **admin/admin123** or **radiologist/rad123**")
        
        return
    
    # Main app (after login)
    st.write(f"**User:** {st.session_state.current_user}")
    
    if st.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.rerun()
    
    # Debug panel
    with st.expander("🔧 System Status", expanded=True):
        st.write(f"**API Key loaded:** {'✅ Yes' if API_KEY else '❌ No'}")
        if API_KEY:
            st.write(f"**Key starts with:** {API_KEY[:20]}...")
        st.write(f"**AI Client:** {'✅ Initialized' if CLIENT else '❌ Failed'}")
        
        if st.button("Test Connection"):
            if CLIENT:
                with st.spinner("Testing..."):
                    try:
                        response = CLIENT.chat.completions.create(
                            model="sonar",
                            messages=[{"role": "user", "content": "Say 'Connected'"}],
                            max_tokens=10
                        )
                        st.success(f"✅ Connection test passed: {response.choices[0].message.content}")
                    except Exception as e:
                        st.error(f"❌ Connection failed: {str(e)}")
            else:
                st.error("AI client not available")
    
    # Main interface
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("✍️ Input")
        
        modality = st.selectbox("Modality", ["MRI", "CT", "X-ray", "Ultrasound", "PET-CT"])
        contrast = st.selectbox("Contrast", ["Without contrast", "With contrast"])
        
        findings = st.text_area(
            "Findings:",
            height=200,
            placeholder="Example: Right MCA territory infarct with mass effect and midline shift..."
        )
        
        if CLIENT and st.button("🤖 Generate AI Report", type="primary", use_container_width=True):
            if findings.strip():
                with st.spinner("AI is generating report..."):
                    try:
                        prompt = f"""You are a senior radiologist. Create a structured report.

TECHNIQUE: {modality}, {contrast}

FINDINGS PROVIDED: {findings}

Please provide a complete report with:
1. TECHNIQUE section
2. DETAILED FINDINGS section
3. IMPRESSION section (numbered conclusions)

Use professional medical terminology."""
                        
                        response = CLIENT.chat.completions.create(
                            model="sonar",
                            messages=[
                                {"role": "system", "content": "You are an expert radiologist."},
                                {"role": "user", "content": prompt}
                            ],
                            max_tokens=1500
                        )
                        
                        report = response.choices[0].message.content
                        st.session_state.generated_report = report
                        st.success("✅ Report generated successfully!")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"AI Error: {str(e)}")
            else:
                st.warning("Please enter findings first")
        elif not CLIENT:
            st.warning("AI not available")
    
    with col2:
        st.header("📋 Generated Report")
        
        if 'generated_report' in st.session_state:
            # Display report
            st.text_area(
                "Report:",
                st.session_state.generated_report,
                height=350,
                key="report_display"
            )
            
            # Download as Word
            try:
                doc = Document()
                doc.add_heading('RADIOLOGY REPORT', 0)
                doc.add_paragraph(f"Modality: {modality}")
                doc.add_paragraph(f"Contrast: {contrast}")
                doc.add_paragraph()
                
                for line in st.session_state.generated_report.split('\n'):
                    if line.strip():
                        doc.add_paragraph(line.strip())
                
                buffer = BytesIO()
                doc.save(buffer)
                buffer.seek(0)
                
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
                st.download_button(
                    label="📄 Download Word Document",
                    data=buffer,
                    file_name=f"RadReport_{timestamp}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )
                
            except Exception as e:
                st.error(f"Document error: {e}")
            
            if st.button("🧹 Clear Report", use_container_width=True):
                del st.session_state.generated_report
                st.rerun()
        
        else:
            st.info("""
            **No report yet.**
            
            To generate a report:
            1. Select modality and contrast
            2. Enter findings in the text area
            3. Click "Generate AI Report"
            
            **Try this example:**
            ```
            Right basal ganglia hemorrhage measuring 3.2 x 2.1 cm
            with surrounding edema and 8 mm midline shift.
            ```
            """)

if __name__ == "__main__":
    main()
