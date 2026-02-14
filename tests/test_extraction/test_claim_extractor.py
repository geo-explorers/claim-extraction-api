"""Tests for ClaimExtractor with mocked Gemini client."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from src.exceptions import ExtractionError
from src.schemas.llm import ClaimWithTopicBaseResult, ClaimWithTopicResult

if TYPE_CHECKING:
    from unittest.mock import AsyncMock, MagicMock


@pytest.fixture()
def claim_extractor(mock_genai_client: MagicMock) -> Any:
    """ClaimExtractor wired to a mock Gemini client."""
    from src.extraction.claim_extractor import ClaimExtractor

    return ClaimExtractor(
        client=mock_genai_client,
        model="gemini-2.5-flash",
        temperature=0.2,
    )


async def test_extract_claims_success(
    claim_extractor: Any,
    mock_genai_client: MagicMock,
    mock_gemini_response: Any,
) -> None:
    """Successful extraction returns list of ClaimWithTopicBaseResult."""
    parsed = ClaimWithTopicResult(
        claim_topics=[
            ClaimWithTopicBaseResult(
                topic="Energy",
                claims=["Claim 1", "Claim 2"],
            ),
        ]
    )
    response = mock_gemini_response(parsed=parsed, finish_reason="STOP")
    generate: AsyncMock = mock_genai_client.aio.models.generate_content
    generate.return_value = response

    result = await claim_extractor.extract("some source text " * 10, ["Energy"])

    assert len(result) == 1
    assert result[0].topic == "Energy"
    assert result[0].claims == ["Claim 1", "Claim 2"]
    generate.assert_awaited_once()


async def test_extract_claims_fallback_parsing(
    claim_extractor: Any,
    mock_genai_client: MagicMock,
    mock_gemini_response: Any,
) -> None:
    """When .parsed is None, falls back to parsing .text as JSON."""
    json_text = (
        '{"claim_topics": [{"topic": "Policy", "claims": ["Fallback claim"]}]}'
    )
    response = mock_gemini_response(
        parsed=None,
        text=json_text,
        finish_reason="STOP",
    )
    generate: AsyncMock = mock_genai_client.aio.models.generate_content
    generate.return_value = response

    result = await claim_extractor.extract(
        "some source text " * 10, ["Policy"]
    )

    assert len(result) == 1
    assert result[0].topic == "Policy"
    assert result[0].claims == ["Fallback claim"]


async def test_extract_claims_parse_failure_raises(
    claim_extractor: Any,
    mock_genai_client: MagicMock,
    mock_gemini_response: Any,
) -> None:
    """Invalid JSON in .text raises ExtractionError."""
    response = mock_gemini_response(
        parsed=None,
        text="not valid json at all",
        finish_reason="STOP",
    )
    generate: AsyncMock = mock_genai_client.aio.models.generate_content
    generate.return_value = response

    with pytest.raises(ExtractionError):
        await claim_extractor.extract(
            "some source text " * 10, ["Topic"]
        )


async def test_extract_claims_includes_topics_in_prompt(
    claim_extractor: Any,
    mock_genai_client: MagicMock,
    mock_gemini_response: Any,
) -> None:
    """The prompt sent to Gemini includes the topic list."""
    parsed = ClaimWithTopicResult(
        claim_topics=[
            ClaimWithTopicBaseResult(
                topic="Science",
                claims=["Science claim 1"],
            ),
        ]
    )
    response = mock_gemini_response(parsed=parsed, finish_reason="STOP")
    generate: AsyncMock = mock_genai_client.aio.models.generate_content
    generate.return_value = response

    await claim_extractor.extract(
        "some source text " * 10,
        ["Science", "Technology"],
    )

    # Verify the contents arg includes both topics
    call_kwargs = generate.call_args
    contents_arg: str = call_kwargs.kwargs.get(
        "contents",
        call_kwargs.args[0] if call_kwargs.args else "",
    )
    assert "Science" in contents_arg
    assert "Technology" in contents_arg
