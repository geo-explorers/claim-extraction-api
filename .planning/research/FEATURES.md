# Feature Research

**Domain:** Claim extraction / fact extraction service (LLM-powered, stateless API with web UI)
**Researched:** 2026-02-14
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Text input with claim output | Core value proposition -- paste text, get claims | MEDIUM | Single `POST /generate/claims` endpoint accepting `{ source_text: string }`. Two-step LLM pipeline: topics first, then claims mapped to topics. |
| Structured JSON response | API consumers and the frontend both need predictable output | LOW | Pydantic response schema: list of `{ claim_topic, claim }` objects. Gemini structured outputs enforce this at the LLM level. |
| Topic-organized claims | Claims without topical grouping are an undifferentiated wall of text -- unusable for curators | MEDIUM | Step 1: extract topics from source text. Step 2: extract claims mapped to those topics. Directly adapted from extraction-api premium pipeline. |
| Self-contained claims (no pronouns, no dangling references) | Claims go into a knowledge graph where they appear in isolation. A claim saying "He did X" is worthless. | LOW (prompt engineering) | Enforce via prompt instructions: the "Shuffle Rule" from extraction-api. Each claim must read correctly if shown alone, out of order, without its topic label. |
| Atomic claims (one fact per claim) | Compound claims are harder to verify and harder to organize in a knowledge graph | LOW (prompt engineering) | Prompt instruction: split compound sentences. Target 5-32 words per claim. |
| Web UI with textarea and results table | Non-technical curators need a visual interface, not just an API | MEDIUM | Plain HTML/JS served by FastAPI. Textarea input, "Generate" button, results table with `claim_topic` and `claim` columns. No framework, no build step. |
| CSV export | Curators need to get claims out of the tool and into spreadsheets/knowledge graph workflows | LOW | Client-side JS: iterate table rows, build CSV string, trigger download. No server involvement needed. |
| Loading/progress indicator | LLM calls take 10-60 seconds. No feedback = users think it is broken. | LOW | Spinner or progress bar on the frontend during the API call. |
| Error handling and user feedback | LLM calls can fail (rate limits, malformed input, empty text). Users need clear error messages. | LOW | API returns structured error responses. Frontend displays them clearly. |
| Source text length handling | Users will paste anything from a tweet to a 50-page paper. The service needs to handle both gracefully. | MEDIUM | Gemini models have large context windows (1M+ tokens). Set reasonable min/max limits. Validate input length on the API side and return clear errors for out-of-bounds input. |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Two-step extraction (topics then claims) | Higher quality than single-pass extraction. Topics provide organizational structure that makes claims more useful for knowledge graph ingestion. Most extraction tools do single-pass. | MEDIUM | Already proven in extraction-api. Step 1: topic extraction from source text (no title/description needed unlike podcast pipeline). Step 2: claim extraction mapped to extracted topics. |
| Attribution stripping | Claims state facts directly ("60% of the American diet is ultra-processed") instead of quoting sources ("Dr. X said that..."). This makes claims more reusable and verifiable. | LOW (prompt engineering) | Prompt instruction from extraction-api: extract the content, not the quote. Exception for biographical facts. |
| Ad/promotional content filtering | Source texts (especially news articles) contain promotional content that should not become claims | LOW (prompt engineering) | Prompt instruction to skip promotional segments. Lighter-weight than extraction-api's ML-based ad classifier since source texts are not podcasts. |
| Topic filtering (min claims threshold) | Topics with only 1-2 claims are noise. Filtering them improves signal-to-noise ratio. | LOW | Post-processing filter: discard topics with fewer than N claims (extraction-api uses 3). Configurable threshold. |
| Configurable model/temperature | Power users and internal team can tune extraction quality without code changes | LOW | Environment variables for model name and temperature (following extraction-api pattern: `GEMINI_MODEL`, `GEMINI_TEMPERATURE`). |
| Copy-to-clipboard for individual claims | Curators often want to grab a single claim, not export the whole table | LOW | Small clipboard icon per row in the results table. Pure JS, no server call. |
| Source text type hints | Telling the LLM what kind of text it is processing (news article, research paper, transcript) could improve extraction quality | LOW | Optional `source_type` field in the API request. Adjusts prompt phrasing. Default: auto-detect or generic. |
| Health check endpoint | Deployment monitoring on Railway needs a way to verify the service is up | LOW | `GET /health` returning `{ "status": "ok" }`. Standard for Railway deployments. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Database / persistence | "Save extraction history for later" | Adds operational complexity (migrations, backups, connection pooling) to a stateless tool. Claims belong in the Geo knowledge graph, not in this service. Contradicts the core architectural principle of statelessness. | CSV export covers the "save results" need. If history is truly needed later, it belongs in a separate service or the knowledge graph itself. |
| User authentication | "Track who extracted what" | No user accounts in the Geo Curator Program for this tool. Auth adds login flows, session management, token handling -- all complexity for a tool where security is handled at the infrastructure level (Railway private networking, API keys). | Infrastructure-level auth if needed (API key for programmatic access). |
| Key takeaway extraction | "Highlight the most important claims" | Extraction-api has this feature, but it is designed for podcast episodes where summarization is valuable. For arbitrary source texts pasted by curators, the curator IS the person deciding importance. Adding AI judgment on "what matters" adds a step that curators will ignore or disagree with. | Let curators select important claims themselves via the UI. They are the domain experts. |
| Real-time streaming of results | "Show claims as they are extracted" | Gemini structured outputs return the complete response at once -- there is no streaming of partial structured JSON. Implementing this would require abandoning structured outputs for freeform generation + parsing, which sacrifices reliability. | Good loading indicator with estimated time. The 10-60 second wait is acceptable for a batch operation. |
| Quote finding / entailment validation | "Link claims back to the exact source text passage" | Podcast-specific feature from extraction-api. Requires transcript search index, reranker service, embedding service -- massive infrastructure for marginal value when curators already have the source text in front of them. | The source text is already visible in the UI. Curators can Ctrl+F to find the relevant passage. |
| Deduplication | "Remove duplicate claims" | Adds complexity (embedding generation, similarity comparison). In a stateless, single-extraction context, the LLM rarely produces true duplicates. Cross-session deduplication requires persistence (anti-feature #1). The extraction-api needs it because it processes many episodes; this service processes one text at a time. | Prompt engineering to avoid repetition. If duplicates appear, it is a prompt quality issue to fix at the source. |
| Multi-language support | "Extract claims from non-English text" | Gemini handles multilingual input natively, but the prompts are English-optimized and the claim quality criteria (self-contained, atomic, attribution-stripped) are harder to enforce across languages. Scope creep for a tool serving English-language Geo curators. | If multilingual need arises, add it as a separate milestone with dedicated prompt engineering per language. |
| Batch processing / multiple texts | "Process many documents at once" | Curators work one text at a time in their workflow. Batch processing adds queue management, progress tracking per item, partial failure handling -- all complexity for a rarely-used feature. | Process one text at a time. If batch is truly needed later, it is a separate API endpoint, not a modification of the core flow. |
| Custom prompt editing in UI | "Let users tweak the extraction prompt" | Non-technical curators should not be editing LLM prompts. Bad prompts produce bad claims, and there is no guardrail to prevent garbage-in-garbage-out. Prompt quality is an engineering concern. | Expose `source_type` hints instead (news, research, etc.) that select pre-engineered prompt variants. |
| DSPy pipeline | "Use DSPy for optimized prompts" | Extraction-api uses DSPy for the standard pipeline, but the premium pipeline (which this service adapts) deliberately avoids DSPy. Direct Gemini API calls with structured outputs are simpler, faster, and more reliable. DSPy adds a heavy dependency and training infrastructure for marginal benefit in a single-call pipeline. | Direct Gemini API with Pydantic response schemas. Proven in extraction-api premium pipeline. |

## Feature Dependencies

```
[Source text input validation]
    +--requires--> [API endpoint POST /generate/claims]
                       +--requires--> [Topic extraction (Step 1)]
                                          +--requires--> [Claim extraction mapped to topics (Step 2)]
                                                             +--requires--> [Topic filtering (min claims)]
                                                                                +--produces--> [Structured JSON response]

[Structured JSON response]
    +--enables--> [Web UI results table]
                      +--enables--> [CSV export]
                      +--enables--> [Copy-to-clipboard per claim]

[FastAPI application]
    +--serves--> [API endpoint POST /generate/claims]
    +--serves--> [Static HTML/JS frontend]
    +--serves--> [Health check endpoint]

[Pydantic models]
    +--used-by--> [API request/response validation]
    +--used-by--> [Gemini structured output schema]

[Environment configuration]
    +--configures--> [Gemini API key]
    +--configures--> [Model name and temperature]
    +--configures--> [Port (Railway)]
```

### Dependency Notes

- **Claim extraction requires topic extraction:** The two-step pipeline means topics must be extracted first, then claims are mapped to those topics. These are sequential LLM calls.
- **CSV export requires results table:** The export function iterates over the rendered table. The table must exist and be populated first.
- **Topic filtering enhances claim extraction:** Post-processing step after claims are returned. Can be added independently without changing the extraction pipeline.
- **Pydantic models serve dual purpose:** Same models validate API input/output AND enforce Gemini's structured output format. This is a proven pattern from extraction-api's `ClaimWithTopicResult` and `TopicDiscussionResult`.

## MVP Definition

### Launch With (v1)

Minimum viable product -- what is needed to validate the concept with curators.

- [x] `POST /generate/claims` endpoint accepting `{ source_text: string }` -- core API
- [x] Two-step extraction pipeline: topics from source text, then claims mapped to topics -- proven quality from extraction-api
- [x] Pydantic response schema with `{ claim_topic, claim }` objects -- structured, predictable output
- [x] Prompts adapted from extraction-api premium pipeline (self-contained, atomic, attribution-stripped claims) -- proven claim quality
- [x] Plain HTML/JS frontend with textarea, generate button, results table -- curator-facing UI
- [x] CSV export from results table -- data export for downstream workflows
- [x] Loading indicator during extraction -- UX for 10-60 second wait
- [x] Error handling with user-friendly messages -- graceful failure
- [x] Input validation (min/max length) -- prevent garbage input
- [x] `GET /health` endpoint -- Railway deployment monitoring
- [x] Dockerfile for Railway deployment -- deployment target
- [x] `.env` configuration for API key, model, port -- operational config

### Add After Validation (v1.x)

Features to add once core is working and curators provide feedback.

- [ ] Copy-to-clipboard per claim row -- add when curators say "I keep copying claims one at a time"
- [ ] Source type hints (`source_type` field) -- add when extraction quality varies significantly by text type
- [ ] Configurable topic filter threshold -- add when curators complain about too many/few topics
- [ ] JSON export alongside CSV -- add when API consumers (not curators) want machine-readable output

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] Prompt variants per source type (news, research, literature) -- defer until clear evidence that one-size-fits-all prompt is insufficient
- [ ] Claim quality scoring / confidence -- defer until there is a feedback loop to train quality metrics
- [ ] API rate limiting -- defer until there are enough users to cause load issues
- [ ] OpenAPI documentation page -- defer; FastAPI auto-generates `/docs` which is sufficient initially

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| API endpoint with two-step extraction | HIGH | MEDIUM | P1 |
| Prompts adapted from extraction-api | HIGH | LOW | P1 |
| Pydantic structured output schemas | HIGH | LOW | P1 |
| Web UI (textarea + table) | HIGH | MEDIUM | P1 |
| CSV export | HIGH | LOW | P1 |
| Loading indicator | MEDIUM | LOW | P1 |
| Error handling | MEDIUM | LOW | P1 |
| Input validation | MEDIUM | LOW | P1 |
| Health check endpoint | MEDIUM | LOW | P1 |
| Dockerfile | HIGH | LOW | P1 |
| Env config | MEDIUM | LOW | P1 |
| Copy-to-clipboard | MEDIUM | LOW | P2 |
| Source type hints | LOW | LOW | P2 |
| Topic filter threshold config | LOW | LOW | P2 |
| JSON export | LOW | LOW | P3 |
| Prompt variants by source type | MEDIUM | MEDIUM | P3 |
| Claim quality scoring | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | extraction-api (reference) | General LLM extraction tools | Our Approach |
|---------|---------------------------|------------------------------|--------------|
| Input type | Podcast transcripts (from database) | Any text (API) | Any source text via paste or API |
| Topic extraction | Yes (two-step with title/description context) | Rare -- most do flat extraction | Yes, but without title/description since source texts are arbitrary |
| Claim quality (self-contained, atomic) | Yes (extensively prompt-engineered) | Varies widely | Reuse extraction-api's proven prompts, adapted for general text |
| Structured output | Gemini response_schema with Pydantic | Varies (many use freeform + parsing) | Gemini structured outputs with Pydantic -- same proven approach |
| Quote/evidence linking | Yes (semantic search + reranker) | Some tools do this | No -- out of scope, curators have source text |
| Deduplication | Yes (embedding + reranker) | Rare | No -- single-text stateless extraction |
| Key takeaways | Yes (third LLM call) | Some tools summarize | No -- curators decide importance |
| Ad filtering | Yes (ML classifier + prompt) | Not applicable | Prompt-based only (no ML classifier needed for non-podcast content) |
| Web UI | No (API only) | Some have UIs | Yes -- primary interface for non-technical curators |
| Export | Database storage | Varies | CSV export (stateless) |
| Persistence | PostgreSQL | Varies | None (stateless) |
| Auth | API key | Varies | None (infrastructure-level) |

## Sources

- **extraction-api reference implementation** (HIGH confidence): Direct codebase analysis of `submodules/extraction-api/src/extraction/premium_claim_extractor.py`, `src/pipeline/premium_extraction_pipeline.py`, `src/config/prompts/claim_extraction_prompt.py`, `src/config/prompts/topics_of_discussion_extraction_prompt.py`
- **PROJECT.md** (HIGH confidence): Project requirements and constraints defined in `.planning/PROJECT.md`
- **Gemini structured outputs pattern** (HIGH confidence): Observed in extraction-api's use of `google.genai` SDK with `response_schema` parameter and Pydantic models
- **Curator workflow context** (MEDIUM confidence): Inferred from PROJECT.md description of Geo Curator Program and non-technical users

---
*Feature research for: Claim extraction / fact extraction service*
*Researched: 2026-02-14*
