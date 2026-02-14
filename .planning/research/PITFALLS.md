# Pitfalls Research

**Domain:** LLM-powered stateless claim extraction API (Gemini structured outputs)
**Researched:** 2026-02-14
**Confidence:** MEDIUM-HIGH (evidence from extraction-api codebase + training data knowledge; no live web verification available)

## Critical Pitfalls

### Pitfall 1: Silent Empty Responses on Gemini API Failures

**What goes wrong:**
Gemini returns empty results (empty topic list, empty claims dict) on API errors, and the service silently returns `[]` or `{}` to the caller. The user sees an empty table with no error message, no indication anything went wrong. They assume the text had no claims.

**Why it happens:**
The extraction-api's `premium_claim_extractor.py` catches all exceptions and returns empty lists/dicts as fallback (lines 120-124, 178-182). This was acceptable for a batch pipeline where failures get logged and retried, but in a user-facing API, silent degradation is a terrible UX. The root cause: Gemini API errors include rate limiting (429), safety filter blocks, malformed schema responses, and transient network failures -- all of which get swallowed.

**How to avoid:**
- Never return empty results silently from a user-facing endpoint. Propagate errors to the API layer as typed exceptions.
- Distinguish between "the text genuinely produced no claims" (valid empty) and "the LLM call failed" (error state). Return different HTTP status codes for each.
- Log the raw Gemini response on failure (the extraction-api does this: `response.text[:500]`). Keep this pattern.
- For the two-step pipeline: if topic extraction fails, do NOT proceed to claim extraction. Fail fast with a clear error.

**Warning signs:**
- Users report "it returned nothing" on texts that clearly contain claims
- Logs show `Error in premium topic extraction` or `Error in premium claim extraction` but API returns 200 OK with empty data
- Gemini `response.text` is `None` or contains a safety filter block message instead of JSON

**Phase to address:**
Phase 1 (Core API) -- error handling must be designed from the start, not bolted on. Define explicit error types: `ExtractionError`, `LLMProviderError`, `SafetyFilterError`, `EmptyInputError`.

---

### Pitfall 2: Prompt Brittle to Non-Podcast Source Text

**What goes wrong:**
The claim extraction and topic prompts from extraction-api are deeply podcast-specific. Directly reusing them on arbitrary source text (news articles, research papers, literature) produces poor-quality claims: topics that don't make sense, claims that reference "the episode" or "the host," ad-filtering logic that rejects legitimate content as "promotional."

**Why it happens:**
The extraction-api prompts contain:
- "podcast transcript" terminology throughout (CLAIM_EXTRACTION_PROMPT, TOPICS_OF_DISCUSSION_PROMPT)
- "host," "guest," "episode" references in topic extraction
- Ad filtering step (Step 1 in claim extraction prompt) that aggressively filters "sign up," "subscribe," "go to [URL]" -- which are legitimate content in news articles or research citations
- "Sponsorship Disclosures" filtering that would incorrectly remove funding acknowledgments in research papers
- Topic count guidance "6-14 topics for typical episodes" tuned for 1-2 hour podcasts, not 500-word news articles

**How to avoid:**
- Adapt prompts before using them. Replace all "transcript"/"podcast"/"episode" references with generic "source text" language.
- Remove or make optional the ad-filtering step. For a general-purpose tool, over-filtering is worse than under-filtering.
- Scale topic count guidance to text length: short texts (< 1000 words) should produce 2-5 topics, not 6-14.
- Test prompts against at least three text types before shipping: (1) news article, (2) research paper abstract, (3) long-form essay.
- Keep the self-containment rules (the "Shuffle Rule," pronoun replacement, attribution stripping) -- these are domain-agnostic and high-value.

**Warning signs:**
- Claims referencing "the episode" or "the speaker" when processing a news article
- Topic labels like "Overview of episode's key themes" appearing for non-podcast text
- Legitimate URLs in research papers being filtered as "promotional"
- Very short texts producing 0 topics (the 6-topic minimum filters them out)

**Phase to address:**
Phase 1 (Core API) -- prompt adaptation is the single most important task. This is not a "polish later" item. The prompts ARE the product.

---

### Pitfall 3: Gemini Structured Output Schema Mismatch Between `response_schema` and `response_json_schema`

**What goes wrong:**
The google-genai SDK has two ways to specify structured outputs: `response_schema=PydanticModel` (passes the Pydantic model directly) and `response_json_schema=Model.model_json_schema()` (passes the JSON schema dict). These behave differently. Using the wrong one causes either runtime errors, schema validation failures, or silently incorrect parsing.

**Why it happens:**
The extraction-api itself uses BOTH patterns inconsistently:
- `premium_claim_extractor.py` uses `response_schema=TopicDiscussionResult` (Pydantic model)
- `gemini_service.py` uses `response_json_schema=ClaimValidationResponse.model_json_schema()` (JSON schema dict)

The `response_schema` parameter (Pydantic model) is the newer, preferred approach in the google-genai SDK. It handles schema conversion internally and supports more Pydantic features. The `response_json_schema` parameter requires manual schema conversion and may not handle all Pydantic v2 features correctly (e.g., discriminated unions, complex validators).

Additionally, Gemini structured outputs have schema constraints:
- No support for `Optional` fields in some model versions (field must be required or have a default)
- Nested model depth limits
- List items must be homogeneous
- Enum values must be strings
- `description` fields in Pydantic models become schema descriptions that guide the LLM

**How to avoid:**
- Standardize on `response_schema=PydanticModel` (the pattern from `premium_claim_extractor.py`). This is the cleaner, more supported path.
- Always validate the response with `PydanticModel.model_validate_json(response.text)` after receiving it, even though structured outputs should guarantee the schema. Defense in depth.
- Keep Pydantic models simple: `str`, `int`, `float`, `bool`, `List[T]`, `Optional[T]`. Avoid complex validators, computed fields, or discriminated unions in response schemas.
- Test schema changes against the actual Gemini API, not just locally. The schema-to-LLM behavior can differ from what Pydantic validates.

**Warning signs:**
- `ValidationError` from Pydantic when parsing Gemini responses
- Gemini returning JSON that doesn't match the expected structure
- Fields showing up as `null` when they should be required
- Different behavior between `gemini-2.5-flash` and `gemini-2.5-pro` for the same schema

**Phase to address:**
Phase 1 (Core API) -- pick one pattern and use it consistently from the start. Standardize on `response_schema=PydanticModel`.

---

### Pitfall 4: Two-Step Extraction Creates Cascading Failure and Doubled Latency

**What goes wrong:**
The two-step pipeline (topics first, then claims mapped to topics) means two sequential Gemini API calls per request. If the first call (topics) returns bad results, the second call (claims) produces garbage. Meanwhile, the user waits for both calls to complete -- potentially 15-30+ seconds for large texts with Gemini Pro.

**Why it happens:**
The extraction-api designed this for batch processing where latency was not user-facing. A 30-60 second pipeline was acceptable. For a synchronous web UI where a user clicks "Generate" and stares at a spinner, this is painful. Furthermore, topic extraction quality directly determines claim quality: if topics are wrong, claims get assigned to wrong topics or discarded entirely (the extraction-api filters topics with < 3 claims).

**How to avoid:**
- Accept the two-step architecture (it produces better results than single-step) but mitigate the UX impact:
  - Show a loading indicator with progress ("Extracting topics..." then "Extracting claims...")
  - Consider streaming the response: return topics first, then claims as they arrive
  - Use `gemini-2.5-flash` for topic extraction (fast, cheap) and `gemini-2.5-pro` for claim extraction (higher quality) -- or flash for both if latency is critical
- Add a configurable timeout per step (not just overall). If topic extraction takes > 10s, something is wrong.
- Validate topic output before proceeding: if 0 topics returned, return an error immediately instead of making a second LLM call with empty topic context.
- For the frontend: use async polling or Server-Sent Events (SSE) so the user sees incremental progress.

**Warning signs:**
- Average response time > 20 seconds for moderate-length texts
- Users refreshing the page because they think it hung
- Second LLM call producing empty claims because topic list was empty/garbage
- Railway deployment timing out (Railway has a 5-minute request timeout by default, but long-running requests consume resources)

**Phase to address:**
Phase 1 (Core API) for the basic timeout/validation; Phase 2 (Frontend) for UX loading states and progress indication.

---

### Pitfall 5: Gemini API Rate Limits and Cost Explosion on the Free Tier

**What goes wrong:**
Gemini API has per-minute rate limits (especially on the free tier: 2 RPM for Pro, 15 RPM for Flash). Each user request triggers 2 LLM calls. With even modest concurrent usage, rate limits are hit immediately. On the paid tier, cost scales linearly with text length since Gemini charges per input/output token -- a single research paper can consume significant tokens.

**Why it happens:**
Developers test with the free tier (generous token limits per day but low RPM) and don't discover rate limit issues until multiple users hit the service simultaneously. The extraction-api handles this with retries and exponential backoff in `gemini_service.py`, but the premium extractor in `premium_claim_extractor.py` has NO retry logic -- it catches the exception and returns empty.

**How to avoid:**
- Implement retry with exponential backoff on the Gemini client from day one. Handle `429 Resource Exhausted` and `503 Service Unavailable` explicitly.
- Add request queuing or rate limiting at the API level (e.g., `slowapi` or `fastapi-limiter`) so users get a "please wait" instead of a silent failure.
- Use `gemini-2.5-flash` as the default model -- it has higher rate limits (30 RPM free, 2000 RPM paid) and is significantly cheaper than Pro.
- Log token usage per request (input + output tokens from the Gemini response metadata) so you can monitor cost.
- Set a maximum input text length to prevent a single request from consuming excessive tokens (e.g., 50,000 characters / ~12,500 tokens).

**Warning signs:**
- `google.api_core.exceptions.ResourceExhausted: 429` in logs
- Intermittent empty results that "work when you try again"
- Monthly Gemini API bill surprises
- Users pasting entire books into the textarea

**Phase to address:**
Phase 1 (Core API) -- retry logic and rate limiting are infrastructure concerns that must be built in, not added later.

---

### Pitfall 6: Safety Filters Blocking Legitimate Content

**What goes wrong:**
Gemini's safety filters can block requests containing content about violence, political topics, health claims, or controversial subjects. The response comes back empty or with a `finish_reason` of `SAFETY` instead of `STOP`. For a claim extraction tool processing news articles about conflict, health research, or political events, this is a critical failure.

**Why it happens:**
Gemini applies content safety filters by default. The extraction-api's `gemini_service.py` already handles this with `BLOCK_NONE` safety settings, but the `premium_claim_extractor.py` does NOT configure safety settings at all -- it relies on defaults. When processing text about political violence, health misinformation, or sensitive topics, the default safety filters can reject the entire request.

**How to avoid:**
- Configure safety settings to `BLOCK_NONE` for all categories in the GenerateContentConfig. The extraction-api's `gemini_service.py` already does this correctly -- copy that pattern.
- Check `response.candidates[0].finish_reason` after each call. If it's `SAFETY` instead of `STOP`, the response was truncated or blocked. Raise a specific `SafetyFilterError` instead of silently returning partial/empty data.
- Document this clearly: if the Gemini API ever changes to disallow `BLOCK_NONE`, you need a fallback strategy.

**Warning signs:**
- Gemini response `finish_reason` is `SAFETY` or `BLOCKED`
- Responses that are mysteriously empty for political/health/violence content
- `response.text` raising an exception because there are no candidates

**Phase to address:**
Phase 1 (Core API) -- configure safety settings in the Gemini client initialization.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Returning empty list on LLM error | Service never crashes | Users get silent failures, no way to distinguish "no claims found" from "LLM error" | Never in user-facing API |
| Hardcoding prompts as Python strings | Simple to edit | No versioning, no A/B testing, no way to update without redeploying | MVP only -- move to config or files in Phase 2 |
| Using synchronous Gemini client with `run_in_executor` | Works with async FastAPI | Thread pool exhaustion under load, no cancellation support | Acceptable until google-genai adds native async |
| No input text length validation | Users can paste anything | Token cost explosion, Gemini timeout on huge texts, OOM on response parsing | Never -- add from Phase 1 |
| Serving frontend from same FastAPI process | Single deployment unit | Static file serving consumes API worker threads, no CDN, no caching headers | Acceptable for this project scope (low traffic internal tool) |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| google-genai SDK | Using `generate_content` synchronously in async FastAPI routes, blocking the event loop | Wrap in `asyncio.to_thread()` or `loop.run_in_executor()` as the extraction-api does |
| google-genai SDK | Not setting `response_mime_type="application/json"` alongside `response_schema` | Always set both: `response_mime_type="application/json"` AND `response_schema=PydanticModel` |
| Gemini API Key | Committing API key to git or Docker image | Use environment variables. Railway sets these via dashboard. Never bake into Dockerfile. |
| Railway deployment | Not reading `PORT` from environment variable | Railway injects `PORT` env var. FastAPI/uvicorn must bind to `0.0.0.0:$PORT`. The extraction-api handles this in `server.py`. |
| Railway deployment | Setting a health check path that requires the LLM to be ready | Use a simple `/health` endpoint that returns 200 without triggering any LLM calls. Do NOT use `/docs` (Swagger UI) as health check -- it works but is slow. |
| Pydantic response schemas | Using `Optional` fields or complex types (Union, Literal) in Gemini response schemas | Stick to simple types: `str`, `int`, `float`, `bool`, `List[str]`, `List[BaseModel]`. Gemini schema support is narrower than full Pydantic. |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| No input text length limit | Requests take 60+ seconds, Gemini may timeout or return truncated output | Validate `len(source_text)` and reject texts over 50,000 chars with 413 status | When a user pastes a full research paper (> 30 pages) |
| Two sequential LLM calls without timeout per step | One slow call makes the entire request take 2x expected time | Set per-step timeouts (e.g., 30s for topics, 60s for claims) with `asyncio.wait_for()` | Under load or with Gemini Pro's "thinking" mode enabled |
| No response caching | Same text extracted multiple times wastes LLM tokens | Hash the input text and cache results in-memory (LRU) for the session | When users click "Generate" repeatedly on the same text |
| Gemini client initialization on every request | Creating `genai.Client()` per request adds latency | Initialize client once at app startup (singleton pattern, as extraction-api does) | Immediately noticeable -- adds 100-200ms per request |
| Large Pydantic model validation on big responses | `model_validate_json()` on 100KB+ JSON responses is slow | Set `max_output_tokens` on Gemini config to bound response size | When extracting from very long texts with 100+ claims |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Exposing Gemini API key in frontend JavaScript | API key theft, unauthorized usage, billing to your account | API key stays server-side only. Frontend calls your FastAPI backend, never Gemini directly. |
| No input sanitization of source text | Prompt injection: user crafts text that manipulates the extraction prompt to produce arbitrary output | Treat source text as untrusted data. Wrap it in clear delimiters in the prompt. Use structured outputs (which constrain the response format). |
| Returning raw Gemini error messages to the frontend | Leaks internal details: model name, prompt structure, API configuration | Catch Gemini exceptions and return generic error messages. Log details server-side only. |
| CORS set to `allow_origins=["*"]` with no auth | Anyone can call your extraction API from any website | Acceptable for internal tool with no auth requirement (per PROJECT.md). If auth is added later, restrict CORS origins. |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No loading state during extraction (10-30 seconds) | User thinks the app is broken, clicks "Generate" again (doubling LLM calls) | Show spinner with phase indication: "Analyzing topics..." then "Extracting claims..." Disable the button during processing. |
| Displaying claims without topic grouping | Flat list of 50+ claims is overwhelming and unusable | Group claims by topic with collapsible sections. The two-step extraction GIVES you topics -- use them. |
| No indication of extraction quality | User doesn't know if the claims are good or if they need a better source text | Show claim count and topic count. "Extracted 47 claims across 8 topics from your text." |
| Empty state with no guidance | User sees a blank textarea and doesn't know what to paste | Add placeholder text: "Paste a news article, research paper, or any source text here..." Show an example or link to try one. |
| CSV export missing metadata | User exports claims but loses topic associations | Include `claim_topic` and `claim` columns in CSV. Consider adding a row number for ordering. |
| No way to retry on partial failure | Topics extracted but claims failed -- user has to start over | If topic extraction succeeds but claim extraction fails, show the topics and offer a "Retry claim extraction" option. |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Claim extraction endpoint:** Often missing input text validation (empty string, whitespace-only, text too short for meaningful extraction, text too long for Gemini context) -- verify all edge cases return appropriate errors
- [ ] **Structured output parsing:** Often missing fallback for when Gemini returns valid JSON that doesn't match the schema (e.g., extra fields, missing fields) -- verify `model_validate_json()` errors are handled, not just LLM call errors
- [ ] **Topic-claim association:** Often missing handling of topics the LLM invents vs. topics from step 1 (LLM may return claims under topics NOT in the provided list) -- verify topic names from step 2 are validated against step 1 output
- [ ] **Frontend CSV export:** Often missing proper CSV escaping (claims with commas, quotes, newlines break CSV) -- verify with a claim containing `"quotes"` and `commas, like this`
- [ ] **Error responses:** Often missing consistent error format (sometimes string, sometimes JSON, sometimes HTML 500) -- verify ALL error paths return `{"error": "...", "detail": "..."}` JSON
- [ ] **Railway health check:** Often missing or pointing to a heavy endpoint -- verify `/health` returns 200 within 1 second with no LLM dependency
- [ ] **Environment configuration:** Often missing validation of required env vars at startup -- verify app fails fast with clear message if `GEMINI_API_KEY` is missing, not on first request

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Silent empty responses | LOW | Add error propagation to API layer, add typed exceptions. ~1 hour of refactoring. |
| Podcast-specific prompts producing bad claims | MEDIUM | Rewrite prompts for generic text. Requires testing against 3+ text types. ~4-8 hours including testing. |
| Schema mismatch causing parse failures | LOW | Standardize on `response_schema=PydanticModel`, update all call sites. ~30 minutes. |
| Rate limit hitting in production | LOW | Add retry with backoff to Gemini client wrapper. ~1 hour. Copy pattern from `gemini_service.py`. |
| Safety filter blocking content | LOW | Add `safety_settings` with `BLOCK_NONE` to GenerateContentConfig. ~15 minutes. Copy from `gemini_service.py`. |
| Cascading failure from bad topics | MEDIUM | Add topic validation between steps, add step-level timeouts, add frontend progress indication. ~4 hours. |
| Cost explosion from unbounded input | LOW | Add `max_length` validation to the request schema. ~15 minutes. |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Silent empty responses | Phase 1 (Core API) | Every endpoint returns typed errors. No 200 OK with empty data on failures. Test with intentionally bad API key. |
| Podcast-specific prompts | Phase 1 (Core API) | Test prompts against 3 text types: news article, research abstract, essay. Claims never reference "episode" or "host." |
| Schema mismatch | Phase 1 (Core API) | All Gemini calls use `response_schema=PydanticModel` consistently. Code review: grep for `response_json_schema` (should find 0 matches). |
| Cascading failure | Phase 1 (Core API) + Phase 2 (Frontend) | API: topic extraction failure returns error, never proceeds to claims. Frontend: shows loading phases. |
| Rate limits | Phase 1 (Core API) | Retry with backoff on 429/503. Test by exceeding free tier RPM. |
| Safety filters | Phase 1 (Core API) | `BLOCK_NONE` configured. Test with political/health text. Check `finish_reason` in response. |
| Cost explosion | Phase 1 (Core API) | Input text length validated. Max 50,000 chars. Test with oversized input returns 413. |
| UX loading state | Phase 2 (Frontend) | Button disabled during extraction. Spinner visible. Progress text updates. Test with slow network throttling. |
| CSV export correctness | Phase 2 (Frontend) | Export tested with claims containing commas, quotes, and newlines. File opens correctly in Excel. |
| Health check endpoint | Phase 1 (Core API) | `/health` returns 200 in < 1 second. Railway health check configured to use it. |

## Sources

- `submodules/extraction-api/src/extraction/premium_claim_extractor.py` -- Reference implementation of Gemini structured outputs with Pydantic response schemas. Shows silent-failure pattern (catches exceptions, returns empty).
- `submodules/extraction-api/src/infrastructure/gemini_service.py` -- Shows retry with exponential backoff, safety settings configuration, and the `response_json_schema` variant.
- `submodules/extraction-api/src/config/prompts/claim_extraction_prompt.py` -- Podcast-specific prompt with ad filtering, topic iteration, and claim quality rules. Needs adaptation for generic text.
- `submodules/extraction-api/src/config/prompts/topics_of_discussion_extraction_prompt.py` -- Podcast-specific topic extraction prompt with "6-14 topics" guidance.
- `submodules/extraction-api/test_json_repair_bug.py` -- Documents the apostrophe/possessive splitting bug in JSON parsing (not applicable to Gemini structured outputs but shows the importance of response validation).
- `submodules/extraction-api/test_json_mode_comprehensive.py` -- Documents intermittent JSON parsing issues with LLM outputs (reinforces why structured outputs via `response_schema` is the correct approach).
- `submodules/extraction-api/src/api/services/premium_extraction_service.py` -- Shows timeout handling pattern with `asyncio.wait_for()`.
- `submodules/extraction-api/railway.toml` -- Shows health check and deployment configuration patterns.
- `submodules/extraction-api/src/config/settings.py` -- Shows Pydantic Settings pattern for configuration with environment variable loading.

---
*Pitfalls research for: LLM-powered claim extraction API (Gemini structured outputs)*
*Researched: 2026-02-14*
