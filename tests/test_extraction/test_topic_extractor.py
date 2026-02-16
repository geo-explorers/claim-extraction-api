"""Tests for TopicExtractor with mocked Gemini client."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from google.genai import types
from tenacity import wait_none

from src.exceptions import ExtractionError, SafetyFilterError
from src.schemas.llm import TopicResult

if TYPE_CHECKING:
    from unittest.mock import AsyncMock, MagicMock


@pytest.fixture()
def topic_extractor(mock_genai_client: MagicMock) -> Any:
    """TopicExtractor wired to a mock Gemini client."""
    from src.extraction.topic_extractor import TopicExtractor

    extractor = TopicExtractor(
        client=mock_genai_client,
        model="gemini-2.5-flash",
        temperature=0.2,
    )
    # Disable retry wait times in tests
    extractor._call_and_parse.retry.wait = wait_none()  # type: ignore[attr-defined]
    return extractor


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
    """Unrepairable JSON raises ExtractionError after retries."""
    response = mock_gemini_response(
        parsed=None,
        text="invalid json {{{",
        finish_reason="STOP",
    )
    generate: AsyncMock = mock_genai_client.aio.models.generate_content
    generate.return_value = response

    with pytest.raises(ExtractionError):
        await topic_extractor.extract("some source text " * 10)

    # Should have retried 3 times (ExtractionError is retryable)
    assert generate.await_count == 3


async def test_extract_topics_safety_filter_raises(
    topic_extractor: Any,
    mock_genai_client: MagicMock,
    mock_gemini_response: Any,
) -> None:
    """Safety-blocked response raises SafetyFilterError without retry."""
    response = mock_gemini_response(
        parsed=None,
        text=None,
        finish_reason=types.FinishReason.SAFETY,
    )
    generate: AsyncMock = mock_genai_client.aio.models.generate_content
    generate.return_value = response

    with pytest.raises(SafetyFilterError):
        await topic_extractor.extract("some source text " * 10)

    # SafetyFilterError is NOT retryable — should only call once
    generate.assert_awaited_once()


async def test_extract_topics_json_repair_fallback(
    topic_extractor: Any,
    mock_genai_client: MagicMock,
    mock_gemini_response: Any,
) -> None:
    """Malformed JSON is repaired and parsed successfully."""
    malformed_json = '{"topics": ["Topic A", "Topic B",]}'
    response = mock_gemini_response(
        parsed=None,
        text=malformed_json,
        finish_reason="STOP",
    )
    generate: AsyncMock = mock_genai_client.aio.models.generate_content
    generate.return_value = response

    result = await topic_extractor.extract("some source text " * 10)

    assert result == ["Topic A", "Topic B"]
    generate.assert_awaited_once()


async def test_extract_topics_retry_on_parse_failure_then_succeed(
    topic_extractor: Any,
    mock_genai_client: MagicMock,
    mock_gemini_response: Any,
) -> None:
    """Parse failure triggers retry; succeeds on second Gemini call."""
    parsed = TopicResult(topics=["Topic A"])
    bad_response = mock_gemini_response(
        parsed=None,
        text=None,
        finish_reason="STOP",
    )
    good_response = mock_gemini_response(parsed=parsed, finish_reason="STOP")

    generate: AsyncMock = mock_genai_client.aio.models.generate_content
    generate.side_effect = [bad_response, good_response]

    result = await topic_extractor.extract("some source text " * 10)

    assert result == ["Topic A"]
    assert generate.await_count == 2
