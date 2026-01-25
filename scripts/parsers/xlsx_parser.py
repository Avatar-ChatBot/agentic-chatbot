"""
Parser for ITB information Excel files using OpenRouter Qwen3-8B for natural language conversion.

This module provides:
- LLMCache: Pickle-based caching for LLM responses
- ITBDocument: Base document class
- BaseSheetParser: Abstract parser for different sheet types
- Concrete parsers: ProgramListParser, ScheduleParser, FeeParser, SimpleInfoParser
- SheetParserFactory: Factory pattern for parser selection
- ITBExcelParser: Main parser orchestrator
"""

from __future__ import annotations

import os
import pickle
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import pandas as pd
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

if TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass
class ITBDocument:
    """Base class for all ITB information documents."""

    content: str  # Natural language description
    metadata: dict[str, Any] = field(default_factory=dict)  # Structured metadata


class LLMCache:
    """Cache manager for LLM-generated results using pickle."""

    def __init__(self, cache_dir: str = "cache") -> None:
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

    def get(self, sheet_name: str) -> Optional[dict[str, Any]]:
        """Load cached documents for a sheet."""
        cache_key = self._get_cache_key(sheet_name)
        cache_file = self.cache_dir / cache_key

        if not cache_file.exists():
            return None

        try:
            with cache_file.open("rb") as f:
                data: dict[str, Any] = pickle.load(f)
            doc_count = len(data.get("documents", []))
            print(f"  [CACHE HIT] Loaded {doc_count} documents from cache")
            return data
        except Exception as e:
            print(f"  [CACHE ERROR] Failed to load cache: {e}")
            return None

    def set(
        self, sheet_name: str, documents: list[ITBDocument], parser_class: str
    ) -> None:
        """Save documents to cache."""
        cache_key = self._get_cache_key(sheet_name)
        cache_file = self.cache_dir / cache_key

        data: dict[str, Any] = {
            "sheet_name": sheet_name,
            "parser_class": parser_class,
            "timestamp": datetime.now().isoformat(),
            "documents": [
                {"content": doc.content, "metadata": doc.metadata} for doc in documents
            ],
        }

        try:
            with cache_file.open("wb") as f:
                pickle.dump(data, f)
            print(f"  [CACHE SAVE] Saved {len(documents)} documents to {cache_key}")
        except Exception as e:
            print(f"  [CACHE ERROR] Failed to save cache: {e}")

    def clear(self, sheet_name: Optional[str] = None) -> None:
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

    def list_cached(self) -> list[str]:
        """List all cached sheet names."""
        cached: list[str] = []
        for cache_file in self.cache_dir.glob("xlsx_admission_*.pkl"):
            try:
                with cache_file.open("rb") as f:
                    data: dict[str, Any] = pickle.load(f)
                sheet_name: str = data["sheet_name"]
                cached.append(sheet_name)
            except Exception:
                pass
        return cached

    def load_all_cached(self) -> list[dict[str, Any]]:
        """Load all cached documents (for re-embedding)."""
        all_docs: list[dict[str, Any]] = []
        for cache_file in self.cache_dir.glob("xlsx_admission_*.pkl"):
            try:
                with cache_file.open("rb") as f:
                    data: dict[str, Any] = pickle.load(f)
                docs: list[dict[str, Any]] = data.get("documents", [])
                all_docs.extend(docs)
            except Exception as e:
                print(f"  [CACHE ERROR] Failed to load {cache_file.name}: {e}")
        return all_docs


class BaseSheetParser(ABC):
    """Abstract base parser for different sheet types."""

    def __init__(
        self,
        sheet_name: str,
        df: pd.DataFrame,
        llm: ChatOpenAI,
        cache: Optional[LLMCache] = None,
    ) -> None:
        self.sheet_name = sheet_name
        self.df = df
        self.llm = llm
        self.cache = cache

    @abstractmethod
    def parse(self) -> list[ITBDocument]:
        """Parse sheet and return list of documents."""
        pass

    def _convert_with_llm(self, data: Mapping[str, Any], prompt_template: str) -> str:
        """Use LLM to convert structured data to natural language."""
        prompt = prompt_template.format(data=data)
        response = self.llm.invoke([HumanMessage(content=prompt)])
        return str(response.content).strip()


class ProgramListParser(BaseSheetParser):
    """Parser for program lists (S1, S2, S3, Keinsinyuran)."""

    def parse(self) -> list[ITBDocument]:
        """Parse program list sheet row by row."""
        # Skip reference row (row 0) and header row (row 1)
        df = (
            self.df.iloc[2:].reset_index(drop=True)
            if len(self.df) > 2
            else pd.DataFrame()
        )
        documents: list[ITBDocument] = []

        for _, row in df.iterrows():
            if row.isna().all():
                continue

            data = self._extract_program_data(row)
            if not data or not data.get("program"):
                continue

            nl_content = self._convert_to_natural_language(data)

            documents.append(
                ITBDocument(
                    content=nl_content,
                    metadata={
                        "source": f"Informasi Umum ITB - {self.sheet_name}",
                        "type": "program_list",
                        **{k: v for k, v in data.items() if v},
                    },
                )
            )

        return documents

    def _extract_program_data(self, row: pd.Series) -> dict[str, Any]:
        """Extract program data from a row."""
        data: dict[str, Any] = {}
        non_null_values: list[tuple[str, str]] = []

        # Collect all non-null values with their column info
        for idx, col in enumerate(row.index):
            val = row.iloc[idx]
            if pd.notna(val) and str(val).strip():
                val_str = str(val).strip()
                # Clean column names
                col_lower = str(col).lower()
                col_name = str(col) if not col_lower.isdigit() else f"col_{idx}"

                if (
                    "prodi" in col_lower
                    or "program" in col_lower
                    or "study" in col_lower
                ):
                    data["program"] = val_str
                elif "fakultas" in col_lower or "faculty" in col_lower:
                    data["fakultas"] = val_str
                elif "kode" in col_lower or "code" in col_lower:
                    data["kode"] = val_str
                elif (
                    "akreditasi" in col_lower
                    or "akredit" in col_lower
                    or "accredit" in col_lower
                ):
                    data["akreditasi"] = val_str
                else:
                    # Store all non-null values
                    data[col_name] = val_str
                    non_null_values.append((col_name, val_str))

        # If no "program" field was found, use the first non-null value as the program name
        if "program" not in data and non_null_values:
            # Use the first column's value as the program name
            first_col, first_val = non_null_values[0]
            data["program"] = first_val
            # Remove it from the dict to avoid duplication
            if first_col in data and first_col != "program":
                del data[first_col]

        return data

    def _convert_to_natural_language(self, data: Mapping[str, Any]) -> str:
        """Convert program data to natural Indonesian using Gemini."""
        prompt = """Convert this ITB study program data to natural Indonesian.
Make it informative and clear for prospective students.

Data: {data}

Output a clear, informative paragraph in formal Indonesian. Focus on what the program is about and key details."""

        return self._convert_with_llm(data, prompt)


class ScheduleParser(BaseSheetParser):
    """Parser for schedule/registration dates."""

    def parse(self) -> list[ITBDocument]:
        """Parse schedule sheet and convert to timeline format."""
        documents: list[ITBDocument] = []

        # Try to detect headers
        df = self.df.copy()
        df = df.dropna(how="all")

        if len(df) < 2:
            return documents

        # First non-empty row is likely the header
        header_row = None
        for idx, row in df.iterrows():
            if not row.isna().all():
                header_row = idx
                break

        if header_row is None:
            return documents

        headers = df.iloc[header_row].fillna("").tolist()
        data_df = df.iloc[header_row + 1 :].reset_index(drop=True)

        # Group rows into logical events
        for _, row in data_df.iterrows():
            if row.isna().all():
                continue

            event_data = self._extract_event_data(row, headers)
            if event_data:
                nl_content = self._convert_event_to_natural_language(event_data)
                documents.append(
                    ITBDocument(
                        content=nl_content,
                        metadata={
                            "source": f"Informasi Umum ITB - {self.sheet_name}",
                            "type": "schedule",
                            **{k: v for k, v in event_data.items() if v},
                        },
                    )
                )

        return documents

    def _extract_event_data(self, row: pd.Series, headers: list[Any]) -> dict[str, Any]:
        """Extract event data from a row."""
        data: dict[str, Any] = {}
        for idx, val in enumerate(row):
            if pd.notna(val) and idx < len(headers):
                col_name = str(headers[idx]).strip().lower()
                val_str = str(val).strip()
                if col_name:
                    data[col_name] = val_str
        return data

    def _convert_event_to_natural_language(self, data: Mapping[str, Any]) -> str:
        """Convert event data to natural Indonesian."""
        prompt = """Convert this ITB admission schedule information to natural Indonesian.
Make it clear when each event occurs.

Data: {data}

Output a clear, informative paragraph in formal Indonesian about the schedule."""

        return self._convert_with_llm(data, prompt)


class FeeParser(BaseSheetParser):
    """Parser for tuition/fee information."""

    def parse(self) -> list[ITBDocument]:
        """Parse fee sheet and convert to readable format."""
        documents: list[ITBDocument] = []

        df = self.df.copy()
        df = df.dropna(how="all")

        if len(df) < 2:
            return documents

        # Find header row
        header_row = None
        for idx, row in df.iterrows():
            if not row.isna().all():
                header_row = idx
                break

        if header_row is None:
            return documents

        headers = df.iloc[header_row].fillna("").tolist()
        data_df = df.iloc[header_row + 1 :].reset_index(drop=True)

        for _, row in data_df.iterrows():
            if row.isna().all():
                continue

            fee_data = self._extract_fee_data(row, headers)
            if fee_data:
                nl_content = self._convert_fee_to_natural_language(fee_data)
                documents.append(
                    ITBDocument(
                        content=nl_content,
                        metadata={
                            "source": f"Informasi Umum ITB - {self.sheet_name}",
                            "type": "fee",
                            **{k: v for k, v in fee_data.items() if v},
                        },
                    )
                )

        return documents

    def _extract_fee_data(self, row: pd.Series, headers: list[Any]) -> dict[str, Any]:
        """Extract fee data from a row."""
        data: dict[str, Any] = {}
        for idx, val in enumerate(row):
            if pd.notna(val) and idx < len(headers):
                col_name = str(headers[idx]).strip().lower()
                val_str = str(val).strip()
                if col_name:
                    data[col_name] = val_str
        return data

    def _convert_fee_to_natural_language(self, data: Mapping[str, Any]) -> str:
        """Convert fee data to natural Indonesian."""
        prompt = """Convert this ITB tuition fee information to natural Indonesian.
Make it clear what the fees are for and the amounts.

Data: {data}

Output a clear, informative paragraph in formal Indonesian about the fees."""

        return self._convert_with_llm(data, prompt)


class SimpleInfoParser(BaseSheetParser):
    """Parser for simple reference information."""

    def parse(self) -> list[ITBDocument]:
        """Parse simple info sheet and convert to natural language."""
        documents: list[ITBDocument] = []

        df = self.df.copy()
        df = df.dropna(how="all")

        # Convert entire sheet to natural language
        # Create a summary document
        summary_data = self._summarize_sheet(df)
        if summary_data:
            nl_content = self._convert_summary_to_natural_language(summary_data)
            documents.append(
                ITBDocument(
                    content=nl_content,
                    metadata={
                        "source": f"Informasi Umum ITB - {self.sheet_name}",
                        "type": "simple_info",
                        "row_count": len(df),
                    },
                )
            )

        # Also process individual rows for granularity
        for idx, row in df.iterrows():
            if row.isna().all():
                continue

            row_data = self._extract_row_data(row)
            if row_data and len(row_data) > 0:
                nl_content = self._convert_row_to_natural_language(row_data)
                documents.append(
                    ITBDocument(
                        content=nl_content,
                        metadata={
                            "source": f"Informasi Umum ITB - {self.sheet_name}",
                            "type": "simple_info",
                            "row": idx,
                            **{k: v for k, v in row_data.items() if v},
                        },
                    )
                )

        return documents

    def _summarize_sheet(self, df: pd.DataFrame) -> dict[str, Any]:
        """Create a summary of the sheet."""
        return {
            "sheet_name": self.sheet_name,
            "total_rows": len(df),
            "columns": list(df.columns)[:10],  # Limit columns
        }

    def _extract_row_data(self, row: pd.Series) -> dict[str, Any]:
        """Extract data from a single row."""
        data: dict[str, Any] = {}
        for idx, val in enumerate(row):
            if pd.notna(val):
                col_name = (
                    f"col_{idx}"
                    if not isinstance(row.index[idx], str)
                    else str(row.index[idx])
                )
                data[col_name] = str(val).strip()
        return data

    def _convert_summary_to_natural_language(self, data: Mapping[str, Any]) -> str:
        """Convert summary to natural Indonesian."""
        prompt = """Provide a brief summary of this ITB information sheet in Indonesian.
Focus on what kind of information this sheet contains.

Data: {data}

Output: A concise 1-2 sentence summary in Indonesian."""

        return self._convert_with_llm(data, prompt)

    def _convert_row_to_natural_language(self, data: Mapping[str, Any]) -> str:
        """Convert row data to natural Indonesian."""
        prompt = """Convert this ITB information to natural Indonesian.
Make it clear and readable.

Data: {data}

Output: A clear, informative sentence in Indonesian."""

        return self._convert_with_llm(data, prompt)


class SheetParserFactory:
    """Factory to create appropriate parser for each sheet type."""

    # Sheet categorization (normalized names - stripped of trailing spaces)
    _RAW_SHEET_CATEGORIES: dict[str, str] = {
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
        "ITB Summer Course Programs": "simple",
        "Program Beasiswa": "simple",
        "Daya Tampung SNBP Peminatan": "simple",
        "Daya Tampung S1 ITB": "simple",
    }

    PARSER_CLASSES: dict[str, type[BaseSheetParser]] = {
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
        llm: ChatOpenAI,
        cache: Optional[LLMCache] = None,
    ) -> BaseSheetParser:
        """Create appropriate parser for the sheet."""
        normalized_name = sheet_name.strip()

        # Try direct match first
        category = cls._RAW_SHEET_CATEGORIES.get(normalized_name)

        # Try partial match if direct fails
        if not category:
            for key, value in cls._RAW_SHEET_CATEGORIES.items():
                if key.strip() in normalized_name or normalized_name in key.strip():
                    category = value
                    break

        if not category:
            category = "simple"

        parser_class = cls.PARSER_CLASSES.get(category, SimpleInfoParser)
        return parser_class(sheet_name, df, llm, cache=cache)

    @classmethod
    def get_sheet_category(cls, sheet_name: str) -> str:
        """Get the category for a sheet name."""
        normalized_name = sheet_name.strip()
        category = cls._RAW_SHEET_CATEGORIES.get(normalized_name)

        if not category:
            for key, value in cls._RAW_SHEET_CATEGORIES.items():
                if key.strip() in normalized_name or normalized_name in key.strip():
                    return value
            return "simple"

        return category


class ITBExcelParser:
    """Main parser for ITB information Excel file."""

    ALL_SHEETS = [
        "Program Studi Magister dan Pasc",
        "International Magister and Doct",
        "Magister and Doctoral Registrat",
        "ITB Student Exchange Schedule",
        "Student Exchange Tuition Fee",
        "Jadwal Keinsinyuran ",
        "Program Studi Program Keinsinyu",
        "Jadwal Pendaftaran Program Prof",
        "Jadwal Pelaksanaan Program Non ",
        "Jadwal Pelaksanaan MBKM ITB-UNP",
        "ITB Summer Course Programs",
        "ITB Virtual Course Tuition Fee",
        "Program Beasiswa",
        "Jadwal Pendaftaran Magister S2",
        "Jadwal Kegiatan SNBP",
        "Jadwal Kegiatan SNBT",
        "Jadwal Kegiatan SM ITB",
        "Program Studi S1",
        "Biaya Pendidikan S1 SNBT dan SN",
        "Daya Tampung SNBP Peminatan",
        "Daya Tampung S1 ITB",
        "ITB IUP Program Sched",
        "IUP Fee Component",
    ]

    def __init__(
        self,
        xlsx_path: str,
        llm: Optional[ChatOpenAI] = None,
        sheets: Optional[list[str]] = None,
        cache_dir: str = "cache",
        use_cache: bool = True,
        force_refresh: bool = False,
    ) -> None:
        self.xlsx_path = Path(xlsx_path)
        self.llm = llm or self._default_llm()
        self.sheets = sheets or self.ALL_SHEETS
        self.all_documents: list[ITBDocument] = []
        self.cache = LLMCache(cache_dir) if use_cache else None
        self.force_refresh = force_refresh

    def _default_llm(self) -> ChatOpenAI:
        """Create default LLM instance using OpenRouter."""
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required")

        return ChatOpenAI(
            model="qwen/qwen3-8b",
            temperature=0,
            openai_api_key=openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": os.getenv("SITE_URL", "https://your-site.com"),
                "X-Title": os.getenv("APP_NAME", "ITB Chatbot"),
            },
            timeout=60,
        )

    def parse(self) -> list[ITBDocument]:
        """Parse all sheets and return combined documents."""
        xlsx = pd.ExcelFile(self.xlsx_path)
        print(f"Configured sheets to process: {self.sheets}")

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
                    for doc_data in cached.get("documents", []):
                        self.all_documents.append(
                            ITBDocument(
                                content=doc_data["content"],
                                metadata=doc_data["metadata"],
                            )
                        )
                    continue

            # Parse from Excel
            df = pd.read_excel(self.xlsx_path, sheet_name=sheet_name, header=None)

            parser = SheetParserFactory.create(sheet_name, df, self.llm, self.cache)
            documents = parser.parse()

            # Save to cache
            if self.cache:
                self.cache.set(sheet_name, documents, parser.__class__.__name__)

            self.all_documents.extend(documents)
            print(f"  -> {len(documents)} documents")

        return self.all_documents

    def to_rag_documents(self) -> list[dict[str, Any]]:
        """Convert to RAG-compatible format."""
        return [
            {
                "page_content": doc.content,
                "metadata": doc.metadata,
            }
            for doc in self.all_documents
        ]

    def get_summary(self) -> dict[str, Any]:
        """Get summary of parsed documents."""
        type_counts: dict[str, int] = {}
        for doc in self.all_documents:
            doc_type = doc.metadata.get("type", "unknown")
            type_counts[doc_type] = type_counts.get(doc_type, 0) + 1

        return {
            "total_documents": len(self.all_documents),
            "source": str(self.xlsx_path),
            "sheets_processed": len(self.sheets),
            "type_distribution": type_counts,
        }
