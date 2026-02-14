# Requirements: Claim Service

**Defined:** 2026-02-14
**Core Value:** Curators can paste any source text and get back a clean table of topic-organized, self-contained claims ready for the Geo knowledge graph.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Extraction

- [ ] **EXTR-01**: Service extracts topics from source text using Gemini structured outputs (TopicResult Pydantic schema)
- [ ] **EXTR-02**: Service extracts claims mapped to extracted topics using Gemini structured outputs (ClaimWithTopicResult Pydantic schema)
- [ ] **EXTR-03**: Claims are self-contained and atomic — no pronouns, no dangling references, one fact per claim (5-32 words)
- [ ] **EXTR-04**: Claims use attribution stripping — extract facts directly, not "Dr. X said that..."
- [ ] **EXTR-05**: Prompts are adapted from extraction-api premium pipeline for generic source text (not podcast-specific)

### API

- [ ] **API-01**: `POST /generate/claims` endpoint accepts `{ "source_text": string }` and returns claims
- [ ] **API-02**: Response format is `{ "claims": [{ "claim_topic": string, "claim": string }] }`
- [ ] **API-03**: Input validation rejects empty, whitespace-only, too-short, and too-long source text with clear error messages
- [ ] **API-04**: Errors propagate as typed exceptions with appropriate HTTP status codes — no silent empty returns on LLM failures
- [ ] **API-05**: Gemini calls retry with exponential backoff on 429/503 errors
- [ ] **API-06**: `GET /health` endpoint returns `{ "status": "ok" }` without LLM dependency
- [ ] **API-07**: Gemini safety settings configured to `BLOCK_NONE` to handle political/health/violence content

### Frontend

- [ ] **UI-01**: Plain HTML/JS page served by FastAPI with textarea input for source text
- [ ] **UI-02**: Generate button triggers `POST /generate/claims` and renders results
- [ ] **UI-03**: Results displayed as table with columns `claim_topic` and `claim`
- [ ] **UI-04**: User can export results table as CSV file
- [ ] **UI-05**: Loading indicator visible during extraction with button disabled to prevent double-submission

### Infrastructure

- [ ] **INFR-01**: Dockerfile using python:3.12-slim base with UV for Railway deployment
- [ ] **INFR-02**: `railway.toml` with Dockerfile builder, health check, and start command
- [ ] **INFR-03**: `.env.example` with GEMINI_API_KEY, GEMINI_MODEL, GEMINI_TEMPERATURE, PORT
- [ ] **INFR-04**: Pydantic BaseSettings loads configuration from environment variables and `.env` file
- [ ] **INFR-05**: Ruff configured for linting and formatting in `pyproject.toml`
- [ ] **INFR-06**: mypy configured with `strict = true` in `pyproject.toml`
- [ ] **INFR-07**: pytest test suite with async support via pytest-asyncio

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Polish

- **PLSH-01**: Copy-to-clipboard button per claim row in results table
- **PLSH-02**: Optional `source_type` field in API request (news, research, literature) for prompt tuning
- **PLSH-03**: Configurable minimum claims threshold per topic (filter low-signal topics)
- **PLSH-04**: JSON export alongside CSV

### Scale

- **SCAL-01**: API rate limiting middleware to prevent Gemini quota exhaustion
- **SCAL-02**: In-memory LRU cache for repeated extractions of the same text

## Out of Scope

| Feature | Reason |
|---------|--------|
| Database / persistence | Stateless service — claims go into Geo knowledge graph, not this service |
| Authentication | Security handled at infrastructure level per project constraints |
| Key takeaway extraction | Curators decide importance — AI judgment adds unnecessary step |
| Quote finding / entailment validation | Podcast-specific features, curators have source text for reference |
| Real-time streaming | Gemini structured outputs return complete response — no partial JSON streaming |
| Deduplication | Single-text stateless extraction — no cross-session duplicates possible |
| DSPy pipeline | Direct Gemini API with structured outputs is simpler and proven |
| Batch processing | Curators work one text at a time — batch adds unnecessary complexity |
| Custom prompt editing in UI | Non-technical curators should not edit LLM prompts |
| Multi-language support | English-language curators — defer to separate milestone if needed |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| EXTR-01 | — | Pending |
| EXTR-02 | — | Pending |
| EXTR-03 | — | Pending |
| EXTR-04 | — | Pending |
| EXTR-05 | — | Pending |
| API-01 | — | Pending |
| API-02 | — | Pending |
| API-03 | — | Pending |
| API-04 | — | Pending |
| API-05 | — | Pending |
| API-06 | — | Pending |
| API-07 | — | Pending |
| UI-01 | — | Pending |
| UI-02 | — | Pending |
| UI-03 | — | Pending |
| UI-04 | — | Pending |
| UI-05 | — | Pending |
| INFR-01 | — | Pending |
| INFR-02 | — | Pending |
| INFR-03 | — | Pending |
| INFR-04 | — | Pending |
| INFR-05 | — | Pending |
| INFR-06 | — | Pending |
| INFR-07 | — | Pending |

**Coverage:**
- v1 requirements: 24 total
- Mapped to phases: 0
- Unmapped: 24 ⚠️

---
*Requirements defined: 2026-02-14*
*Last updated: 2026-02-14 after initial definition*
