"""
AI-Powered Professional Radiology Reporting Assistant
Version 6.0 - Enhanced with Analytics, Quality Assurance & DICOM Support
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
import tempfile
from pathlib import Path
import plotly.graph_objects as go
import plotly.express as px

# Try to import DICOM support
try:
    import pydicom
    from pydicom.errors import InvalidDicomError
    DICOM_AVAILABLE = True
except ImportError:
    DICOM_AVAILABLE = False

# ===== CONFIGURATION =====
CONFIG_FILE = "radiology_config.json"
HISTORY_FILE = "report_history.json"
TEMPLATES_FILE = "saved_templates.json"
UPLOADED_TEMPLATES_DIR = "uploaded_templates"
EXPORT_DIR = "exported_reports"
AUDIT_LOG_FILE = "audit_logs.json"

# Create directories if they don't exist
os.makedirs(UPLOADED_TEMPLATES_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)

# ===== ENHANCED DIFFERENTIAL DIAGNOSIS DATABASE =====
DIFFERENTIAL_DATABASE = {
    "brain_lesion_enhancing": [
        {"diagnosis": "Meningioma", "confidence": "High", "features": "Dural-based, homogeneous enhancement", "modality": "MRI", "urgency": "Non-urgent"},
        {"diagnosis": "Metastasis", "confidence": "High", "features": "Multiple, at gray-white junction", "modality": "MRI", "urgency": "Urgent"},
        {"diagnosis": "Glioblastoma", "confidence": "Medium", "features": "Irregular rim enhancement", "modality": "MRI", "urgency": "Urgent"}
    ],
    "white_matter": [
        {"diagnosis": "Microvascular ischemia", "confidence": "High", "features": "Periventricular, punctate", "modality": "MRI", "urgency": "Non-urgent"},
        {"diagnosis": "Multiple Sclerosis", "confidence": "Medium", "features": "Ovoid, perivenular", "modality": "MRI", "urgency": "Non-urgent"}
    ],
    "stroke": [
        {"diagnosis": "Ischemic infarct", "confidence": "High", "features": "Vascular territory, DWI bright", "modality": "MRI/CT", "urgency": "Urgent"},
        {"diagnosis": "Venous infarct", "confidence": "Medium", "features": "Hemorrhagic, non-arterial", "modality": "MRI/CT", "urgency": "Urgent"}
    ],
    "spinal_lesion": [
        {"diagnosis": "Disc herniation", "confidence": "High", "features": "Disc material extrusion", "modality": "MRI", "urgency": "Non-urgent"},
        {"diagnosis": "Metastasis", "confidence": "Medium", "features": "Vertebral body destruction", "modality": "MRI", "urgency": "Urgent"}
    ],
    "lung_nodule": [
        {"diagnosis": "Primary lung cancer", "confidence": "Medium", "features": "Spiculated, >2cm", "modality": "CT", "urgency": "Urgent"},
        {"diagnosis": "Metastasis", "confidence": "Medium", "features": "Multiple, peripheral", "modality": "CT", "urgency": "Urgent"}
    ],
    "liver_lesion": [
        {"diagnosis": "Hemangioma", "confidence": "High", "features": "Peripheral nodular enhancement", "modality": "MRI/CT", "urgency": "Non-urgent"},
        {"diagnosis": "Metastasis", "confidence": "Medium", "features": "Multiple, ring enhancement", "modality": "MRI/CT", "urgency": "Urgent"}
    ]
}

# ===== ANALYTICS DASHBOARD CLASS =====
class AnalyticsDashboard:
    def __init__(self):
        self.metrics = {
            "turnaround_time": [],
            "report_length": [],
            "template_usage": defaultdict(int),
            "critical_findings_count": 0,
            "modality_usage": defaultdict(int),
            "user_productivity": defaultdict(int)
        }
    
    def update_metrics(self, report_data):
        """Update metrics with new report data"""
        # Report length
        report_length = len(report_data.get('report', ''))
        self.metrics["report_length"].append(report_length)
        
        # Modality usage
        modality = report_data.get('technique_info', {}).get('modality', 'Unknown')
        self.metrics["modality_usage"][modality] += 1
        
        # User productivity
        user = report_data.get('created_by', 'unknown')
        self.metrics["user_productivity"][user] += 1
        
        # Template usage
        templates_used = report_data.get('templates_used', [])
        if isinstance(templates_used, str) and templates_used != "None":
            self.metrics["template_usage"][templates_used] += 1
        elif isinstance(templates_used, list):
            for template in templates_used:
                self.metrics["template_usage"][template] += 1
        
        # Check for critical findings
        report_text = report_data.get('report', '').lower()
        critical_keywords = ["hemorrhage", "stroke", "infarct", "herniation", "compression", "rupture", "abscess"]
        if any(keyword in report_text for keyword in critical_keywords):
            self.metrics["critical_findings_count"] += 1
    
    def generate_dashboard(self):
        """Generate comprehensive analytics dashboard"""
        if not st.session_state.get('report_history'):
            return None
        
        # Calculate metrics
        total_reports = len(st.session_state.report_history)
        avg_report_length = sum(self.metrics["report_length"]) / len(self.metrics["report_length"]) if self.metrics["report_length"] else 0
        critical_percentage = (self.metrics["critical_findings_count"] / total_reports * 100) if total_reports > 0 else 0
        
        metrics_data = {
            "Total Reports": total_reports,
            "Average Report Length": f"{avg_report_length:.0f} chars",
            "Critical Findings %": f"{critical_percentage:.1f}%",
            "Your Productivity": self.metrics["user_productivity"].get(st.session_state.current_user, 0),
            "Most Used Modality": max(self.metrics["modality_usage"].items(), key=lambda x: x[1], default=("None", 0))[0],
            "Most Used Template": max(self.metrics["template_usage"].items(), key=lambda x: x[1], default=("None", 0))[0]
        }
        
        return {
            "metrics": metrics_data,
            "charts": {
                "modality_distribution": self.create_modality_chart(),
                "productivity_chart": self.create_productivity_chart(),
                "report_length_trend": self.create_length_trend_chart()
            },
            "raw_data": self.metrics
        }
    
    def create_modality_chart(self):
        """Create modality distribution pie chart"""
        if not self.metrics["modality_usage"]:
            return None
        
        modalities = list(self.metrics["modality_usage"].keys())
        counts = list(self.metrics["modality_usage"].values())
        
        fig = px.pie(
            values=counts,
            names=modalities,
            title="Modality Distribution",
            hole=0.3
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        return fig
    
    def create_productivity_chart(self):
        """Create user productivity bar chart"""
        if not self.metrics["user_productivity"]:
            return None
        
        users = list(self.metrics["user_productivity"].keys())
        counts = list(self.metrics["user_productivity"].values())
        
        fig = px.bar(
            x=users,
            y=counts,
            title="User Productivity (Reports Created)",
            labels={'x': 'User', 'y': 'Number of Reports'}
        )
        fig.update_layout(xaxis_tickangle=-45)
        return fig
    
    def create_length_trend_chart(self):
        """Create report length trend chart"""
        if len(self.metrics["report_length"]) < 2:
            return None
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=list(range(len(self.metrics["report_length"]))),
            y=self.metrics["report_length"],
            mode='lines+markers',
            name='Report Length'
        ))
        
        # Add moving average
        if len(self.metrics["report_length"]) > 5:
            window = min(5, len(self.metrics["report_length"]))
            moving_avg = pd.Series(self.metrics["report_length"]).rolling(window=window).mean()
            fig.add_trace(go.Scatter(
                x=list(range(len(moving_avg))),
                y=moving_avg,
                mode='lines',
                name=f'{window}-Report Moving Average',
                line=dict(dash='dash')
            ))
        
        fig.update_layout(
            title="Report Length Trend",
            xaxis_title="Report Number",
            yaxis_title="Characters"
        )
        return fig
    
    def export_statistics_csv(self):
        """Export statistics as CSV"""
        data = []
        for user, count in self.metrics["user_productivity"].items():
            data.append({
                "User": user,
                "Reports Created": count,
                "Most Common Modality": max(self.metrics["modality_usage"].items(), key=lambda x: x[1])[0] if self.metrics["modality_usage"] else "N/A"
            })
        
        df = pd.DataFrame(data)
        return df.to_csv(index=False)

# ===== QUALITY ASSURANCE CLASS =====
class QualityAssurance:
    def __init__(self):
        self.quality_metrics = {
            "required_sections": ["FINDINGS", "IMPRESSION"],
            "recommended_sections": ["TECHNIQUE", "CLINICAL HISTORY", "COMPARISON"],
            "min_findings_length": 50,
            "max_findings_length": 2000,
            "ambiguous_terms": ["possible", "likely", "suggestive of", "cannot exclude", "may represent", "probably"],
            "forbidden_terms": ["normal", "unremarkable"]  # Too vague
        }
    
    def audit_report(self, report_text):
        """Audit report for quality metrics"""
        audit_results = {
            "score": 100,
            "warnings": [],
            "suggestions": [],
            "missing_sections": [],
            "strengths": []
        }
        
        # Check for required sections
        for section in self.quality_metrics["required_sections"]:
            if section not in report_text.upper():
                audit_results["missing_sections"].append(section)
                audit_results["score"] -= 20
                audit_results["warnings"].append(f"Missing required section: {section}")
        
        # Check findings length and content
        findings_match = re.search(r'FINDINGS:(.*?)(?=\n\n[A-Z]+:|$)', report_text, re.DOTALL | re.IGNORECASE)
        if findings_match:
            findings_text = findings_match.group(1).strip()
            
            # Length check
            if len(findings_text) < self.quality_metrics["min_findings_length"]:
                audit_results["warnings"].append(f"Findings section is brief ({len(findings_text)} chars)")
                audit_results["score"] -= 10
                audit_results["suggestions"].append("Consider adding more descriptive details")
            elif len(findings_text) > self.quality_metrics["max_findings_length"]:
                audit_results["warnings"].append(f"Findings section is verbose ({len(findings_text)} chars)")
                audit_results["score"] -= 5
                audit_results["suggestions"].append("Consider being more concise")
            else:
                audit_results["strengths"].append("Findings section has appropriate length")
            
            # Check for ambiguous language
            for term in self.quality_metrics["ambiguous_terms"]:
                if term in findings_text.lower():
                    audit_results["suggestions"].append(f"Consider clarifying ambiguous term: '{term}'")
                    audit_results["score"] -= 3
            
            # Check for forbidden vague terms
            for term in self.quality_metrics["forbidden_terms"]:
                if term in findings_text.lower() and len(findings_text) < 100:
                    audit_results["warnings"].append(f"Avoid vague term: '{term}' without supporting details")
                    audit_results["score"] -= 5
        
        # Check for consistent measurements
        measurement_patterns = [
            (r'(\d+\.?\d*)\s*cm', "cm"),
            (r'(\d+\.?\d*)\s*mm', "mm"),
            (r'(\d+\.?\d*)\s*x\s*(\d+\.?\d*)', "dimensions")
        ]
        
        units_used = set()
        for pattern, unit in measurement_patterns:
            if re.search(pattern, report_text):
                units_used.add(unit)
        
        if len(units_used) > 1:
            audit_results["suggestions"].append(f"Mixed measurement units detected: {', '.join(units_used)}")
        
        # Check for comparison section
        if "COMPARISON" in report_text.upper():
            audit_results["strengths"].append("Includes comparison with prior studies")
            audit_results["score"] += 10
        
        # Check for differential diagnosis
        if "DIFFERENTIAL" in report_text.upper():
            audit_results["strengths"].append("Includes differential diagnosis")
            audit_results["score"] += 5
        
        # Cap score between 0-100
        audit_results["score"] = max(0, min(100, audit_results["score"]))
        
        # Determine grade
        if audit_results["score"] >= 90:
            audit_results["grade"] = "Excellent"
            audit_results["grade_color"] = "green"
        elif audit_results["score"] >= 75:
            audit_results["grade"] = "Good"
            audit_results["grade_color"] = "blue"
        elif audit_results["score"] >= 60:
            audit_results["grade"] = "Fair"
            audit_results["grade_color"] = "orange"
        else:
            audit_results["grade"] = "Needs Improvement"
            audit_results["grade_color"] = "red"
        
        return audit_results
    
    def generate_quality_report(self, audit_results):
        """Generate formatted quality report"""
        report = f"## 📊 Quality Assurance Report\n\n"
        report += f"### Overall Score: **{audit_results['score']}/100** "
        report += f"({audit_results['grade']})\n\n"
        
        if audit_results['strengths']:
            report += "### ✅ Strengths:\n"
            for strength in audit_results['strengths']:
                report += f"- {strength}\n"
            report += "\n"
        
        if audit_results['warnings']:
            report += "### ⚠️ Warnings:\n"
            for warning in audit_results['warnings']:
                report += f"- {warning}\n"
            report += "\n"
        
        if audit_results['suggestions']:
            report += "### 💡 Suggestions for Improvement:\n"
            for suggestion in audit_results['suggestions']:
                report += f"- {suggestion}\n"
        
        return report
    
    def save_audit_log(self, report_id, audit_results, user):
        """Save audit log to file"""
        log_entry = {
            "report_id": report_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "user": user,
            "score": audit_results["score"],
            "grade": audit_results["grade"],
            "warnings": audit_results["warnings"],
            "suggestions": audit_results["suggestions"]
        }
        
        # Load existing logs
        logs = []
        if os.path.exists(AUDIT_LOG_FILE):
            try:
                with open(AUDIT_LOG_FILE, 'r') as f:
                    logs = json.load(f)
            except:
                logs = []
        
        # Add new log
        logs.append(log_entry)
        
        # Save logs
        with open(AUDIT_LOG_FILE, 'w') as f:
            json.dump(logs, f, indent=2)

# ===== MULTI-MODAL INTEGRATION CLASS =====
class MultiModalIntegrator:
    def __init__(self):
        self.modality_templates = {
            "MRI": {
                "sequences": ["T1", "T2", "FLAIR", "DWI", "ADC", "SWI", "T1+C", "T2*", "MRA", "MRV"],
                "protocols": ["Brain", "Spine", "MSK", "Abdomen", "Pelvis", "Cardiac", "Breast", "MRA", "MRV"],
                "field_strengths": ["1.5T", "3.0T", "7.0T"],
                "recommended_sequences": {
                    "Brain": ["T1", "T2", "FLAIR", "DWI"],
                    "Spine": ["T1", "T2", "STIR"],
                    "MSK": ["PD", "T2", "T1+C"]
                }
            },
            "CT": {
                "protocols": ["Non-contrast", "Contrast-enhanced", "CTA", "Perfusion", "High-resolution", "Low-dose"],
                "reconstructions": ["Axial", "Coronal", "Sagittal", "3D", "MIP", "MPR"],
                "slice_thickness": ["0.5mm", "1.0mm", "2.0mm", "3.0mm", "5.0mm"],
                "kv_settings": ["80", "100", "120", "140"]
            },
            "Ultrasound": {
                "modes": ["B-mode", "Doppler", "Color Doppler", "Power Doppler", "Elastography", "Contrast-enhanced"],
                "approaches": ["Transabdominal", "Endoscopic", "Intraoperative", "Transvaginal", "Transrectal"],
                "probes": ["Linear", "Curvilinear", "Phased array", "Endocavitary"]
            },
            "X-ray": {
                "views": ["AP", "PA", "Lateral", "Oblique", "Special views"],
                "techniques": ["Digital", "CR", "Portable", "Fluoroscopy"]
            }
        }
        
        self.imaging_recommendations = {
            "MRI": {
                "stroke": "Consider adding DWI, ADC, and perfusion sequences",
                "tumor": "Consider pre- and post-contrast T1, perfusion, spectroscopy",
                "infection": "Consider contrast-enhanced sequences",
                "MSK": "Consider cartilage-sensitive sequences (PD, T2)"
            },
            "CT": {
                "hemorrhage": "Consider non-contrast CT initially",
                "tumor": "Consider contrast-enhanced CT with multiple phases",
                "trauma": "Consider whole-body CT for polytrauma",
                "pulmonary_embolism": "CT pulmonary angiography required"
            }
        }
    
    def generate_detailed_technique(self, modality, protocol=None, body_part=None):
        """Generate detailed technique section"""
        if modality not in self.modality_templates:
            return f"{modality} examination performed as per standard protocol."
        
        technique = f"{modality} examination"
        
        if modality == "MRI":
            technique += " was performed"
            if "field_strengths" in self.modality_templates["MRI"]:
                technique += f" on a [FIELD_STRENGTH] scanner."
            
            if protocol:
                technique += f" {protocol} protocol was utilized."
            
            if body_part and body_part in self.modality_templates["MRI"]["recommended_sequences"]:
                technique += " Sequences included: "
                sequences = self.modality_templates["MRI"]["recommended_sequences"][body_part]
                technique += ", ".join(sequences) + "."
            else:
                technique += " Standard sequences were obtained."
            
            technique += " Contrast: [CONTRAST_DETAILS]."
        
        elif modality == "CT":
            technique += " was performed"
            technique += " using [SLICE_COUNT]-slice scanner."
            technique += " Parameters: [KV] kV, [MA] mA."
            
            if protocol:
                technique += f" {protocol}."
            
            technique += " Reconstruction: [RECONSTRUCTION]."
            technique += " Slice thickness: [SLICE_THICKNESS]."
        
        elif modality == "Ultrasound":
            technique += " was performed"
            if "approaches" in self.modality_templates["Ultrasound"]:
                technique += " via [APPROACH] approach."
            technique += " using [PROBE] probe."
            technique += " Doppler assessment was performed as indicated."
        
        return technique
    
    def suggest_additional_imaging(self, findings, current_modality, body_part=None):
        """Suggest additional imaging modalities or protocols"""
        findings_lower = findings.lower()
        recommendations = []
        
        # Modality-specific recommendations
        if current_modality in self.imaging_recommendations:
            for condition, recommendation in self.imaging_recommendations[current_modality].items():
                condition_keywords = {
                    "stroke": ["stroke", "infarct", "ischemia", "dwi"],
                    "tumor": ["mass", "tumor", "neoplasm", "enhancing"],
                    "infection": ["infection", "abscess", "phlegmon", "empyema"],
                    "hemorrhage": ["hemorrhage", "bleed", "hematoma"],
                    "trauma": ["fracture", "trauma", "injury"],
                    "pulmonary_embolism": ["pe", "embolism", "thrombus"]
                }
                
                if condition in condition_keywords:
                    if any(keyword in findings_lower for keyword in condition_keywords[condition]):
                        recommendations.append(recommendation)
        
        # Cross-modality recommendations
        if "nodule" in findings_lower and current_modality == "CT":
            recommendations.append("Consider PET-CT for further characterization")
        
        if "metastasis" in findings_lower:
            recommendations.append("Consider whole-body imaging for staging")
        
        if "infection" in findings_lower and current_modality != "MRI":
            recommendations.append("Consider MRI for better soft tissue characterization")
        
        return list(set(recommendations))[:3]  # Return unique recommendations, max 3

# ===== DICOM METADATA EXTRACTOR =====
class DICOMMetadataExtractor:
    def __init__(self):
        self.metadata_fields = {
            "Patient": ["PatientName", "PatientID", "PatientBirthDate", "PatientSex", "PatientAge"],
            "Study": ["StudyDate", "StudyTime", "StudyDescription", "AccessionNumber", "ReferringPhysicianName"],
            "Series": ["SeriesDescription", "Modality", "BodyPartExamined", "ProtocolName", "SequenceName"],
            "Image": ["SliceThickness", "PixelSpacing", "ConvolutionKernel", "KV", "MA", "ExposureTime"]
        }
    
    def extract_metadata(self, dicom_file):
        """Extract metadata from DICOM file"""
        try:
            ds = pydicom.dcmread(dicom_file, stop_before_pixels=True)
            
            metadata = {"Patient": {}, "Study": {}, "Series": {}, "Image": {}, "Success": True}
            
            for category, fields in self.metadata_fields.items():
                for field in fields:
                    if hasattr(ds, field):
                        value = getattr(ds, field)
                        # Handle different DICOM value types
                        if hasattr(value, 'original_string'):
                            metadata[category][field] = str(value.original_string)
                        elif hasattr(value, 'value'):
                            metadata[category][field] = str(value.value)
                        elif isinstance(value, list):
                            metadata[category][field] = str(value[0]) if value else ""
                        else:
                            metadata[category][field] = str(value)
            
            # Try to get patient age in years
            if 'PatientAge' in metadata['Patient']:
                age_str = metadata['Patient']['PatientAge']
                if age_str.endswith('Y'):
                    metadata['Patient']['AgeYears'] = age_str[:-1]
            
            return metadata
        
        except Exception as e:
            return {"Success": False, "Error": str(e)}
    
    def generate_technique_from_dicom(self, metadata):
        """Generate technique section from DICOM metadata"""
        if not metadata.get("Success", False):
            return "Unable to extract technique details from DICOM file."
        
        technique = "TECHNIQUE:\n"
        
        # Add modality
        modality = metadata.get("Series", {}).get("Modality", "Unknown")
        technique += f"Modality: {modality}\n"
        
        # Add study description
        study_desc = metadata.get("Study", {}).get("StudyDescription", "")
        if study_desc:
            technique += f"Protocol: {study_desc}\n"
        
        # Add series description
        series_desc = metadata.get("Series", {}).get("SeriesDescription", "")
        if series_desc:
            technique += f"Series: {series_desc}\n"
        
        # Add imaging parameters
        if modality.upper() == "CT":
            kv = metadata.get("Image", {}).get("KV", "")
            ma = metadata.get("Image", {}).get("MA", "")
            if kv or ma:
                technique += f"Parameters: {kv if kv else 'N/A'} kV, {ma if ma else 'N/A'} mA\n"
        
        elif modality.upper() == "MR":
            sequence = metadata.get("Series", {}).get("SequenceName", "")
            if sequence:
                technique += f"Sequence: {sequence}\n"
        
        # Add slice thickness
        slice_thickness = metadata.get("Image", {}).get("SliceThickness", "")
        if slice_thickness:
            technique += f"Slice thickness: {slice_thickness} mm\n"
        
        return technique
    
    def populate_patient_info(self, metadata):
        """Populate patient information from DICOM metadata"""
        patient_info = {}
        
        if metadata.get("Success", False):
            patient_data = metadata.get("Patient", {})
            
            # Extract name
            if 'PatientName' in patient_data:
                # DICOM names are often in format 'Last^First^Middle'
                name_parts = patient_data['PatientName'].split('^')
                if len(name_parts) >= 2:
                    patient_info['name'] = f"{name_parts[1]} {name_parts[0]}".strip()
                else:
                    patient_info['name'] = patient_data['PatientName']
            
            # Extract ID
            if 'PatientID' in patient_data:
                patient_info['id'] = patient_data['PatientID']
            
            # Extract age
            if 'AgeYears' in patient_data:
                patient_info['age'] = patient_data['AgeYears']
            elif 'PatientAge' in patient_data:
                age_str = patient_data['PatientAge']
                if age_str.endswith('Y'):
                    patient_info['age'] = age_str[:-1]
            
            # Extract sex
            if 'PatientSex' in patient_data:
                sex_map = {'M': 'M', 'F': 'F', 'O': 'Other'}
                patient_info['sex'] = sex_map.get(patient_data['PatientSex'], patient_data['PatientSex'])
        
        return patient_info

# ===== ADVANCED UI COMPONENTS =====
class AdvancedUIComponents:
    def __init__(self):
        self.ui_styles = """
        <style>
        /* Progress indicator */
        .progress-container {
            background: #f0f2f6;
            border-radius: 10px;
            padding: 10px;
            margin-bottom: 20px;
        }
        
        .progress-step {
            display: inline-block;
            width: 30px;
            height: 30px;
            line-height: 30px;
            border-radius: 50%;
            text-align: center;
            margin: 0 5px;
            font-weight: bold;
        }
        
        .step-active {
            background: #4CAF50;
            color: white;
        }
        
        .step-completed {
            background: #2196F3;
            color: white;
        }
        
        .step-pending {
            background: #E0E0E0;
            color: #666;
        }
        
        /* Quality score indicators */
        .score-excellent { color: #4CAF50; font-weight: bold; }
        .score-good { color: #2196F3; font-weight: bold; }
        .score-fair { color: #FF9800; font-weight: bold; }
        .score-poor { color: #F44336; font-weight: bold; }
        
        /* Priority badges */
        .priority-critical { background: #F44336; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; }
        .priority-urgent { background: #FF9800; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; }
        .priority-routine { background: #4CAF50; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; }
        .priority-low { background: #9E9E9E; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; }
        
        /* Mobile responsive */
        @media (max-width: 768px) {
            .mobile-stack { display: block !important; }
            .mobile-hide { display: none !important; }
        }
        </style>
        """
    
    def create_progress_indicator(self, current_step, total_steps=5):
        """Create visual progress indicator"""
        steps = ["Patient", "Technique", "Findings", "Impression", "Review"]
        
        html = '<div class="progress-container"><div>'
        for i in range(total_steps):
            if i < current_step:
                css_class = "step-completed"
            elif i == current_step:
                css_class = "step-active"
            else:
                css_class = "step-pending"
            
            html += f'<span class="progress-step {css_class}">{i+1}</span>'
            if i < total_steps - 1:
                html += '<span style="margin: 0 5px;">→</span>'
        
        html += '</div><div style="margin-top: 10px; font-size: 14px;">'
        html += f'<strong>Current: {steps[min(current_step, len(steps)-1)]}</strong>'
        html += '</div></div>'
        
        return html
    
    def create_priority_badge(self, priority_level):
        """Create priority badge"""
        badges = {
            "Critical": '<span class="priority-critical">CRITICAL</span>',
            "Urgent": '<span class="priority-urgent">URGENT</span>',
            "Routine": '<span class="priority-routine">ROUTINE</span>',
            "Low": '<span class="priority-low">LOW</span>'
        }
        return badges.get(priority_level, '<span>UNKNOWN</span>')
    
    def create_quality_score_display(self, score):
        """Create quality score display with color coding"""
        if score >= 90:
            css_class = "score-excellent"
            emoji = "⭐"
        elif score >= 75:
            css_class = "score-good"
            emoji = "👍"
        elif score >= 60:
            css_class = "score-fair"
            emoji = "⚠️"
        else:
            css_class = "score-poor"
            emoji = "❌"
        
        return f'<span class="{css_class}">{emoji} {score}/100</span>'
    
    def create_keyboard_shortcuts_panel(self):
        """Create keyboard shortcuts help panel"""
        shortcuts = [
            ("Ctrl+S / Cmd+S", "Save current draft"),
            ("Ctrl+G", "Generate report"),
            ("Ctrl+D", "Show differential diagnosis"),
            ("Ctrl+Q", "Quality check"),
            ("Ctrl+E", "Export options"),
            ("Ctrl+H", "Show history")
        ]
        
        html = '<div style="background: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid #2196F3;">'
        html += '<h4 style="margin-top: 0;">⌨️ Keyboard Shortcuts</h4>'
        html += '<table style="width: 100%; font-size: 14px;">'
        
        for shortcut, description in shortcuts:
            html += f'<tr>'
            html += f'<td style="padding: 5px 0;"><code>{shortcut}</code></td>'
            html += f'<td style="padding: 5px 0;">{description}</td>'
            html += f'</tr>'
        
        html += '</table>'
        html += '</div>'
        
        return html

# ===== TEMPLATE SYSTEM =====
class TemplateSystem:
    """Template system for managing report templates."""
    
    def __init__(self):
        self.templates = {}
        self.load_templates()
    
    def load_templates(self):
        """Load templates from file."""
        if os.path.exists(TEMPLATES_FILE):
            try:
                with open(TEMPLATES_FILE, 'r') as f:
                    self.templates = json.load(f)
            except:
                self.templates = {}
    
    def save_templates(self):
        """Save templates to file."""
        try:
            with open(TEMPLATES_FILE, 'w') as f:
                json.dump(self.templates, f, indent=2)
        except:
            pass
    
    def add_template(self, name, content, template_type="findings"):
        """Add a new template."""
        self.templates[name] = {
            "content": content,
            "type": template_type,
            "created_by": st.session_state.get('current_user', 'unknown'),
            "created_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "used_count": 0
        }
        self.save_templates()
    
    def get_template_heading(self, template_name):
        """Get heading format for a template."""
        if template_name not in self.templates:
            return template_name.upper()
        
        template = self.templates[template_name]
        template_type = template.get("type", "findings")
        
        heading_map = {
            "technique": "TECHNIQUE",
            "findings": "FINDINGS",
            "impression": "IMPRESSION",
            "clinical": "CLINICAL HISTORY",
            "differential": "DIFFERENTIAL DIAGNOSIS",
            "comparison": "COMPARISON"
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

# ===== HELPER FUNCTIONS =====
def generate_differential_diagnosis(text, modality_filter=None):
    """Generate differential diagnosis based on findings."""
    if not text:
        return []
    
    text_lower = text.lower()
    results = []
    
    # Check for patterns in various categories
    if any(word in text_lower for word in ["enhanc", "mass", "tumor", "neoplasm", "gadolinium"]):
        results.extend(DIFFERENTIAL_DATABASE["brain_lesion_enhancing"])
    
    if any(word in text_lower for word in ["white matter", "flair", "hyperintensity", "msa", "demyelinating"]):
        results.extend(DIFFERENTIAL_DATABASE["white_matter"])
    
    if any(word in text_lower for word in ["stroke", "infarct", "ischemi", "mca", "aca", "pca"]):
        results.extend(DIFFERENTIAL_DATABASE["stroke"])
    
    if any(word in text_lower for word in ["spinal", "cord", "disc", "vertebral", "canal", "foraminal"]):
        results.extend(DIFFERENTIAL_DATABASE["spinal_lesion"])
    
    if any(word in text_lower for word in ["lung", "pulmonary", "nodule", "chest", "thorax", "pleural"]):
        results.extend(DIFFERENTIAL_DATABASE["lung_nodule"])
    
    if any(word in text_lower for word in ["liver", "hepatic", "lesion", "hepato", "portal"]):
        results.extend(DIFFERENTIAL_DATABASE["liver_lesion"])
    
    # Apply modality filter if specified
    if modality_filter and modality_filter != "All":
        results = [r for r in results if r.get('modality') == modality_filter]
    
    # Remove duplicates
    seen = set()
    unique_results = []
    for r in results:
        key = r['diagnosis']
        if key not in seen:
            seen.add(key)
            unique_results.append(r)
    
    return unique_results[:6]

def create_word_document(patient_info, report_text, report_date, technique_info=None):
    """Create a Word document with proper formatting including patient data."""
    doc = Document()
    
    # Title
    title = doc.add_heading('RADIOLOGY REPORT', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Add spacing
    doc.add_paragraph()
    
    # PATIENT INFORMATION Section - only if data exists
    if patient_info and any(patient_info.values()):
        doc.add_heading('PATIENT INFORMATION', level=1)
        
        # Add patient information
        if patient_info.get('name'):
            doc.add_paragraph(f"Patient Name: {patient_info['name']}")
        if patient_info.get('id'):
            doc.add_paragraph(f"Patient ID: {patient_info['id']}")
        if patient_info.get('age') or patient_info.get('sex'):
            doc.add_paragraph(f"Age/Sex: {patient_info.get('age', '')}/{patient_info.get('sex', '')}")
        if patient_info.get('history'):
            doc.add_paragraph(f"Clinical History: {patient_info['history']}")
        
        doc.add_paragraph(f"Report Date: {report_date if report_date else datetime.datetime.now().strftime('%Y-%m-%d')}")
    
    # Add spacing
    doc.add_paragraph()
    
    # Parse and add report sections
    lines = report_text.split('\n')
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            doc.add_paragraph()  # Preserve paragraph breaks
            continue
            
        # Check if line is a heading (ends with colon and is mostly uppercase)
        if line_stripped.endswith(':') and line_stripped[:-1].replace(' ', '').isupper():
            heading_text = line_stripped[:-1]  # Remove colon
            doc.add_heading(heading_text, level=1)
        else:
            # Regular content
            doc.add_paragraph(line_stripped)
    
    # Add footer with radiologist info
    doc.add_page_break()
    doc.add_heading('REPORT DETAILS', level=1)
    p = doc.add_paragraph()
    p.add_run(f"Generated by: {st.session_state.get('current_user', 'Unknown')}\n")
    p.add_run(f"Generation date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return doc

# ===== INITIALIZE SESSION STATE =====
def init_session_state():
    """Initialize session state variables."""
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
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
        st.session_state.current_user = "default"
        st.session_state.logged_in = False
        st.session_state.differential_results = []
        st.session_state.template_system = TemplateSystem()
        st.session_state.selected_template = ""
        st.session_state.new_template_name = ""
        st.session_state.new_template_content = ""
        st.session_state.new_template_type = "findings"
        st.session_state.technique_info = {
            "modality": "MRI",
            "contrast": "Without contrast",
            "sequences": "Standard sequences"
        }
        st.session_state.show_differential_suggestions = False
        
        # New: Initialize enhanced components
        st.session_state.analytics_dashboard = AnalyticsDashboard()
        st.session_state.quality_assurance = QualityAssurance()
        st.session_state.multi_modal_integrator = MultiModalIntegrator()
        st.session_state.ui_components = AdvancedUIComponents()
        
        if DICOM_AVAILABLE:
            st.session_state.dicom_extractor = DICOMMetadataExtractor()
        else:
            st.session_state.dicom_extractor = None
        
        st.session_state.show_analytics = False
        st.session_state.show_quality_check = False
        st.session_state.dicom_file = None
        st.session_state.dicom_metadata = None

# ===== STREAMLIT APP =====
def main():
    # Page config
    st.set_page_config(
        page_title="Professional Radiology Assistant v6.0",
        layout="wide",
        page_icon="🏥",
        menu_items={
            'Get Help': 'https://streamlit.io',
            'Report a bug': None,
            'About': "### Radiology Reporting Assistant v6.0\nEnhanced with Analytics, Quality Assurance & DICOM Support"
        }
    )
    
    # Initialize session state
    init_session_state()
    
    # Inject UI styles
    st.markdown(st.session_state.ui_components.ui_styles, unsafe_allow_html=True)
    
    # ===== LOGIN SYSTEM =====
    if not st.session_state.logged_in:
        st.title("🔐 Radiology Assistant - Login")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.container(border=True):
                st.subheader("Login")
                username = st.text_input("Username", key="login_user")
                password = st.text_input("Password", type="password", key="login_pass")
                
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
                
                st.info("Demo accounts: admin/admin123, neuro/neuro123, body/body123")
        
        return
    
    # ===== MAIN APPLICATION =====
    
    # Header
    st.title("🏥 Enhanced Radiology Reporting Assistant v6.0")
    
    # User info and enhanced controls
    col_header1, col_header2, col_header3, col_header4 = st.columns([2, 1, 1, 1])
    with col_header1:
        st.markdown(f"**Welcome, {st.session_state.current_user}!**")
    with col_header2:
        if st.button("📊 Analytics", use_container_width=True, key="analytics_button"):
            st.session_state.show_analytics = not st.session_state.show_analytics
            st.rerun()
    with col_header3:
        if st.button("🔍 Quality Check", use_container_width=True, key="quality_button"):
            st.session_state.show_quality_check = not st.session_state.show_quality_check
            st.rerun()
    with col_header4:
        if st.button("🚪 Logout", use_container_width=True, key="logout_button"):
            st.session_state.logged_in = False
            st.rerun()
    
    # Show progress indicator
    current_step = 0
    if st.session_state.patient_info and any(st.session_state.patient_info.values()):
        current_step += 1
    if st.session_state.technique_info and any(st.session_state.technique_info.values()):
        current_step += 1
    if st.session_state.report_draft:
        current_step += 2  # Findings and impression
    if st.session_state.ai_report:
        current_step = 4  # Review
    
    st.markdown(st.session_state.ui_components.create_progress_indicator(current_step), unsafe_allow_html=True)
    
    # ===== ANALYTICS DASHBOARD =====
    if st.session_state.show_analytics and st.session_state.report_history:
        with st.container(border=True):
            st.subheader("📈 Analytics Dashboard")
            
            # Update metrics with all history
            for report in st.session_state.report_history:
                st.session_state.analytics_dashboard.update_metrics(report)
            
            dashboard = st.session_state.analytics_dashboard.generate_dashboard()
            
            if dashboard:
                # Display metrics
                col_metrics = st.columns(3)
                metrics = dashboard["metrics"]
                metric_items = list(metrics.items())
                
                for i in range(0, len(metric_items), 3):
                    row_items = metric_items[i:i+3]
                    cols = st.columns(len(row_items))
                    for col_idx, (key, value) in enumerate(row_items):
                        with cols[col_idx]:
                            st.metric(key, value)
                
                # Display charts
                if dashboard["charts"]["modality_distribution"]:
                    st.plotly_chart(dashboard["charts"]["modality_distribution"], use_container_width=True)
                
                if dashboard["charts"]["productivity_chart"]:
                    st.plotly_chart(dashboard["charts"]["productivity_chart"], use_container_width=True)
                
                # Export options
                st.divider()
                col_export1, col_export2 = st.columns(2)
                with col_export1:
                    csv_data = st.session_state.analytics_dashboard.export_statistics_csv()
                    st.download_button(
                        label="📥 Download Statistics (CSV)",
                        data=csv_data,
                        file_name=f"radiology_analytics_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                with col_export2:
                    if st.button("🔄 Refresh Analytics", use_container_width=True):
                        st.rerun()
            else:
                st.info("Generate more reports to see analytics!")
    
    # Main columns
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # ===== LEFT PANEL: INPUT & DRAFT =====
        st.header("✍️ Report Creation")
        
        # DICOM Upload Section (if available)
        if DICOM_AVAILABLE and st.session_state.dicom_extractor:
            with st.expander("📁 Upload DICOM File (Optional)", expanded=False):
                dicom_file = st.file_uploader("Choose a DICOM file", type=['dcm', 'dicom'], key="dicom_upload")
                
                if dicom_file:
                    if st.button("📊 Extract DICOM Metadata", key="extract_dicom"):
                        with st.spinner("Extracting DICOM metadata..."):
                            st.session_state.dicom_metadata = st.session_state.dicom_extractor.extract_metadata(dicom_file)
                            
                            if st.session_state.dicom_metadata.get("Success", False):
                                st.success("DICOM metadata extracted successfully!")
                                
                                # Populate patient info
                                patient_info = st.session_state.dicom_extractor.populate_patient_info(st.session_state.dicom_metadata)
                                if patient_info:
                                    st.session_state.patient_info.update(patient_info)
                                    st.info("Patient information updated from DICOM")
                                
                                # Show extracted metadata
                                with st.expander("View DICOM Metadata"):
                                    st.json(st.session_state.dicom_metadata)
                            else:
                                st.error(f"Failed to extract DICOM metadata: {st.session_state.dicom_metadata.get('Error', 'Unknown error')}")
        
        # Technique Information with enhanced options
        with st.expander("🔬 Technique Details", expanded=True):
            col_tech1, col_tech2 = st.columns(2)
            with col_tech1:
                modality = st.selectbox(
                    "Modality",
                    ["MRI", "CT", "Ultrasound", "X-ray", "PET-CT", "Mammography", "Angiography"],
                    key="modality_select",
                    index=0
                )
                
                contrast = st.selectbox(
                    "Contrast Administration",
                    ["Without contrast", "With contrast", "With and without contrast", "Not specified"],
                    key="contrast_select",
                    index=0
                )
            
            with col_tech2:
                body_part = st.selectbox(
                    "Body Part",
                    ["Not specified", "Brain", "Spine", "Chest", "Abdomen", "Pelvis", "Extremities"],
                    key="body_part_select"
                )
                
                sequences = st.text_area(
                    "Sequences/Protocol",
                    value=st.session_state.technique_info.get('sequences', ''),
                    placeholder="e.g., T1, T2, FLAIR, DWI, ADC",
                    key="sequences_input",
                    height=80
                )
            
            # Generate detailed technique using multi-modal integrator
            if st.button("🤖 Generate Detailed Technique", key="gen_technique"):
                detailed_tech = st.session_state.multi_modal_integrator.generate_detailed_technique(
                    modality, 
                    protocol=sequences if sequences else None,
                    body_part=body_part if body_part != "Not specified" else None
                )
                st.session_state.technique_info = {
                    "modality": modality,
                    "contrast": contrast,
                    "sequences": detailed_tech,
                    "body_part": body_part
                }
                st.success("Detailed technique generated!")
            
            if st.button("💾 Save Technique", key="save_tech_button", use_container_width=True):
                st.session_state.technique_info = {
                    "modality": modality,
                    "contrast": contrast,
                    "sequences": sequences if sequences else "Standard sequences",
                    "body_part": body_part
                }
                st.success("Technique details saved!")
            
            # Show additional imaging recommendations if findings exist
            if st.session_state.report_draft:
                recommendations = st.session_state.multi_modal_integrator.suggest_additional_imaging(
                    st.session_state.report_draft,
                    modality,
                    body_part if body_part != "Not specified" else None
                )
                if recommendations:
                    st.info("**Imaging Recommendations:**")
                    for rec in recommendations:
                        st.write(f"- {rec}")
        
        # Patient Information (Optional)
        with st.expander("🧾 Patient Information (Optional)", expanded=False):
            col_pat1, col_pat2 = st.columns(2)
            with col_pat1:
                p_name = st.text_input("Full Name", value=st.session_state.patient_info.get('name', ''), key="pat_name")
                p_id = st.text_input("Patient ID", value=st.session_state.patient_info.get('id', ''), key="pat_id")
            with col_pat2:
                p_age = st.text_input("Age", value=st.session_state.patient_info.get('age', ''), key="pat_age")
                p_sex = st.selectbox("Sex", ["", "M", "F", "Other"], 
                                    index=["", "M", "F", "Other"].index(st.session_state.patient_info.get('sex', '')) 
                                    if st.session_state.patient_info.get('sex') in ["", "M", "F", "Other"] else 0,
                                    key="pat_sex")
            
            p_history = st.text_area("Clinical History", value=st.session_state.patient_info.get('history', ''), 
                                    height=80, key="pat_history")
            
            if st.button("💾 Save Patient Info", key="save_patient_button", use_container_width=True):
                st.session_state.patient_info = {
                    "name": p_name, "id": p_id, "age": p_age, 
                    "sex": p_sex, "history": p_history
                }
                st.success("Patient info saved!")
        
        # Main Draft Area
        st.subheader("📝 Report Draft")
        draft_text = st.text_area(
            "Type your report below:",
            value=st.session_state.report_draft,
            height=250,
            key="draft_input",
            label_visibility="collapsed",
            placeholder="Start typing your report here...\nPatient information is optional."
        )
        st.session_state.report_draft = draft_text
        
        # Action Buttons
        col_actions = st.columns(4)
        with col_actions[0]:
            if st.button("🤖 Generate", type="primary", use_container_width=True, key="generate_button"):
                # Always allow report generation, even without patient details
                formatted_report = ""
                
                # Add patient info if available
                if st.session_state.patient_info and any(st.session_state.patient_info.values()):
                    formatted_report += "PATIENT INFORMATION:\n"
                    if st.session_state.patient_info.get('name'):
                        formatted_report += f"Name: {st.session_state.patient_info['name']}\n"
                    if st.session_state.patient_info.get('id'):
                        formatted_report += f"ID: {st.session_state.patient_info['id']}\n"
                    if st.session_state.patient_info.get('age') or st.session_state.patient_info.get('sex'):
                        formatted_report += f"Age/Sex: {st.session_state.patient_info.get('age', '')}/{st.session_state.patient_info.get('sex', '')}\n"
                    if st.session_state.patient_info.get('history'):
                        formatted_report += f"Clinical History: {st.session_state.patient_info['history']}\n"
                
                # Add technique section
                formatted_report += "\nTECHNIQUE:\n"
                tech_info = st.session_state.technique_info
                formatted_report += f"Modality: {tech_info.get('modality', 'Not specified')}\n"
                formatted_report += f"Contrast: {tech_info.get('contrast', 'Without contrast')}\n"
                if tech_info.get('sequences'):
                    formatted_report += f"{tech_info['sequences']}\n"
                
                # Add the main draft content
                if draft_text:
                    formatted_report += "\n" + draft_text
                
                # Ensure IMPRESSION section exists if not in draft
                if "IMPRESSION:" not in formatted_report and "IMPRESSION" not in formatted_report:
                    formatted_report += "\n\nIMPRESSION:\nFindings as described above. Clinical correlation recommended."
                
                st.session_state.ai_report = formatted_report
                st.session_state.report_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                st.success("Report generated successfully!")
        
        with col_actions[1]:
            if st.button("🧠 AI Suggestions", use_container_width=True, key="suggestions_button"):
                st.session_state.show_differential_suggestions = True
                current_modality = st.session_state.technique_info.get('modality', 'All')
                st.session_state.differential_results = generate_differential_diagnosis(draft_text, current_modality)
                st.rerun()
        
        with col_actions[2]:
            if st.button("📋 Templates", use_container_width=True, key="templates_button"):
                # This would open template sidebar - implemented separately
                st.info("Use templates from the right panel")
        
        with col_actions[3]:
            if st.button("🧹 Clear", use_container_width=True, key="clear_button"):
                st.session_state.report_draft = ""
                st.rerun()
        
        # Differential Diagnosis Suggestions
        if st.session_state.show_differential_suggestions and st.session_state.differential_results:
            st.subheader("🧠 AI Differential Suggestions")
            
            for i, dx in enumerate(st.session_state.differential_results):
                with st.container(border=True):
                    col_dx1, col_dx2 = st.columns([3, 1])
                    with col_dx1:
                        urgency_icon = "🔴" if dx.get('urgency') == "Urgent" else "🟢"
                        st.markdown(f"**{dx['diagnosis']}** {urgency_icon}")
                        st.caption(f"**Features:** {dx['features']}")
                        st.caption(f"**Modality:** {dx.get('modality', 'N/A')} | "
                                 f"**Confidence:** {dx.get('confidence', 'N/A')} | "
                                 f"**Urgency:** {dx.get('urgency', 'N/A')}")
                    
                    with col_dx2:
                        if st.button("➕ Add", key=f"add_dx_{i}", use_container_width=True):
                            if "DIFFERENTIAL DIAGNOSIS:" not in st.session_state.report_draft:
                                dx_text = f"\n\nDIFFERENTIAL DIAGNOSIS:\n1. {dx['diagnosis']} - {dx['features']}"
                            else:
                                lines = st.session_state.report_draft.split('\n')
                                last_number = 1
                                for line in reversed(lines):
                                    if line.strip().startswith(tuple(str(i) for i in range(10))):
                                        try:
                                            last_number = int(line.split('.')[0]) + 1
                                            break
                                        except:
                                            pass
                                dx_text = f"\n{last_number}. {dx['diagnosis']} - {dx['features']}"
                            
                            st.session_state.report_draft += dx_text
                            st.success(f"Added {dx['diagnosis']} to draft!")
                            st.rerun()
    
    with col2:
        # ===== RIGHT PANEL: OUTPUT & ENHANCED FEATURES =====
        st.header("📋 Report Output & Analysis")
        
        if st.session_state.ai_report:
            # Quality Check Results
            if st.session_state.show_quality_check:
                with st.container(border=True):
                    st.subheader("🔍 Quality Assurance Check")
                    audit_results = st.session_state.quality_assurance.audit_report(st.session_state.ai_report)
                    
                    # Display score
                    col_score1, col_score2 = st.columns([1, 2])
                    with col_score1:
                        st.markdown(f"### {audit_results['score']}/100")
                        st.markdown(st.session_state.ui_components.create_quality_score_display(audit_results['score']), 
                                  unsafe_allow_html=True)
                    
                    with col_score2:
                        st.markdown(f"**Grade:** {audit_results['grade']}")
                    
                    # Show warnings and suggestions
                    if audit_results['warnings']:
                        st.warning("**Warnings:**")
                        for warning in audit_results['warnings']:
                            st.write(f"- {warning}")
                    
                    if audit_results['suggestions']:
                        st.info("**Suggestions:**")
                        for suggestion in audit_results['suggestions']:
                            st.write(f"- {suggestion}")
                    
                    if audit_results['strengths']:
                        st.success("**Strengths:**")
                        for strength in audit_results['strengths']:
                            st.write(f"- {strength}")
                    
                    # Save audit log
                    if st.button("💾 Save Quality Report", key="save_quality_report"):
                        report_id = f"{st.session_state.patient_info.get('id', 'unknown')}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        st.session_state.quality_assurance.save_audit_log(
                            report_id,
                            audit_results,
                            st.session_state.current_user
                        )
                        st.success("Quality report saved!")
            
            # Report preview
            with st.container(border=True, height=300):
                st.text_area(
                    "Generated Report:",
                    value=st.session_state.ai_report,
                    height=280,
                    key="report_preview",
                    label_visibility="collapsed"
                )
            
            # Export options
            st.subheader("📤 Export Options")
            
            col_export = st.columns(3)
            with col_export[0]:
                # Word document
                try:
                    doc = create_word_document(
                        patient_info=st.session_state.patient_info,
                        report_text=st.session_state.ai_report,
                        report_date=st.session_state.report_date,
                        technique_info=st.session_state.technique_info
                    )
                    
                    buffer = BytesIO()
                    doc.save(buffer)
                    buffer.seek(0)
                    
                    patient_id = st.session_state.patient_info.get('id', 'Unknown')
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    
                    st.download_button(
                        label="📄 Word",
                        data=buffer,
                        file_name=f"RadReport_{patient_id}_{timestamp}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                        key="download_word"
                    )
                except Exception as e:
                    st.error(f"Word export error: {str(e)}")
            
            with col_export[1]:
                # Plain text
                txt_data = st.session_state.ai_report
                st.download_button(
                    label="📝 Text",
                    data=txt_data,
                    file_name=f"RadReport_{patient_id}_{timestamp}.txt",
                    mime="text/plain",
                    use_container_width=True,
                    key="download_text"
                )
            
            with col_export[2]:
                # JSON export
                report_data = {
                    "metadata": {
                        "generated_by": st.session_state.current_user,
                        "generation_date": st.session_state.report_date,
                        "patient_info": st.session_state.patient_info,
                        "technique_info": st.session_state.technique_info
                    },
                    "report_content": st.session_state.ai_report
                }
                
                json_data = json.dumps(report_data, indent=2)
                st.download_button(
                    label="📊 JSON",
                    data=json_data,
                    file_name=f"RadReport_{patient_id}_{timestamp}.json",
                    mime="application/json",
                    use_container_width=True,
                    key="download_json"
                )
            
            # Save to history with analytics update
            st.divider()
            st.subheader("💾 Save Report")
            
            report_name = st.text_input(
                "Report Name:",
                value=f"{st.session_state.patient_info.get('name', 'Unnamed')}_{st.session_state.report_date.split()[0]}",
                key="report_name_input"
            )
            
            if st.button("💾 Save to History", type="secondary", use_container_width=True, key="save_history"):
                history_entry = {
                    "name": report_name,
                    "date": st.session_state.report_date,
                    "patient_info": st.session_state.patient_info,
                    "technique_info": st.session_state.technique_info,
                    "report": st.session_state.ai_report,
                    "created_by": st.session_state.current_user,
                    "has_patient_data": bool(st.session_state.patient_info and any(st.session_state.patient_info.values()))
                }
                st.session_state.report_history.append(history_entry)
                
                # Update analytics
                st.session_state.analytics_dashboard.update_metrics(history_entry)
                
                st.success("Report saved to history with analytics update!")
        
        else:
            # Empty state with enhanced features preview
            with st.container(border=True, height=400):
                st.info("""
                ## 🚀 Enhanced Features Available:
                
                **📊 Analytics Dashboard**
                - Track report metrics and productivity
                - Visualize modality distribution
                - Monitor quality trends
                
                **🔍 Quality Assurance**
                - Automated report auditing
                - Quality scoring (0-100)
                - Improvement suggestions
                
                **🔬 Multi-Modal Integration**
                - Detailed technique generation
                - Imaging recommendations
                - Protocol suggestions
                
                **📁 DICOM Support** {}
                - Metadata extraction
                - Auto-populate patient info
                - Technique from DICOM headers
                
                **🎨 Enhanced UI**
                - Progress indicators
                - Quality score displays
                - Keyboard shortcuts
                """.format("✅" if DICOM_AVAILABLE else "❌ (Install pydicom)"))
        
        # Template Management
        st.divider()
        st.header("📚 Template Library")
        
        # Quick templates
        quick_templates = {
            "Normal Brain MRI": "Normal study. No acute intracranial hemorrhage, mass effect, or territorial infarct. Ventricles and sulci are normal. No abnormal enhancement.",
            "White Matter Changes": "Scattered punctate FLAIR hyperintensities in the periventricular and deep white matter, consistent with chronic microvascular ischemic changes.",
            "Disc Herniation": "Disc bulge/protrusion causing mild neural foraminal narrowing without significant cord compression."
        }
        
        col_templates = st.columns(3)
        for idx, (name, content) in enumerate(quick_templates.items()):
            with col_templates[idx]:
                if st.button(name, key=f"qt_{idx}", use_container_width=True):
                    st.session_state.report_draft += f"\n\nFINDINGS:\n{content}"
                    st.success(f"Added {name} template!")
                    st.rerun()
        
        # Create new template
        with st.expander("➕ Create New Template", expanded=False):
            new_name = st.text_input("Template Name", key="new_template_name_input")
            new_type = st.selectbox("Type", ["findings", "technique", "impression"], key="new_template_type_select")
            new_content = st.text_area("Content", height=100, key="new_template_content_area")
            
            if st.button("💾 Save Template", key="save_new_template_button", use_container_width=True):
                if new_name and new_content:
                    st.session_state.template_system.add_template(new_name, new_content, new_type)
                    st.success(f"Template '{new_name}' saved!")
                    st.rerun()
                else:
                    st.warning("Please enter both name and content")
        
        # Keyboard shortcuts panel
        st.markdown(st.session_state.ui_components.create_keyboard_shortcuts_panel(), unsafe_allow_html=True)
    
    # ===== REPORT HISTORY =====
    st.divider()
    st.header("📜 Report History")
    
    if st.session_state.report_history:
        # Show last 5 reports
        for i, report in enumerate(reversed(st.session_state.report_history[-5:])):
            with st.expander(f"{report['name']} - {report['date']}", expanded=False):
                col_hist1, col_hist2, col_hist3 = st.columns([2, 1, 1])
                with col_hist1:
                    patient_name = report['patient_info'].get('name', 'No patient data')
                    modality = report['technique_info'].get('modality', 'Unknown')
                    st.caption(f"**Patient:** {patient_name} | **Modality:** {modality}")
                
                with col_hist2:
                    if st.button("📥 Load", key=f"load_{i}", use_container_width=True):
                        st.session_state.patient_info = report['patient_info']
                        st.session_state.technique_info = report['technique_info']
                        st.session_state.ai_report = report['report']
                        st.session_state.report_date = report['date']
                        st.success("Report loaded!")
                        st.rerun()
                
                with col_hist3:
                    report_idx = len(st.session_state.report_history) - 1 - i
                    if st.button("🗑️ Delete", key=f"delete_{i}", use_container_width=True):
                        st.session_state.report_history.pop(report_idx)
                        st.warning("Report deleted!")
                        st.rerun()
                
                # Preview with quality score if available
                preview = report['report'][:200] + "..." if len(report['report']) > 200 else report['report']
                st.text(preview)
                
                # Quick quality check
                if st.button(f"🔍 Quick Quality Check", key=f"quality_{i}", use_container_width=True):
                    audit_results = st.session_state.quality_assurance.audit_report(report['report'])
                    st.info(f"Quality Score: {audit_results['score']}/100 ({audit_results['grade']})")
    else:
        st.info("No reports in history yet. Generate and save your first report!")

# ===== RUN APPLICATION =====
if __name__ == "__main__":
    main()
