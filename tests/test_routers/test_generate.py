"""Tests for the POST /generate/claims endpoint."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.exceptions import ExtractionError, LLMProviderError

if TYPE_CHECKING:
    from unittest.mock import AsyncMock

    from fastapi.testclient import TestClient

    from src.schemas.responses import ClaimGenerationResponse


def test_generate_claims_success(
    app_client: TestClient,
    mock_claim_generation_service: AsyncMock,
    sample_claim_generation_response: ClaimGenerationResponse,
    sample_source_text: str,
) -> None:
    """POST /generate/claims with valid text returns 200 with claims."""
    mock_claim_generation_service.generate_claims.return_value = (
        sample_claim_generation_response
    )

    response = app_client.post(
        "/generate/claims",
        json={"source_text": sample_source_text},
    )

    assert response.status_code == 200
    data = response.json()
    assert "claims" in data
    assert len(data["claims"]) == 2
    assert data["claims"][0]["claim_topic"] == "Renewable Energy Investment"
    assert "claim" in data["claims"][0]


def test_generate_claims_empty_text(app_client: TestClient) -> None:
    """POST with empty source_text returns 422."""
    response = app_client.post(
        "/generate/claims",
        json={"source_text": ""},
    )
    assert response.status_code == 422


def test_generate_claims_too_short(app_client: TestClient) -> None:
    """POST with source_text below min_length returns 422."""
    response = app_client.post(
        "/generate/claims",
        json={"source_text": "short"},
    )
    assert response.status_code == 422


def test_generate_claims_too_long(app_client: TestClient) -> None:
    """POST with source_text above max_length returns 422."""
    response = app_client.post(
        "/generate/claims",
        json={"source_text": "x" * 50001},
    )
    assert response.status_code == 422


def test_generate_claims_missing_field(app_client: TestClient) -> None:
    """POST with empty body returns 422."""
    response = app_client.post(
        "/generate/claims",
        json={},
    )
    assert response.status_code == 422


def test_generate_claims_extraction_error(
    app_client: TestClient,
    mock_claim_generation_service: AsyncMock,
    sample_source_text: str,
) -> None:
    """Extraction errors surface as 502 with descriptive message."""
    mock_claim_generation_service.generate_claims.side_effect = ExtractionError(
        "test extraction error"
    )

    response = app_client.post(
        "/generate/claims",
        json={"source_text": sample_source_text},
    )

    assert response.status_code == 502
    assert "test extraction error" in response.json()["detail"]


def test_generate_claims_llm_provider_error(
    app_client: TestClient,
    mock_claim_generation_service: AsyncMock,
    sample_source_text: str,
) -> None:
    """LLM provider errors surface as 502."""
    mock_claim_generation_service.generate_claims.side_effect = LLMProviderError()

    response = app_client.post(
        "/generate/claims",
        json={"source_text": sample_source_text},
    )

    assert response.status_code == 502
    assert "LLM provider error" in response.json()["detail"]
