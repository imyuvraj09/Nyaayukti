"""
Statutory Provision and Boundary Verification Schemas for Nyaayukti.

Defines canonical representations of parsed statutory units, structural provision
hierarchies, and validation statuses for boundary checking and section-text alignment.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ProvisionBoundaryStatus(str, Enum):
    """Status indicating the structural and textual integrity of a statutory provision."""

    VALID = "VALID"
    CONTAMINATED = "CONTAMINATED"
    MULTI_SECTION = "MULTI_SECTION"
    TRUNCATED = "TRUNCATED"
    ORPHAN_HEADING = "ORPHAN_HEADING"
    UNVERIFIED = "UNVERIFIED"


class SectionTextValidationStatus(str, Enum):
    """Status of the alignment between section metadata and actual provision text."""

    VALID = "VALID"
    SECTION_TEXT_MISMATCH = "SECTION_TEXT_MISMATCH"
    UNVERIFIED = "UNVERIFIED"


class StatutoryProvision(BaseModel):
    """Canonical model for a structurally parsed and validated statutory provision."""

    provision_id: str = Field(
        ...,
        description="Deterministic unique provision identifier (e.g. bns_2023_s303 or bns_2023_s303_1)",
    )
    parent_provision_id: str | None = Field(
        default=None,
        description="Parent provision ID for subsections, clauses, or explanations (e.g. bns_2023_s303)",
    )
    document_id: str = Field(
        ...,
        description="Canonical document identifier (e.g. bns_2023, bnss_2023, bsa_2023)",
    )
    act_name: str = Field(
        ...,
        description="Official title of the statute",
    )
    act_year: int | None = Field(
        default=None,
        description="Enactment year of the statute",
    )
    chapter_number: str | None = Field(
        default=None,
        description="Roman or Arabic chapter identifier (e.g. XVIII or 18)",
    )
    chapter_title: str | None = Field(
        default=None,
        description="Title or heading of the containing chapter",
    )
    section_number: str = Field(
        ...,
        description="Section or Article number (e.g. '303', '303A', '21')",
    )
    section_title: str = Field(
        default="",
        description="Marginal heading or title of the section (e.g. 'Theft')",
    )
    subsection_number: str | None = Field(
        default=None,
        description="Subsection number if this unit represents or starts with a subsection (e.g. '1', '2')",
    )
    clause_identifier: str | None = Field(
        default=None,
        description="Clause identifier if applicable (e.g. '(a)', '(b)')",
    )
    proviso_identifier: str | None = Field(
        default=None,
        description="Proviso identifier (e.g. 'Proviso 1')",
    )
    explanation_identifier: str | None = Field(
        default=None,
        description="Explanation identifier (e.g. 'Explanation 1')",
    )
    illustration_identifier: str | None = Field(
        default=None,
        description="Illustration identifier (e.g. 'Illustration (a)')",
    )
    text: str = Field(
        ...,
        description="Substantive text of the provision",
    )
    page_start: int = Field(
        default=1,
        description="Starting 1-based page number",
    )
    page_end: int = Field(
        default=1,
        description="Ending 1-based page number",
    )
    source_start_offset: int = Field(
        default=0,
        description="Start character offset in document text",
    )
    source_end_offset: int = Field(
        default=0,
        description="End character offset in document text",
    )
    boundary_verified: bool = Field(
        default=False,
        description="Whether this provision passed boundary integrity validation",
    )
    boundary_status: ProvisionBoundaryStatus = Field(
        default=ProvisionBoundaryStatus.UNVERIFIED,
        description="Detailed boundary validation status",
    )
    parser_confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Parser confidence score in structural extraction",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional structural or provenance metadata",
    )
