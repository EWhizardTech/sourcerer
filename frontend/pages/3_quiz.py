import streamlit as st

from components.api import generate_quiz
from components.styling import apply_custom_styles, render_page_header


st.set_page_config(page_title="Quiz | Sourcerer", page_icon="📝")
apply_custom_styles()

render_page_header(
    "📝 Quiz Generator",
    "Generate multiple-choice questions from the same retrieval-backed corpus used by Sourcerer.",
)

with st.form("quiz_form"):
    st.markdown("### Quiz Parameters")

    query = st.text_area(
        "Query *",
        value="what is information retrieval?",
        height=110,
        help="Ask for a topic, concept, or chapter you want quiz questions from.",
    )

    col1, col2 = st.columns(2)
    with col1:
        course_code = st.text_input("Course Code (Optional)", value="20XW81")
        tags = st.text_input(
            "Tags (Optional, comma-separated)",
            help="For example: retrieval, embeddings, qdrant",
        )
    with col2:
        year = st.text_input("Year (Optional)", value="2026")
        num_questions = st.number_input(
            "Number of Questions",
            min_value=1,
            max_value=20,
            value=11,
            step=1,
        )

    # allow_unfiltered_fallback = st.checkbox(
    #     "Fallback to unfiltered retrieval when filters return no matches",
    #     value=True,
    #     help="If enabled, quiz generation retries without course/year/tags filters when no filtered chunks are found.",
    # )

    submitted = st.form_submit_button("Generate Quiz", type="primary")

if submitted:
    cleaned_query = query.strip()
    if not cleaned_query:
        st.error("Query is required.")
    else:
        with st.spinner("Generating quiz from retrieved content..."):
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()] or None
            response_data = generate_quiz(
                query=cleaned_query,
                course_code=course_code.strip() or None,
                year=year.strip() or None,
                tags=tag_list,
                num_questions=int(num_questions),
                allow_unfiltered_fallback=True,
            )

            if response_data:
                st.success(f"Generated {len(response_data)} question(s).")

                for index, item in enumerate(response_data, start=1):
                    with st.expander(f"Question {index}", expanded=index == 1):
                        st.markdown(f"**Question:** {item.get('question', '')}")
                        options = item.get("options", [])
                        if options:
                            st.markdown("**Options:**")
                            for option in options:
                                st.write(f"- {option}")
                        st.markdown(f"**Answer:** {item.get('answer', '')}")
                        st.markdown(f"**Difficulty:** {item.get('difficulty', 'unknown')}")
                        source_ids = item.get("source_chunk_ids", [])
                        if source_ids:
                            st.caption(f"Source chunk IDs: {', '.join(map(str, source_ids))}")
            else:
                st.error("Quiz generation failed. Check that the backend has indexed content for these filters.")
