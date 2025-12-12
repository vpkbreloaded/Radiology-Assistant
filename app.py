"""
Streamlined Radiology Reporting Assistant
WITH Perplexity AI Integration
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

# ===== LOAD ENVIRONMENT VARIABLES =====
load_dotenv()

# Get API key
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

# Debug: Check if API key is loaded
if PERPLEXITY_API_KEY:
    print(f"✅ API Key loaded (starts with: {PERPLEXITY_API_KEY[:10]}...)")
else:
    print("❌ ERROR: PERPLEXITY_API_KEY not found in .env file")
    print("💡 Make sure you have a .env file with: PERPLEXITY_API_KEY=your_key_here")

# ===== PERPLEXITY AI INTEGRATION =====
class PerplexityAIHelper:
    """Helper class for Perplexity AI integration."""
    
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.client = None
        if self.api_key:
            try:
                self.client = openai.OpenAI(
                    api_key=self.api_key,
                    base_url="https://api.perplexity.ai"
                )
                print("✅ Perplexity AI Connected via OpenAI SDK!")
            except Exception as e:
                print(f"❌ Failed to initialize Perplexity AI: {str(e)}")
    
    def is_available(self):
        """Check if Perplexity AI is available."""
        return self.client is not None
    
    def generate_report_from_findings(self, findings_text, modality="MRI", contrast="Without contrast", style="Standard"):
        """Generate a complete radiology report from findings."""
        if not self.client or not findings_text.strip():
            return None
        
        try:
            prompt = f"""You are a senior radiologist. Generate a structured radiology report based on these findings:

Modality: {modality}
Contrast: {contrast}

Findings: {findings_text}

Please generate a complete radiology report with:
1. TECHNIQUE section
2. FINDINGS section (expand on the provided findings)
3. IMPRESSION section (conclusions and recommendations)

Use proper medical terminology."""
            
            response = self.client.chat.completions.create(
                model="sonar",
                messages=[
                    {"role": "system", "content": "You are a senior radiologist assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500
            )
            
            if response.choices:
                return response.choices[0].message.content
            return None
            
        except Exception as e:
            st.error(f"AI generation error: {str(e)}")
            return None

# ===== TEMPLATE SYSTEM =====
class TemplateSystem:
    def __init__(self):
        self.templates = {}
    
    def add_template(self, name, content):
        self.templates[name] = content
    
    def apply_template(self, template_name, current_text=""):
        if template_name in self.templates:
            return current_text + "\n" + self.templates[template_name]
        return current_text

# ===== INITIALIZE SESSION STATE =====
def init_session_state():
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.users = {
            "admin": {"password": hashlib.sha256("admin123".encode()).hexdigest(), "role": "admin"},
            "radiologist": {"password": hashlib.sha256("rad123".encode()).hexdigest(), "role": "radiologist"}
        }
        st.session_state.report_history = []
        st.session_state.report_draft = ""
        st.session_state.ai_report = ""
        st.session_state.current_user = "default"
        st.session_state.logged_in = False
        st.session_state.template_system = TemplateSystem()
        
        # Initialize AI helper
        if PERPLEXITY_API_KEY:
            st.session_state.ai_helper = PerplexityAIHelper(PERPLEXITY_API_KEY)
        else:
            st.session_state.ai_helper = None

# ===== STREAMLIT APP =====
def main():
    st.set_page_config(
        page_title="Radiology Reporting Assistant",
        layout="wide",
        page_icon="🏥"
    )
    
    init_session_state()
    
    # Login System
    if not st.session_state.logged_in:
        st.title("🔐 Login")
        
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
                            
                            # Check AI status
                            if st.session_state.ai_helper and st.session_state.ai_helper.is_available():
                                st.success(f"✅ Welcome, {username}! AI is ready.")
                            else:
                                st.warning(f"⚠️ Welcome, {username}! AI is not available.")
                            
                            st.rerun()
                        else:
                            st.error("Invalid password")
                    else:
                        st.error("User not found")
                
                st.info("Demo: admin/admin123 or radiologist/rad123")
        
        return
    
    # Main App
    st.title("🏥 Radiology Reporting Assistant")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("📝 Input Findings")
        
        # Technique
        modality = st.selectbox("Modality", ["MRI", "CT", "X-ray", "Ultrasound"])
        contrast = st.selectbox("Contrast", ["Without contrast", "With contrast"])
        
        # Findings input
        findings = st.text_area("Enter your findings:", height=200)
        
        # AI Generation
        if st.session_state.ai_helper and st.session_state.ai_helper.is_available():
            if st.button("🤖 Generate Report with AI", type="primary", use_container_width=True):
                if findings:
                    with st.spinner("AI is generating report..."):
                        ai_report = st.session_state.ai_helper.generate_report_from_findings(
                            findings, modality, contrast
                        )
                        if ai_report:
                            st.session_state.ai_report = ai_report
                            st.success("✅ Report generated!")
                        else:
                            st.error("❌ Failed to generate report")
                else:
                    st.warning("Please enter findings first")
        else:
            st.warning("⚠️ AI is not available. Check your .env file.")
    
    with col2:
        st.header("📋 Generated Report")
        
        if st.session_state.ai_report:
            st.text_area("Report:", st.session_state.ai_report, height=400)
            
            # Download as Word
            if st.button("📄 Download as Word", use_container_width=True):
                doc = Document()
                doc.add_heading('RADIOLOGY REPORT', 0)
                doc.add_paragraph(st.session_state.ai_report)
                
                buffer = BytesIO()
                doc.save(buffer)
                buffer.seek(0)
                
                st.download_button(
                    label="Download",
                    data=buffer,
                    file_name="radiology_report.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

# Run the app
if __name__ == "__main__":
    main()
