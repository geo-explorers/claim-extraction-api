"""Text sanitization for LLM input.

Normalizes Unicode characters that trigger escape sequence bugs
in Gemini structured JSON output.
"""

from __future__ import annotations

import re

# Smart/curly quotes → ASCII
_QUOTE_MAP: dict[str, str] = {
    "\u201c": '"',  # "
    "\u201d": '"',  # "
    "\u2018": "'",  # '
    "\u2019": "'",  # '
    "\u201a": "'",  # ‚
    "\u201b": "'",  # ‛
    "\u201e": '"',  # „
    "\u201f": '"',  # ‟
}

# Dashes → ASCII
_DASH_MAP: dict[str, str] = {
    "\u2014": "--",  # em dash —
    "\u2013": "-",   # en dash –
}

# Other problematic Unicode → ASCII
_MISC_MAP: dict[str, str] = {
    "\u2026": "...",  # ellipsis …
    "\u00a0": " ",    # non-breaking space
}

_CHAR_MAP: dict[str, str] = {**_QUOTE_MAP, **_DASH_MAP, **_MISC_MAP}
_CHAR_PATTERN = re.compile("|".join(re.escape(c) for c in _CHAR_MAP))

# 3+ consecutive newlines → double newline
_EXCESSIVE_NEWLINES = re.compile(r"\n{3,}")


def sanitize_source_text(text: str) -> str:
    """Normalize Unicode characters that cause Gemini JSON escaping bugs.

    Applies:
        - Smart/curly quotes → ASCII quotes
        - Em/en dashes → ASCII dashes
        - Ellipsis, NBSP → ASCII equivalents
        - \\r\\n → \\n
        - Collapse 3+ consecutive newlines to \\n\\n
    """
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Replace problematic Unicode characters
    text = _CHAR_PATTERN.sub(lambda m: _CHAR_MAP[m.group()], text)

    # Collapse excessive newlines
    text = _EXCESSIVE_NEWLINES.sub("\n\n", text)

    return text
