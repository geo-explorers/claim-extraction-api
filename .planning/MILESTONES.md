# Milestones

## v1.0 MVP (Shipped: 2026-02-14)

**Phases completed:** 3 phases, 6 plans, 12 tasks
**Lines of code:** 1,642 Python
**Git range:** `feat(01-01)` → `feat(03-01)`

**Delivered:** Stateless claim extraction API and web UI that lets Geo curators paste source text and get back topic-organized claims ready for the knowledge graph, deployable on Railway.

**Key accomplishments:**
1. Two-step Gemini extraction pipeline (topics → claims) with tenacity retry, BLOCK_NONE safety, and structured Pydantic outputs
2. Tailwind-styled web UI with textarea input, topic-grouped results table, and RFC 4180 CSV export
3. Graceful degradation — health endpoint works without GEMINI_API_KEY; generate returns clear 503 when unconfigured
4. 28-test suite across all layers (endpoints, services, extractors) with mocked Gemini, passing ruff + mypy --strict
5. Multi-stage Docker image (219MB) with Railway config-as-code and health checks

---

