# Implementation Plan: XLSX to Qdrant with Gemini 2.0 Flash

**Date:** 2026-01-18
**Status:** Draft

---

## Overview

Convert ITB information Excel file (23 sheets, ~517 rows) to Qdrant knowledge base using Gemini 2.0 Flash for intelligent natural language conversion.

---

## File Analysis

| Category | Sheets | Rows |
|----------|--------|------|
| Magister/Doktor | 4 | ~195 |
| Sarjana (S1) | 7 | ~195 |
| Profesi/Non-Regular | 5 | ~54 |
| Student Exchange | 2 | ~15 |
| IUP (International Undergraduate) | 2 | ~20 |
| Keinsinyuran | 2 | ~32 |
| Beasiswa | 1 | ~6 |
| **Total** | **23** | **~517** |

---

## Tech Stack

| Component | Choice |
|-----------|--------|
| **LLM** | Gemini 2.0 Flash (`gemini-2.0-flash-exp`) |
| **LangChain** | `langchain-google-genai` |
| **Parser** | pandas + openpyxl |
| **Cache** | pickle (for LLM response persistence) |
| **Vector Store** | Existing Qdrant setup |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Informasi Umum ITB.xlsx                   │
│                      (23 sheets)                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    SheetParserFactory                        │
│  - Detects sheet type (program list, schedule, fee, etc.)   │
│  - Returns appropriate parser strategy                      │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ ProgramParser   │ │ ScheduleParser  │ │ FeeParser       │
│ (row-by-row)    │ │ (table format)  │ │ (simple table)  │
└─────────────────┘ └─────────────────┘ └─────────────────┘
          │                   │                   │
          └───────────────────┼───────────────────┘
                              ▼
                    ┌─────────────────┐
                    │  LLMCache       │
                    │  (pickle files) │
                    │  - cache/       │
                    │    - sheet1.pkl │
                    │    - sheet2.pkl │
                    └─────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
     ┌─────────────────┐           ┌─────────────────┐
     │     Cache HIT   │           │     Cache MISS  │
     │  Load from .pkl │           │  Call Gemini    │
     └─────────────────┘           └─────────────────┘
              │                               │
              └───────────────┬───────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Gemini 2.0 Flash                         │
│              (Natural Language Conversion)                  │
│                         │                                   │
│                         └──> Save to .pkl                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Qdrant Vector Store                      │
│              (Collection: informasi-umum-itb)               │
└─────────────────────────────────────────────────────────────┘
```

---

## Cache Strategy

### Why Pickle?

1. **Persist LLM results** - Don't pay for duplicate Gemini calls
2. **Re-embed anytime** - Load cached documents and re-upload to Qdrant
3. **Debug/inspect** - View natural language outputs before embedding
4. **Incremental updates** - Re-parse specific sheets without redoing all

### Cache File Structure

```
cache/
├── xlsx_admission_program_studi_s1.pkl          # Sheet documents
├── xlsx_admission_jadwal_pendaftaran_s2.pkl     # Sheet documents
├── xlsx_admission_biaya_pendidikan_s1.pkl       # Sheet documents
├── ...
└── xlsx_admission_metadata.json                 # Global metadata
```

### Cache File Format

Each `.pkl` file contains:
```python
{
    "sheet_name": "Program Studi S1",
    "parser_class": "ProgramListParser",
    "timestamp": "2026-01-18T10:30:00",
    "documents": [
        {
            "content": "Program Studi Teknik Informatika...",
            "metadata": {...}
        },
        ...
    ]
}
```

---

## Implementation Steps

### Step 0: Add cache/ to .gitignore

**File:** `.gitignore`

Add the cache directory to prevent committing LLM response pickle files:

```gitignore
# LLM response cache (pickle files)
cache/
```

### Step 1: Install Dependencies

```bash
uv add langchain-google-genai google-generativeai
```

### Step 2: Create Cache Manager

**File:** `scripts/parsers/xlsx_parser.py`

```python
import pickle
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import json

class LLMCache:
    """Cache manager for LLM-generated results using pickle."""

    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.cache_dir / "xlsx_admission_metadata.json"

    def _get_cache_key(self, sheet_name: str) -> str:
        """Generate cache filename from sheet name."""
        # Clean sheet name for filename
        clean_name = sheet_name.strip().lower()
        clean_name = clean_name.replace(" ", "_").replace("/", "_")
        clean_name = "".join(c for c in clean_name if c.isalnum() or c in "_-")
        return f"xlsx_admission_{clean_name}.pkl"

    def get(self, sheet_name: str) -> Optional[Dict[str, Any]]:
        """Load cached documents for a sheet."""
        cache_key = self._get_cache_key(sheet_name)
        cache_file = self.cache_dir / cache_key

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "rb") as f:
                data = pickle.load(f)
            print(f"  [CACHE HIT] Loaded {len(data['documents'])} documents from cache")
            return data
        except Exception as e:
            print(f"  [CACHE ERROR] Failed to load cache: {e}")
            return None

    def set(self, sheet_name: str, documents: List["ITBDocument"], parser_class: str):
        """Save documents to cache."""
        cache_key = self._get_cache_key(sheet_name)
        cache_file = self.cache_dir / cache_key

        data = {
            "sheet_name": sheet_name,
            "parser_class": parser_class,
            "timestamp": datetime.now().isoformat(),
            "documents": [
                {"content": doc.content, "metadata": doc.metadata}
                for doc in documents
            ]
        }

        try:
            with open(cache_file, "wb") as f:
                pickle.dump(data, f)
            print(f"  [CACHE SAVE] Saved {len(documents)} documents to {cache_key}")
        except Exception as e:
            print(f"  [CACHE ERROR] Failed to save cache: {e}")

    def clear(self, sheet_name: Optional[str] = None):
        """Clear cache for specific sheet or all sheets."""
        if sheet_name:
            cache_key = self._get_cache_key(sheet_name)
            cache_file = self.cache_dir / cache_key
            if cache_file.exists():
                cache_file.unlink()
                print(f"  [CACHE CLEAR] Cleared cache for: {sheet_name}")
        else:
            # Clear all xlsx_admission cache files
            for cache_file in self.cache_dir.glob("xlsx_admission_*.pkl"):
                cache_file.unlink()
                print(f"  [CACHE CLEAR] Deleted: {cache_file.name}")

    def list_cached(self) -> List[str]:
        """List all cached sheet names."""
        cached = []
        for cache_file in self.cache_dir.glob("xlsx_admission_*.pkl"):
            try:
                with open(cache_file, "rb") as f:
                    data = pickle.load(f)
                cached.append(data["sheet_name"])
            except Exception:
                pass
        return cached

    def load_all_cached(self) -> List[Dict[str, Any]]:
        """Load all cached documents (for re-embedding)."""
        all_docs = []
        for cache_file in self.cache_dir.glob("xlsx_admission_*.pkl"):
            try:
                with open(cache_file, "rb") as f:
                    data = pickle.load(f)
                all_docs.extend(data["documents"])
            except Exception as e:
                print(f"  [CACHE ERROR] Failed to load {cache_file.name}: {e}")
        return all_docs
```

### Step 3: Create Base Parser

**File:** `scripts/parsers/xlsx_parser.py`

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

@dataclass
class ITBDocument:
    """Base class for all ITB information documents."""
    content: str           # Natural language description
    metadata: Dict[str, Any]  # Structured metadata

class BaseSheetParser(ABC):
    """Abstract base parser for different sheet types."""

    def __init__(
        self,
        sheet_name: str,
        df: pd.DataFrame,
        llm: ChatGoogleGenerativeAI,
        cache: Optional["LLMCache"] = None
    ):
        self.sheet_name = sheet_name
        self.df = df
        self.llm = llm
        self.cache = cache

    @abstractmethod
    def parse(self) -> List[ITBDocument]:
        """Parse sheet and return list of documents."""
        pass

    def _convert_with_gemini(self, data: Dict, prompt_template: str) -> str:
        """Use Gemini to convert structured data to natural language."""
        prompt = prompt_template.format(**data)
        response = self.llm.invoke([HumanMessage(content=prompt)])
        return response.content.strip()
```

### Step 4: Parser Strategies

```python
class ProgramListParser(BaseSheetParser):
    """Parser for program lists (S1, S2, S3, Keinsinyuran)."""

    def parse(self) -> List[ITBDocument]:
        # Clean header
        df = self.df.iloc[1:].reset_index(drop=True)
        documents = []

        for _, row in df.iterrows():
            if row.isna().all():
                continue

            data = self._extract_program_data(row)
            nl_content = self._convert_to_natural_language(data)

            documents.append(ITBDocument(
                content=nl_content,
                metadata={
                    "source": f"Informasi Umum ITB - {self.sheet_name}",
                    "type": "program_list",
                    **data
                }
            ))

        return documents

    def _convert_to_natural_language(self, data: Dict) -> str:
        prompt = """Convert this ITB study program data to natural Indonesian.

Data: {data}

Output a clear, informative sentence in formal Indonesian."""
        return self._convert_with_gemini(data, prompt)


class ScheduleParser(BaseSheetParser):
    """Parser for schedule/registration dates."""

    def parse(self) -> List[ITBDocument]:
        # Parse as table (usually header + date rows)
        # Convert to natural language timeline
        pass


class FeeParser(BaseSheetParser):
    """Parser for tuition/fee information."""

    def parse(self) -> List[ITBDocument]:
        # Parse fee structure
        # Convert to readable format
        pass


class SimpleInfoParser(BaseSheetParser):
    """Parser for simple reference information."""

    def parse(self) -> List[ITBDocument]:
        # Just convert table to natural language
        pass
```

### Step 5: Factory Pattern

```python
class SheetParserFactory:
    """Factory to create appropriate parser for each sheet type."""

    # Sheet categorization (normalized names - stripped of trailing spaces)
    _RAW_SHEET_CATEGORIES = {
        # Program lists
        "Program Studi Magister dan Pasc": "program_list",
        "International Magister and Doct": "program_list",
        "Program Studi Program Keinsinyu": "program_list",
        "Program Studi S1": "program_list",

        # Schedules
        "Magister and Doctoral Registrat": "schedule",
        "Jadwal Pendaftaran Magister S2": "schedule",
        "ITB Student Exchange Schedule": "schedule",
        "Jadwal Keinsinyuran": "schedule",
        "Jadwal Pendaftaran Program Prof": "schedule",
        "Jadwal Pelaksanaan Program Non": "schedule",
        "Jadwal Pelaksanaan MBKM ITB-UNP": "schedule",
        "Jadwal Kegiatan SNBP": "schedule",
        "Jadwal Kegiatan SNBT": "schedule",
        "Jadwal Kegiatan SM ITB": "schedule",
        "ITB IUP Program Sched": "schedule",

        # Fees
        "Student Exchange Tuition Fee": "fee",
        "ITB Virtual Course Tuition Fee": "fee",
        "Biaya Pendidikan S1 SNBT dan SN": "fee",
        "IUP Fee Component": "fee",

        # Other
        "ITB Summer Course Programs": "course_list",
        "Program Beasiswa": "scholarship",
        "Daya Tampung SNBP Peminatan": "capacity",
        "Daya Tampung S1 ITB": "capacity",
    }

    PARSER_CLASSES = {
        "program_list": ProgramListParser,
        "schedule": ScheduleParser,
        "fee": FeeParser,
        "simple": SimpleInfoParser,
    }

    @classmethod
    def create(
        cls,
        sheet_name: str,
        df: pd.DataFrame,
        llm,
        cache: Optional["LLMCache"] = None
    ) -> BaseSheetParser:
        """Create appropriate parser for the sheet."""
        normalized_name = sheet_name.strip()
        category = cls.SHEET_CATEGORIES.get(normalized_name, "simple")
        parser_class = cls.PARSER_CLASSES.get(category, SimpleInfoParser)
        return parser_class(sheet_name, df, llm, cache=cache)
```

### Step 6: Main Excel Parser

```python
class ITBExcelParser:
    """Main parser for ITB information Excel file."""

    ALL_SHEETS = [
        'Program Studi Magister dan Pasc',
        'International Magister and Doct',
        'Magister and Doctoral Registrat',
        'ITB Student Exchange Schedule',
        'Student Exchange Tuition Fee',
        'Jadwal Keinsinyuran ',
        'Program Studi Program Keinsinyu',
        'Jadwal Pendaftaran Program Prof',
        'Jadwal Pelaksanaan Program Non ',
        'Jadwal Pelaksanaan MBKM ITB-UNP',
        'ITB Summer Course Programs',
        'ITB Virtual Course Tuition Fee',
        'Program Beasiswa',
        'Jadwal Pendaftaran Magister S2',
        'Jadwal Kegiatan SNBP',
        'Jadwal Kegiatan SNBT',
        'Jadwal Kegiatan SM ITB',
        'Program Studi S1',
        'Biaya Pendidikan S1 SNBT dan SN',
        'Daya Tampung SNBP Peminatan',
        'Daya Tampung S1 ITB',
        'ITB IUP Program Sched',
        'IUP Fee Component',
    ]

    def __init__(
        self,
        xlsx_path: str,
        llm: Optional[ChatGoogleGenerativeAI] = None,
        sheets: Optional[List[str]] = None,
        cache_dir: str = "cache",
        use_cache: bool = True,
        force_refresh: bool = False,
    ):
        self.xlsx_path = Path(xlsx_path)
        self.llm = llm or self._default_llm()
        self.sheets = sheets or self.ALL_SHEETS
        self.all_documents: List[ITBDocument] = []
        self.cache = LLMCache(cache_dir) if use_cache else None
        self.force_refresh = force_refresh

    def _default_llm(self) -> ChatGoogleGenerativeAI:
        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            temperature=0
        )

    def parse(self) -> List[ITBDocument]:
        """Parse all sheets and return combined documents."""
        xlsx = pd.ExcelFile(self.xlsx_path)

        for sheet_name in self.sheets:
            if sheet_name not in xlsx.sheet_names:
                print(f"Warning: Sheet '{sheet_name}' not found")
                continue

            print(f"Parsing: {sheet_name}")

            # Check cache first
            if self.cache and not self.force_refresh:
                cached = self.cache.get(sheet_name)
                if cached:
                    # Convert cached dict back to ITBDocument objects
                    for doc_data in cached["documents"]:
                        self.all_documents.append(ITBDocument(
                            content=doc_data["content"],
                            metadata=doc_data["metadata"]
                        ))
                    continue

            # Parse from Excel
            df = pd.read_excel(xlsx, sheet_name=sheet_name, header=None)

            parser = SheetParserFactory.create(sheet_name, df, self.llm, self.cache)
            documents = parser.parse()

            # Save to cache
            if self.cache:
                self.cache.set(sheet_name, documents, parser.__class__.__name__)

            self.all_documents.extend(documents)
            print(f"  -> {len(documents)} documents")

        return self.all_documents

    def to_rag_documents(self) -> List[Dict[str, Any]]:
        """Convert to RAG-compatible format."""
        return [
            {
                "page_content": doc.content,
                "metadata": doc.metadata
            }
            for doc in self.all_documents
        ]
```

### Step 7: CLI Script

**File:** `scripts/parse_xlsx_admission.py`

```python
#!/usr/bin/env python3
"""Parse ITB information Excel and upload to Qdrant."""

import argparse
import os
from dotenv import load_dotenv
from scripts.parsers.xlsx_parser import ITBExcelParser, LLMCache
from scripts.parse_peraturan_pdf import upload_to_qdrant

def main():
    parser = argparse.ArgumentParser(
        description="Parse ITB information Excel file to Qdrant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Parse all sheets with caching (first run - calls LLM)
  python scripts/parse_xlsx_admission.py --upload-to-qdrant

  # Re-run using cache (no LLM calls)
  python scripts/parse_xlsx_admission.py --upload-to-qdrant

  # Force refresh (ignore cache, re-call LLM)
  python scripts/parse_xlsx_admission.py --force-refresh --upload-to-qdrant

  # Re-embed from cache (load cached .pkl files, upload to Qdrant)
  python scripts/parse_xlsx_admission.py --from-cache --upload-to-qdrant

  # Parse specific sheets only
  python scripts/parse_xlsx_admission.py \\
    --sheets "Program Studi S1" "Jadwal Pendaftaran Magister S2" \\
    --upload-to-qdrant

  # Clear cache for a specific sheet
  python scripts/parse_xlsx_admission.py --clear-cache "Program Studi S1"

  # Clear all cache
  python scripts/parse_xlsx_admission.py --clear-cache-all

  # List cached sheets
  python scripts/parse_xlsx_admission.py --list-cache
        """,
    )

    # Input options
    parser.add_argument("--xlsx-path", default="scripts/Informasi Umum ITB - Tabel.xlsx")
    parser.add_argument("--sheets", nargs="+", help="Specific sheets to parse")
    parser.add_argument("--from-cache", action="store_true",
                        help="Load documents from cache .pkl files instead of parsing XLSX")

    # Cache options
    parser.add_argument("--cache-dir", default="cache",
                        help="Directory to store cache .pkl files (default: cache)")
    parser.add_argument("--no-cache", action="store_true",
                        help="Disable caching (always call LLM)")
    parser.add_argument("--force-refresh", action="store_true",
                        help="Ignore existing cache and re-parse with LLM")
    parser.add_argument("--clear-cache", metavar="SHEET",
                        help="Clear cache for specific sheet")
    parser.add_argument("--clear-cache-all", action="store_true",
                        help="Clear all cache")
    parser.add_argument("--list-cache", action="store_true",
                        help="List all cached sheets")

    # Output options
    parser.add_argument("--upload-to-qdrant", action="store_true")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--embedding-provider", default="openai", choices=["openai", "qwen"])

    args = parser.parse_args()

    # Initialize cache
    cache = LLMCache(args.cache_dir)

    # Handle cache management commands
    if args.clear_cache_all:
        print("Clearing all cache...")
        cache.clear()
        return

    if args.clear_cache:
        print(f"Clearing cache for: {args.clear_cache}")
        cache.clear(args.clear_cache)
        return

    if args.list_cache:
        cached = cache.list_cached()
        print(f"Cached sheets ({len(cached)}):")
        for sheet in cached:
            print(f"  - {sheet}")
        return

    print("=" * 60)
    print("ITB Excel to Qdrant Parser")
    print("=" * 60)

    # Load from cache or parse
    if args.from_cache:
        print("Loading from cache...")
        rag_docs = cache.load_all_cached()
        print(f"Loaded {len(rag_docs)} documents from cache")
    else:
        # Initialize parser
        xlsx_parser = ITBExcelParser(
            xlsx_path=args.xlsx_path,
            sheets=args.sheets,
            cache_dir=args.cache_dir,
            use_cache=not args.no_cache,
            force_refresh=args.force_refresh,
        )

        # Parse
        documents = xlsx_parser.parse()
        rag_docs = xlsx_parser.to_rag_documents()

    print(f"\nTotal documents: {len(rag_docs)}")

    # Upload to Qdrant
    if args.upload_to_qdrant:
        upload_to_qdrant(rag_docs, args.batch_size, args.embedding_provider)

if __name__ == "__main__":
    main()
```

---

## Usage

```bash
# First run: Parse all 23 sheets (calls Gemini 2.0 Flash, saves to cache/)
uv run scripts/parse_xlsx_admission.py --upload-to-qdrant

# Re-run: Uses cached .pkl files (no LLM calls, much faster!)
uv run scripts/parse_xlsx_admission.py --upload-to-qdrant

# Re-embed from cache: Load .pkl files and upload to Qdrant
# (Useful if you changed Qdrant collection or embedding model)
uv run scripts/parse_xlsx_admission.py --from-cache --upload-to-qdrant

# Force refresh: Ignore cache, re-parse with LLM
uv run scripts/parse_xlsx_admission.py --force-refresh --upload-to-qdrant

# Parse specific sheets only
uv run scripts/parse_xlsx_admission.py \
  --sheets "Program Studi S1" "Jadwal Pendaftaran Magister S2" \
  --upload-to-qdrant

# List cached sheets
uv run scripts/parse_xlsx_admission.py --list-cache

# Clear cache for a specific sheet
uv run scripts/parse_xlsx_admission.py --clear-cache "Program Studi S1"

# Clear all cache
uv run scripts/parse_xlsx_admission.py --clear-cache-all

# Parse without uploading (for testing/inspection)
uv run scripts/parse_xlsx_admission.py

# Use different cache directory
uv run scripts/parse_xlsx_admission.py --cache-dir cache/xlsx_data --upload-to-qdrant
```

---

## Metadata Schema

Common metadata fields:
```python
{
    "source": "Informasi Umum ITB - {sheet_name}",
    "type": "program_list | schedule | fee | scholarship | capacity",
    "category": "magister | s1 | exchange | iup | ...",
    # ... specific fields per type
}
```

---

## File Structure

```
scripts/
├── parsers/
│   ├── __init__.py
│   ├── peraturan_parser.py       # Existing
│   └── xlsx_parser.py            # NEW (with LLMCache and parser strategies)
├── parse_peraturan_pdf.py        # Existing
└── parse_xlsx_admission.py       # NEW (CLI)

cache/                            # Created on first run
├── xlsx_admission_program_studi_s1.pkl
├── xlsx_admission_jadwal_pendaftaran_magister_s2.pkl
├── xlsx_admission_biaya_pendidikan_s1.pkl
├── ... (23 .pkl files total)
└── xlsx_admission_metadata.json
```

---

## Implementation Order

1. **Phase 0**: Add `cache/` to `.gitignore`
2. **Phase 1**: Base classes + ProgramListParser (covers ~70% of data)
3. **Phase 2**: ScheduleParser + FeeParser
4. **Phase 3**: Other specialized parsers
5. **Phase 4**: Testing + Qdrant upload

---

## Notes

- **Pickle Caching**: All LLM responses are cached to `cache/*.pkl` files automatically
  - First run: ~517 Gemini calls (~$0.10-0.50)
  - Subsequent runs: 0 Gemini calls (loads from pickle)
  - Re-embed anytime: Use `--from-cache` to load cached documents and upload to Qdrant
- **Batch processing**: Process rows individually for better granularity in cache
- **Cost savings**: With caching, you only pay for LLM calls once per unique row
- **Cache invalidation**: Use `--clear-cache` for specific sheets or `--clear-cache-all` to reset
- **Inspect cached results**: You can load .pkl files in Python to inspect the natural language outputs before embedding

---

## References

- [LangChain ChatGoogleGenerativeAI Docs](https://docs.langchain.com/oss/python/integrations/chat/google_generative_ai)
- [Gemini 2.0 Flash Documentation](https://ai.google.dev/gemini-api/docs/models/gemini)
