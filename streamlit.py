import uuid

import streamlit as st
from agents.rag import process_rag


def init_session_state():
    """Initialize Streamlit session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())


def render_sources(sources: list):
    """Render structured sources with quotes.

    Args:
        sources: List of source dicts with title, quote, and source keys
    """
    if not sources:
        return

    with st.expander(f"📚 Sumber ({len(sources)})"):
        for i, source in enumerate(sources, 1):
            # Title
            title = source.get("title", source.get("source", "Sumber tidak diketahui"))
            st.markdown(f"**{i}. {title}**")

            # Quote (highlight the specific text used)
            if source.get("quote"):
                st.info(f'📝 "{source["quote"]}"')

            # Original source/link if different from title
            if source.get("source") and source.get("source") != title:
                st.caption(f"🔗 {source['source']}")

            if i < len(sources):
                st.divider()


def render_message(message: dict):
    """Render a chat message with optional sources.

    Args:
        message: Message dict with role, content, and optional sources
    """
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            render_sources(message["sources"])


def display_chat_history():
    """Display all messages from chat history."""
    for message in st.session_state.messages:
        render_message(message)


def main():
    """Main Streamlit application."""
    # Create layout with columns for title and icon
    col1, col2 = st.columns([1, 6])

    with col1:
        st.image("assets/itb_logo.png", width=80)

    with col2:
        st.title("ITB Chatbot")
        st.caption("Asisten informasi akademik ITB")

    # Initialize session state
    init_session_state()

    # Display chat history
    display_chat_history()

    # Chat input
    if prompt := st.chat_input("Apa yang ingin Anda ketahui?"):
        # Display user message
        with st.chat_message("user"):
            st.write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Mencari informasi..."):
                response = process_rag(
                    message=prompt,
                    thread_id=st.session_state.thread_id,
                    emotion="neutral",
                )

                # Display answer
                st.markdown(response["answer"])

                # Display structured sources
                if response.get("sources"):
                    render_sources(response["sources"])

                # Save to history
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": response["answer"],
                        "sources": response.get("sources", []),
                    }
                )


if __name__ == "__main__":
    main()
