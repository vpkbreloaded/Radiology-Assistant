"""
Radiology Reporting Assistant - WORKING VERSION
"""

import streamlit as st
import os
import openai
from dotenv import load_dotenv
from docx import Document
from io import BytesIO
import datetime

# ===== INITIALIZATION =====
print("=" * 60)
print("STARTING RADIOLOGY ASSISTANT")
print("=" * 60)

# Load environment variables
load_dotenv()

# Get API key
API_KEY = os.getenv("PERPLEXITY_API_KEY")

if API_KEY:
    print(f"✅ API Key loaded: {API_KEY[:20]}...")
else:
    print("❌ API Key NOT loaded")

# Initialize OpenAI client for Perplexity
client = None
if API_KEY:
    try:
        client = openai.OpenAI(
            api_key=API_KEY,
            base_url="https://api.perplexity.ai"
        )
        print("✅ Perplexity AI client initialized")
    except Exception as e:
        print(f"❌ Error initializing AI: {e}")
        client = None

print("=" * 60)

# ===== STREAMLIT APP =====
st.set_page_config(
    page_title="Radiology Reporting Assistant",
    layout="wide",
    page_icon="🏥"
)

# Title with status
if client:
    st.title("🏥 Radiology Reporting Assistant 🤖")
    st.success("✅ AI Assistant is READY to generate reports!")
else:
    st.title("🏥 Radiology Reporting Assistant")
    st.error("⚠️ AI Assistant is NOT available")

# Initialize session state
if 'report_history' not in st.session_state:
    st.session_state.report_history = []
if 'current_report' not in st.session_state:
    st.session_state.current_report = ""
if 'technique_info' not in st.session_state:
    st.session_state.technique_info = {
        "modality": "MRI",
        "contrast": "Without contrast",
        "protocol": "Standard sequences"
    }

# Main layout
col1, col2 = st.columns([1, 1])

with col1:
    st.header("✍️ Report Input")
    
    # Technique Information
    with st.expander("🔬 Technique Details", expanded=True):
        st.session_state.technique_info["modality"] = st.selectbox(
            "Modality",
            ["MRI", "CT", "X-ray", "Ultrasound", "PET-CT", "Mammography"],
            key="modality"
        )
        
        st.session_state.technique_info["contrast"] = st.selectbox(
            "Contrast Administration",
            ["Without contrast", "With contrast", "With and without contrast"],
            key="contrast"
        )
        
        st.session_state.technique_info["protocol"] = st.text_area(
            "Protocol/Sequences",
            value=st.session_state.technique_info["protocol"],
            placeholder="e.g., T1, T2, FLAIR, DWI",
            height=80,
            key="protocol"
        )
    
    # Findings Input
    st.subheader("📝 Findings")
    findings_input = st.text_area(
        "Describe the findings:",
        height=200,
        placeholder="Example: There is a 2.3 cm enhancing mass in the right frontal lobe with surrounding edema and mass effect...",
        key="findings_input",
        help="Be as detailed as possible for better AI analysis"
    )
    
    # AI Generation Options
    if client:
        st.subheader("🤖 AI Options")
        
        ai_mode = st.radio(
            "Generation Mode:",
            ["Complete Report", "Findings Only", "Impression Only"],
            horizontal=True
        )
        
        if st.button("🚀 Generate with AI", type="primary", use_container_width=True):
            if findings_input.strip():
                with st.spinner("🤖 AI is generating report..."):
                    try:
                        # Build prompt based on mode
                        if ai_mode == "Complete Report":
                            prompt = f"""You are a senior radiologist. Create a complete structured radiology report.

TECHNIQUE:
Modality: {st.session_state.technique_info['modality']}
Contrast: {st.session_state.technique_info['contrast']}
Protocol: {st.session_state.technique_info['protocol']}

FINDINGS PROVIDED:
{findings_input}

Please generate a complete professional radiology report with:
1. TECHNIQUE section (brief)
2. FINDINGS section (expand on provided findings with proper terminology)
3. IMPRESSION section (numbered conclusions and recommendations)

Use proper medical terminology and structure."""
                            
                        elif ai_mode == "Findings Only":
                            prompt = f"""You are a radiologist. Expand these findings into detailed radiological descriptions:

Brief findings: {findings_input}

Provide detailed findings organized by anatomical region with proper measurements and terminology."""
                            
                        else:  # Impression Only
                            prompt = f"""You are a radiologist. Based on these findings, provide an IMPRESSION section:

Findings: {findings_input}

Generate an IMPRESSION section with:
1. Numbered conclusions (2-4 points)
2. Clinical recommendations
3. Follow-up suggestions if needed"""
                        
                        # Call Perplexity AI
                        response = client.chat.completions.create(
                            model="sonar",
                            messages=[
                                {"role": "system", "content": "You are a senior radiologist assistant."},
                                {"role": "user", "content": prompt}
                            ],
                            max_tokens=2000
                        )
                        
                        # Store the generated report
                        st.session_state.current_report = response.choices[0].message.content
                        
                        # Add to history
                        history_entry = {
                            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "modality": st.session_state.technique_info['modality'],
                            "report": st.session_state.current_report
                        }
                        st.session_state.report_history.append(history_entry)
                        
                        st.success("✅ Report generated successfully!")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ AI generation failed: {str(e)}")
            else:
                st.warning("⚠️ Please enter findings first")
    else:
        st.warning("AI features disabled. Check console for details.")

with col2:
    st.header("📋 Generated Report")
    
    if st.session_state.current_report:
        # Display report
        report_display = st.text_area(
            "Report Preview:",
            value=st.session_state.current_report,
            height=350,
            key="report_display"
        )
        
        # Report actions
        col_actions1, col_actions2 = st.columns(2)
        
        with col_actions1:
            report_name = st.text_input(
                "Save as:",
                value=f"Report_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}",
                key="report_name"
            )
            
            if st.button("💾 Save Report", use_container_width=True):
                st.success(f"Report saved as '{report_name}'")
        
        with col_actions2:
            # Create Word document
            try:
                doc = Document()
                
                # Title
                doc.add_heading('RADIOLOGY REPORT', 0)
                
                # Technique
                doc.add_heading('TECHNIQUE', level=1)
                doc.add_paragraph(f"Modality: {st.session_state.technique_info['modality']}")
                doc.add_paragraph(f"Contrast: {st.session_state.technique_info['contrast']}")
                doc.add_paragraph(f"Protocol: {st.session_state.technique_info['protocol']}")
                doc.add_paragraph()
                
                # Add report content
                lines = st.session_state.current_report.split('\n')
                for line in lines:
                    line = line.strip()
                    if line:
                        if line.endswith(':'):
                            doc.add_heading(line[:-1], level=1)
                        else:
                            doc.add_paragraph(line)
                
                # Footer
                doc.add_page_break()
                doc.add_heading('REPORT DETAILS', level=1)
                doc.add_paragraph(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                doc.add_paragraph(f"AI-assisted via Perplexity AI")
                
                # Save to buffer
                buffer = BytesIO()
                doc.save(buffer)
                buffer.seek(0)
                
                # Download button
                st.download_button(
                    label="📄 Download Word Document",
                    data=buffer,
                    file_name=f"{report_name}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )
                
            except Exception as e:
                st.error(f"Error creating document: {e}")
        
        # Clear button
        if st.button("🧹 Clear Report", use_container_width=True):
            st.session_state.current_report = ""
            st.rerun()
    
    else:
        # Empty state
        st.info("""
        **No report generated yet.**
        
        **To generate a report:**
        1. Fill in technique details
        2. Enter findings in the text area
        3. Click "Generate with AI"
        
        **Example findings to try:**
        ```
        Right basal ganglia hemorrhage measuring 3.2 x 2.1 cm
        with surrounding edema and mass effect.
        Midline shift of 8 mm to the left.
        ```
        """)

# Report History
if st.session_state.report_history:
    st.divider()
    st.header("📜 Report History")
    
    for i, report in enumerate(reversed(st.session_state.report_history[-5:])):
        with st.expander(f"{report['timestamp']} - {report['modality']}", expanded=False):
            st.text(report['report'][:300] + "..." if len(report['report']) > 300 else report['report'])
            
            col_h1, col_h2 = st.columns(2)
            with col_h1:
                if st.button(f"📥 Load", key=f"load_{i}"):
                    st.session_state.current_report = report['report']
                    st.rerun()
            
            with col_h2:
                if st.button(f"🗑️ Delete", key=f"delete_{i}"):
                    st.session_state.report_history.pop(len(st.session_state.report_history) - 1 - i)
                    st.rerun()

# Debug/Info panel
with st.sidebar:
    st.header("ℹ️ Information")
    
    # Status
    if client:
        st.success("**Status:** ✅ AI Connected")
        if st.button("Test AI Connection", use_container_width=True):
            with st.spinner("Testing..."):
                try:
                    response = client.chat.completions.create(
                        model="sonar",
                        messages=[{"role": "user", "content": "Say 'OK' if working"}],
                        max_tokens=5
                    )
                    st.success(f"Response: {response.choices[0].message.content}")
                except Exception as e:
                    st.error(f"Test failed: {e}")
    else:
        st.error("**Status:** ❌ AI Disconnected")
    
    # Quick templates
    st.subheader("⚡ Quick Templates")
    template = st.selectbox(
        "Select template:",
        ["Select...", "Normal Brain MRI", "Disc Herniation", "Pneumonia", "Bone Fracture"]
    )
    
    if template != "Select...":
        templates = {
            "Normal Brain MRI": "No acute intracranial hemorrhage, infarct, or mass. Ventricles and sulci are normal for age.",
            "Disc Herniation": "Disc bulge at L4-L5 causing mild thecal sac compression without nerve root impingement.",
            "Pneumonia": "Consolidation in right lower lobe with air bronchograms, consistent with pneumonia.",
            "Bone Fracture": "Non-displaced fracture of the distal radius with associated soft tissue swelling."
        }
        
        if st.button(f"Insert {template}"):
            st.session_state.findings_input = templates[template]
            st.rerun()
    
    # Instructions
    with st.expander("📋 How to Use"):
        st.markdown("""
        1. **Enter technique details** (modality, contrast, protocol)
        2. **Describe findings** in the text area
        3. **Select AI mode** (Complete, Findings, or Impression)
        4. **Click "Generate with AI"**
        5. **Review and download** the generated report
        
        **Tips:**
        - Be specific with measurements
        - Mention comparison to prior studies if available
        - Include clinical context when known
        """)

print("\n" + "=" * 60)
print("✅ App is running. Open browser to: http://localhost:8501")
print("=" * 60)
