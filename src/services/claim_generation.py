"""Claim generation orchestration service.

Coordinates the two-step extraction pipeline: topic extraction then claim extraction.
Transforms LLM output shape into the API response shape.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from tenacity import RetryError

from src.exceptions import EmptyExtractionError, LLMProviderError
from src.schemas.responses import ClaimGenerationResponse, ClaimResponse
from src.utils.text import sanitize_source_text

if TYPE_CHECKING:
    from src.extraction.claim_extractor import ClaimExtractor
    from src.extraction.topic_extractor import TopicExtractor

logger = logging.getLogger(__name__)


class ClaimGenerationService:
    """Orchestrates topic extraction -> claim extraction pipeline."""

    def __init__(
        self,
        topic_extractor: TopicExtractor,
        claim_extractor: ClaimExtractor,
    ) -> None:
        self._topic_extractor = topic_extractor
        self._claim_extractor = claim_extractor

    async def generate_claims(self, source_text: str) -> ClaimGenerationResponse:
        """Run the full extraction pipeline on source text.

        Args:
            source_text: Raw text to extract claims from.

        Returns:
            ClaimGenerationResponse with flattened list of topic-claim pairs.

        Raises:
            EmptyExtractionError: If no topics or no claims could be extracted.
            LLMProviderError: If Gemini calls fail after all retries exhausted.
            SafetyFilterError: If content is blocked by safety filters.
            ExtractionError: If response parsing fails.
        """
        try:
            # Normalize Unicode that triggers Gemini JSON escaping bugs
            source_text = sanitize_source_text(source_text)

            # Step 1: Extract topics
            topics = await self._topic_extractor.extract(source_text)
            if not topics:
                raise EmptyExtractionError(
                    "No topics could be extracted from the source text"
                )
            logger.info("Extracted %d topics", len(topics))

            # Step 2: Extract claims organized by topics
            claims_by_topic = await self._claim_extractor.extract(
                source_text, topics
            )

            # Transform LLM output shape to API response shape
            claims: list[ClaimResponse] = []
            for item in claims_by_topic:
                for claim_text in item.claims:
                    claims.append(
                        ClaimResponse(claim_topic=item.topic, claim=claim_text)
                    )

            if not claims:
                raise EmptyExtractionError(
                    "No claims could be extracted from the source text"
                )

            logger.info("Extracted %d total claims across %d topics", len(claims), len(topics))
            return ClaimGenerationResponse(claims=claims)

        except RetryError as exc:
            original = exc.last_attempt.exception() if exc.last_attempt else None
            detail = f"LLM provider error after retries exhausted: {original}"
            raise LLMProviderError(detail=detail) from exc
