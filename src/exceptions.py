"""Typed exception hierarchy for the Claim API.

Each exception maps to an HTTP status code and has a default detail message.
All extend HTTPException so FastAPI handles them automatically.
"""

from fastapi import HTTPException, status


class ExtractionError(HTTPException):
    """Base exception for extraction pipeline failures."""

    def __init__(self, detail: str = "Extraction failed") -> None:
        super().__init__(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)


class LLMProviderError(ExtractionError):
    """Gemini API call failed after retries exhausted."""

    def __init__(self, detail: str = "LLM provider error after retries exhausted") -> None:
        super().__init__(detail=detail)


class SafetyFilterError(ExtractionError):
    """Content blocked by Gemini safety filters."""

    def __init__(self, detail: str = "Content blocked by safety filters") -> None:
        super().__init__(detail=detail)


class EmptyExtractionError(ExtractionError):
    """Gemini returned no topics or claims."""

    def __init__(self, detail: str = "No topics or claims could be extracted") -> None:
        super().__init__(detail=detail)


class InputValidationError(HTTPException):
    """Invalid source text input."""

    def __init__(self, detail: str = "Invalid input") -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail
        )
