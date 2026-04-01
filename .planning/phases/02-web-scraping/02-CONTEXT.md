# Phase 2: Web Scraping - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Fetch all paginated event listings from moravska-galerie.cz/program/deti-a-rodiny/ and extract structured event data (title, date text, venue, description, detail URL) with Czech text preserved. This is a one-shot script that runs once a day to update a calendar.

</domain>

<decisions>
## Implementation Decisions

### Pagination Strategy
- **D-01:** Agent's discretion — do the right thing. Parse `data-settings` JSON from `div.ecs-posts` for `max_num_pages`, or follow next-page links. Use dynamic page count discovery, never hardcode page count.

### Extraction Completeness
- **D-02:** If an event card is missing critical fields, **warn and skip** the event. Log what was missing. Continue processing remaining events. Consistent with Phase 1's D-04 error handling philosophy.

### Request Resilience
- **D-03:** This is a one-shot script that runs daily. Warn on individual failures, produce whatever output we can. If we're getting a LOT of failures (e.g., majority of pages failing), bail on the entire run with a clear error — something is fundamentally wrong (site down, structure changed). Don't overcomplicate retry logic.
- **D-04:** 1-second delay between page fetches. Descriptive User-Agent header. Be a polite scraper.

### Agent's Discretion
- **Retry strategy:** Agent decides how many retries per page (if any) — keep it simple.
- **Failure threshold:** Agent decides what "a lot of failures" means — use reasonable judgment.
- **HTML selector strategy:** Agent decides Elementor CSS selectors based on research. Selectors may change when site updates — that's expected and acceptable.
- **Integration with date parser:** Agent decides how scraper feeds raw date text to the Phase 1 date parser.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Site Structure
- `.planning/research/ARCHITECTURE.md` — HTML selectors, Elementor structure, page layout analysis
- `.planning/research/FEATURES.md` — Date Format Matrix, event card field inventory
- `.planning/research/PITFALLS.md` — Scraping pitfalls, encoding issues, selector stability

### Existing Code
- `cal_scraper/models.py` — ParsedDate and Event dataclasses (from Phase 1)
- `cal_scraper/date_parser.py` — Czech date parser (from Phase 1)

### Requirements
- `.planning/REQUIREMENTS.md` — SCRP-01 through SCRP-07

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `cal_scraper/models.py` — Event dataclass with title, date_text, parsed_date, venue, description, url, uid fields
- `cal_scraper/date_parser.py` — `parse_date(text)` function returns ParsedDate or None
- `cal_scraper/models.py` — PRAGUE_TZ and DEFAULT_DURATION constants

### Established Patterns
- Warn-and-skip on unparseable data (D-04 from Phase 1)
- Flat module structure in `cal_scraper/` package
- pytest for testing

### Integration Points
- Scraper produces list of Event objects → feeds into Phase 3 (ICS generation)
- Scraper calls `parse_date()` to convert raw date text to ParsedDate objects
- WordPress post IDs from HTML classes (e.g., `post-19256`) → use for stable UIDs

</code_context>

<specifics>
## Specific Ideas

- This runs once a day to update a calendar — it's not a real-time service
- Czech diacritics must be preserved (UTF-8 throughout)
- Include link to event detail page in each Event for downstream iCal URL field

</specifics>

<deferred>
## Deferred Ideas

- Detail page scraping (full descriptions, images) — v2 requirement, not Phase 2
- Caching/conditional requests (If-Modified-Since) — unnecessary for daily one-shot

</deferred>

---

*Phase: 02-web-scraping*
*Context gathered: 2026-04-01*
