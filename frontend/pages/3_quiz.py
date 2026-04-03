import streamlit as st
from components.api import generate_quiz
from components.styling import apply_custom_styles, render_page_header

st.set_page_config(page_title="Quiz | Sourcerer", page_icon="🧠")
apply_custom_styles()

render_page_header(
    "🧠 Quiz Generation",
    "Generate MCQs from retrieved chunks using query and metadata filters.",
)

with st.form("quiz_form"):
    st.markdown("### Quiz Parameters")

    query = st.text_area(
        "Query *",
        help="Natural language prompt used to retrieve relevant chunks.",
    )
    course_code = st.text_input("Course Code (Optional)")
    year = st.text_input("Year (Optional)")
    tags_csv = st.text_input(
        "Tags (Optional, comma-separated)",
        help="Example: arrays, recursion, sorting",
    )
    num_questions = st.number_input(
        "Number of Questions",
        min_value=1,
        max_value=20,
        value=5,
        step=1,
    )

    submitted = st.form_submit_button("Generate Quiz", type="primary")

if submitted:
    if not query.strip():
        st.error("Query is required.")
    else:
        with st.spinner("Generating quiz..."):
            parsed_tags = [item.strip() for item in tags_csv.split(",") if item.strip()]
            result = generate_quiz(
                query=query.strip(),
                course_code=course_code.strip() or None,
                year=year.strip() or None,
                tags=parsed_tags or None,
                num_questions=int(num_questions),
            )

        if result is not None:
            st.success(f"Generated {len(result)} question(s).")
            for idx, item in enumerate(result, start=1):
                st.markdown(f"### Q{idx}. {item['question']}")
                st.write(f"Difficulty: {item['difficulty']}")
                st.write("Options:")
                for option in item["options"]:
                    st.write(f"- {option}")
                st.caption(f"Answer: {item['answer']}")
                st.caption(
                    "Source Chunks: " + ", ".join(item.get("source_chunk_ids", []))
                )
                st.divider()
