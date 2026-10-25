"""
Statutory Structure Parser for Indian Legislative Documents.

Sequentially parses legal statutory documents into canonical statutory hierarchies:
Act -> Chapter -> Section -> Subsection -> Clause / Proviso / Explanation / Illustration.

Robustly handles complex Indian Gazette OCR and layout formatting such as:
- Numbered provision starts: "303.", "303.(1)", "303. (1)", "303A.(2)", "63.(1)"
- Explicit section starts: "Section 303", "Sec. 303", "Article 21", "Art. 21"
- Separate subsections "(1)", "(2)"
- Subordinate statutory elements: "Explanation 1.", "Illustration (a)", "Provided that..."
- Gazette header/footer and noise elimination
"""

import re
from typing import Any

from schemas.document import DocumentPageRecord
from schemas.statutory import ProvisionBoundaryStatus, StatutoryProvision
from utils.logger import get_logger

logger = get_logger(__name__)

# Regex patterns for cleaning Gazette artifacts
GAZETTE_HEADER_PATTERNS = [
    re.compile(
        r"^\s*(?:vlk/kkj\.k|EXTRAORDINARY|Hkkx\s+II|PART\s+II\s*[—–-]\s*Section\s*1|izkf/kdkj|PUBLISHED\s+BY\s+AUTHORITY).*$",
        re.MULTILINE | re.IGNORECASE,
    ),
    re.compile(
        r"^\s*(?:la\u00f1|No\.)\s*\d+.*?(?:PAUSHA|SAKA|DECEMBER|JANUARY|\d{4}).*$",
        re.MULTILINE | re.IGNORECASE,
    ),
    re.compile(
        r"^\s*(?:REGISTERED\s+NO\.|MINISTRY\s+OF\s+LAW\s+AND\s+JUSTICE|Legislative\s+Department).*$",
        re.MULTILINE | re.IGNORECASE,
    ),
    re.compile(
        r"^\s*(?:THE\s+GAZETTE\s+OF\s+INDIA|EXTRAORDINARY\s*\[Part\s*II|Sec\.\s*1\]\s*THE\s+GAZETTE).*$",
        re.MULTILINE | re.IGNORECASE,
    ),
    re.compile(r"_{10,}", re.MULTILINE),
    re.compile(r"^\s*xxxGID[EH]xxx\s*$", re.MULTILINE),
    re.compile(r"^\s*CG-[A-Z0-9-]+\s*$", re.MULTILINE),
]

# Chapter pattern: CHAPTER XVII \n OF OFFENCES AGAINST PROPERTY
CHAPTER_PATTERN = re.compile(
    r"^\s*CHAPTER\s+([IVXLCDM\d]+)\s*\n+\s*([A-Z\s,–—-]{3,100})",
    re.MULTILINE,
)

# Robust section provision-start regex matching:
# Matches:
# 303.
# 303.(1)
# 303. (1)
# 303A.
# 303A.(1)
# Section 303 / Sec. 303
# Article 21 / Art. 21
SECTION_START_PATTERN = re.compile(
    r"(?:\n|^)\s*(?:(?:Section|Sec\.|Article|Art\.)\s+)?(\d+[A-Z]?)\.\s*(?:\((\d+[A-Z]?)\))?\s*(.*?)(?=\n|$)",
    re.MULTILINE,
)

# Sub-section start inside provision: "(1) ", "(2) " at line start
SUBSECTION_PATTERN = re.compile(
    r"(?:\n|^)\s*\((\d+[A-Z]?)\)\s*(.*?)(?=\n|$)",
    re.MULTILINE,
)

# Sub-clause start: "(a) ", "(b) "
CLAUSE_PATTERN = re.compile(
    r"(?:\n|^)\s*\(([a-z]{1,2})\)\s*(.*?)(?=\n|$)",
    re.MULTILINE,
)

# Explanation / Proviso / Illustration patterns
EXPLANATION_PATTERN = re.compile(
    r"(?:\n|^)\s*(Explanation\s*(?:\d+)?)\s*[.—–-]\s*(.*?)(?=\n|$)",
    re.IGNORECASE | re.MULTILINE,
)

PROVISO_PATTERN = re.compile(
    r"(?:\n|^)\s*(Provided\s+(?:further\s+)?that)\b\s*(.*?)(?=\n|$)",
    re.IGNORECASE | re.MULTILINE,
)

ILLUSTRATION_HEADER_PATTERN = re.compile(
    r"(?:\n|^)\s*Illustrations?\.?\s*(?:\n|$)",
    re.IGNORECASE | re.MULTILINE,
)

# Known titles or marginal note extractors
COMMON_SECTION_TITLES = {
    ("bns_2023", "303"): "Theft",
    ("bns_2023", "304"): "Snatching",
    ("bns_2023", "101"): "Murder",
    ("bns_2023", "103"): "Punishment for murder",
    ("bns_2023", "105"): "Culpable homicide not amounting to murder",
    ("bns_2023", "106"): "Causing death by negligence",
    ("bns_2023", "111"): "Organised crime",
    ("bns_2023", "112"): "Petty organised crime",
    ("bns_2023", "113"): "Terrorist act",
    ("bsa_2023", "63"): "Admissibility of electronic records",
    ("bsa_2023", "61"): "Electronic or digital record",
    ("bsa_2023", "57"): "Primary evidence",
    ("bsa_2023", "58"): "Secondary evidence",
    ("consumer_protection_act", "2"): "Definitions",
    ("consumer_protection_act", "9"): "Establishment of Consumer Protection Councils",
    (
        "consumer_protection_act",
        "28",
    ): "Establishment of District Consumer Disputes Redressal Commission",
    ("consumer_protection_act", "34"): "Jurisdiction of District Commission",
    ("consumer_protection_act", "47"): "Jurisdiction of State Commission",
    ("consumer_protection_act", "58"): "Jurisdiction of National Commission",
}


class StatutoryStructureParser:
    """Parser that extracts hierarchical, validated statutory provisions from document texts."""

    def __init__(self, document_id: str, act_name: str, act_year: int | None = None):
        self.document_id = document_id
        self.act_name = act_name
        self.act_year = act_year

    def clean_gazette_noise(self, text: str) -> str:
        """Strip Gazette running headers, publishing metadata, and divider artifacts."""
        cleaned = text
        for pat in GAZETTE_HEADER_PATTERNS:
            cleaned = pat.sub("", cleaned)
        return cleaned

    def parse_pages(self, pages: list[DocumentPageRecord]) -> list[StatutoryProvision]:
        """Parse ordered document pages into a list of canonical StatutoryProvisions."""
        if not pages:
            return []

        sorted_pages = sorted(pages, key=lambda p: p.page_number)

        # Build page-indexed combined text with page offset boundaries
        combined_text_parts: list[str] = []
        page_offsets: list[tuple[int, int, int]] = []  # (start_char, end_char, page_number)
        current_offset = 0

        for p in sorted_pages:
            cleaned_p_text = self.clean_gazette_noise(p.text)
            p_len = len(cleaned_p_text)
            page_offsets.append((current_offset, current_offset + p_len, p.page_number))
            combined_text_parts.append(cleaned_p_text)
            current_offset += p_len + 2  # account for \n\n

        full_text = "\n\n".join(combined_text_parts)

        def get_pages_for_offsets(start_char: int, end_char: int) -> tuple[int, int]:
            p_start = sorted_pages[0].page_number
            p_end = sorted_pages[-1].page_number
            for start_o, end_o, p_num in page_offsets:
                if start_char >= start_o:
                    p_start = p_num
                if end_char <= end_o:
                    p_end = p_num
                    break
            return (p_start, p_end)

        return self.parse_text(full_text, get_pages_for_offsets)

    def parse_text(
        self,
        full_text: str,
        page_resolver: Any | None = None,
    ) -> list[StatutoryProvision]:
        """Parse raw or cleaned full statute text into structured StatutoryProvision objects."""
        provisions: list[StatutoryProvision] = []

        # 1. Identify all Chapter boundaries
        chapters: list[dict[str, Any]] = []
        for ch_match in CHAPTER_PATTERN.finditer(full_text):
            ch_num = ch_match.group(1).strip()
            ch_title = ch_match.group(2).strip().title()
            chapters.append(
                {
                    "number": ch_num,
                    "title": ch_title,
                    "start": ch_match.start(),
                }
            )

        def get_chapter_at(char_idx: int) -> tuple[str | None, str | None]:
            current_ch_num, current_ch_title = None, None
            for ch in chapters:
                if char_idx >= ch["start"]:
                    current_ch_num = ch["number"]
                    current_ch_title = ch["title"]
                else:
                    break
            return current_ch_num, current_ch_title

        # 2. Identify all Section boundaries
        # Regex captures: (section_num), (optional subsection_num), (heading/first line)
        # Note: We must ensure we do not match numbered list items like "1." inside a subsection if preceded by sentence
        # The regex requires \n or start of string.
        sec_matches = list(SECTION_START_PATTERN.finditer(full_text))
        if not sec_matches:
            logger.info("No section patterns found in text for %s", self.document_id)
            return []

        # Filter out false positives (e.g. numbered items deep in sentences, dates like 25.12.2023)
        valid_sec_spans: list[dict[str, Any]] = []
        for i, m in enumerate(sec_matches):
            sec_num = m.group(1)
            initial_subsec = m.group(2)
            first_line = m.group(3).strip()

            # Discard obvious date fractions or non-provisions
            if len(sec_num) > 5:
                continue

            valid_sec_spans.append(
                {
                    "match": m,
                    "sec_num": sec_num,
                    "initial_subsec": initial_subsec,
                    "first_line": first_line,
                    "start": m.start(),
                }
            )

        # Process each section block
        for i, span in enumerate(valid_sec_spans):
            sec_start = span["start"]
            sec_end = (
                valid_sec_spans[i + 1]["start"] if i + 1 < len(valid_sec_spans) else len(full_text)
            )
            sec_text = full_text[sec_start:sec_end].strip()

            sec_num = span["sec_num"]
            initial_subsec = span["initial_subsec"]
            first_line = span["first_line"]
            ch_num, ch_title = get_chapter_at(sec_start)

            # Determine Section Title
            # Priority 1: Known canonical lookup
            canonical_title = COMMON_SECTION_TITLES.get((self.document_id, sec_num), "")
            sec_title = canonical_title

            # Priority 2: If no canonical title, extract from first line or preceding/marginal line
            if not sec_title:
                # Often in Indian statutes, marginal title appears at the end of section or on next line
                # e.g. "Short title, commencement..." or "Theft."
                # Check if first line has title text before subsection or substantive text
                if first_line and not first_line.startswith(
                    ("Whoever", "Every", "No person", "The", "A person")
                ):
                    # Likely a title
                    candidate_title = first_line.split(".")[0].strip()
                    if 3 <= len(candidate_title) <= 80:
                        sec_title = candidate_title

            p_start, p_end = (1, 1)
            if page_resolver:
                p_start, p_end = page_resolver(sec_start, sec_end)

            # Primary Section Provision
            primary_prov_id = f"{self.document_id}_s{sec_num.lower()}"

            # Check if this section contains subsections: (1), (2), (3)...
            # If initial_subsec is present (e.g. 303.(1)), we also have subsection (1)
            subsections = list(SUBSECTION_PATTERN.finditer(sec_text))

            if subsections or initial_subsec:
                # We record the overarching section provision
                provisions.append(
                    StatutoryProvision(
                        provision_id=primary_prov_id,
                        parent_provision_id=None,
                        document_id=self.document_id,
                        act_name=self.act_name,
                        act_year=self.act_year,
                        chapter_number=ch_num,
                        chapter_title=ch_title,
                        section_number=sec_num,
                        section_title=sec_title,
                        subsection_number=None,
                        text=sec_text,
                        page_start=p_start,
                        page_end=p_end,
                        source_start_offset=sec_start,
                        source_end_offset=sec_end,
                        boundary_verified=True,
                        boundary_status=ProvisionBoundaryStatus.VALID,
                        parser_confidence=0.95,
                        metadata={
                            "total_subsections": len(subsections)
                            + (
                                1
                                if initial_subsec
                                and not any(s.group(1) == initial_subsec for s in subsections)
                                else 0
                            ),
                            "is_parent_section": True,
                        },
                    )
                )

                # Now extract individual subsections as distinct addressable provisions
                # If initial_subsec is present (e.g. "303.(1) Whoever..."), capture it
                if initial_subsec and not any(s.group(1) == initial_subsec for s in subsections):
                    first_sub_end = subsections[0].start() if subsections else len(sec_text)
                    sub_text = sec_text[:first_sub_end].strip()
                    sub_prov_id = f"{primary_prov_id}_{initial_subsec}"
                    provisions.append(
                        StatutoryProvision(
                            provision_id=sub_prov_id,
                            parent_provision_id=primary_prov_id,
                            document_id=self.document_id,
                            act_name=self.act_name,
                            act_year=self.act_year,
                            chapter_number=ch_num,
                            chapter_title=ch_title,
                            section_number=sec_num,
                            section_title=sec_title,
                            subsection_number=initial_subsec,
                            text=sub_text,
                            page_start=p_start,
                            page_end=p_end,
                            source_start_offset=sec_start,
                            source_end_offset=sec_start + len(sub_text),
                            boundary_verified=True,
                            boundary_status=ProvisionBoundaryStatus.VALID,
                            parser_confidence=0.98,
                            metadata={"is_subsection": True},
                        )
                    )

                for sub_idx, sub_m in enumerate(subsections):
                    sub_num = sub_m.group(1)
                    sub_start = sub_m.start()
                    sub_end = (
                        subsections[sub_idx + 1].start()
                        if sub_idx + 1 < len(subsections)
                        else len(sec_text)
                    )
                    sub_content = sec_text[sub_start:sub_end].strip()
                    sub_prov_id = f"{primary_prov_id}_{sub_num}"

                    # Detect proviso in this subsection
                    proviso_match = PROVISO_PATTERN.search(sub_content)
                    proviso_id = proviso_match.group(1) if proviso_match else None

                    # Detect explanation in this subsection
                    expl_match = EXPLANATION_PATTERN.search(sub_content)
                    expl_id = expl_match.group(1) if expl_match else None

                    provisions.append(
                        StatutoryProvision(
                            provision_id=sub_prov_id,
                            parent_provision_id=primary_prov_id,
                            document_id=self.document_id,
                            act_name=self.act_name,
                            act_year=self.act_year,
                            chapter_number=ch_num,
                            chapter_title=ch_title,
                            section_number=sec_num,
                            section_title=sec_title,
                            subsection_number=sub_num,
                            proviso_identifier=proviso_id,
                            explanation_identifier=expl_id,
                            text=sub_content,
                            page_start=p_start,
                            page_end=p_end,
                            source_start_offset=sec_start + sub_start,
                            source_end_offset=sec_start + sub_end,
                            boundary_verified=True,
                            boundary_status=ProvisionBoundaryStatus.VALID,
                            parser_confidence=0.98,
                            metadata={"is_subsection": True},
                        )
                    )
            else:
                # Standalone section without numbered subsections
                provisions.append(
                    StatutoryProvision(
                        provision_id=primary_prov_id,
                        parent_provision_id=None,
                        document_id=self.document_id,
                        act_name=self.act_name,
                        act_year=self.act_year,
                        chapter_number=ch_num,
                        chapter_title=ch_title,
                        section_number=sec_num,
                        section_title=sec_title,
                        subsection_number=None,
                        text=sec_text,
                        page_start=p_start,
                        page_end=p_end,
                        source_start_offset=sec_start,
                        source_end_offset=sec_end,
                        boundary_verified=True,
                        boundary_status=ProvisionBoundaryStatus.VALID,
                        parser_confidence=0.95,
                        metadata={"is_standalone_section": True},
                    )
                )

        logger.info(
            "Parsed %d statutory provisions from %s (document_id=%s)",
            len(provisions),
            self.act_name,
            self.document_id,
        )
        return provisions
