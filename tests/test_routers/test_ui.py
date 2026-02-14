"""Tests for the web UI route."""

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
def ui_client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    """Create a test client for UI tests without GEMINI_API_KEY."""
    _clear_gemini_key(monkeypatch)
    with TestClient(app) as client:
        yield client


def test_index_returns_html(ui_client: TestClient) -> None:
    """GET / returns 200 with content-type text/html and body containing Claim Extractor."""
    response = ui_client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Claim Extractor" in response.text


def test_index_contains_textarea(ui_client: TestClient) -> None:
    """GET / response body contains the source-text textarea."""
    response = ui_client.get("/")
    assert 'id="source-text"' in response.text


def test_index_contains_generate_button(ui_client: TestClient) -> None:
    """GET / response body contains the generate button."""
    response = ui_client.get("/")
    assert 'id="generate-btn"' in response.text


def test_index_loads_app_js(ui_client: TestClient) -> None:
    """GET / response body contains the app.js script tag."""
    response = ui_client.get("/")
    assert "/static/app.js" in response.text


def test_static_app_js_served(ui_client: TestClient) -> None:
    """GET /static/app.js returns 200 with JavaScript content type."""
    response = ui_client.get("/static/app.js")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
