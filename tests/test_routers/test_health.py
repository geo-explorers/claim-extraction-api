"""Tests for the health endpoint."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from fastapi.testclient import TestClient

from src.main import app

if TYPE_CHECKING:
    from collections.abc import Generator


def _health_client() -> Generator[TestClient, None, None]:
    """Create a test client for health tests without service dependencies."""
    os.environ.setdefault("GEMINI_API_KEY", "test-key")
    with TestClient(app) as client:
        yield client


def test_health_returns_ok() -> None:
    """GET /health returns 200 with status ok."""
    for client in _health_client():
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_health_no_auth_required() -> None:
    """GET /health works without any specific API key header."""
    for client in _health_client():
        response = client.get("/health")
        assert response.status_code == 200
