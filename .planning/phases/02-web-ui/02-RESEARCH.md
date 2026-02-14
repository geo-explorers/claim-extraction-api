# Phase 2: Web UI - Research

**Researched:** 2026-02-14
**Domain:** FastAPI Jinja2 templates, Tailwind CSS CDN, vanilla JS client-side interactions
**Confidence:** HIGH

## Summary

Phase 2 adds a single web page to the existing FastAPI application. The page lets curators paste source text, call the existing `POST /generate/claims` endpoint via `fetch()`, see results in a table grouped by topic, and export them as CSV. All infrastructure is already in place: FastAPI 0.129.0 includes `Jinja2Templates` and `StaticFiles` via the `fastapi[standard]` extra (Jinja2 3.1.6 is already installed). No new Python dependencies are needed.

The technical surface is small: one Jinja2 template, one JavaScript file for fetch/render/CSV logic, a FastAPI route serving the template at `/`, and Tailwind CSS v4 via CDN `<script>` tag for styling. The API response shape (`{ "claims": [{ "claim_topic": str, "claim": str }] }`) is already stable from Phase 1, so the JS simply groups by `claim_topic` and renders HTML table rows.

**Primary recommendation:** Keep everything in three files -- one Jinja2 template (`src/templates/index.html`), one JS file (`src/static/app.js`), and one new route in `src/main.py` (or a dedicated `src/routers/ui.py`). No build step, no bundlers, no npm.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Page layout & style
- Minimal and utilitarian -- clean, no frills, developer-tool feel
- Medium centered layout (~960px max-width)
- Light mode only, no dark mode or theme switching
- Simple title bar with app name (e.g. "Claim Extractor"), no navigation links

#### Results presentation
- Claims grouped by `claim_topic` with bold header rows spanning the table
- Each topic header shows per-topic count, e.g. "Economics (7 claims)"
- Total claims count displayed above the table, e.g. "42 claims extracted"
- No sorting or filtering -- static table, what the API returns is what you see

#### Interaction flow
- Textarea stays visible after generation -- user can edit and re-generate
- Loading state: small spinner with "Thinking..." label, Generate button disabled
- Export CSV button placed above the table, near the total claims count
- Re-generating with new text shows a confirmation dialog before replacing current results

#### Tools & frameworks
- Vanilla HTML/JS -- no React or frontend framework
- Tailwind CSS via CDN script tag -- no build step
- Tailwind utility classes only -- no custom CSS files
- Jinja2 templates served by FastAPI -- allows server-side value injection
- Static files live in `src/static/`

### Claude's Discretion
- Exact typography choices and spacing
- Loading spinner implementation
- Confirmation dialog style (native browser confirm vs custom)
- Error message styling and placement
- Textarea placeholder text and sizing
- Table border/stripe styling

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI `Jinja2Templates` | 0.129.0 (installed) | Server-side HTML template rendering | Built into `fastapi[standard]`; Jinja2 3.1.6 already in venv |
| FastAPI `StaticFiles` | 0.129.0 (installed) | Serve `app.js` and any other static assets | Built into `fastapi[standard]` via Starlette 0.52.1 |
| Tailwind CSS v4 Play CDN | 4.1 (CDN) | Utility-first CSS styling, zero build step | Official CDN script tag, user decision |
| Vanilla JavaScript (Fetch API) | ES2020+ | API calls, DOM manipulation, CSV export | User decision -- no framework |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Jinja2 | 3.1.6 (installed) | Template engine behind `Jinja2Templates` | Already a transitive dependency of `fastapi[standard]` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Tailwind v4 CDN | Tailwind v3 CDN (`cdn.tailwindcss.com`) | v3 has wider browser support (no `@property`/`color-mix()` requirement) but v4 is current and the CDN tag is cleaner. v4 works in Chrome 111+, Firefox 128+, Safari 16.4+. Recommend v4 unless legacy browsers are needed. |
| Native `confirm()` | Custom modal | Native is zero-code and matches "utilitarian" feel. Custom modal requires extra JS/HTML. **Recommend native `confirm()`.** |
| CSS `@keyframes` spinner | SVG spinner / animated border | CSS border spinner (`border-t-transparent animate-spin`) is simplest with Tailwind. **Recommend CSS border spinner.** |

**Installation:**
```bash
# No new dependencies needed. Jinja2 and StaticFiles are already available via fastapi[standard].
# Tailwind is loaded via CDN <script> tag in the HTML template.
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── main.py              # Add: mount /static, set up Jinja2Templates, add GET / route
├── templates/
│   └── index.html       # NEW: Jinja2 template with Tailwind CDN
├── static/
│   └── app.js           # NEW: fetch, render, CSV export logic
├── routers/
│   ├── generate.py      # Existing: POST /generate/claims (unchanged)
│   ├── health.py        # Existing: GET /health (unchanged)
│   └── ui.py            # NEW (optional): GET / route if separating from main.py
├── schemas/             # Existing (unchanged)
├── services/            # Existing (unchanged)
└── config/              # Existing (unchanged)
```

### Pattern 1: Path Resolution for Templates and Static Files
**What:** Use `pathlib.Path(__file__).resolve().parent` to construct absolute paths to `templates/` and `static/` directories, avoiding breakage when the app is run from different working directories.
**When to use:** Always, in `main.py` where `StaticFiles` and `Jinja2Templates` are initialized.
**Example:**
```python
# Source: https://fastapi.tiangolo.com/advanced/templates/
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")
```

### Pattern 2: TemplateResponse with Named Parameters (FastAPI 0.108.0+)
**What:** Pass `request` as a named parameter, not in the context dict. This is the modern API since Starlette 0.29.0.
**When to use:** All template responses.
**Example:**
```python
# Source: https://fastapi.tiangolo.com/advanced/templates/
from fastapi import Request
from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={},  # Add any server-side values here
    )
```

### Pattern 3: Client-Side Fetch + JSON POST
**What:** Use `fetch()` to POST JSON to `/generate/claims`, parse the JSON response, and render into the DOM.
**When to use:** The Generate button click handler.
**Example:**
```javascript
// Vanilla JS -- no framework
async function generateClaims(sourceText) {
    const response = await fetch("/generate/claims", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source_text: sourceText }),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "An unexpected error occurred");
    }

    return await response.json(); // { claims: [{ claim_topic, claim }] }
}
```

### Pattern 4: Client-Side CSV Export via Blob
**What:** Build a CSV string from the claims array, create a Blob, generate a temporary URL, and trigger download via a hidden anchor element.
**When to use:** The Export CSV button click handler.
**Example:**
```javascript
// RFC 4180 compliant CSV escaping
function escapeCSV(value) {
    if (/[",\n\r]/.test(value)) {
        return '"' + value.replace(/"/g, '""') + '"';
    }
    return value;
}

function downloadCSV(claims, filename = "claims.csv") {
    const header = "claim_topic,claim";
    const rows = claims.map(c =>
        escapeCSV(c.claim_topic) + "," + escapeCSV(c.claim)
    );
    const csv = [header, ...rows].join("\r\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}
```

### Pattern 5: Grouping Claims by Topic for Display
**What:** Transform the flat `claims` array into a grouped structure for rendering topic header rows.
**When to use:** After receiving the API response, before rendering the table.
**Example:**
```javascript
function groupByTopic(claims) {
    const groups = {};
    for (const claim of claims) {
        if (!groups[claim.claim_topic]) {
            groups[claim.claim_topic] = [];
        }
        groups[claim.claim_topic].push(claim.claim);
    }
    return groups;
    // Returns: { "Economics": ["claim1", "claim2"], "Policy": ["claim3"] }
}
```

### Anti-Patterns to Avoid
- **Hardcoded URL paths in JS:** Use relative URLs (`/generate/claims`) not absolute URLs with host/port. The app may run on different ports or behind a reverse proxy.
- **Template directory as relative string:** Always use `pathlib.Path(__file__)` resolution. A bare `"templates"` string breaks if `uvicorn` is started from a different directory.
- **Mixing Jinja2 `{{ }}` with JS template literals:** Jinja2 uses `{{ }}` for variable interpolation. If JS template literals appear in the Jinja2 template, use `{% raw %}...{% endraw %}` blocks or move all JS to a separate `.js` file (preferred approach -- user decided static files in `src/static/`).
- **Building CSV without RFC 4180 escaping:** Claims may contain commas, quotes, or newlines. Always wrap fields that contain special characters in double quotes and escape internal double quotes by doubling them.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSS styling | Custom CSS framework | Tailwind CSS CDN | User decision; utility classes cover all layout needs |
| Template rendering | String concatenation in Python | FastAPI `Jinja2Templates` | Handles escaping, inheritance, caching automatically |
| CSV escaping | Naive `value.replace()` | RFC 4180-compliant `escapeCSV()` function | Claims can contain commas, quotes, newlines -- naive string join corrupts data |
| Static file serving | Custom file-read middleware | FastAPI `StaticFiles` | Handles MIME types, caching headers, 404s automatically |

**Key insight:** This phase has almost no novel technical problems. Every piece (template serving, static files, fetch API, CSV generation) is well-trodden ground with standard solutions. The risk is in the integration and polish, not in any single technical challenge.

## Common Pitfalls

### Pitfall 1: Template/Static Directory Path Breaks on Different CWD
**What goes wrong:** `Jinja2Templates(directory="templates")` or `StaticFiles(directory="static")` fails with `RuntimeError` when the app is started from a directory other than `src/`.
**Why it happens:** Relative paths resolve against `os.getcwd()`, not against the file containing the code.
**How to avoid:** Always use `Path(__file__).resolve().parent / "templates"` and `Path(__file__).resolve().parent / "static"` for directory arguments.
**Warning signs:** Works in development, breaks in Docker or CI where `WORKDIR` differs.

### Pitfall 2: Jinja2 Syntax Conflicts with JavaScript
**What goes wrong:** JavaScript code in a `.html` template uses `${}` template literals or object destructuring `{ key }` which Jinja2 tries to interpret as `{{ }}` expressions, causing `UndefinedError`.
**Why it happens:** Jinja2 processes the entire template file, including `<script>` blocks.
**How to avoid:** Keep all JavaScript in `src/static/app.js` (separate file), not inline in the template. This is already aligned with the user's decision to have `src/static/`.
**Warning signs:** `jinja2.exceptions.UndefinedError` on template render.

### Pitfall 3: Missing Error Body Parsing
**What goes wrong:** When the API returns 4xx/5xx, the JS code tries to parse `.json()` but the response may not be JSON (e.g., HTML error page from a proxy, or connection refused).
**Why it happens:** FastAPI always returns JSON for its own errors, but network errors, timeouts, and proxy errors don't produce JSON responses.
**How to avoid:** Wrap `response.json()` in try-catch. If JSON parsing fails, fall back to `response.statusText` or a generic message.
**Warning signs:** Unhandled promise rejection or silent failure when the API is down.

### Pitfall 4: Double-Submit During Slow Extraction
**What goes wrong:** User clicks Generate multiple times while waiting, triggering parallel API calls. Results arrive out of order, showing stale data.
**Why it happens:** No debouncing and button not disabled during fetch.
**How to avoid:** Disable the Generate button immediately on click, re-enable on success or error. User decision already requires this (UI-05).
**Warning signs:** Multiple "Thinking..." spinners, table flashing between results.

### Pitfall 5: CSV BOM for Excel Compatibility
**What goes wrong:** Excel on Windows doesn't recognize UTF-8 encoding of the CSV, displaying garbled characters for non-ASCII text (accented names, etc.).
**Why it happens:** Excel defaults to the system locale encoding unless a UTF-8 BOM is present.
**How to avoid:** Prepend `\uFEFF` (UTF-8 BOM) to the CSV string before creating the Blob. This is a single-character prefix that signals UTF-8 to Excel.
**Warning signs:** Claims with accented characters (e.g., "Ursula von der Leyen") display as mojibake in Excel.

### Pitfall 6: StaticFiles Mount Order vs Route Priority
**What goes wrong:** If `app.mount("/static", ...)` is placed after route registration, or if a catch-all route is added, static files may not be served.
**Why it happens:** FastAPI/Starlette processes routes in registration order. Mounted apps (StaticFiles) are checked after regular routes.
**How to avoid:** Mount static files early in `main.py`, before `app.include_router(...)` calls, or at least before any catch-all routes.
**Warning signs:** 404 for `/static/app.js` despite the file existing on disk.

## Code Examples

Verified patterns from official sources:

### FastAPI Template + Static Files Setup
```python
# Source: https://fastapi.tiangolo.com/advanced/templates/
# In src/main.py

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(...)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="index.html")
```

### Jinja2 Template with Tailwind v4 CDN
```html
<!-- Source: https://tailwindcss.com/docs/installation/play-cdn -->
<!-- In src/templates/index.html -->
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claim Extractor</title>
    <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
</head>
<body class="bg-gray-50 text-gray-900">
    <div class="max-w-[960px] mx-auto px-4 py-8">
        <!-- Title bar -->
        <h1 class="text-2xl font-bold mb-6">Claim Extractor</h1>

        <!-- Textarea -->
        <textarea id="source-text" rows="10"
            class="w-full border border-gray-300 rounded p-3 font-mono text-sm"
            placeholder="Paste your source text here..."></textarea>

        <!-- Generate button -->
        <button id="generate-btn"
            class="mt-3 px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed">
            Generate
        </button>

        <!-- Loading indicator (hidden by default) -->
        <div id="loading" class="hidden mt-3 flex items-center gap-2 text-gray-500">
            <div class="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin"></div>
            <span>Thinking...</span>
        </div>

        <!-- Error message (hidden by default) -->
        <div id="error" class="hidden mt-3 p-3 bg-red-50 border border-red-200 text-red-700 rounded"></div>

        <!-- Results section (hidden by default) -->
        <div id="results" class="hidden mt-6">
            <div class="flex items-center justify-between mb-3">
                <span id="total-count" class="text-sm text-gray-600 font-medium"></span>
                <button id="export-btn"
                    class="px-4 py-1.5 bg-green-600 text-white text-sm rounded hover:bg-green-700">
                    Export CSV
                </button>
            </div>
            <table class="w-full border-collapse border border-gray-200">
                <thead>
                    <tr class="bg-gray-100">
                        <th class="border border-gray-200 px-3 py-2 text-left text-sm font-semibold">Topic</th>
                        <th class="border border-gray-200 px-3 py-2 text-left text-sm font-semibold">Claim</th>
                    </tr>
                </thead>
                <tbody id="claims-body"></tbody>
            </table>
        </div>
    </div>

    <script src="{{ url_for('static', path='app.js') }}"></script>
</body>
</html>
```

### JavaScript Fetch + Render + CSV Export
```javascript
// In src/static/app.js

// --- State ---
let currentClaims = [];

// --- DOM Elements ---
const sourceText = document.getElementById("source-text");
const generateBtn = document.getElementById("generate-btn");
const loading = document.getElementById("loading");
const errorDiv = document.getElementById("error");
const results = document.getElementById("results");
const totalCount = document.getElementById("total-count");
const claimsBody = document.getElementById("claims-body");
const exportBtn = document.getElementById("export-btn");

// --- Event Listeners ---
generateBtn.addEventListener("click", handleGenerate);
exportBtn.addEventListener("click", handleExport);

// --- Handlers ---
async function handleGenerate() {
    const text = sourceText.value.trim();
    if (!text) return;

    // Confirmation dialog if results already exist
    if (currentClaims.length > 0) {
        if (!confirm("This will replace the current results. Continue?")) return;
    }

    setLoading(true);
    hideError();

    try {
        const response = await fetch("/generate/claims", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ source_text: text }),
        });

        if (!response.ok) {
            let message = "An unexpected error occurred";
            try {
                const err = await response.json();
                message = err.detail || message;
            } catch {
                message = response.statusText || message;
            }
            throw new Error(message);
        }

        const data = await response.json();
        currentClaims = data.claims;
        renderClaims(currentClaims);
    } catch (err) {
        showError(err.message);
        results.classList.add("hidden");
    } finally {
        setLoading(false);
    }
}

// --- Rendering ---
function renderClaims(claims) {
    const grouped = groupByTopic(claims);
    totalCount.textContent = `${claims.length} claims extracted`;
    claimsBody.innerHTML = "";

    for (const [topic, topicClaims] of Object.entries(grouped)) {
        // Topic header row
        const headerRow = document.createElement("tr");
        headerRow.className = "bg-gray-100";
        headerRow.innerHTML = `<td colspan="2" class="border border-gray-200 px-3 py-2 font-bold text-sm">
            ${escapeHTML(topic)} (${topicClaims.length} claims)
        </td>`;
        claimsBody.appendChild(headerRow);

        // Claim rows
        for (const claim of topicClaims) {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td class="border border-gray-200 px-3 py-2 text-sm text-gray-500">${escapeHTML(topic)}</td>
                <td class="border border-gray-200 px-3 py-2 text-sm">${escapeHTML(claim)}</td>
            `;
            claimsBody.appendChild(row);
        }
    }

    results.classList.remove("hidden");
}

// --- Helpers ---
function groupByTopic(claims) {
    const groups = {};
    for (const c of claims) {
        if (!groups[c.claim_topic]) groups[c.claim_topic] = [];
        groups[c.claim_topic].push(c.claim);
    }
    return groups;
}

function escapeHTML(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

function setLoading(on) {
    loading.classList.toggle("hidden", !on);
    generateBtn.disabled = on;
}

function showError(message) {
    errorDiv.textContent = message;
    errorDiv.classList.remove("hidden");
}

function hideError() {
    errorDiv.classList.add("hidden");
}

// --- CSV Export ---
function handleExport() {
    if (!currentClaims.length) return;
    const header = "claim_topic,claim";
    const rows = currentClaims.map(c =>
        escapeCSV(c.claim_topic) + "," + escapeCSV(c.claim)
    );
    const csv = "\uFEFF" + [header, ...rows].join("\r\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "claims.csv";
    a.click();
    URL.revokeObjectURL(url);
}

function escapeCSV(value) {
    if (/[",\n\r]/.test(value)) {
        return '"' + value.replace(/"/g, '""') + '"';
    }
    return value;
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tailwind v3 CDN (`cdn.tailwindcss.com`) | Tailwind v4 CDN (`@tailwindcss/browser@4`) | Jan 2025 (v4.0 release) | New CDN URL, CSS-first config via `@theme`, oklch colors. Most utility class names unchanged. |
| `TemplateResponse("name.html", {"request": request})` | `TemplateResponse(request=request, name="name.html")` | FastAPI 0.108.0 / Starlette 0.29.0 | Named params preferred; old positional style still works but deprecated |
| `<script src="cdn.tailwindcss.com"></script>` | `<script src="cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>` | Jan 2025 | New CDN host for v4 |

**Deprecated/outdated:**
- Tailwind v3 CDN still works but is no longer the current version. v4 is the active development line.
- Old `TemplateResponse` positional argument style is deprecated in favor of named parameters.

## Discretion Recommendations

These are areas where the user granted Claude's discretion. Recommendations based on research:

### Loading Spinner Implementation
**Recommend:** CSS border spinner using Tailwind's `animate-spin` utility. A `div` with `border-2 border-gray-400 border-t-transparent rounded-full animate-spin` at 16x16px (`w-4 h-4`). Zero additional CSS or SVG needed. Matches the utilitarian feel.

### Confirmation Dialog Style
**Recommend:** Native browser `confirm()`. Zero code overhead, universally understood by users, cannot be styled but matches the "developer-tool feel" aesthetic. A custom modal would add HTML/CSS/JS complexity for no functional benefit.

### Error Message Styling and Placement
**Recommend:** Red-tinted banner below the Generate button. Use Tailwind: `bg-red-50 border border-red-200 text-red-700 rounded p-3`. Shows the `detail` field from the API error response. Placed between the button area and the results table so it's immediately visible without scrolling.

### Textarea Placeholder Text and Sizing
**Recommend:** Placeholder: `"Paste your source text here..."`. Size: 10 rows tall, full width. Monospace font (`font-mono`) for readability of raw text. This gives enough space to see a few paragraphs without excessive whitespace.

### Table Border/Stripe Styling
**Recommend:** Light borders (`border-gray-200`) on all cells for clear delineation. Topic header rows with a subtle gray background (`bg-gray-100`) to visually separate groups. No zebra striping on claim rows -- keep it clean and minimal per the utilitarian feel.

### Exact Typography
**Recommend:** System font stack (Tailwind's default `font-sans`). Title at `text-2xl font-bold`. Body text at default size. Table cells at `text-sm`. Monospace for the textarea only.

## Open Questions

1. **Tailwind v4 vs v3 CDN: Which to use?**
   - What we know: v4 CDN (`@tailwindcss/browser@4`) is current. v3 CDN (`cdn.tailwindcss.com`) still works. v4 requires Chrome 111+, Firefox 128+, Safari 16.4+. Most utility class names are the same between v3 and v4.
   - What's unclear: Whether the user's "Tailwind via CDN" intent was specifically v3 or version-agnostic.
   - Recommendation: **Use Tailwind v4 CDN.** It is the current version, the browser requirements are met by any modern browser, and this is a new project with no v3 lock-in. If browser compatibility issues arise during testing, switching to v3 CDN is a one-line change (swap the `<script>` tag).

2. **Route organization: inline in main.py or separate ui.py router?**
   - What we know: It's a single `GET /` route. The existing `main.py` already imports and registers routers.
   - Recommendation: **Add the route directly in `main.py`** since it's a single route and `main.py` already handles template/static setup. A separate `ui.py` router is acceptable but adds a file for one route.

## Sources

### Primary (HIGH confidence)
- Context7 `/websites/fastapi_tiangolo` -- Jinja2Templates, StaticFiles setup, TemplateResponse API
- Context7 `/websites/tailwindcss` -- Play CDN script tag, custom CSS via `type="text/tailwindcss"`
- [FastAPI Templates docs](https://fastapi.tiangolo.com/advanced/templates/) -- Official template/static file documentation
- [Tailwind CSS Play CDN](https://tailwindcss.com/docs/installation/play-cdn) -- Official CDN installation instructions

### Secondary (MEDIUM confidence)
- [RFC 4180](https://datatracker.ietf.org/doc/html/rfc4180) -- CSV format specification for proper field escaping
- [Tailwind v4 CDN setup guide](https://tailkits.com/blog/tailwind-css-v4-cdn-setup/) -- CDN version and browser requirements
- [Tailwind v4 vs v3 comparison](https://staticmania.com/blog/tailwind-v4-vs-v3-comparison) -- Breaking changes and migration notes
- [Client-side CSV download using Blob](https://riptutorial.com/javascript/example/24711/client-side-csv-download-using-blob) -- Blob/URL.createObjectURL pattern

### Tertiary (LOW confidence)
- None. All findings verified with at least two sources.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- Jinja2/StaticFiles are built into FastAPI, verified installed. Tailwind CDN verified via official docs.
- Architecture: HIGH -- Single-page app pattern is well-established. All code examples verified against official docs.
- Pitfalls: HIGH -- Path resolution, Jinja2/JS conflicts, CSV escaping are all well-documented issues with known solutions.

**Research date:** 2026-02-14
**Valid until:** 2026-03-14 (stable technologies, no fast-moving changes expected)
