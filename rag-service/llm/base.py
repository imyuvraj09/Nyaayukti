"""
Base LLM provider abstraction for Nyaayukti Legal Knowledge Assistant.

Defines the contract for LLM integrations, enabling seamless swapping between
Google Gemini, OpenAI, self-hosted vLLM/Ollama, or mock testing providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class LLMError(RuntimeError):
    """Base exception for LLM errors with category classification and retryability flag."""

    def __init__(
        self,
        message: str,
        category: str = "UNKNOWN_ERROR",
        status_code: int | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.category = category
        self.status_code = status_code
        self.retryable = retryable


class LLMRateLimitError(LLMError):
    """HTTP 429 rate limit reached (requests or tokens per minute). Temporary and retryable."""

    def __init__(
        self,
        message: str = "LLM API rate limit reached. Please try again shortly.",
        status_code: int | None = 429,
    ) -> None:
        super().__init__(
            message=message,
            category="RATE_LIMITED",
            status_code=status_code,
            retryable=True,
        )


class LLMQuotaExceededError(LLMError):
    """API quota or billing limit exceeded. Permanent until funded / quota refreshed."""

    def __init__(
        self,
        message: str = "LLM API quota exceeded. Please check your account plan or billing limits.",
        status_code: int | None = 429,
    ) -> None:
        super().__init__(
            message=message,
            category="QUOTA_EXCEEDED",
            status_code=status_code,
            retryable=False,
        )


class LLMAuthenticationError(LLMError):
    """API key invalid or permission denied (HTTP 401/403). Non-retryable."""

    def __init__(
        self,
        message: str = "LLM authentication failed. Please verify your API key.",
        status_code: int | None = 401,
    ) -> None:
        super().__init__(
            message=message,
            category="AUTH_ERROR",
            status_code=status_code,
            retryable=False,
        )


class LLMInvalidModelError(LLMError):
    """Requested model not found or unsupported by provider (HTTP 404). Non-retryable."""

    def __init__(
        self,
        message: str = "Configured LLM model is invalid or unavailable.",
        status_code: int | None = 404,
    ) -> None:
        super().__init__(
            message=message,
            category="INVALID_MODEL",
            status_code=status_code,
            retryable=False,
        )


class LLMTimeoutError(LLMError):
    """Request timeout communicating with LLM API. Temporary and retryable."""

    def __init__(
        self,
        message: str = "LLM inference request timed out.",
        status_code: int | None = 504,
    ) -> None:
        super().__init__(
            message=message,
            category="TIMEOUT",
            status_code=status_code,
            retryable=True,
        )


class LLMNetworkError(LLMError):
    """Network connection or DNS resolution failure. Temporary and retryable."""

    def __init__(
        self,
        message: str = "Network connection error communicating with LLM provider.",
        status_code: int | None = 503,
    ) -> None:
        super().__init__(
            message=message,
            category="NETWORK_ERROR",
            status_code=status_code,
            retryable=True,
        )


class LLMOutputTruncatedError(LLMError):
    """Model output was cut off or exceeded max token budget before completion."""

    def __init__(
        self,
        message: str = "LLM response was truncated before completion (token budget exceeded).",
        status_code: int | None = 502,
        raw_output: str | None = None,
    ) -> None:
        super().__init__(
            message=message,
            category="OUTPUT_TRUNCATED",
            status_code=status_code,
            retryable=False,
        )
        self.raw_output = raw_output


class LLMJsonParseError(LLMError):
    """Model generated non-JSON or syntactically invalid output."""

    def __init__(
        self,
        message: str = "Failed to parse model response as valid JSON.",
        status_code: int | None = 502,
        raw_output: str | None = None,
    ) -> None:
        super().__init__(
            message=message,
            category="JSON_PARSE_FAILED",
            status_code=status_code,
            retryable=True,
        )
        self.raw_output = raw_output


class LLMSchemaValidationError(LLMError):
    """Model output JSON does not conform to the expected Pydantic schema."""

    def __init__(
        self,
        message: str = "Model response structure does not match the required schema.",
        status_code: int | None = 502,
        validation_errors: Any = None,
        raw_output: str | None = None,
    ) -> None:
        super().__init__(
            message=message,
            category="SCHEMA_VALIDATION_FAILED",
            status_code=status_code,
            retryable=True,
        )
        self.validation_errors = validation_errors
        self.raw_output = raw_output


class LLMReviewFailedError(LLMError):
    """Structured evidence review failed to validate against sources."""

    def __init__(
        self,
        message: str = "Structured legal evidence review failed.",
        status_code: int | None = 502,
    ) -> None:
        super().__init__(
            message=message,
            category="REVIEW_FAILED",
            status_code=status_code,
            retryable=False,
        )


class LLMUnconfiguredError(LLMError):
    """LLM provider credentials or configuration are missing."""

    def __init__(
        self,
        message: str = "AI generation provider is not configured. Please supply a valid API key.",
        status_code: int | None = 500,
    ) -> None:
        super().__init__(
            message=message,
            category="UNCONFIGURED",
            status_code=status_code,
            retryable=False,
        )


class LLMMalformedResponseError(LLMError):
    """Provider returned response that cannot be parsed as valid content/JSON. Non-retryable."""

    def __init__(
        self,
        message: str = "LLM provider returned a malformed response.",
        status_code: int | None = 502,
    ) -> None:
        super().__init__(
            message=message,
            category="MALFORMED_RESPONSE",
            status_code=status_code,
            retryable=False,
        )


class LLMEmptyResponseError(LLMError):
    """Provider returned empty completion content. Temporary and retryable."""

    def __init__(
        self,
        message: str = "LLM provider returned an empty response.",
        status_code: int | None = 502,
    ) -> None:
        super().__init__(
            message=message,
            category="EMPTY_RESPONSE",
            status_code=status_code,
            retryable=True,
        )


class LLMProviderError(LLMError):
    """Provider server-side 5xx error or internal failure. Temporary and retryable."""

    def __init__(
        self,
        message: str = "LLM provider encountered an internal service error.",
        status_code: int | None = 503,
    ) -> None:
        super().__init__(
            message=message,
            category="PROVIDER_ERROR",
            status_code=status_code,
            retryable=True,
        )


# Backward-compatible alias
LLMServiceUnavailableError = LLMProviderError


@dataclass
class LLMResponse:
    """Standardized response from an LLM provider."""

    content: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    finish_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseLLMProvider(ABC):
    """Abstract interface for LLM inference providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g. 'google', 'openai', 'custom')."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model identifier being used."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Check whether valid credentials and configuration exist for this provider."""
        pass

    def check_health(self) -> dict[str, Any]:
        """Perform a lightweight diagnostic check without sending generation requests.
        Never exposes API keys.
        """
        configured = self.is_configured()
        return {
            "provider": self.provider_name,
            "model": self.model_name,
            "configured": configured,
            "available": configured,
        }

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: str | None = None,
    ) -> LLMResponse:
        """Generate text completion from the language model."""
        pass
