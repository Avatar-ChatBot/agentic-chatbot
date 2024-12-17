import uuid

import streamlit as st
from agents.rag import process_rag  # Now this should work


def init_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())


def display_chat_history():
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if message.get("sources"):
                with st.expander("Sources"):
                    st.write(message["sources"])


def main():
    st.title("AI Chat Assistant")

    # Initialize session state
    init_session_state()

    # Display chat history
    display_chat_history()

    # Chat input
    if prompt := st.chat_input("What would you like to know?"):
        # Display user message
        with st.chat_message("user"):
            st.write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = process_rag(
                    message=prompt,
                    thread_id=st.session_state.thread_id,
                    emotion="neutral",  # You can modify this based on your needs
                )

                # Display the response
                st.write(response["answer"])
                if response["sources"]:
                    with st.expander("Sources"):
                        st.write(response["sources"])

                # Save the response to chat history
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": response["answer"],
                        "sources": response["sources"],
                    }
                )


if __name__ == "__main__":
    main()
