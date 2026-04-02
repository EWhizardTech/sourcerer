import streamlit as st

from components.styling import apply_custom_styles, render_page_header

st.set_page_config(page_title="Retrieval | Sourcerer", page_icon="🔍")
apply_custom_styles()

render_page_header("🔍 Retrieval", "Search and query documents ingested in the RAG Pipeline.")

st.info("The retrieval endpoints are currently under development. Check back later!")

# Placeholder for future retrieval UI
st.text_input("Search Query", disabled=True, placeholder="How does the ingestion process work?")
st.button("Search", disabled=True)
