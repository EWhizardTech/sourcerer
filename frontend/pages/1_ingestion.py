import streamlit as st
import json

from components.styling import apply_custom_styles, render_page_header
from components.api import ingest_gdrive

st.set_page_config(page_title="Ingestion | Sourcerer", page_icon="📥")
apply_custom_styles()

render_page_header("📥 Google Drive Ingestion", "Import documents from a Google Drive folder into the RAG Pipeline.")

with st.form("ingestion_form"):
    st.markdown("### Ingestion Parameters")
    
    folder_id = st.text_input("Google Drive Folder ID *", help="The ID of the shared Google Drive folder containing documents.")
    course_code = st.text_input("Course Code (Optional)", help="e.g., CS101")
    year = st.text_input("Year (Optional)", help="e.g., 2024")
    include_root_as_tag = st.checkbox("Include Root Folder as Tag")

    submitted = st.form_submit_button("Start Ingestion", type="primary")

if submitted:
    if not folder_id:
        st.error("Folder ID is required.")
    else:
        with st.spinner(f"Ingesting from folder ID: {folder_id}..."):
            # Clean up inputs for the API
            course_val = course_code.strip() if course_code.strip() else None
            year_val = year.strip() if year.strip() else None
            
            response_data = ingest_gdrive(
                folder_id=folder_id.strip(),
                course_code=course_val,
                year=year_val,
                include_root=include_root_as_tag
            )
            
            if response_data is not None:
                st.success(f"Successfully processed {len(response_data)} file(s)!")
                
                with st.expander("View Backend Response"):
                    # Remove the large base64 'content' strings for UI display to avoid freezing the browser
                    clean_res = []
                    for f in response_data:
                        f_clean = f.copy()
                        if "content" in f_clean:
                            f_clean["content"] = "<base64 details omitted for UI>"
                        clean_res.append(f_clean)
                    
                    st.json(clean_res)
