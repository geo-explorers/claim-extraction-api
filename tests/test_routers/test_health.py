"""Tests for the health endpoint."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from src.main import app

if TYPE_CHECKING:
    from collections.abc import Generator


def _clear_gemini_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Override GEMINI_API_KEY to empty string so .env file value is ignored."""
    monkeypatch.setenv("GEMINI_API_KEY", "")


@pytest.fixture()
def health_client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    """Create a test client for health tests without GEMINI_API_KEY."""
    _clear_gemini_key(monkeypatch)
    with TestClient(app) as client:
        yield client


def test_health_returns_ok(health_client: TestClient) -> None:
    """GET /health returns 200 with status ok."""
    response = health_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_no_auth_required(health_client: TestClient) -> None:
    """GET /health works without any specific API key header."""
    response = health_client.get("/health")
    assert response.status_code == 200


def test_health_works_without_gemini_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GET /health returns 200 even when GEMINI_API_KEY is not set.

    This is the KEY test proving the gap is closed: the app starts
    and the health endpoint responds without requiring Gemini config.
    """
    _clear_gemini_key(monkeypatch)
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_generate_returns_503_without_gemini_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST /generate/claims returns 503 when GEMINI_API_KEY is not set.

    When the Gemini API key is absent, the app starts successfully but
    the generate endpoints return a clear 503 Service Unavailable error.
    """
    _clear_gemini_key(monkeypatch)
    with TestClient(app) as client:
        response = client.post(
            "/generate/claims",
            json={
                "source_text": "Test text that is long enough "
                "to pass validation. " * 10
            },
        )
        assert response.status_code == 503
        data = response.json()
        assert "not configured" in data["detail"].lower()
