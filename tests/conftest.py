"""Shared test fixtures for the Claim API test suite.

Provides mock Gemini clients, sample data, and app test client.
All tests mock Gemini -- NO real API calls.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.dependencies import get_claim_generation_service
from src.main import app
from src.schemas.llm import ClaimWithTopicBaseResult, ClaimWithTopicResult, TopicResult
from src.schemas.responses import ClaimGenerationResponse, ClaimResponse
from src.services.claim_generation import ClaimGenerationService

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture()
def sample_source_text() -> str:
    """A realistic 200-word news article snippet about renewable energy."""
    return (
        "The European Union announced a landmark renewable energy investment "
        "package worth 50 billion euros on Tuesday, marking the largest single "
        "commitment to clean energy in the bloc's history. The initiative, dubbed "
        "the Green Transition Accelerator, will fund solar and wind installations "
        "across 15 member states over the next decade. European Commission President "
        "Ursula von der Leyen described the package as essential for meeting the EU's "
        "2050 net-zero targets. The funding will be distributed through a competitive "
        "grant process, with priority given to projects in regions heavily dependent "
        "on fossil fuels. Poland and Germany are expected to receive the largest "
        "allocations, reflecting their current reliance on coal and natural gas. "
        "Environmental groups have broadly welcomed the announcement, though some "
        "critics argue the timeline is too slow. Greenpeace spokesperson Maria Santos "
        "noted that the investment, while substantial, represents only a fraction of "
        "what is needed to avert the worst effects of climate change. Meanwhile, "
        "industry representatives expressed concern about the regulatory requirements "
        "attached to the funding, warning that excessive red tape could delay project "
        "implementation by years."
    )


@pytest.fixture()
def sample_short_text() -> str:
    """A string below the minimum length threshold."""
    return "Too short to extract claims."


@pytest.fixture()
def sample_topics() -> list[str]:
    """Sample topics extracted from the renewable energy article."""
    return ["Renewable Energy Investment", "Policy Changes", "Economic Impact"]


@pytest.fixture()
def sample_topic_result(sample_topics: list[str]) -> TopicResult:
    """A TopicResult instance with sample topics."""
    return TopicResult(topics=sample_topics)


@pytest.fixture()
def sample_claims_result() -> ClaimWithTopicResult:
    """A ClaimWithTopicResult with realistic claims organized by topic."""
    return ClaimWithTopicResult(
        claim_topics=[
            ClaimWithTopicBaseResult(
                topic="Renewable Energy Investment",
                claims=[
                    "The EU announced a 50 billion euro renewable energy package.",
                    "The Green Transition Accelerator funds solar and wind.",
                    "The funding covers 15 EU member states over the next decade.",
                ],
            ),
            ClaimWithTopicBaseResult(
                topic="Policy Changes",
                claims=[
                    "Von der Leyen called the package essential for net-zero.",
                    "Funding uses competitive grants for fossil-fuel regions.",
                ],
            ),
        ]
    )


@pytest.fixture()
def mock_gemini_response() -> Any:
    """Factory fixture creating a mock Gemini response."""

    def _create(
        parsed: Any = None,
        text: str | None = None,
        finish_reason: str = "STOP",
    ) -> MagicMock:
        response = MagicMock()
        response.parsed = parsed
        response.text = text

        candidate = MagicMock()
        candidate.finish_reason = finish_reason
        response.candidates = [candidate]

        return response

    return _create


@pytest.fixture()
def mock_genai_client() -> MagicMock:
    """A mock genai.Client with async generate_content."""
    client = MagicMock()
    client.aio = MagicMock()
    client.aio.models = MagicMock()
    client.aio.models.generate_content = AsyncMock()
    return client


@pytest.fixture()
def mock_claim_generation_service() -> AsyncMock:
    """A mock ClaimGenerationService for endpoint testing."""
    service = AsyncMock(spec=ClaimGenerationService)
    return service


@pytest.fixture()
def app_client(
    mock_claim_generation_service: AsyncMock,
) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with mocked service dependency.

    Overrides the get_claim_generation_service dependency so no real
    Gemini calls are made during endpoint tests.
    """
    os.environ.setdefault("GEMINI_API_KEY", "test-key")

    app.dependency_overrides[get_claim_generation_service] = (
        lambda: mock_claim_generation_service
    )
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture()
def sample_claim_generation_response() -> ClaimGenerationResponse:
    """A complete ClaimGenerationResponse for endpoint testing."""
    return ClaimGenerationResponse(
        claims=[
            ClaimResponse(
                claim_topic="Renewable Energy Investment",
                claim=(
                    "The EU announced a 50 billion euro renewable "
                    "energy investment package."
                ),
            ),
            ClaimResponse(
                claim_topic="Policy Changes",
                claim=(
                    "Von der Leyen called the package essential "
                    "for 2050 net-zero targets."
                ),
            ),
        ]
    )
