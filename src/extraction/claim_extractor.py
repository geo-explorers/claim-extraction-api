"""Claim extraction from source text using Gemini structured output.

Extracts atomic, self-contained claims organized by topic from source text.
Retries on transient Gemini errors (429 rate limit, 5xx server errors)
and non-deterministic parse failures (malformed JSON from Gemini).
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, cast

from google.genai import errors as genai_errors
from google.genai import types
from json_repair import repair_json
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from src.config.prompts.claim_extraction import CLAIM_EXTRACTION_PROMPT
from src.exceptions import ExtractionError, SafetyFilterError
from src.schemas.llm import ClaimWithTopicBaseResult, ClaimWithTopicResult

if TYPE_CHECKING:
    from google import genai

logger = logging.getLogger(__name__)


def _is_retryable(exc: BaseException) -> bool:
    """Check if an exception is retryable.

    Retries on:
    - Gemini 429 rate limit or 5xx server errors
    - ExtractionError (non-deterministic malformed JSON from Gemini)

    Does NOT retry SafetyFilterError (content blocked — deterministic).
    """
    if isinstance(exc, SafetyFilterError):
        return False
    if isinstance(exc, ExtractionError):
        return True
    if isinstance(exc, genai_errors.ServerError):
        return True
    if isinstance(exc, genai_errors.ClientError):
        return cast("bool", getattr(exc, "code", 0) == 429)
    return False


class ClaimExtractor:
    """Extracts claims organized by topic from source text via Gemini."""

    def __init__(
        self, client: genai.Client, model: str, temperature: float
    ) -> None:
        self._client = client
        self._model = model
        self._config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ClaimWithTopicResult,
            temperature=temperature,
            max_output_tokens=8192,
            safety_settings=[
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
            ],
        )

    async def extract(
        self, source_text: str, topics: list[str]
    ) -> list[ClaimWithTopicBaseResult]:
        """Extract claims from source text organized by the given topics.

        Args:
            source_text: The raw text to extract claims from.
            topics: Ordered list of topic labels to organize claims under.

        Returns:
            List of ClaimWithTopicBaseResult, one per topic with its claims.

        Raises:
            SafetyFilterError: If content is blocked by Gemini safety filters.
            ExtractionError: If response cannot be parsed after retries.
        """
        topics_json = json.dumps(topics)
        prompt = CLAIM_EXTRACTION_PROMPT.format(
            source_text=source_text, topics=topics_json
        )
        result = await self._call_and_parse(prompt)
        return result.claim_topics

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception(_is_retryable),
        reraise=True,
    )
    async def _call_and_parse(self, prompt: str) -> ClaimWithTopicResult:
        """Call Gemini and parse the response, with retry on transient failures."""
        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=prompt,
            config=self._config,
        )

        # Check finish reason for blocking or truncation
        if response.candidates:
            finish_reason = response.candidates[0].finish_reason
            if finish_reason == types.FinishReason.SAFETY:
                raise SafetyFilterError()
            if finish_reason == types.FinishReason.MAX_TOKENS:
                raise ExtractionError(
                    "Claim extraction response truncated (output token limit reached)"
                )

        return self._parse_response(response)

    def _parse_response(self, response: Any) -> ClaimWithTopicResult:
        """Parse Gemini response into ClaimWithTopicResult."""
        # Try .parsed first (typed structured output)
        try:
            parsed: ClaimWithTopicResult | None = cast(
                "ClaimWithTopicResult | None", response.parsed
            )
            if parsed is not None:
                return parsed
        except Exception:
            logger.warning("response.parsed access failed, falling back to text")

        # Fall back to manual JSON parsing from response text
        text: str | None = response.text
        if text is None:
            logger.error(
                "Gemini returned no text; finish_reason=%s",
                response.candidates[0].finish_reason if response.candidates else "N/A",
            )
            raise ExtractionError("Failed to parse claim extraction response: empty text")

        # Try direct parse, then JSON repair fallback
        try:
            return ClaimWithTopicResult.model_validate_json(text)
        except Exception as direct_exc:
            logger.warning("Direct JSON parse failed, attempting repair: %s", direct_exc)

        try:
            repaired = repair_json(text)
            return ClaimWithTopicResult.model_validate_json(repaired)
        except Exception as exc:
            logger.error("Claim response parse failed after repair: %s", exc)
            raise ExtractionError(
                f"Failed to parse claim extraction response: {exc}"
            ) from exc
