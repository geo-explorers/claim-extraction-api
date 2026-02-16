"""Tests for text sanitization utility."""

from __future__ import annotations

from src.utils.text import sanitize_source_text


def test_smart_quotes_normalized() -> None:
    """Smart/curly quotes are replaced with ASCII equivalents."""
    text = "\u201cHello,\u201d she said. \u2018World.\u2019"
    result = sanitize_source_text(text)
    assert result == '"Hello," she said. \'World.\''


def test_em_dash_normalized() -> None:
    """Em dashes are replaced with double hyphens."""
    text = "word\u2014another word"
    result = sanitize_source_text(text)
    assert result == "word--another word"


def test_en_dash_normalized() -> None:
    """En dashes are replaced with hyphens."""
    text = "pages 10\u201320"
    result = sanitize_source_text(text)
    assert result == "pages 10-20"


def test_ellipsis_normalized() -> None:
    """Unicode ellipsis is replaced with three dots."""
    text = "and so on\u2026"
    result = sanitize_source_text(text)
    assert result == "and so on..."


def test_nbsp_normalized() -> None:
    """Non-breaking space is replaced with regular space."""
    text = "hello\u00a0world"
    result = sanitize_source_text(text)
    assert result == "hello world"


def test_crlf_normalized() -> None:
    """Windows line endings are normalized to Unix."""
    text = "line one\r\nline two\r\nline three"
    result = sanitize_source_text(text)
    assert result == "line one\nline two\nline three"


def test_excessive_newlines_collapsed() -> None:
    """Three or more consecutive newlines are collapsed to two."""
    text = "paragraph one\n\n\n\nparagraph two\n\n\n\n\nparagraph three"
    result = sanitize_source_text(text)
    assert result == "paragraph one\n\nparagraph two\n\nparagraph three"


def test_double_newlines_preserved() -> None:
    """Normal paragraph breaks (double newlines) are not altered."""
    text = "paragraph one\n\nparagraph two"
    result = sanitize_source_text(text)
    assert result == "paragraph one\n\nparagraph two"


def test_plain_ascii_unchanged() -> None:
    """Plain ASCII text passes through unmodified."""
    text = "Hello, world! This is a test. No special chars here."
    result = sanitize_source_text(text)
    assert result == text


def test_combined_sanitization() -> None:
    """Multiple sanitization rules apply together."""
    text = "\u201cHello\u201d \u2014 she said\u2026\r\n\r\n\r\nNext paragraph."
    result = sanitize_source_text(text)
    assert result == '"Hello" -- she said...\n\nNext paragraph.'
