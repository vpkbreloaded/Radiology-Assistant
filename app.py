# ===== SIDEBAR: Patient Info & Template Management =====
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
    
    # ===== STEP 1 & 2: TEMPLATE LIBRARY =====
    st.header("📚 Template Library")
    
    # --- SECTION A: Save Current Draft as a New Template ---
    st.subheader("💾 Save Current Draft")
    # Use the main draft text from the left column as the template content
    new_template_name = st.text_input("Give this template a name:")
    
    if st.button("💾 Save as New Template", key="save_button"):
        if not new_template_name:
            st.warning("Please enter a name for the template.")
        elif not st.session_state.report_draft:
            st.warning("Your draft is empty. Type something in the left column first.")
        else:
            # Initialize the saved templates dictionary if it doesn't exist
            if 'saved_templates' not in st.session_state:
                st.session_state.saved_templates = {}
            
            # Save the current draft text with the given name
            st.session_state.saved_templates[new_template_name] = st.session_state.report_draft
            st.success(f"Template **'{new_template_name}'** saved successfully!")
    
    st.divider()
    
    # --- SECTION B: Load a Saved Template ---
    st.subheader("📂 Load a Saved Template")
    
    # Check if we have any saved templates
    if 'saved_templates' in st.session_state and st.session_state.saved_templates:
        # Create a dropdown from the saved template names
        template_list = list(st.session_state.saved_templates.keys())
        selected_template_name = st.selectbox("Choose a template:", options=template_list, key="template_selector")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Load into Draft", key="load_button"):
                # Load the selected template's text into the main draft area
                st.session_state.report_draft = st.session_state.saved_templates[selected_template_name]
                st.success(f"Loaded **'{selected_template_name}'**!")
                st.rerun()  # Refresh to show the loaded text immediately
        with col2:
            if st.button("🗑️ Delete", key="delete_button"):
                # Remove the template from the dictionary
                del st.session_state.saved_templates[selected_template_name]
                st.warning(f"Deleted template **'{selected_template_name}'**.")
                st.rerun()
        
        # Optional: Show a small preview of the selected template
        with st.expander("Preview selected template"):
            preview_text = st.session_state.saved_templates[selected_template_name]
            st.caption(preview_text[:200] + "..." if len(preview_text) > 200 else preview_text)
    else:
        st.info("No saved templates yet. Save your first draft above!")
    
    st.divider()
    
    # ===== QUICK TEMPLATES (Your existing feature - kept for convenience) =====
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
            # Append the new text to the existing draft
            separator = "\n" if current_draft else ""
            st.session_state.report_draft = current_draft + separator + new_text
            st.rerun()
    
    st.divider()
    
    # Clear All Button
    if st.button("🧹 Clear All Text (Draft & AI Report)"):
        st.session_state.report_draft = ""
        st.session_state.ai_report = ""
        st.rerun()
