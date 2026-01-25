import json
import os
import re
from typing import List

from langchain_core.documents import Document
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from agents.models import llm, vectorstore
from agents.embedding_utils import format_query_for_embedding, should_use_instructions
from prompts.rag import RAG_AGENT_SYSTEM_MESSAGE
from utils.checkpointer import get_checkpointer


# Indonesian academic term synonyms for query expansion
QUERY_EXPANSION_DICT = {
    "biaya": ["uang", "pendidikan", "kuliah", "ukt", "spp", "pembayaran"],
    "program studi": ["prodi", "jurusan", "major", "study program", "program"],
    "syarat": ["persyaratan", "kualifikasi", "requirements", "ketentuan"],
    "pendaftaran": ["registrasi", "enrollment", "penerimaan", "admisi"],
    "beasiswa": ["bantuan keuangan", "penghargaan", "grant", "financial aid"],
    "jadwal": ["waktu", "schedule", "kalender", "timeline"],
    "kuliah": ["perkuliahan", "pembelajaran", "studi", "lecture"],
    "kampus": ["kawasan", "lokasi", "area", "facilities"],
    "fakultas": ["fakultas", "school", "faculty"],
    "dosen": ["pengajar", "lecturer", "profesor", "guru besar"],
    "mahasiswa": ["siswa", "student", "pelajar"],
    "skripsi": ["tesis", "disertasi", "tugas akhir", "thesis"],
    "uji": ["tes", "test", "ujian", "examination"],
    "nilai": ["grade", "skor", "score", "ipk", "gpa"],
}


def _expand_with_synonyms(query: str) -> List[str]:
    """Expand query with Indonesian synonyms.

    Args:
        query: The original search query

    Returns:
        List of expanded queries with synonyms
    """
    expanded_queries = [query]
    query_lower = query.lower()

    for term, synonyms in QUERY_EXPANSION_DICT.items():
        if term in query_lower:
            for synonym in synonyms:
                # Replace term with synonym in the query
                expanded_query = query_lower.replace(term, synonym)
                if expanded_query != query_lower:
                    expanded_queries.append(expanded_query)

    return expanded_queries


def _is_complex_query(query: str) -> bool:
    """Check if query is complex and should be decomposed.

    Args:
        query: The search query

    Returns:
        True if query should be decomposed
    """
    # Check for conjunctions that indicate multiple questions
    complex_indicators = ["dan", "atau", "serta", "juga", "plus", "disertai"]
    query_lower = query.lower()

    return any(indicator in query_lower for indicator in complex_indicators)


def _decompose_query(query: str) -> List[str]:
    """Decompose complex query into simpler sub-queries.

    Args:
        query: The complex search query

    Returns:
        List of decomposed queries
    """
    decomposed = [query]

    # Split on common Indonesian conjunctions
    separators = [" dan ", " atau ", " serta "]
    for sep in separators:
        if sep in query.lower():
            parts = query.lower().split(sep)
            decomposed.extend([p.strip() for p in parts if p.strip()])
            break

    return decomposed


def _generate_expanded_queries(query: str, num_queries: int = 3) -> List[str]:
    """Generate expanded queries using multiple techniques.

    Args:
        query: The original search query
        num_queries: Maximum number of queries to generate

    Returns:
        List of expanded queries
    """
    queries = [query]

    # 1. Synonym expansion
    synonym_queries = _expand_with_synonyms(query)
    queries.extend(synonym_queries[: num_queries - 1])

    # 2. Query decomposition for complex questions
    if _is_complex_query(query):
        sub_queries = _decompose_query(query)
        queries.extend(sub_queries)

    # Deduplicate while preserving order
    seen = set()
    unique_queries = []
    for q in queries:
        if q.lower() not in seen:
            seen.add(q.lower())
            unique_queries.append(q)

    return unique_queries[:num_queries]


def _deduplicate_docs(docs: List) -> List:
    """Deduplicate documents by content.

    Args:
        docs: List of (Document, score) tuples

    Returns:
        Deduplicated list sorted by score
    """
    seen_content = set()
    unique_docs = []

    for doc, score in docs:
        # Convert to string to ensure proper hashing for both real docs and mocks
        content_hash = hash(str(doc.page_content))
        if content_hash not in seen_content:
            seen_content.add(content_hash)
            unique_docs.append((doc, score))

    # Sort by score (descending - higher score is better in similarity search)
    return sorted(unique_docs, key=lambda x: x[1], reverse=True)


@tool
def fetch_documents(search_query: str, num_queries: int = 3) -> str:
    """Fetch documents from the vector database using query expansion.

    Args:
        search_query: The search query (can contain multiple expanded queries)
        num_queries: Number of alternative queries to generate internally

    Returns:
        JSON string with fetched documents including their metadata and quotes
    """
    print(f"TOOL: fetch documents with search query: {search_query}")

    # Check if we should use instruction-aware formatting (Qwen3-Embedding)
    embedding_model = os.getenv("EMBEDDING_MODEL", "qwen/qwen3-embedding-8b")
    use_instructions = should_use_instructions(embedding_model)

    # Generate expanded queries
    expanded_queries = _generate_expanded_queries(search_query, num_queries)
    print(f"TOOL: expanded queries: {expanded_queries}")

    # Format queries with instruction if using instruction-aware model
    if use_instructions:
        expanded_queries = [
            format_query_for_embedding(q, model_name=embedding_model)
            for q in expanded_queries
        ]
        print(f"TOOL: formatted queries for instruction-aware model")

    # Fetch documents for each query
    all_docs = []
    for query in expanded_queries:
        docs = vectorstore.similarity_search_with_score(query, k=5)
        all_docs.extend(docs)

    # Deduplicate and rerank by score
    unique_docs = _deduplicate_docs(all_docs)

    # Format as structured output for the LLM
    result = {
        "query_used": search_query,
        "expanded_queries": expanded_queries,
        "documents": [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score),
            }
            for doc, score in unique_docs[:10]
        ],
    }

    return json.dumps(result, ensure_ascii=False)


memory = get_checkpointer()
tools = [fetch_documents]


# Factory function to create RAG agent (allows for proper mocking in tests)
def get_rag_agent():
    """Get or create the RAG agent instance.

    Returns:
        Compiled LangGraph agent for RAG operations
    """
    return create_react_agent(
        llm,
        tools,
        checkpointer=memory,
        state_modifier=RAG_AGENT_SYSTEM_MESSAGE,  # Updated from deprecated messages_modifier
    )


def _extract_json_from_response(response: str) -> dict:
    """Extract JSON from LLM response, handling various formats.

    Args:
        response: Raw response string from LLM

    Returns:
        Parsed JSON dict or empty dict if parsing fails
    """
    if not response:
        return {}

    # Try direct JSON parsing first
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from markdown code blocks
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find raw JSON object in the response
    json_match = re.search(r"\{.*\}", response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    return {}


def process_rag(message: str, thread_id: str, emotion: str = "neutral") -> dict:
    """Process RAG query with JSON structured output.

    Args:
        message: User message
        thread_id: Conversation thread ID
        emotion: User emotion (for context)

    Returns:
        Dict with 'answer' and 'sources' keys
    """
    inputs = {
        "messages": [
            ("system", f"Emosi pengguna: {emotion}"),
            ("user", message),
        ],
    }
    config = {"configurable": {"thread_id": thread_id}}

    final_answer = None

    # Get agent instance from factory function
    agent = get_rag_agent()

    for s in agent.stream(
        inputs,
        config=config,
        stream_mode="values",
    ):
        msg = s["messages"][-1]

        if isinstance(msg, tuple):
            print(msg)
        else:
            msg.pretty_print()
            final_answer = msg.content

    # Handle thinking tags if present
    if final_answer and "<think>" in final_answer:
        # Remove thinking content
        final_answer = re.sub(
            r"<think>.*?</think>", "", final_answer, flags=re.DOTALL
        ).strip()

    # Parse JSON response
    parsed = _extract_json_from_response(final_answer or "")

    if parsed:
        answer = parsed.get("answer", final_answer or "")
        sources = parsed.get("sources", [])
    else:
        # Fallback for non-JSON responses
        answer = (
            final_answer or "Maaf, terjadi kesalahan dalam memproses pertanyaan Anda."
        )
        sources = []

    return {"answer": answer, "sources": sources}
