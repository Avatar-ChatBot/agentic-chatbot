# Qwen3-Embedding Migration Plan

## Problem Summary

Current migration from OpenAI to Qwen3-Embedding-8B via OpenRouter is producing poor results. Analysis revealed two critical issues:

1. **Wrong Embedding Dimension**: Using 1024 dimensions for `qwen/qwen3-embedding-8b`, but this model's native dimension is **4096**. We're losing 75% of the model's representational capacity.

2. **Missing Instructions**: Qwen3-Embedding is "Instruction Aware" - queries should use instructions for 1-5% better retrieval performance according to [official docs](https://github.com/QwenLM/Qwen3-Embedding).

## Model Dimension Reference

| Model | Size | Native Embedding Dimension |
|-------|------|---------------------------|
| Qwen3-Embedding-0.6B | 0.6B | **1024** |
| Qwen3-Embedding-4B | 4B | **2560** |
| Qwen3-Embedding-8B | 8B | **4096** |

Source: [Qwen3-Embedding GitHub](https://github.com/QwenLM/Qwen3-Embedding)

---

## Implementation Plan

### Phase 1: Fix Dimension Issues

**Files to modify:**
1. `scripts/reembed_snapshot.py`
2. `scripts/query_qdrant.py`
3. `agents/rag.py` (if applicable)

**Changes:**

#### 1. Update `scripts/reembed_snapshot.py` (Line 48-54)

```python
# BEFORE
EMBEDDING_DIMENSIONS = {
    "openai/text-embedding-3-small": 1536,
    "openai/text-embedding-3-large": 3072,
    "openai/text-embedding-ada-002": 1536,
    "qwen/qwen2-7b-instruct": 1536,
    "qwen/qwen3-embedding-8b": 1024,  # WRONG!
}

# AFTER
EMBEDDING_DIMENSIONS = {
    "openai/text-embedding-3-small": 1536,
    "openai/text-embedding-3-large": 3072,
    "openai/text-embedding-ada-002": 1536,
    "qwen/qwen2-7b-instruct": 1536,
    "qwen/qwen3-embedding-0.6b": 1024,
    "qwen/qwen3-embedding-4b": 2560,
    "qwen/qwen3-embedding-8b": 4096,  # FIXED!
}
```

#### 2. Update `scripts/reembed_snapshot.py` (Line 199-226)

```python
# BEFORE
def _embed_batch_openrouter(self, texts: List[str]) -> Optional[List[List[float]]]:
    url = "https://openrouter.ai/api/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {self.api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com",
    }

    data = {
        "input": texts,
        "model": self.embedding_model,
        "dimensions": 1024,  # WRONG - hardcoded!
    }
    ...

# AFTER
def _embed_batch_openrouter(self, texts: List[str]) -> Optional[List[List[float]]]:
    url = "https://openrouter.ai/api/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {self.api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com",
    }

    # Determine dimensions based on model
    dimensions = None  # Let OpenRouter use model's native dimension
    for model_key, dim in self.EMBEDDING_DIMENSIONS.items():
        if model_key in self.embedding_model:
            dimensions = dim
            break

    data = {
        "input": texts,
        "model": self.embedding_model,
    }

    # Only specify dimensions if explicitly needed (not recommended for Qwen3-8B)
    if dimensions and self.embedding_model != "qwen/qwen3-embedding-8b":
        data["dimensions"] = dimensions
```

**Note:** For `qwen3-embedding-8b`, we should NOT specify the `dimensions` parameter at all, letting OpenRouter use the model's native 4096 dimensions. The model supports MRL (Matryoshka Representation Learning) but using full dimensions gives best performance.

#### 3. Update `scripts/query_qdrant.py` (Line 27-46)

```python
# BEFORE
def get_embeddings(embedding_provider: str = "openai"):
    ...
    if embedding_provider == "qwen":
        embedding_model = os.getenv("EMBEDDING_MODEL", "qwen/qwen3-embedding-8b")
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required for qwen embeddings")
        return OpenAIEmbeddings(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_api_key,
            model=embedding_model,
            dimensions=1024,  # WRONG!
        )
    return OpenAIEmbeddings(model="text-embedding-3-large")

# AFTER
def get_embeddings(embedding_provider: str = "openai"):
    ...
    if embedding_provider == "qwen":
        embedding_model = os.getenv("EMBEDDING_MODEL", "qwen/qwen3-embedding-8b")
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required for qwen embeddings")

        # Map model to dimension
        embedding_dimensions = {
            "qwen/qwen3-embedding-0.6b": 1024,
            "qwen/qwen3-embedding-4b": 2560,
            "qwen/qwen3-embedding-8b": None,  # Use native dimension (4096)
        }

        dimension = embedding_dimensions.get(embedding_model)
        kwargs = {
            "base_url": "https://openrouter.ai/api/v1",
            "api_key": openrouter_api_key,
            "model": embedding_model,
        }

        # Only add dimensions parameter if not using 8B (let 8B use native)
        if dimension is not None:
            kwargs["dimensions"] = dimension

        return OpenAIEmbeddings(**kwargs)
    return OpenAIEmbeddings(model="text-embedding-3-large")
```

---

### Phase 2: Add Instruction-Aware Embedding Support

According to [Qwen3-Embedding docs](https://github.com/QwenLM/Qwen3-Embedding):

> "Our evaluation indicates that, for most downstream tasks, using instructions typically yields an improvement of **1% to 5%** compared to not using them."

**Key insight:**
- **Documents (indexing)**: No instruction needed
- **Queries (searching)**: Should use instruction format

The instruction format from official docs:
```python
def get_detailed_instruct(task_description: str, query: str) -> str:
    return f'Instruct: {task_description}\nQuery:{query}'
```

#### 2.1 Add instruction helper function

**Create new file: `agents/embedding_utils.py`**

```python
"""
Embedding utilities for instruction-aware models like Qwen3-Embedding.
"""

from typing import Optional


# Default task instruction for RAG/search scenarios
DEFAULT_RAG_INSTRUCTION = "Given a web search query, retrieve relevant passages that answer the query"


def get_detailed_instruct(task_description: str, query: str) -> str:
    """Format query with instruction for Qwen3-Embedding.

    Args:
        task_description: Task description (e.g., "Given a web search query...")
        query: The actual search query

    Returns:
        Formatted string with instruction prefix

    Example:
        >>> get_detailed_instruct("Search for relevant passages", "What is ITB?")
        'Instruct: Search for relevant passages\\nQuery:What is ITB?'
    """
    return f'Instruct: {task_description}\nQuery:{query}'


def format_query_for_embedding(
    query: str,
    instruction: Optional[str] = None,
    model_type: str = "qwen3"
) -> str:
    """Format a query string with instruction if the model supports it.

    Args:
        query: The search query
        instruction: Optional custom instruction (uses default if None and qwen3)
        model_type: Model type - "qwen3" for instruction-aware models

    Returns:
        Formatted query string
    """
    if model_type == "qwen3":
        task_instruction = instruction or DEFAULT_RAG_INSTRUCTION
        return get_detailed_instruct(task_instruction, query)
    return query


def should_use_instructions(model_name: str) -> bool:
    """Check if a model supports and should use instructions.

    Args:
        model_name: The embedding model name

    Returns:
        True if model is instruction-aware (Qwen3-Embedding series)
    """
    instruction_aware_models = [
        "qwen3-embedding",
        "qwen/qwen3-embedding",
    ]
    return any(model in model_name.lower() for model in instruction_aware_models)
```

#### 2.2 Update `scripts/query_qdrant.py`

Add support for instruction-aware query embedding:

```python
# Add import
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from agents.embedding_utils import format_query_for_embedding, should_use_instructions

# Modify the search part
def main():
    ...
    # Perform search
    print(f"\n{'='*60}")
    print(f"Query: {args.query}")
    print(f"Collection: {args.collection}")
    print(f"Embedding: {args.embedding_provider}")
    print(f"{'='*60}\n")

    # Format query with instruction if using Qwen3
    search_query = args.query
    if args.embedding_provider == "qwen":
        model = os.getenv("EMBEDDING_MODEL", "qwen/qwen3-embedding-8b")
        if should_use_instructions(model):
            search_query = format_query_for_embedding(args.query)
            print(f"[DEBUG] Formatted query: {search_query[:100]}...")

    results = vectorstore.similarity_search_with_score(search_query, k=args.top)
```

---

### Phase 3: Re-embed with Correct Configuration

Once code changes are complete, re-run the migration:

```bash
# Dry run first to verify
python scripts/reembed_snapshot.py \
    --source-collection informasi-umum-itb \
    --provider openrouter \
    --embedding-model qwen/qwen3-embedding-8b \
    --output-collection informasi-umum-itb-qwen3 \
    --dry-run

# Actual migration
python scripts/reembed_snapshot.py \
    --source-collection informasi-umum-itb \
    --provider openrouter \
    --embedding-model qwen/qwen3-embedding-8b \
    --output-collection informasi-umum-itb-qwen3 \
    --batch-size 100
```

---

### Phase 4: Verify and Test

After migration, test with and without instructions:

```bash
# Test WITHOUT instruction (baseline)
python scripts/query_qdrant.py "biaya kuliah itb" \
    --embedding-provider qwen \
    --collection informasi-umum-itb-qwen3 \
    --top 5

# Compare with OpenAI results
python scripts/query_qdrant.py "biaya kuliah itb" \
    --embedding-provider openai \
    --collection informasi-umum-itb \
    --top 5
```

---

## Additional Considerations

### OpenRouter API Compatibility

OpenRouter provides an OpenAI-compatible API. Based on [OpenRouter embeddings docs](https://openrouter.ai/docs/api/reference/embeddings):

- The API accepts `input` (string or array) and `model` parameters
- The `dimensions` parameter is optional but model-dependent
- For Qwen3-8B, **omit** the `dimensions` parameter to use native 4096

### MRL (Matryoshka Representation Learning)

Qwen3-Embedding supports custom dimensions via MRL, but:
- Using full native dimension (4096 for 8B) gives best performance
- Only use reduced dimensions if you have specific storage/indexing constraints
- 1024 dimensions for 8B model = 75% information loss

### Collection Migration Notes

- Documents are embedded **WITHOUT** instruction (current behavior is correct)
- Only queries need instruction formatting during search
- No need to re-embed documents differently - the issue is dimension mismatch

---

## Checklist

- [ ] Update `EMBEDDING_DIMENSIONS` dict in `reembed_snapshot.py`
- [ ] Remove hardcoded `dimensions: 1024` in `_embed_batch_openrouter`
- [ ] Update `query_qdrant.py` `get_embeddings()` function
- [ ] Create `agents/embedding_utils.py` with instruction helpers
- [ ] Update query logic to use instructions for searches
- [ ] Update `.env.example` if needed (document model choices)
- [ ] Re-embed collection with correct dimensions
- [ ] Test search quality with both providers
- [ ] Update documentation/README with findings

---

## Sources

- [Qwen3-Embedding GitHub](https://github.com/QwenLM/Qwen3-Embedding)
- [OpenRouter Qwen3-Embedding-8B](https://openrouter.ai/qwen/qwen3-embedding-8b)
- [OpenRouter Embeddings API](https://openrouter.ai/docs/api/reference/embeddings)
