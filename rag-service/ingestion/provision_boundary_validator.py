"""
Provision Boundary Validator for Nyaayukti Ingestion & Retrieval.

Performs structural and textual integrity validation on candidate statutory provisions
and retrieved chunks to detect:
1. Multi-section contamination (chunks bleeding into subsequent or preceding sections).
2. Orphan headings without substantive statutory content.
3. Gazette publishing / page-header contamination (e.g. "Part II-Sec 1", underscores, publisher notes).
4. Table of Contents / Arrangement of Sections fragments.
5. Truncated provisions (sentences cut off abruptly).
"""

import re

from schemas.statutory import ProvisionBoundaryStatus, StatutoryProvision
from utils.logger import get_logger

logger = get_logger(__name__)

# Patterns indicating other sections contaminating current chunk
OTHER_SECTION_PATTERN = re.compile(
    r"(?:\n|^)\s*(?:(?:Section|Sec\.)\s+)?(\d+[A-Z]?)\.\s*(?:\([0-9A-Za-z]+\))?\s*[A-Z]",
    re.MULTILINE,
)

# Table of Contents / Arrangement of Sections pattern
TOC_PATTERN = re.compile(
    r"(?:Arrangement\s+of\s+Sections|TABLE\s+OF\s+CONTENTS|CHAPTERS\s*\n\s*SECTIONS|\b\d+\.\s+[A-Za-z\s]{3,60}\.{3,}\s*\d+)",
    re.IGNORECASE,
)

# Gazette headers and publishing markers
GAZETTE_MARKER_PATTERN = re.compile(
    r"(?:THE\s+GAZETTE\s+OF\s+INDIA|EXTRAORDINARY\s*\[Part\s*II|Sec\.\s*1\]\s*THE\s+GAZETTE|vlk/kkj\.k|izkf/kdkj\s+ls\s+izdkf'kr|Hkkx\s+II|_{10,}|xxxGID[EH]xxx)",
    re.IGNORECASE,
)


class ProvisionBoundaryValidator:
    """Validates structural boundary integrity and prevents statutory text contamination."""

    @classmethod
    def validate_text(
        cls,
        text: str,
        expected_section: str | None = None,
        is_heading_allowed: bool = True,
    ) -> tuple[ProvisionBoundaryStatus, list[str]]:
        """Validate text of a provision or chunk against boundary integrity rules.

        Returns:
            Tuple of (ProvisionBoundaryStatus, List of warning/issue descriptions).
        """
        issues: list[str] = []
        stripped = text.strip()

        if not stripped:
            return ProvisionBoundaryStatus.ORPHAN_HEADING, ["Empty provision text"]

        # 1. Check for Table of Contents / Arrangement of Sections
        if TOC_PATTERN.search(stripped):
            issues.append("Contains Table of Contents or Arrangement of Sections fragments")
            return ProvisionBoundaryStatus.CONTAMINATED, issues

        # 2. Check for Gazette publishing artifacts
        if GAZETTE_MARKER_PATTERN.search(stripped):
            issues.append("Contains uncleaned Gazette publishing markers or running headers")

        # 3. Check for Orphan Headings (e.g. short text with no substantive sentence)
        lines = [line.strip() for line in stripped.splitlines() if line.strip()]
        if len(lines) == 1 and len(lines[0]) < 80 and not lines[0].endswith((".", ";", ":", ")")):
            if not any(
                word in lines[0].lower()
                for word in [
                    "shall",
                    "punished",
                    "means",
                    "includes",
                    "whoever",
                    "where",
                ]
            ):
                issues.append("Orphan heading detected without substantive provision text")
                return ProvisionBoundaryStatus.ORPHAN_HEADING, issues

        # 4. Check for Multi-Section Contamination
        # If expected_section is given (e.g. "303"), check if another section header (e.g. "302.", "304.") appears inside
        if expected_section:
            clean_sec = expected_section.upper().replace("SECTION", "").replace("SEC.", "").strip()
            found_sections = OTHER_SECTION_PATTERN.findall(stripped)
            contaminants = [s for s in found_sections if s != clean_sec]
            if contaminants:
                issues.append(
                    f"Contaminated with adjacent or alien sections: {contaminants} (expected: {clean_sec})"
                )
                return ProvisionBoundaryStatus.CONTAMINATED, issues
        else:
            found_sections = OTHER_SECTION_PATTERN.findall(stripped)
            if len(set(found_sections)) > 1:
                issues.append(
                    f"Multiple distinct sections detected in single provision: {set(found_sections)}"
                )
                return ProvisionBoundaryStatus.MULTI_SECTION, issues

        # 5. Check for Truncation
        # A provision shouldn't end mid-word or with an unfinished connector like "and", "or", "with", "the"
        last_word = stripped.split()[-1].lower().rstrip(".,;:")
        if last_word in (
            "and",
            "or",
            "with",
            "the",
            "that",
            "of",
            "to",
            "by",
            "in",
            "for",
        ):
            issues.append(
                f"Provision appears truncated; ends on dangling conjunction/preposition '{last_word}'"
            )
            return ProvisionBoundaryStatus.TRUNCATED, issues

        if issues:
            return ProvisionBoundaryStatus.CONTAMINATED, issues

        return ProvisionBoundaryStatus.VALID, []

    @classmethod
    def validate_provision(cls, provision: StatutoryProvision) -> StatutoryProvision:
        """Run validation on a StatutoryProvision instance and update its boundary status."""
        status, issues = cls.validate_text(
            text=provision.text,
            expected_section=provision.section_number,
        )

        provision.boundary_status = status
        provision.boundary_verified = status == ProvisionBoundaryStatus.VALID
        if issues:
            provision.metadata["boundary_issues"] = issues
            if not provision.boundary_verified:
                provision.parser_confidence = max(0.1, provision.parser_confidence - 0.3)

        return provision

    @classmethod
    def sanitize_provision_text(cls, text: str, target_section: str | None = None) -> str:
        """Sanitize text by stripping trailing or leading contaminated sections and Gazette noise."""
        cleaned = text

        # Strip Gazette noise
        cleaned = GAZETTE_MARKER_PATTERN.sub("", cleaned)

        # If contaminated by a subsequent section (e.g. "304. Snatching..."), cut before it
        if target_section:
            clean_sec = target_section.upper().replace("SECTION", "").replace("SEC.", "").strip()
            # Find next section match
            for match in OTHER_SECTION_PATTERN.finditer(cleaned):
                sec_num = match.group(1)
                if sec_num != clean_sec and match.start() > 50:
                    cleaned = cleaned[: match.start()].strip()
                    break

        return cleaned.strip()
