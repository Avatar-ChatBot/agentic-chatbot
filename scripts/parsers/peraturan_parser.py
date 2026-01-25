"""
Parser for Indonesian legal documents (Peraturan Perundang-undangan).

This module extracts structured Pasal objects from PDF documents of Indonesian
legislation, following the format defined in UU No. 12 Tahun 2011.

Document structure:
    BAB (Chapter) - Roman numeral
    ├── Bagian (Part) - Optional
    ├── Paragraf (Paragraph) - Optional
    └── Pasal (Article) - Number
        ├── Pasal Title (Optional)
        └── Ayat (Clause) - Numbered (1), (2), (3)...
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple


@dataclass
class Pasal:
    """Represents a single Pasal (Article) from Indonesian legal document."""

    content: str  # Full text of all ayat within this pasal
    pasal: int  # Article number (e.g., 1, 15, 100)
    pasal_title: Optional[str] = None  # Optional title (e.g., "Ruang Lingkup")
    bab: str = ""  # Roman numeral (e.g., "I", "II", "III")
    bab_title: str = ""  # Chapter title (e.g., "KETENTUAN UMUM")
    source: str = ""  # Document name/filename

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "content": self.content,
            "pasal": self.pasal,
            "pasal_title": self.pasal_title,
            "bab": self.bab,
            "bab_title": self.bab_title,
            "source": self.source,
        }

    def to_metadata(self) -> Dict[str, Any]:
        """Convert to metadata format for RAG pipeline."""
        return {
            "pasal": self.pasal,
            "pasal_title": self.pasal_title,
            "bab": self.bab,
            "bab_title": self.bab_title,
            "source": self.source,
        }


class PeraturanParser:
    """
    Parse Indonesian legal documents (peraturan perundang-undangan).

    Supports PDF and plain text input. Extracts BAB (chapters), Pasal (articles),
    and Ayat (clauses) into structured Pasal objects.
    """

    # Regex patterns for document structure
    BAB_PATTERN = re.compile(
        r"^BAB\s+(?P<roman>[IVXLCDM]+)\s+(?P<title>[^\n\r]+)",
        re.MULTILINE | re.IGNORECASE
    )

    PASAL_PATTERN = re.compile(
        r"^Pasal\s+(?P<number>\d+)",
        re.MULTILINE | re.IGNORECASE
    )

    AYAT_PATTERN = re.compile(
        r"^\((?P<number>\d+)\)\s*(?P<content>[^\n]+)",
        re.MULTILINE
    )

    BAGIAN_PATTERN = re.compile(
        r"^Bagian\s+(?P<ordinal>Kesatu|Kedua|Ketiga|Keempat|Kelima|Keenam|Ketujuh|Kedelapan|Kesembilan|Kesepuluh|[IVXLCDM]+)",
        re.MULTILINE | re.IGNORECASE
    )

    PARAGRAF_PATTERN = re.compile(
        r"^Paragraf\s+(?P<number>\d+)",
        re.MULTILINE | re.IGNORECASE
    )

    HURUF_PATTERN = re.compile(
        r"^[a-z]\)\s*",
        re.MULTILINE
    )

    PENJELASAN_PATTERN = re.compile(
        r"^PENJELASAN\s+",
        re.MULTILINE | re.IGNORECASE
    )

    def __init__(self, source_path: str, source_name: Optional[str] = None):
        """
        Initialize parser.

        Args:
            source_path: Path to PDF or text file
            source_name: Optional source name (defaults to filename)
        """
        self.source_path = Path(source_path)
        self.source_name = source_name or self.source_path.stem
        self.raw_text: str = ""
        self.babs: List[Dict[str, Any]] = []
        self.pasals: List[Pasal] = []

    def parse(self, text: Optional[str] = None) -> List[Pasal]:
        """
        Parse document and return list of Pasal objects.

        Args:
            text: Optional pre-extracted text. If not provided, will attempt
                  to read from source_path.

        Returns:
            List of Pasal objects extracted from the document.
        """
        if text:
            self.raw_text = text
        else:
            self.raw_text = self._read_file()

        # Preprocess text
        cleaned_text = self._preprocess_text(self.raw_text)

        # Remove Penjelasan section if present
        cleaned_text = self._remove_penjelasan(cleaned_text)

        # Parse BAB structure
        self.babs = self._parse_babs(cleaned_text)

        # Parse Pasal within each BAB
        self.pasals = self._parse_pasals(cleaned_text)

        return self.pasals

    def _read_file(self) -> str:
        """Read text from file based on extension."""
        suffix = self.source_path.suffix.lower()

        if suffix == ".pdf":
            return self._read_pdf()
        elif suffix in [".txt", ".text"]:
            return self.source_path.read_text(encoding="utf-8")
        else:
            raise ValueError(
                f"Unsupported file type: {suffix}. "
                "Supported types: .pdf, .txt"
            )

    def _read_pdf(self) -> str:
        """Extract text from PDF using pdfplumber."""
        try:
            import pdfplumber
        except ImportError:
            raise ImportError(
                "pdfplumber is required for PDF parsing. "
                "Install it with: pip install pdfplumber"
            )

        text_parts = []
        with pdfplumber.open(self.source_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        return "\n\n".join(text_parts)

    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess extracted text.

        - Fix hyphenated words split across lines
        - Normalize whitespace
        - Remove page numbers
        """
        # Fix hyphenated words
        text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

        # Remove standalone page numbers (common pattern: centered numbers)
        text = re.sub(r"\n\s*\d+\s*\n", "\n", text)

        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Remove excessive blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    def _remove_penjelasan(self, text: str) -> str:
        """Remove PENJELASAN (explanation) section from the end."""
        match = self.PENJELASAN_PATTERN.search(text)
        if match:
            text = text[:match.start()]
        return text.strip()

    def _parse_babs(self, text: str) -> List[Dict[str, Any]]:
        """Extract all BAB (chapters) from text."""
        babs = []
        default_bab = {"roman": "", "title": "UMUM", "start": 0, "end": len(text)}

        matches = list(self.BAB_PATTERN.finditer(text))

        for i, match in enumerate(matches):
            roman = match.group("roman").upper()
            title = match.group("title").strip()
            start = match.start()

            # Set end position (start of next BAB or end of text)
            if i + 1 < len(matches):
                end = matches[i + 1].start()
            else:
                end = len(text)

            babs.append({
                "roman": roman,
                "title": title,
                "start": start,
                "end": end,
            })

        # If no BAB found, use default
        if not babs:
            babs.append(default_bab)

        return babs

    def _parse_pasals(self, text: str) -> List[Pasal]:
        """Parse all Pasal within BAB structure."""
        pasals = []

        for bab in self.babs:
            bab_text = text[bab["start"]:bab["end"]]
            bab_pasals = self._parse_pasals_in_bab(bab_text, bab)
            pasals.extend(bab_pasals)

        return pasals

    def _is_pasal_reference(self, match: re.Match, bab_text: str) -> bool:
        """
        Check if this Pasal match is likely a reference, not a declaration.

        References like "Pasal 14, Pasal 15, dan Pasal 16" should be filtered out.
        """
        # Get the line containing this match
        start = match.start()
        line_start = bab_text.rfind("\n", 0, start) + 1
        line_end = bab_text.find("\n", start)
        if line_end == -1:
            line_end = len(bab_text)
        line = bab_text[line_start:line_end]

        # Check if line contains multiple "Pasal" occurrences (likely a reference)
        pasal_count_in_line = len(list(self.PASAL_PATTERN.finditer(line)))
        if pasal_count_in_line > 1:
            return True

        # Check if followed by comma, "dan", or another Pasal within short distance
        # Look at next ~100 chars after "Pasal X"
        next_chars = bab_text[start:start + 100]

        # Pattern like "Pasal 14, Pasal 15" or "Pasal 14, Pasal 15, dan Pasal 16"
        if re.search(r'Pasal\s+\d+[,.\s]+(?:dan\s+)?Pasal\s+\d+', next_chars, re.IGNORECASE):
            return True

        return False

    def _parse_pasals_in_bab(self, bab_text: str, bab_info: Dict[str, Any]) -> List[Pasal]:
        """Parse Pasal within a single BAB."""
        pasals = []

        # Find all Pasal matches in this BAB
        all_matches = list(self.PASAL_PATTERN.finditer(bab_text))

        # Filter out references (keep only real declarations)
        valid_matches = [m for m in all_matches if not self._is_pasal_reference(m, bab_text)]

        for i, match in enumerate(valid_matches):
            pasal_num = int(match.group("number"))

            # Get the content range for this Pasal
            start = match.end()

            # End is start of next VALID Pasal, or end of BAB
            if i + 1 < len(valid_matches):
                end = valid_matches[i + 1].start()
            else:
                end = len(bab_text)

            # Extract raw content
            content_text = bab_text[start:end].strip()

            # Extract pasal title from first line(s) before first ayat
            # The title is typically the first line that doesn't start with (digit)
            pasal_title, content_body = self._extract_pasal_title_and_content(content_text)

            # Build content with pasal header included
            pasal_header = f"Pasal {pasal_num}"
            if pasal_title:
                pasal_header += f" {pasal_title}"
            content_with_header = f"{pasal_header}\n{content_body}"

            pasals.append(Pasal(
                content=content_with_header,
                pasal=pasal_num,
                pasal_title=pasal_title if pasal_title else None,
                bab=bab_info["roman"],
                bab_title=bab_info["title"],
                source=self.source_name,
            ))

        return pasals

    def _extract_pasal_title_and_content(self, content: str) -> Tuple[Optional[str], str]:
        """
        Extract pasal title and content body from raw text.

        The title is the text before the first ayat (1), (2), etc.
        Returns (title, content_body) tuple.
        """
        if not content:
            return None, ""

        # Split into lines
        lines = content.split("\n")
        lines = [line.strip() for line in lines if line.strip()]

        title_lines = []
        content_lines = []
        found_first_ayat = False

        for line in lines:
            # Check if this line starts an ayat
            if self.AYAT_PATTERN.match(line):
                found_first_ayat = True
                content_lines.append(line)
            elif found_first_ayat:
                # Already past the title, this is content continuation
                content_lines.append(line)
            else:
                # Still before first ayat - could be title or intro text
                # Stop collecting title if line ends with colon or is short
                if line.endswith(":") or line.endswith("."):
                    title_lines.append(line)
                elif len(line) < 100 and not line.startswith("("):
                    # Likely a title line (short, doesn't start with ayat)
                    title_lines.append(line)
                else:
                    # Longer text, likely part of content
                    content_lines.append(line)

        # Join title and content
        title = " ".join(title_lines).strip() if title_lines else None
        # Clean up title - if it's too long, treat it as content instead
        if title and len(title) > 150:
            content_lines = list(title_lines) + content_lines
            title = None

        # Build content body preserving ayat structure
        content_body = self._build_content_body(content_lines)

        return title, content_body

    def _build_content_body(self, lines: List[str]) -> str:
        """Build content body from lines, preserving ayat structure."""
        formatted_lines = []
        current_ayat: List[str] = []

        for line in lines:
            # Check if this is an ayat line
            ayat_match = self.AYAT_PATTERN.match(line)

            if ayat_match:
                # Save previous ayat if exists
                if current_ayat:
                    formatted_lines.append(" ".join(current_ayat))
                    current_ayat = []

                # Start new ayat
                current_ayat.append(line)
            else:
                # Continuation of current ayat or standalone text
                current_ayat.append(line)

        # Don't forget the last ayat
        if current_ayat:
            formatted_lines.append(" ".join(current_ayat))

        result = " ".join(formatted_lines)

        # Clean up extra whitespace
        result = re.sub(r"\s+", " ", result).strip()

        return result

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics of parsed document."""
        return {
            "source": self.source_name,
            "total_babs": len(self.babs),
            "total_pasals": len(self.pasals),
            "bab_range": f"{self.pasals[0].bab if self.pasals else 'N/A'} - "
                         f"{self.pasals[-1].bab if self.pasals else 'N/A'}",
            "pasal_range": f"{min(p.pasal for p in self.pasals) if self.pasals else 'N/A'} - "
                          f"{max(p.pasal for p in self.pasals) if self.pasals else 'N/A'}",
        }

    def export_json(self, output_path: Optional[str] = None) -> str:
        """
        Export parsed Pasal objects to JSON file.

        Args:
            output_path: Path to output JSON file. If not provided, uses
                        source_name with .json extension.

        Returns:
            Path to the created JSON file.
        """
        import json

        if output_path is None:
            output_path = f"{self.source_path.stem}_parsed.json"

        output_path = Path(output_path)

        data = {
            "metadata": self.get_summary(),
            "pasals": [p.to_dict() for p in self.pasals],
        }

        output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

        return str(output_path)

    def export_markdown(self, output_path: Optional[str] = None) -> str:
        """
        Export parsed Pasal objects to Markdown file.

        Args:
            output_path: Path to output MD file. If not provided, uses
                        source_name with .md extension.

        Returns:
            Path to the created Markdown file.
        """
        if output_path is None:
            output_path = f"{self.source_path.stem}_parsed.md"

        output_path = Path(output_path)

        lines = [f"# {self.source_name}", ""]

        # Group by BAB
        current_bab = None
        for pasal in self.pasals:
            if pasal.bab != current_bab:
                current_bab = pasal.bab
                lines.append(f"\n## BAB {pasal.bab} - {pasal.bab_title}\n")

            title_suffix = f" - {pasal.pasal_title}" if pasal.pasal_title else ""
            lines.append(f"### Pasal {pasal.pasal}{title_suffix}")
            lines.append(pasal.content)
            lines.append("")

        output_path.write_text("\n".join(lines))

        return str(output_path)

    def to_rag_documents(self) -> List[Dict[str, Any]]:
        """
        Convert parsed Pasal objects to format compatible with RAG pipeline.

        Returns:
            List of dictionaries with 'page_content' and 'metadata' keys.
        """
        return [
            {
                "page_content": pasal.content,
                "metadata": pasal.to_metadata(),
            }
            for pasal in self.pasals
        ]
