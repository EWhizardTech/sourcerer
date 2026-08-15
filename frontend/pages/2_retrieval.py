import streamlit as st
from components.api import retrieve_chunks
from components.styling import apply_custom_styles, render_page_header

from components.api import retrieve_answer

st.set_page_config(page_title="Retrieval | Sourcerer", page_icon="🔍")
apply_custom_styles()

render_page_header(
    "🔍 Retrieval", "Search and query documents ingested in the RAG Pipeline."
)

# Dev mode toggle
dev_mode = st.toggle("Dev mode", value=False, help="Show the retrieved document chunks used by the LLM.")

# Initialize session state for messages
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display existing chat messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if dev_mode and msg.get("chunks"):
            with st.expander("Retrieved Chunks"):
                st.text(msg["chunks"])

# Chat input
if query := st.chat_input("Ask Sourcerer a question... e.g., What are data structures?"):
    # Add user message to state and display
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)
    
    # Process the query
    with st.chat_message("assistant"):
        with st.spinner("Searching the knowledge base..."):
            response = retrieve_answer(query)
            
            if response and "answer" in response:
                answer = response["answer"]
                chunks = response.get("chunks")
                
                st.markdown(answer)
                if dev_mode and chunks:
                    with st.expander("Retrieved Chunks"):
                        st.text(chunks)
                        
                # Add assistant message to state
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": answer,
                    "chunks": chunks
                })
            elif response:
                st.error("Unexpected response from the server.")
                st.json(response)
