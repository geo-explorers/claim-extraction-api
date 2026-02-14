# Claim Service

## What This Is

A lightweight, stateless API and web UI for generating structured claims from any source text (news articles, research papers, literature, etc.). Built for the Geo Curator Program, where non-technical participants organize and publish data to the Geo knowledge graph. Extracts factual, verifiable, atomic claims organized by topic using Gemini structured outputs.

## Core Value

Curators can paste any source text and get back a clean table of topic-organized, self-contained claims ready for the Geo knowledge graph.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] API endpoint `POST /generate/claims` accepts `{ source_text: string }` and returns claims
- [ ] Claims are extracted using Gemini with structured outputs (Pydantic response schema)
- [ ] Two-step extraction: topics from source text, then claims mapped to those topics
- [ ] Prompts adapted from extraction-api premium pipeline (claim extraction + topics of discussion)
- [ ] Response format: list of `{ claim_topic, claim }` objects
- [ ] Plain HTML/JS frontend served by FastAPI — no build step
- [ ] Frontend has textarea input for source text and a generate button
- [ ] Frontend displays results as a table with columns `claim_topic` and `claim`
- [ ] Frontend supports CSV export of the results table
- [ ] Strict Python typing throughout (Pydantic strict mode, mypy)
- [ ] Linting and formatting via Ruff
- [ ] Test suite with pytest
- [ ] Dockerfile for Railway deployment
- [ ] `.env` configuration for Gemini API key and model settings

### Out of Scope

- Database / persistence — stateless service, no storage
- Authentication — security handled at infrastructure level
- Key takeaway extraction — not needed for curator workflow
- Quote finding / entailment validation — podcast-specific features from extraction-api
- Ad filtering — source texts are not podcasts
- DSPy pipeline — using direct Gemini API with structured outputs only
- OAuth / user accounts — no user management needed
- Mobile app — web UI only

## Context

- Part of the Geo content team's tooling for the Geo Curator Program
- Previously published podcast data using extraction-api (submodule at `submodules/extraction-api/`)
- The premium claim extraction pipeline in extraction-api is the reference implementation
- Claims are a reused entity throughout Geo — this service generalizes claim generation beyond podcasts
- Curators are non-technical — UI must be simple and self-explanatory
- The extraction-api uses `google-genai` SDK with `response_schema` for structured outputs

## Constraints

- **LLM Provider**: Gemini — reuse existing Gemini infrastructure and API patterns from extraction-api
- **Structured Outputs**: Must use Pydantic models as Gemini response schemas — no freeform JSON parsing
- **Deployment**: Railway — needs Dockerfile and PORT env var support
- **Frontend**: Plain HTML/JS served by FastAPI static files — no separate frontend build/deploy
- **Package Manager**: UV — consistent with extraction-api
- **Python Version**: 3.12+ — modern type hints, consistent with extraction-api

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Reuse premium pipeline prompts (adapted) | Proven claim quality, team familiarity | — Pending |
| Gemini over OpenAI/Claude | Consistency with existing extraction-api infrastructure | — Pending |
| Stateless (no DB) | Simplifies deployment, claims go into Geo knowledge graph not this service | — Pending |
| Plain HTML over React | Non-technical users, no build step, served by same FastAPI instance | — Pending |
| Ruff for linting + formatting | Single tool replaces flake8 + black + isort, fast | — Pending |
| mypy for type checking | Industry standard strict type checking for Python | — Pending |

---
*Last updated: 2026-02-14 after initialization*
