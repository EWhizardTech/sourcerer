import streamlit as st

from components.styling import apply_custom_styles, render_page_header
from components.api import get_health

st.set_page_config(
    page_title="Sourcerer Admin",
    page_icon="🔮",
    layout="centered",
    initial_sidebar_state="expanded",
)

apply_custom_styles()

def main():
    render_page_header("🔮 Sourcerer Control Panel", "Manage your AI-powered RAG backend.")

    # Check Backend Status
    st.subheader("System Status")
    is_healthy = get_health()
    
    if is_healthy:
        st.markdown('<span class="status-badge status-ok">Backend Online</span>', unsafe_allow_html=True)
        st.success("Successfully connected to the Sourcerer backend API.")
    else:
        st.markdown('<span class="status-badge status-error">Backend Offline</span>', unsafe_allow_html=True)
        st.error("Failed to connect to the backend. Please ensure the backend server is running on port 8000.")

    st.divider()
    
    st.markdown("""
    ### Available Features
    Use the sidebar to navigate to the desired functionality:
    
    * **📥 Ingestion:** Ingest documents from Google Drive by providing a Folder ID.
    * **🔍 Retrieval:** (Coming Soon) Search and retrieve context from the ingested documents.
    """)

if __name__ == "__main__":
    main()
