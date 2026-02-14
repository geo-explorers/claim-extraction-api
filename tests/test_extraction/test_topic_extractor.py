"""Tests for TopicExtractor with mocked Gemini client."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from google.genai import types

from src.exceptions import ExtractionError, SafetyFilterError
from src.schemas.llm import TopicResult

if TYPE_CHECKING:
    from unittest.mock import AsyncMock, MagicMock


@pytest.fixture()
def topic_extractor(mock_genai_client: MagicMock) -> Any:
    """TopicExtractor wired to a mock Gemini client."""
    from src.extraction.topic_extractor import TopicExtractor

    return TopicExtractor(
        client=mock_genai_client,
        model="gemini-2.5-flash",
        temperature=0.2,
    )


async def test_extract_topics_success(
    topic_extractor: Any,
    mock_genai_client: MagicMock,
    mock_gemini_response: Any,
) -> None:
    """Successful extraction returns list of topic strings."""
    parsed = TopicResult(topics=["Topic A", "Topic B"])
    response = mock_gemini_response(parsed=parsed, finish_reason="STOP")
    generate: AsyncMock = mock_genai_client.aio.models.generate_content
    generate.return_value = response

    result = await topic_extractor.extract("some source text " * 10)

    assert result == ["Topic A", "Topic B"]
    generate.assert_awaited_once()


async def test_extract_topics_fallback_to_text_parsing(
    topic_extractor: Any,
    mock_genai_client: MagicMock,
    mock_gemini_response: Any,
) -> None:
    """When .parsed is None, falls back to parsing .text as JSON."""
    response = mock_gemini_response(
        parsed=None,
        text='{"topics": ["Fallback A", "Fallback B"]}',
        finish_reason="STOP",
    )
    generate: AsyncMock = mock_genai_client.aio.models.generate_content
    generate.return_value = response

    result = await topic_extractor.extract("some source text " * 10)

    assert result == ["Fallback A", "Fallback B"]


async def test_extract_topics_parse_failure_raises(
    topic_extractor: Any,
    mock_genai_client: MagicMock,
    mock_gemini_response: Any,
) -> None:
    """Invalid JSON in .text raises ExtractionError."""
    response = mock_gemini_response(
        parsed=None,
        text="invalid json {{{",
        finish_reason="STOP",
    )
    generate: AsyncMock = mock_genai_client.aio.models.generate_content
    generate.return_value = response

    with pytest.raises(ExtractionError):
        await topic_extractor.extract("some source text " * 10)


async def test_extract_topics_safety_filter_raises(
    topic_extractor: Any,
    mock_genai_client: MagicMock,
    mock_gemini_response: Any,
) -> None:
    """Safety-blocked response raises SafetyFilterError."""
    response = mock_gemini_response(
        parsed=None,
        text=None,
        finish_reason=types.FinishReason.SAFETY,
    )
    generate: AsyncMock = mock_genai_client.aio.models.generate_content
    generate.return_value = response

    with pytest.raises(SafetyFilterError):
        await topic_extractor.extract("some source text " * 10)
