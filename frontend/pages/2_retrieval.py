import streamlit as st
from components.styling import apply_custom_styles, render_page_header

from components.api import retrieve_answer

st.set_page_config(page_title="Retrieval | Sourcerer", page_icon="🔍")
apply_custom_styles()

render_page_header(
    "🔍 Retrieval", "Search and query documents ingested in the RAG Pipeline."
)

query = st.text_input(
    "Search Query", placeholder="e.g., What are data structures?"
)
search_button = st.button("Search", type="primary")

if search_button and query:
    with st.spinner("Searching the knowledge base..."):
        response = retrieve_answer(query)
        if response and "answer" in response:
            st.markdown("### Answer")
            st.info(response["answer"])
        elif response:
            st.error("Unexpected response from the server.")
            st.json(response)
