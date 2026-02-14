"""Topic extraction from source text using Gemini structured output.

Extracts an ordered list of discussion topics from arbitrary source text.
Retries on transient Gemini errors (429 rate limit, 5xx server errors).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

from google.genai import errors as genai_errors
from google.genai import types
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from src.config.prompts.topic_extraction import TOPIC_EXTRACTION_PROMPT
from src.exceptions import ExtractionError, SafetyFilterError
from src.schemas.llm import TopicResult

if TYPE_CHECKING:
    from google import genai

logger = logging.getLogger(__name__)


def _is_retryable(exc: BaseException) -> bool:
    """Check if an exception is retryable (429 rate limit or 5xx server error)."""
    if isinstance(exc, genai_errors.ServerError):
        return True
    if isinstance(exc, genai_errors.ClientError):
        return cast("bool", getattr(exc, "code", 0) == 429)
    return False


class TopicExtractor:
    """Extracts discussion topics from source text via Gemini."""

    def __init__(
        self, client: genai.Client, model: str, temperature: float
    ) -> None:
        self._client = client
        self._model = model
        self._config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=TopicResult,
            temperature=temperature,
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

    async def extract(self, source_text: str) -> list[str]:
        """Extract topics from source text.

        Args:
            source_text: The raw text to extract topics from.

        Returns:
            Ordered list of topic label strings.

        Raises:
            SafetyFilterError: If content is blocked by Gemini safety filters.
            ExtractionError: If response cannot be parsed.
        """
        prompt = TOPIC_EXTRACTION_PROMPT.format(source_text=source_text)
        response = await self._call_gemini(prompt)

        # Check for safety blocking
        if response.candidates:
            finish_reason = response.candidates[0].finish_reason
            if finish_reason == types.FinishReason.SAFETY:
                raise SafetyFilterError()

        # Parse response: try .parsed first, fall back to manual JSON parse
        result = self._parse_response(response)
        return result.topics

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception(_is_retryable),
        reraise=True,
    )
    async def _call_gemini(self, prompt: str) -> Any:
        """Call Gemini API with retry on transient errors."""
        return await self._client.aio.models.generate_content(
            model=self._model,
            contents=prompt,
            config=self._config,
        )

    def _parse_response(self, response: Any) -> TopicResult:
        """Parse Gemini response into TopicResult."""
        # Try .parsed first (typed structured output)
        parsed: TopicResult | None = cast("TopicResult | None", response.parsed)
        if parsed is not None:
            return parsed

        # Fall back to manual JSON parsing from response text
        try:
            text: str | None = response.text
            if text is None:
                raise ExtractionError("Failed to parse topic extraction response")
            return TopicResult.model_validate_json(text)
        except Exception as exc:
            if isinstance(exc, ExtractionError):
                raise
            raise ExtractionError(
                "Failed to parse topic extraction response"
            ) from exc
