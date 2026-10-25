"""
Conservative text cleaning module for legal document ingestion.

Prepares raw extracted PDF text for downstream chunking and embedding
without modifying legal terminology, punctuation, numbering, or formatting structure.
"""

import re


def clean_text(raw_text: str | None) -> str:
    """Conservatively clean extracted text from a legal document page.

    Operations performed:
    1. Remove null characters and unicode replacement/control artifacts.
    2. Normalize line terminators (\\r\\n and \\r to \\n).
    3. Strip trailing spaces from individual lines.
    4. Remove noise: long underscore separators, gazette headers, and font artifacts.
    5. Normalize excessive horizontal whitespace (multiple spaces/tabs to a single space).
    6. Collapse 3+ consecutive newlines to 2 newlines (retaining paragraph boundaries).
    7. Strip overall leading and trailing whitespace.

    Strictly preserves:
    - Legal sections, articles, clause identifiers, and numerals
    - Case sensitivity and exact legal phraseology
    - Punctuation marks and citations
    - Explanations and statutory illustrations
    """
    if not raw_text:
        return ""

    # 1. Remove null bytes
    cleaned = raw_text.replace("\x00", "")

    # 2. Normalize line endings to standard LF
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")

    # 3. Remove repeated underscore separators
    cleaned = re.sub(r"_{4,}", "", cleaned)

    # 4. Remove gazette running headers / footers and corrupted font lines
    cleaned = re.sub(
        r"(?im)^\s*(?:SEC\.\s*\d+\]?\s*)?(?:\d+\]?\s*)?THE\s+GAZETTE\s+OF\s+INDIA\s+EXTRAORDINARY(?:\s*\[[^\]\n]*\])?(?:\s*\d+)?\s*$",
        "",
        cleaned,
    )
    cleaned = re.sub(
        r"(?i)\b\d+\s+THE\s+GAZETTE\s+OF\s+INDIA\s+EXTRAORDINARY\s*\[?Part\s+[IVX]+[^\n]*",
        "",
        cleaned,
    )
    cleaned = re.sub(
        r"(?im)^\s*(?:EXTRAORDINARY\s+PART\s+[I|V|X]+|PUBLISHED\s+BY\s+AUTHORITY)\s*$",
        "",
        cleaned,
    )
    cleaned = re.sub(
        r"(?im)^\s*Separate paging is given to this Part[^\n]*$",
        "",
        cleaned,
    )
    cleaned = re.sub(
        r"(?im)^\s*REGISTERED NO\.[^\n]*$",
        "",
        cleaned,
    )
    cleaned = re.sub(
        r"(?im)^\s*No\.\s*\d+\]\s*NEW DELHI,\s*[^\n]*$",
        "",
        cleaned,
    )
    cleaned = re.sub(
        r"(?im)^\s*(?:bl\s+Hkkx|xxxGID[EH]xxx|jftLV\S*|vlk/kkj|Hkkx\s+II|izkf/kdkj|lañ\s+\d+\]|DL[—\-]\(N\)\d+|'kqØokj|¼'kd½)[^\n]*$",
        "",
        cleaned,
    )
    cleaned = re.sub(r"(?m)^\s*Sec\.\s*\d*\]?\s*$", "", cleaned)

    # 5. Clean line by line: normalize inline horizontal whitespace while preserving line structure
    lines = cleaned.split("\n")
    cleaned_lines = []
    for line in lines:
        line_clean = re.sub(r"[ \t]+", " ", line).strip()
        cleaned_lines.append(line_clean)

    cleaned = "\n".join(cleaned_lines)

    # 6. Collapse 3 or more consecutive newlines into 2 (preserves paragraph breaks)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    # 7. Final strip of outer whitespace
    return cleaned.strip()


def clean_source_snippet(raw_text: str | None) -> str:
    """Clean a retrieved source snippet for prompt context and display without altering meaning."""
    return clean_text(raw_text)
