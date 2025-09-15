import streamlit as st
from scripts.retrieve_and_answer import answer_question

st.set_page_config(page_title="Prague Events Chat", page_icon="🎭")

st.title("Prague Events Chat")

st.write("Ask me about events in Prague, e.g. 'Tell me about rental apartment situation in Prague'")

# Use a session state to store the query and answer
if "query" not in st.session_state:
    st.session_state.query = ""
if "answer" not in st.session_state:
    st.session_state.answer = ""

# Input field for the user's question
query = st.text_input("Your question:", value=st.session_state.query, key="query_input")

# Button to submit the question
if st.button("Ask"):
    if query.strip():
        with st.spinner("Searching and generating answer..."):
            st.session_state.answer = answer_question(query)
        st.session_state.query = ""  # Clear the input field after processing

# Display the answer
if st.session_state.answer:
    st.markdown("### Answer:")
    st.write(st.session_state.answer)