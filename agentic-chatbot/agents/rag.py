from langchain_core.documents import Document
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from typing import List

from agents.models import vectorstore, llm
from agents.sql import process_sql
from prompts.rag import RAG_AGENT_SYSTEM_MESSAGE


@tool
def fetch_documents(search_query: str) -> List[Document]:
    """Fetch documents from the vector database.

    Args:
        search_query (str): The search query to fetch documents from the vector database. Could be the user's original question or a reformulated query.

    Returns:
        List[Document]: The list of documents fetched from the vector database.
    """
    print("TOOL: fetch documents with search query:", search_query)
    docs = vectorstore.similarity_search(search_query, k=10)
    return docs


memory = MemorySaver()
tools = [process_sql, fetch_documents]

rag_agent = create_react_agent(
    llm,
    tools,
    checkpointer=memory,
    messages_modifier=RAG_AGENT_SYSTEM_MESSAGE,
)


def process_rag(message: str, thread_id: str):
    inputs = {"messages": [("user", message)]}
    config = {"configurable": {"thread_id": thread_id}}

    final_answer = None

    for s in rag_agent.stream(
        inputs,
        config=config,
        stream_mode="values",
    ):
        message = s["messages"][-1]

        if isinstance(message, tuple):
            print(message)
        else:
            message.pretty_print()
            final_answer = message.content

    if "<|source_sep|>" in final_answer:
        answer, sources = final_answer.split("<|source_sep|>")
        final_answer = answer
    else:
        sources = ""

    return {"answer": final_answer, "sources": sources}
