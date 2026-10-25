"""
Request schema for incoming legal queries.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class QueryRequest(BaseModel):
    conversation_history: list[ConversationMessage] = Field(default_factory=list, max_length=12)

    """Schema for a user's legal question submitted to the RAG pipeline.

    Attributes:
        query:      The legal question (3–2000 characters, stripped).
        session_id: Optional session identifier for conversation tracking.
    """

    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The legal question to ask (3–2000 characters).",
        examples=["What are my legal rights if someone threatens me?"],
    )
    session_id: str | None = Field(
        default=None,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
        description="Optional session ID for conversation continuity.",
        examples=["session-abc-123"],
    )
    request_id: str | None = Field(
        default=None,
        max_length=80,
        pattern=r"^[A-Za-z0-9_-]+$",
        description="Unique correlation ID for request tracing and isolation.",
        examples=["req-789-xyz"],
    )
    use_query_answer_grounding: bool | None = Field(
        default=None,
        description="Enable multi-tier statutory provision retrieval, question-evidence alignment, and citation auditing.",
    )

    @field_validator("query", mode="before")
    @classmethod
    def strip_and_validate_query(cls, value: str) -> str:
        """Strip whitespace; reject empty or blank strings."""
        if not isinstance(value, str):
            raise ValueError("query must be a string")
        stripped = value.strip()
        if not stripped:
            raise ValueError("query cannot be empty or blank")
        return stripped

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "What are my legal rights if someone threatens me?",
                    "session_id": "test-session-001",
                }
            ]
        }
    }
