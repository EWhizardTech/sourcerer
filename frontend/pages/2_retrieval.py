import streamlit as st
from components.api import retrieve_chunks
from components.styling import apply_custom_styles, render_page_header

st.set_page_config(page_title="Retrieval | Sourcerer", page_icon="🔍")
apply_custom_styles()

render_page_header(
    "🔍 Retrieval", "Search and query documents ingested in the RAG Pipeline."
)

with st.form("retrieval_form"):
    st.markdown("### Retrieval Parameters")

    query = st.text_area(
        "Search Query *",
        placeholder="How does the ingestion process work?",
    )
    course_code = st.text_input("Course Code (Optional)")
    year = st.text_input("Year (Optional)")
    tags_csv = st.text_input(
        "Tags (Optional, comma-separated)",
        help="Example: recursion, arrays",
    )
    top_k = st.number_input(
        "Top K",
        min_value=1,
        max_value=50,
        value=5,
        step=1,
    )

    submitted = st.form_submit_button("Search", type="primary")

if submitted:
    if not query.strip():
        st.error("Search query is required.")
    else:
        with st.spinner("Retrieving chunks..."):
            parsed_tags = [item.strip() for item in tags_csv.split(",") if item.strip()]
            results = retrieve_chunks(
                query=query.strip(),
                course_code=course_code.strip() or None,
                year=year.strip() or None,
                tags=parsed_tags or None,
                top_k=int(top_k),
            )

        if results is not None:
            st.success(f"Retrieved {len(results)} chunk(s).")
            st.json(results)
