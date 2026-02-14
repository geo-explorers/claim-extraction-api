# Claim Service

## What This Is

A stateless claim extraction API and web UI for generating structured, topic-organized claims from any source text. Built for the Geo Curator Program, where non-technical participants paste news articles, research papers, or literature and get back a clean table of atomic, self-contained claims ready for the Geo knowledge graph. Powered by Gemini structured outputs with a two-step extraction pipeline (topics then claims).

## Core Value

Curators can paste any source text and get back a clean table of topic-organized, self-contained claims ready for the Geo knowledge graph.

## Requirements

### Validated

- ✓ API endpoint `POST /generate/claims` accepts `{ source_text: string }` and returns claims — v1.0
- ✓ Two-step Gemini extraction: topics from source text, then claims mapped to topics — v1.0
- ✓ Claims are self-contained, atomic, attribution-stripped (5-32 words) — v1.0
- ✓ Prompts adapted from extraction-api premium pipeline for generic source text — v1.0
- ✓ Input validation with clear error messages for empty/short/long text — v1.0
- ✓ Gemini retry with exponential backoff on 429/503 errors — v1.0
- ✓ Health endpoint works without GEMINI_API_KEY (graceful degradation) — v1.0
- ✓ Safety settings BLOCK_NONE for political/health/violence content — v1.0
- ✓ Plain HTML/JS frontend with textarea, generate button, results table, CSV export — v1.0
- ✓ Loading indicator with disabled button during extraction — v1.0
- ✓ Dockerfile with UV multi-stage build for Railway deployment — v1.0
- ✓ Strict typing throughout: mypy --strict, Pydantic strict mode — v1.0
- ✓ 28-test suite passing ruff check + mypy --strict + pytest — v1.0

### Active

(None — define in next milestone with `/gsd:new-milestone`)

### Out of Scope

- Database / persistence — stateless service, claims go into Geo knowledge graph
- Authentication — security handled at infrastructure level
- Key takeaway extraction — curators decide importance
- Quote finding / entailment validation — podcast-specific features from extraction-api
- Ad filtering — source texts are not podcasts
- DSPy pipeline — direct Gemini API with structured outputs is simpler and proven
- Real-time streaming — Gemini structured outputs return complete response
- Batch processing — curators work one text at a time
- Custom prompt editing in UI — non-technical curators should not edit LLM prompts
- Multi-language support — English-language curators, defer to separate milestone if needed

## Context

Shipped v1.0 MVP with 1,642 LOC Python.
Tech stack: FastAPI, google-genai, Pydantic, Jinja2, Tailwind v4 CDN, Docker, Railway.
Part of the Geo content team's tooling for the Geo Curator Program.
Previously published podcast data using extraction-api (submodule at `submodules/extraction-api/`).
The premium claim extraction pipeline in extraction-api is the reference implementation — v1.0 adapted its prompts for generic source text.

## Constraints

- **LLM Provider**: Gemini — reuse existing infrastructure and API patterns from extraction-api
- **Structured Outputs**: Pydantic models as Gemini response schemas — no freeform JSON parsing
- **Deployment**: Railway — Dockerfile with PORT env var support
- **Frontend**: Plain HTML/JS served by FastAPI — no separate frontend build/deploy
- **Package Manager**: UV
- **Python Version**: 3.12+

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Reuse premium pipeline prompts (adapted) | Proven claim quality, team familiarity | ✓ Good — prompts adapted successfully for generic text |
| Gemini over OpenAI/Claude | Consistency with existing extraction-api infrastructure | ✓ Good — structured outputs work well |
| Stateless (no DB) | Simplifies deployment, claims go into Geo knowledge graph | ✓ Good — clean separation of concerns |
| Plain HTML over React | Non-technical users, no build step, served by same FastAPI instance | ✓ Good — simple and effective |
| Ruff for linting + formatting | Single tool replaces flake8 + black + isort, fast | ✓ Good — zero config issues |
| mypy strict mode | Industry standard strict type checking | ✓ Good — caught real issues during development |
| Settings not singleton | Instantiated in FastAPI lifespan for fail-fast on missing config | ✓ Good — clear startup validation |
| Tenacity for retry | Exponential backoff on Gemini 429/5xx errors | ✓ Good — resilient extraction |
| Optional GEMINI_API_KEY | Health endpoint must work without LLM dependency | ✓ Good — enables deployment health checks before config |
| Removed ad-filtering from prompts | Generic source texts have legitimate URLs/CTAs | ✓ Good — avoids false positives |
| Shell-form CMD in Dockerfile | Required for Railway $PORT expansion | ✓ Good — works correctly |
| Tailwind v4 CDN | Current version, no build step, modern browser support | ✓ Good — clean styling with zero tooling |

---
*Last updated: 2026-02-14 after v1.0 milestone*
