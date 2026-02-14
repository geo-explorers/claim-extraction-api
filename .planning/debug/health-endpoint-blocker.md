---
status: investigating
trigger: "Health endpoint unreachable without GEMINI_API_KEY"
created: 2026-02-14T00:00:00Z
updated: 2026-02-14T00:00:00Z
---

## Current Focus

hypothesis: FastAPI lifespan function unconditionally creates Settings() which requires gemini_api_key, blocking app startup before routes can respond
test: Read src/main.py lifespan and src/config/settings.py to confirm validation behavior
expecting: Settings() requires gemini_api_key with no default, and lifespan runs before route registration
next_action: Document confirmed root cause with specific code locations

## Symptoms

expected: GET /health should return {"status": "ok"} without requiring GEMINI_API_KEY environment variable
actual: FastAPI app crashes on startup with `pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings gemini_api_key Field required`
errors: `pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings gemini_api_key Field required`
reproduction: Start the app without GEMINI_API_KEY set, then try to reach GET /health
started: Always been broken - app requires GEMINI_API_KEY to start

## Eliminated

(none yet)

## Evidence

- timestamp: 2026-02-14T00:00:00Z
  checked: /home/john_malkovich/work/claim-api/src/routers/health.py
  found: Health endpoint is completely independent - just returns {"status": "ok"} with no dependencies on settings, Gemini client, or any app.state
  implication: Health check should work without any external configuration

- timestamp: 2026-02-14T00:00:00Z
  checked: /home/john_malkovich/work/claim-api/src/config/settings.py lines 23-24
  found: `gemini_api_key: str = Field(description="Google Gemini API key (required)")` has no default value
  implication: Pydantic will raise ValidationError if GEMINI_API_KEY environment variable is missing

- timestamp: 2026-02-14T00:00:00Z
  checked: /home/john_malkovich/work/claim-api/src/main.py lines 25-50 (lifespan function)
  found: Lifespan function unconditionally calls `settings = Settings()` on line 28, then uses it to create `genai.Client(api_key=settings.gemini_api_key)` on line 33
  implication: Settings validation happens during app startup, before any routes can respond. If validation fails, the entire app crashes before route registration completes

- timestamp: 2026-02-14T00:00:00Z
  checked: /home/john_malkovich/work/claim-api/src/main.py lines 52-56 (FastAPI app creation)
  found: `app = FastAPI(lifespan=lifespan, ...)` - lifespan is executed during app startup
  implication: The lifespan context manager runs before the app can serve any requests. FastAPI won't respond to any routes (including /health) until lifespan completes its setup phase

- timestamp: 2026-02-14T00:00:00Z
  checked: /home/john_malkovich/work/claim-api/src/main.py lines 76-77 (router registration)
  found: `app.include_router(health_router)` happens after `app = FastAPI(lifespan=lifespan)` but lifespan's startup phase blocks app initialization
  implication: Even though health_router is registered, the app never reaches a state where it can serve requests if lifespan fails

## Resolution

root_cause: **CONFIRMED** - The FastAPI lifespan function in /home/john_malkovich/work/claim-api/src/main.py unconditionally creates Settings() on line 28, which requires gemini_api_key per /home/john_malkovich/work/claim-api/src/config/settings.py line 23. Since FastAPI's lifespan runs during app initialization (before routes can respond), Pydantic's ValidationError for the missing gemini_api_key crashes the entire app before GET /health can ever be reached.

**Specific code locations:**

1. **Blocker:** /home/john_malkovich/work/claim-api/src/main.py line 28
   ```python
   settings = Settings()  # Crashes here if GEMINI_API_KEY missing
   ```

2. **Validation requirement:** /home/john_malkovich/work/claim-api/src/config/settings.py line 23
   ```python
   gemini_api_key: str = Field(description="Google Gemini API key (required)")
   # No default = Pydantic requires env var
   ```

3. **Dependencies created in lifespan:** /home/john_malkovich/work/claim-api/src/main.py lines 33-44
   ```python
   client = genai.Client(api_key=settings.gemini_api_key)
   # ... TopicExtractor, ClaimExtractor, ClaimGenerationService
   ```

4. **What actually needs Gemini:** Only POST /generate/claims (via ClaimGenerationService)
   - GET /health: No dependencies (line-by-line inspection confirms)

**Fix direction:**

The lifespan function should be refactored to:
- Allow the app to start without GEMINI_API_KEY for health checks
- Defer Gemini client initialization until it's actually needed (lazy initialization)
- OR make gemini_api_key optional in Settings and handle None gracefully
- OR move Settings validation to only the routes that need it (dependency injection)

**Key insight:** The health endpoint is completely independent but is held hostage by the lifespan function's eager initialization of Gemini dependencies.

fix: (not applied - diagnosis only)
verification: (not applicable - diagnosis only)
files_changed: []
