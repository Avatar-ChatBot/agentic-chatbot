# XLSX to Qdrant: Best Practices Analysis

**Date:** 2026-01-18
**Source File:** `scripts/Informasi Umum ITB - Tabel.xlsx`
**Target:** Qdrant Vector Database integration

---

## 1. Data Analysis

### 1.1 File Structure

The Excel file contains ITB (Institut Teknologi Bandung) master and doctoral program availability data:

| Attribute | Value |
|-----------|-------|
| **Rows** | 84 data rows (1 header row) |
| **Columns** | 9 columns |
| **Data Type** | Tabular / Structured |

### 1.2 Column Schema

| Column | Description | Sample Values | Unique Count |
|--------|-------------|---------------|--------------|
| Program Studi | Study program name | "Teknik Geologi", "Matematika" | 61 |
| Strata | Degree level | S2 (Master), S3 (Doctoral) | 2 |
| Fakultas / Sekolah | Faculty/School | FITB, FMIPA, FTI, etc. | 13 |
| Gelombang 1-6 | Available in admission wave | "Ya", "Tidak" | 2-3 per column |

### 1.3 Data Characteristics

- **High cardinality columns**: Program Studi (61 unique values)
- **Low cardinality columns**: Strata (2), Gelombang availability (2-3)
- **Reference URL**: First row contains `https://admission.itb.ac.id/info/international-master-program/`
- **Query patterns expected**: "Program S2 yang tersedia gelombang 1", "Prodi di FMIPA", etc.

---

## 2. Best Practices Research Summary

### 2.1 Tabular Data Chunking Strategies

Based on current research (2024-2025):

| Strategy | Description | Use Case |
|----------|-------------|----------|
| **Row-wise Chunking** | Each row becomes a separate chunk | **Recommended for this data** |
| Table-as-a-Chunk | Entire table as one chunk | Small tables only |
| Column-wise Chunking | Group by column values | Analytics queries |
| Cell-level Chunking | Each cell as separate chunk | Fine-grained retrieval |
| Fusion Chunking | Hybrid approach | Complex scenarios |

**Sources:**
- [RAG Chunking Techniques for Tabular Data: 10 Powerful Strategies](https://pub.towardsai.net/rag-chunking-techniques-for-tabular-data-10-powerful-strategies-aba887de331e)
- [Fusion Chunking for RAG with Tabular Data](https://medium.com/@pillai.deepakb/fusion-chunking-an-effective-approach-for-rag-applications-with-tabular-data-44dc3d855cd3)
- [Finetuning Embedding Models For Tabular RAG Applications](https://arxiv.org/html/2405.01585v1)

### 2.2 Qdrant-Specific Best Practices

| Area | Best Practice |
|------|---------------|
| **Batch Upload** | Use batches of 50-100 points for optimal performance |
| **Payload Indexing** | Create indexes for fields used in filters |
| **Metadata** | Include all filterable fields as payload |
| **IDs** | Use deterministic IDs for deduplication (upsert) |
| **Collection** | Separate collection or same with type metadata |

**Sources:**
- [Qdrant Payload Documentation](https://qdrant.tech/documentation/concepts/payload/)
- [Complete Guide to Filtering in Vector Search](https://qdrant.tech/articles/vector-search-filtering/)
- [Vector Search Production Guide](https://qdrant.tech/articles/vector-search-production/)

### 2.3 Content Formatting for Embeddings

Key recommendations:
- **Include headers with each chunk** for context preservation
- **Natural language conversion** for tabular data improves retrieval
- **Metadata enrichment** enhances filterability

**Sources:**
- [How to Handle Tables During Chunking](https://www.rohan-paul.com/p/how-to-handle-tables-during-chunking)
- [Text Chunking Strategies - Qdrant](https://qdrant.tech/course/essentials/day-1/chunking-strategies/)
- [Best Chunking Strategies for RAG in 2025](https://www.firecrawl.dev/blog/best-chunking-strategies-rag-2025)

---

## 3. Recommended Implementation Strategy

### 3.1 Chunking Approach: Row-Level with Natural Language Conversion

**Why Row-Level?**
- Each row represents a complete, queryable entity (a study program at a specific level)
- Users will likely query by "program", "faculty", or "availability in waves"
- 84 rows is manageable without excessive chunking

**Why Natural Language Conversion?**
Tabular data doesn't embed well as-is. Converting to natural language improves semantic search:

```
Original: ["Teknik Geologi", "S2", "FITB", "Ya", "Ya", "Ya", "Ya", "Ya", "Tidak"]

Converted: "Program Magister (S2) Teknik Geologi di Fakultas Ilmu dan Teknologi
Kebumian (FITB) tersedia pada pendaftaran Gelombang 1, 2, 3, 4, dan 5.
Tidak tersedia pada Gelombang 6."
```

### 3.2 Metadata Schema

```python
metadata = {
    "source": "Informasi Umum ITB - Tabel",
    "type": "program_pendaftaran",
    "program_studi": "Teknik Geologi",
    "strata": "S2",
    "fakultas": "FITB",
    "gelombang_1": "Ya",
    "gelombang_2": "Ya",
    "gelombang_3": "Ya",
    "gelombang_4": "Ya",
    "gelombang_5": "Ya",
    "gelombang_6": "Tidak",
    "gelombang_tersedia": [1, 2, 3, 4, 5],  # For easy filtering
    "reference_url": "https://admission.itb.ac.id/info/international-master-program/"
}
```

### 3.3 Qdrant Integration

Following the existing pattern in `scripts/parse_peraturan_pdf.py`:

```python
# Use existing collection: "informasi-umum-itb" (OpenAI) or "informasi-umum-itb-qwen3" (Qwen)
# Use existing embedding: OpenAI text-embedding-3-large or Qwen qwen3-embedding-8b
# Batch size: 50 (default)
```

### 3.4 Payload Indexing Recommendations

Create payload indexes for frequently filtered fields:

```python
# After uploading, create indexes for filterable fields
from qdrant_client.models import PayloadSchemaType, PayloadIndexParams

client.create_payload_index(
    collection_name="informasi-umum-itb",
    field_schema=PayloadIndexParams(
        field_name="metadata.strata",
        field_schema=PayloadSchemaType.KEYWORD
    )
)

# Repeat for: fakultas, program_studi, type
```

---

## 4. Implementation Considerations

### 4.1 Advantages of Proposed Approach

| Benefit | Explanation |
|---------|-------------|
| **Semantic Search** | Natural language conversion enables better query matching |
| **Filterable** | Metadata allows precise filtering by strata, faculty, etc. |
| **Consistent** | Follows existing pattern from PeraturanParser |
| **Queryable** | Supports both semantic and exact-match queries |
| **Scalable** | Easy to add more rows or update existing ones |

### 4.2 Alternative Approaches Considered

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| Raw CSV as single chunk | Simple | Poor retrieval for specific queries | Not recommended |
| Cell-level chunking | Granular | Too many chunks, loses context | Not recommended |
| Column-based chunking | Good for faculty-wide queries | Loses program-specific info | Not recommended |
| **Row-level with NL conversion** | Balanced | Requires preprocessing | **Recommended** |

### 4.3 Query Pattern Support

The proposed approach supports expected query patterns:

| Query Type | Example | How It's Handled |
|------------|---------|------------------|
| Program-specific | "Program S2 Teknik Geologi" | Semantic match + metadata filter |
| Faculty-wide | "Semua prodi di FMIPA" | Metadata filter on fakultas |
| Wave-specific | "Prodi yang buka gelombang 1" | Metadata filter on gelombang_1 |
| Availability | "Prodi S3 yang tersedia" | Semantic + metadata combination |

---

## 5. Implementation Plan

### 5.1 New Parser Module: `xlsx_parser.py`

Create following the pattern of `peraturan_parser.py`:

```python
# scripts/parsers/xlsx_parser.py

from dataclasses import dataclass
from typing import List, Dict, Any
import pandas as pd

@dataclass
class ProgramPendaftaran:
    """Represents a study program's admission availability."""
    content: str  # Natural language description
    program_studi: str
    strata: str
    fakultas: str
    gelombang_availability: Dict[str, str]
    reference_url: str = "https://admission.itb.ac.id/info/international-master-program/"

    def to_metadata(self) -> Dict[str, Any]:
        """Convert to metadata format for RAG pipeline."""
        available_waves = [i for i, v in self.gelombang_availability.items() if v == "Ya"]
        return {
            "source": "Informasi Umum ITB - Tabel",
            "type": "program_pendaftaran",
            "program_studi": self.program_studi,
            "strata": self.strata,
            "fakultas": self.fakultas,
            **{f"gelombang_{k}": v for k, v in self.gelombang_availability.items()},
            "gelombang_tersedia": available_waves,
            "reference_url": self.reference_url,
        }

class XLSXAdmissionParser:
    """Parse ITB admission availability Excel file."""

    def __init__(self, xlsx_path: str):
        self.xlsx_path = Path(xlsx_path)
        self.programs: List[ProgramPendaftaran] = []

    def parse(self) -> List[ProgramPendaftaran]:
        """Parse Excel and return program objects."""
        df = pd.read_excel(self.xlsx_path, header=0)

        # Set proper headers
        df.columns = df.iloc[0]
        df = df[1:].reset_index(drop=True)

        for _, row in df.iterrows():
            program = self._create_program_from_row(row)
            self.programs.append(program)

        return self.programs

    def _create_program_from_row(self, row) -> ProgramPendaftaran:
        """Create ProgramPendaftaran from DataFrame row."""
        program_studi = row["Program Studi"]
        strata = row["Strata"]
        fakultas = row["Fakultas / Sekolah"]

        # Build availability dict
        gelombang = {}
        for i in range(1, 7):
            col = f"Tersedia pada Pendaftaran Gelombang {i}"
            gelombang[str(i)] = row[col]

        # Build natural language content
        content = self._build_natural_language(
            program_studi, strata, fakultas, gelombang
        )

        return ProgramPendaftaran(
            content=content,
            program_studi=program_studi,
            strata=strata,
            fakultas=fakultas,
            gelombang_availability=gelombang,
        )

    def _build_natural_language(
        self, program: str, strata: str, fakultas: str, gelombang: Dict[str, str]
    ) -> str:
        """Build natural language description from row data."""
        strata_full = "Magister (S2)" if strata == "S2" else "Doktor (S3)"

        available = [int(k) for k, v in gelombang.items() if v == "Ya"]
        not_available = [int(k) for k, v in gelombang.items() if v == "Tidak"]

        parts = [
            f"Program {strata_full} {program} di {fakultas}",
        ]

        if available:
            if len(available) == 6:
                parts.append("tersedia pada semua gelombang pendaftaran.")
            elif len(available) == len(not_available):
                wave_list = ", ".join(map(str, sorted(available)))
                parts.append(f"tersedia pada Gelombang {wave_list}.")
            else:
                wave_list = self._format_wave_list(available)
                parts.append(f"tersedia pada pendaftaran {wave_list}.")

        return " ".join(parts)

    def _format_wave_list(self, waves: List[int]) -> str:
        """Format wave list as natural language."""
        if not waves:
            return ""
        waves = sorted(waves)
        if len(waves) == 1:
            return f"Gelombang {waves[0]}"
        elif len(waves) == 2:
            return f"Gelombang {waves[0]} dan {waves[1]}"
        else:
            all_but_last = ", ".join(f"Gelombang {w}" for w in waves[:-1])
            return f"{all_but_last}, dan Gelombang {waves[-1]}"

    def to_rag_documents(self) -> List[Dict[str, Any]]:
        """Convert to RAG-compatible format."""
        return [
            {
                "page_content": prog.content,
                "metadata": prog.to_metadata(),
            }
            for prog in self.programs
        ]
```

### 5.2 Integration Steps

1. **Create the parser module** at `scripts/parsers/xlsx_parser.py`
2. **Create a CLI script** similar to `parse_peraturan_pdf.py`
3. **Test with Qdrant upload** using existing infrastructure
4. **Verify retrieval** with sample queries

---

## 6. References

### Primary Sources
- [Qdrant Official Documentation](https://qdrant.tech/documentation/)
- [LangChain Qdrant Integration](https://docs.langchain.com/oss/python/integrations/vectorstores/qdrant)
- [RAG Chunking Techniques for Tabular Data](https://pub.towardsai.net/rag-chunking-techniques-for-tabular-data-10-powerful-strategies-aba887de331e)
- [Fusion Chunking for Tabular Data](https://medium.com/@pillai.deepakb/fusion-chunking-an-effective-approach-for-rag-applications-with-tabular-data-44dc3d855cd3)
- [How to Handle Tables During Chunking](https://www.rohan-paul.com/p/how-to-handle-tables-during-chunking)
- [Qdrant Text Chunking Strategies](https://qdrant.tech/course/essentials/day-1/chunking-strategies/)
- [Vector Search Production Guide](https://qdrant.tech/articles/vector-search-production/)
- [Best Chunking Strategies for RAG in 2025](https://www.firecrawl.dev/blog/best-chunking-strategies-rag-2025)

### Academic Papers
- [Finetuning Embedding Models For Tabular RAG Applications](https://arxiv.org/html/2405.01585v1) (April 2024)
- [TableRAG: A Retrieval Augmented Generation Framework](https://aclanthology.org/2025.emnlp-main.710.pdf) (2025)

---

## 7. Summary

**Recommended approach:** Row-level chunking with natural language conversion

**Key reasons:**
1. Presures complete information per study program
2. Enables semantic search with metadata filtering
3. Follows existing project patterns
4. Scales well for additional data

**Next steps:**
1. Implement `xlsx_parser.py` following the `peraturan_parser.py` pattern
2. Create CLI tool for parsing and uploading
3. Test retrieval with sample queries
4. Consider adding payload indexes for common filters
