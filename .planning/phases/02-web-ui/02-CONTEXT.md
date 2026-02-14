# Phase 2: Web UI - Context

**Gathered:** 2026-02-14
**Status:** Ready for planning

<domain>
## Phase Boundary

A web page where non-technical curators paste source text, generate claims via the Phase 1 API, and export results as CSV. The page has a textarea, a Generate button, a claims table grouped by topic, and an Export CSV button. Error handling shows human-readable messages. No authentication, no multi-user features, no database.

</domain>

<decisions>
## Implementation Decisions

### Page layout & style
- Minimal and utilitarian — clean, no frills, developer-tool feel
- Medium centered layout (~960px max-width)
- Light mode only, no dark mode or theme switching
- Simple title bar with app name (e.g. "Claim Extractor"), no navigation links

### Results presentation
- Claims grouped by `claim_topic` with bold header rows spanning the table
- Each topic header shows per-topic count, e.g. "Economics (7 claims)"
- Total claims count displayed above the table, e.g. "42 claims extracted"
- No sorting or filtering — static table, what the API returns is what you see

### Interaction flow
- Textarea stays visible after generation — user can edit and re-generate
- Loading state: small spinner with "Thinking..." label, Generate button disabled
- Export CSV button placed above the table, near the total claims count
- Re-generating with new text shows a confirmation dialog before replacing current results

### Tools & frameworks
- Vanilla HTML/JS — no React or frontend framework
- Tailwind CSS via CDN script tag — no build step
- Tailwind utility classes only — no custom CSS files
- Jinja2 templates served by FastAPI — allows server-side value injection
- Static files live in `src/static/`

### Claude's Discretion
- Exact typography choices and spacing
- Loading spinner implementation
- Confirmation dialog style (native browser confirm vs custom)
- Error message styling and placement
- Textarea placeholder text and sizing
- Table border/stripe styling

</decisions>

<specifics>
## Specific Ideas

- Loading label specifically "Thinking..." (not "Generating..." or "Loading...")
- User wants Tailwind via CDN for zero build complexity

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-web-ui*
*Context gathered: 2026-02-14*
