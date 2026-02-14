"""Tests for ClaimGenerationService orchestration logic."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.exceptions import EmptyExtractionError
from src.schemas.llm import ClaimWithTopicBaseResult
from src.schemas.responses import ClaimGenerationResponse
from src.services.claim_generation import ClaimGenerationService


@pytest.fixture()
def mock_topic_extractor() -> AsyncMock:
    """Mock TopicExtractor."""
    return AsyncMock()


@pytest.fixture()
def mock_claim_extractor() -> AsyncMock:
    """Mock ClaimExtractor."""
    return AsyncMock()


@pytest.fixture()
def service(
    mock_topic_extractor: AsyncMock,
    mock_claim_extractor: AsyncMock,
) -> ClaimGenerationService:
    """ClaimGenerationService with mocked extractors."""
    return ClaimGenerationService(mock_topic_extractor, mock_claim_extractor)


async def test_generate_claims_success(
    service: ClaimGenerationService,
    mock_topic_extractor: AsyncMock,
    mock_claim_extractor: AsyncMock,
    sample_source_text: str,
) -> None:
    """Service returns ClaimGenerationResponse with correct structure."""
    mock_topic_extractor.extract.return_value = ["Topic A", "Topic B"]
    mock_claim_extractor.extract.return_value = [
        ClaimWithTopicBaseResult(
            topic="Topic A",
            claims=["Claim A1", "Claim A2"],
        ),
        ClaimWithTopicBaseResult(
            topic="Topic B",
            claims=["Claim B1"],
        ),
    ]

    result = await service.generate_claims(sample_source_text)

    assert isinstance(result, ClaimGenerationResponse)
    assert len(result.claims) == 3
    mock_topic_extractor.extract.assert_awaited_once_with(sample_source_text)
    mock_claim_extractor.extract.assert_awaited_once()


async def test_generate_claims_empty_topics_raises(
    service: ClaimGenerationService,
    mock_topic_extractor: AsyncMock,
    sample_source_text: str,
) -> None:
    """Empty topic list raises EmptyExtractionError."""
    mock_topic_extractor.extract.return_value = []

    with pytest.raises(EmptyExtractionError):
        await service.generate_claims(sample_source_text)


async def test_generate_claims_empty_claims_raises(
    service: ClaimGenerationService,
    mock_topic_extractor: AsyncMock,
    mock_claim_extractor: AsyncMock,
    sample_source_text: str,
) -> None:
    """Empty claims for all topics raises EmptyExtractionError."""
    mock_topic_extractor.extract.return_value = ["Topic A"]
    mock_claim_extractor.extract.return_value = [
        ClaimWithTopicBaseResult(topic="Topic A", claims=[]),
    ]

    with pytest.raises(EmptyExtractionError):
        await service.generate_claims(sample_source_text)


async def test_generate_claims_transforms_output_correctly(
    service: ClaimGenerationService,
    mock_topic_extractor: AsyncMock,
    mock_claim_extractor: AsyncMock,
    sample_source_text: str,
) -> None:
    """Verify flattening: 2 topics with 3+2 claims yields 5 ClaimResponse items."""
    mock_topic_extractor.extract.return_value = ["Energy", "Policy"]
    mock_claim_extractor.extract.return_value = [
        ClaimWithTopicBaseResult(
            topic="Energy",
            claims=["Energy claim 1", "Energy claim 2", "Energy claim 3"],
        ),
        ClaimWithTopicBaseResult(
            topic="Policy",
            claims=["Policy claim 1", "Policy claim 2"],
        ),
    ]

    result = await service.generate_claims(sample_source_text)

    assert len(result.claims) == 5

    # Check topic assignments
    energy_claims = [c for c in result.claims if c.claim_topic == "Energy"]
    policy_claims = [c for c in result.claims if c.claim_topic == "Policy"]
    assert len(energy_claims) == 3
    assert len(policy_claims) == 2
    assert energy_claims[0].claim == "Energy claim 1"
    assert policy_claims[1].claim == "Policy claim 2"
