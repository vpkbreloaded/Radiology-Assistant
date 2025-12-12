"""
Streamlined Radiology Reporting Assistant
WITH WORKING Perplexity AI Integration
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
from collections import defaultdict
import openai
from dotenv import load_dotenv

# ===== INITIALIZATION =====
print("=" * 60)
print("🚀 STARTING RADIOLOGY ASSISTANT")
print("=" * 60)

# Load environment
load_dotenv()
API_KEY = os.getenv("PERPLEXITY_API_KEY")

if API_KEY:
    print(f"✅ API Key loaded: {API_KEY[:20]}...")
else:
    print("❌ API Key NOT loaded")

# Initialize AI client
client = None
if API_KEY:
    try:
        client = openai.OpenAI(
            api_key=API_KEY,
            base_url="https://api.perplexity.ai"
        )
        print("✅ Perplexity AI client initialized")
    except Exception as e:
        print(f"❌ AI client error: {e}")
        client = None

print("=" * 60)

# ===== CONFIGURATION =====
TEMPLATES_FILE = "saved_templates.json"

# ===== TEMPLATE SYSTEM =====
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
    
    def save_templates(self):
        try:
            with open(TEMPLATES_FILE, 'w') as f:
                json.dump(self.templates, f, indent=2)
        except:
            pass
    
    def add_template(self, name, content, template_type="findings"):
        self.templates[name] = {
            "content": content,
            "type": template_type,
            "created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "used": 0
        }
        self.save_templates()
    
    def get_template(self, name):
        return self.templates.get(name)
    
    def increment_use(self, name):
        if name in self.templates:
            self.templates[name]["used"] = self.templates[name].get("used", 0) + 1
            self.save_templates()

def create_word_document(report_text, technique_info):
    """Create Word document."""
    doc = Document()
    
    # Title
    title = doc.add_heading('RADIOLOGY REPORT', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    doc.add_paragraph()
    
    # Technique
    doc.add_heading('TECHNIQUE', level=1)
    doc.add_paragraph(f"Modality: {technique_info.get('modality', 'Not specified')}")
    doc.add_paragraph(f"Contrast: {technique_info.get('contrast', 'Without contrast')}")
    if technique_info.get('protocol'):
        doc.add_paragraph(f"Protocol: {technique_info['protocol']}")
    
    doc.add_paragraph()
    
    # Report content
    lines = report_text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            doc.add_paragraph()
            continue
            
        if line.endswith(':') and line[:-1].replace(' ', '').isupper():
            doc.add_heading(line[:-1], level=1)
        else:
            doc.add_paragraph(line)
    
    # Footer
    doc.add_page_break()
    doc.add_heading('REPORT DETAILS', level=1)
    doc.add_paragraph(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    doc.add_paragraph(f"AI-assisted via Perplexity AI")
    
    return doc

# ===== INITIALIZE SESSION STATE =====
def init_session_state():
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.users = {
            "admin": {"password": hashlib.sha256("admin123".encode()).hexdigest(), "role": "admin"},
            "radiologist": {"password": hashlib.sha256("rad123".encode()).hexdigest(), "role": "radiologist"}
        }
        st.session_state.report_history = []
        st.session_state.current_report = ""
        st.session_state.report_draft = ""
        st.session_state.current_user = ""
        st.session_state.logged_in = False
        st.session_state.template_system = TemplateSystem()
        st.session_state.technique_info = {
            "modality": "MRI",
            "contrast": "Without contrast",
            "protocol": "Standard sequences"
        }
        st.session_state.ai_client = client  # Store the AI client

# ===== STREAMLIT APP =====
def main():
    st.set_page_config(
        page_title="Radiology Reporting Assistant",
        layout="wide",
        page_icon="🏥"
    )
    
    init_session_state()
    
    # ===== LOGIN SYSTEM =====
    if not st.session_state.logged_in:
        st.title("🔐 Radiology Assistant - Login")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.container(border=True):
                st.subheader("Login")
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                
                if st.button("Login", type="primary", use_container_width=True):
                    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
                    if username in st.session_state.users:
                        if st.session_state.users[username]["password"] == hashed_pw:
                            st.session_state.logged_in = True
                            st.session_state.current_user = username
                            
                            # Check AI status
                            if st.session_state.ai_client:
                                st.success(f"✅ Welcome, {username}! AI Assistant is ready.")
                            else:
                                st.warning(f"⚠️ Welcome, {username}! AI features unavailable.")
                            
                            st.rerun()
                        else:
                            st.error("Invalid password")
                    else:
                        st.error("User not found")
                
                st.info("Demo: admin/admin123 or radiologist/rad123")
        
        return
    
    # ===== MAIN APPLICATION =====
    
    # Header
    st.title("🏥 Radiology Reporting Assistant 🤖")
    
    # AI Status
    if st.session_state.ai_client:
        st.success("✅ AI Assistant is ACTIVE and ready!")
    else:
        st.error("⚠️ AI Assistant is DISABLED. Check console logs.")
    
    col_user1, col_user2 = st.columns([3, 1])
    with col_user1:
        st.markdown(f"**User:** {st.session_state.current_user}")
    
    with col_user2:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()
    
    # Main columns
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # ===== LEFT PANEL =====
        st.header("✍️ Report Creation")
        
        # Technique
        with st.expander("🔬 Technique Details", expanded=True):
            col_tech1, col_tech2 = st.columns(2)
            with col_tech1:
                st.session_state.technique_info["modality"] = st.selectbox(
                    "Modality",
                    ["MRI", "CT", "Ultrasound", "X-ray", "PET-CT", "Mammography"],
                    key="modality"
                )
                
                st.session_state.technique_info["contrast"] = st.selectbox(
                    "Contrast",
                    ["Without contrast", "With contrast", "With and without contrast", "Not specified"],
                    key="contrast"
                )
            
            with col_tech2:
                st.session_state.technique_info["protocol"] = st.text_area(
                    "Protocol/Sequences",
                    value=st.session_state.technique_info["protocol"],
                    placeholder="e.g., T1, T2, FLAIR, DWI, ADC",
                    height=80,
                    key="protocol"
                )
        
        # AI Assistance
        if st.session_state.ai_client:
            st.divider()
            st.header("🤖 AI Assistance")
            
            ai_mode = st.radio(
                "AI Mode:",
                ["Generate Full Report", "Enhance Findings", "Differential Diagnosis"],
                horizontal=True
            )
            
            # Quick AI Input
            st.subheader("⚡ Quick Input")
            quick_input = st.text_area(
                "Brief findings:",
                height=100,
                placeholder="e.g., 'Right MCA infarct with mass effect'",
                key="quick_input"
            )
            
            col_ai1, col_ai2 = st.columns(2)
            with col_ai1:
                if st.button("🚀 Generate with AI", type="primary", use_container_width=True):
                    if quick_input:
                        with st.spinner("🤖 AI is working..."):
                            try:
                                if ai_mode == "Generate Full Report":
                                    prompt = f"""Create a complete radiology report.

Technique: {st.session_state.technique_info['modality']}, {st.session_state.technique_info['contrast']}
Findings: {quick_input}

Provide: TECHNIQUE, FINDINGS, and IMPRESSION sections."""
                                
                                elif ai_mode == "Enhance Findings":
                                    prompt = f"""Expand and enhance these findings with proper terminology:

Original: {quick_input}

Provide detailed radiological descriptions."""
                                
                                else:  # Differential Diagnosis
                                    prompt = f"""Provide differential diagnosis for:

Findings: {quick_input}

List: Most likely diagnosis, alternatives, and recommendations."""
                                
                                response = st.session_state.ai_client.chat.completions.create(
                                    model="sonar",
                                    messages=[
                                        {"role": "system", "content": "You are a senior radiologist."},
                                        {"role": "user", "content": prompt}
                                    ],
                                    max_tokens=1500
                                )
                                
                                st.session_state.current_report = response.choices[0].message.content
                                st.success("✅ AI report generated!")
                                
                            except Exception as e:
                                st.error(f"AI error: {str(e)}")
                    else:
                        st.warning("Enter findings first")
            
            with col_ai2:
                if st.button("🔄 Test Connection", use_container_width=True):
                    if st.session_state.ai_client:
                        with st.spinner("Testing..."):
                            try:
                                response = st.session_state.ai_client.chat.completions.create(
                                    model="sonar",
                                    messages=[{"role": "user", "content": "Say 'OK' if working"}],
                                    max_tokens=5
                                )
                                st.success(f"✅ Connected: {response.choices[0].message.content}")
                            except Exception as e:
                                st.error(f"❌ Failed: {str(e)}")
        
        # Templates
        st.divider()
        st.header("📚 Templates")
        
        # Quick Templates
        quick_templates = {
            "Normal Brain MRI": "No acute intracranial abnormality. Ventricles and sulci are normal.",
            "Disc Herniation": "Disc bulge causing mild neural foraminal narrowing.",
            "Pneumonia": "Consolidation with air bronchograms in right lower lobe.",
            "Bone Fracture": "Non-displaced fracture with soft tissue swelling."
        }
        
        selected = st.selectbox("Quick Templates:", ["Select..."] + list(quick_templates.keys()))
        
        if selected != "Select...":
            if st.button(f"Insert '{selected}'", use_container_width=True):
                st.session_state.report_draft += f"\n{quick_templates[selected]}"
                st.success("Template inserted!")
                st.rerun()
        
        # Manual Input
        st.subheader("📝 Manual Input")
        st.session_state.report_draft = st.text_area(
            "Type your draft:",
            value=st.session_state.report_draft,
            height=150,
            placeholder="Or type your findings here...",
            key="draft_area"
        )
    
    with col2:
        # ===== RIGHT PANEL =====
        st.header("📋 Generated Report")
        
        if st.session_state.current_report:
            # Display report
            report_display = st.text_area(
                "Report:",
                value=st.session_state.current_report,
                height=350,
                key="report_display"
            )
            
            # Actions
            col_act1, col_act2 = st.columns(2)
            
            with col_act1:
                report_name = st.text_input(
                    "Save as:",
                    value=f"Report_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}",
                    key="report_name"
                )
                
                if st.button("💾 Save", use_container_width=True):
                    st.session_state.report_history.append({
                        "name": report_name,
                        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "report": st.session_state.current_report,
                        "technique": st.session_state.technique_info
                    })
                    st.success("Saved!")
            
            with col_act2:
                # Create Word document
                try:
                    doc = create_word_document(
                        st.session_state.current_report,
                        st.session_state.technique_info
                    )
                    
                    buffer = BytesIO()
                    doc.save(buffer)
                    buffer.seek(0)
                    
                    st.download_button(
                        label="📄 Download DOCX",
                        data=buffer,
                        file_name=f"{report_name}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True
                    )
                    
                except Exception as e:
                    st.error(f"Document error: {e}")
            
            # Clear button
            if st.button("🧹 Clear Report", use_container_width=True):
                st.session_state.current_report = ""
                st.rerun()
        
        else:
            # Empty state
            st.info("""
            **No report generated yet.**
            
            **To get started:**
            1. Set technique details
            2. Use AI panel or type manually
            3. Generate report
            
            **AI Features Available:** ✅
            - Generate complete reports
            - Enhance findings
            - Differential diagnosis
            """)
        
        # Report History
        if st.session_state.report_history:
            st.divider()
            st.header("📜 Recent Reports")
            
            for i, report in enumerate(reversed(st.session_state.report_history[-3:])):
                with st.expander(f"{report['name']} - {report['date']}"):
                    st.text(report['report'][:200] + "..." if len(report['report']) > 200 else report['report'])
                    
                    if st.button(f"📥 Load", key=f"load_{i}"):
                        st.session_state.current_report = report['report']
                        st.session_state.technique_info = report['technique']
                        st.rerun()
    
    # Sidebar
    with st.sidebar:
        st.header("ℹ️ Info")
        
        # Status
        if st.session_state.ai_client:
            st.success("**AI Status:** ✅ Connected")
        else:
            st.error("**AI Status:** ❌ Disconnected")
        
        # Quick actions
        st.subheader("⚡ Quick Actions")
        
        if st.button("📋 Example Report", use_container_width=True):
            example = """TECHNIQUE:
MRI brain without contrast.

FINDINGS:
No acute intracranial hemorrhage, mass effect, or territorial infarct.
Mild chronic small vessel ischemic changes in the periventricular white matter.
Ventricles and sulci are normal for age.
No abnormal enhancement.

IMPRESSION:
1. No acute intracranial abnormality.
2. Mild chronic microvascular ischemic changes.
3. Clinical correlation recommended."""
            
            st.session_state.current_report = example
            st.rerun()
        
        # Instructions
        with st.expander("📖 How to Use"):
            st.markdown("""
            1. **Login** with demo credentials
            2. **Set technique** details
            3. **Enter findings** (AI or manual)
            4. **Generate** report
            5. **Download** as Word document
            
            **AI Modes:**
            - **Full Report**: Complete structured report
            - **Enhance**: Improve terminology
            - **DDx**: Differential diagnosis
            """)

if __name__ == "__main__":
    main()
