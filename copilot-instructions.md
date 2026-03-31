<!-- GSD:project-start source:PROJECT.md -->
## Project

**Cal-Scraper**

A Python script that scrapes the Moravská galerie (Moravian Gallery in Brno) website's children and family events section and generates an iCal (.ics) feed. The events are in Czech and are not translated — the .ics file preserves the original Czech text. Users run the script manually to get a fresh calendar file.

**Core Value:** Reliably extract all upcoming children/family events from moravska-galerie.cz and produce a valid .ics file that any calendar app can import.

### Constraints

- **Language:** Python — good ecosystem for scraping (requests, BeautifulSoup) and iCal generation (icalendar)
- **No JS rendering:** The site serves static HTML, so no headless browser needed
- **Respectful scraping:** Include reasonable delays between page fetches, proper User-Agent header
- **Timezone:** Events are in Europe/Prague timezone (CET/CEST)
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### Python Version
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | ≥3.10 | Runtime | Required by `requests` 2.33+ and `icalendar` 7.x. Local system has 3.14.3. Use `>=3.10` as floor to match strictest dependency. |
### Core Libraries
| Library | Version | Purpose | Why | Confidence |
|---------|---------|---------|-----|------------|
| **requests** | 2.33.1 | HTTP fetching | De facto standard for synchronous HTTP. Simple API, automatic retries with adapters, session support for connection pooling across paginated fetches. No async needed — we're hitting 5 sequential pages with polite delays. | HIGH — verified PyPI 2026-03-31 |
| **beautifulsoup4** | 4.14.3 | HTML parsing + extraction | Best library for messy real-world HTML. The target site uses WordPress/Elementor with deeply nested divs — BS4's CSS selectors and `.find()`/`.find_all()` handle this cleanly. Forgiving parser handles malformed HTML. | HIGH — verified PyPI 2026-03-31 |
| **lxml** | 6.0.2 | BS4 parser backend | Use `lxml` as BeautifulSoup's parser (`BeautifulSoup(html, 'lxml')`). ~10x faster than `html.parser`, handles malformed HTML better than `html5lib`. The 137KB pages from the target site parse noticeably faster. C extension, but wheels available for all platforms. | HIGH — verified PyPI 2026-03-31 |
| **icalendar** | 7.0.3 | iCal (.ics) generation | The standard Python library for RFC 5545 iCalendar files. v7 has a clean `Event.new()` constructor API with named parameters (`summary`, `start`, `end`, `location`, `description`, `url`). Handles VTIMEZONE generation via `calendar.add_missing_timezones()`. Actively maintained (4 releases in Feb-Mar 2026). | HIGH — verified PyPI 2026-03-31, API verified from source |
### Supporting Libraries
| Library | Version | Purpose | When to Use | Confidence |
|---------|---------|---------|-------------|------------|
| **python-dateutil** | 2.9.0.post0 | Timezone support | Already a dependency of `icalendar` — comes for free. Not used for date parsing here (Czech date formats need custom regex), but provides `tz` utilities if needed. | HIGH — verified PyPI |
| **zoneinfo** (stdlib) | — | Europe/Prague timezone | Python 3.9+ stdlib module. Use `ZoneInfo("Europe/Prague")` for all event datetimes. Preferred over `pytz` which is in maintenance mode. `icalendar` v7 works natively with `zoneinfo`. | HIGH — stdlib |
| **tzdata** | ≥2025.3 | Timezone database | Already a dependency of `icalendar` 7.x. Required on platforms without system timezone data. No action needed — installed automatically. | HIGH — verified from icalendar deps |
| **re** (stdlib) | — | Czech date parsing | Custom regex for the 6 date formats found on the target site. No library handles `"31/3/2026, 15 H"` or `"13/7 – 17/7/2026, 9–16 H"` out of the box. | HIGH — stdlib |
| **argparse** (stdlib) | — | CLI argument parsing | Configure output path, verbosity. Stdlib is sufficient for a simple CLI with 2-3 options. No need for `click` or `typer`. | HIGH — stdlib |
| **logging** (stdlib) | — | Structured logging | Report progress, warnings for unparseable events, network errors. | HIGH — stdlib |
### Dev Dependencies
| Library | Version | Purpose | Confidence |
|---------|---------|---------|------------|
| **pytest** | latest | Testing | Standard test runner. | HIGH |
| **responses** | latest | Mock HTTP responses | Mock `requests` calls for testing without hitting the live site. Avoids flaky tests and respects the site. | HIGH |
| **ruff** | latest | Linting + formatting | Single tool replaces flake8, isort, black. Fast, opinionated. | HIGH |
## Alternatives Considered
| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| HTTP client | **requests** 2.33 | httpx 0.28 | httpx's async support is wasted here — we need synchronous sequential fetching with delays. requests has a simpler API, is more widely known, and has no extra complexity. httpx would be better if we needed async or HTTP/2, neither of which applies. |
| HTTP client | **requests** 2.33 | urllib3 / urllib | Too low-level. requests wraps urllib3 already. No reason to handle connection pools and encoding manually. |
| HTTP client | **requests** 2.33 | scrapy | Nuclear option for 5 pages. Scrapy is a full crawling framework with its own event loop, middleware pipeline, and project structure. Massive overkill for a one-shot linear script. |
| HTML parser | **beautifulsoup4** + lxml | selectolax 0.4.7 | Faster but smaller ecosystem, less forgiving with malformed HTML, smaller community. Speed doesn't matter for 5 pages. |
| HTML parser | **beautifulsoup4** + lxml | parsel 1.1.0 | Scrapy's parser. Good for XPath but CSS selectors are enough here. Smaller community outside Scrapy. |
| HTML parser backend | **lxml** 6.0 | html.parser (stdlib) | Slower and less tolerant of malformed HTML. lxml is worth the dependency for reliability. |
| HTML parser backend | **lxml** 6.0 | html5lib | Very slow (pure Python). Overkill HTML5 compliance not needed — the WordPress site produces valid-enough HTML. |
| iCal generation | **icalendar** 7.0 | ics.py | Less actively maintained, fewer features, smaller community. icalendar is the canonical Python iCal library. |
| iCal generation | **icalendar** 7.0 | Manual string building | Fragile. RFC 5545 has subtle rules (line folding, escaping, VTIMEZONE). Let a tested library handle it. |
| Date parsing | **Custom regex** | python-dateutil parser | dateutil's parser doesn't understand Czech date formats like "31/3/2026, 15 H" or "7/7 – 11/7/2026". You'd spend more time configuring it than writing regex. |
| Date parsing | **Custom regex** | babel / locale-aware parsing | Still doesn't handle the gallery's nonstandard format (bullet prefix, "H" suffix, en-dash ranges). Custom parsing is the only reliable path. |
| Timezone | **zoneinfo** (stdlib) | pytz | pytz is in maintenance mode. Its `.localize()` API is error-prone. `zoneinfo` is stdlib since 3.9 and is what `icalendar` v7 uses internally. |
| CLI framework | **argparse** (stdlib) | click / typer | Two options for a script with 1-2 flags is overkill. argparse is zero-dependency and sufficient. |
## Date Formats Found on Target Site
| Format | Example | Frequency | Parsing Approach |
|--------|---------|-----------|-----------------|
| Day with hour | `31/3/2026, 15 H` | Most common | Regex: `(\d{1,2})/(\d{1,2})/(\d{4}),\s*(\d{1,2})\s*H` |
| Day with fractional hour | `8/4/2026, 16.30 H` | Occasional | Regex: `(\d{1,2})/(\d{1,2})/(\d{4}),\s*(\d{1,2})\.(\d{2})\s*H` |
| Day without time | `23/5/2026` | Rare | Regex: `(\d{1,2})/(\d{1,2})/(\d{4})$` → all-day event |
| Day with multiple times | `24/5/2026, 15 H / 16 H / 17 H` | Rare | Parse first time, or create multiple events |
| Multi-day range (no time) | `7/7 – 11/7/2026` | Summer camps | Regex with en-dash: `(\d{1,2})/(\d{1,2})\s*–\s*(\d{1,2})/(\d{1,2})/(\d{4})` |
| Multi-day range with time | `13/7 – 17/7/2026, 9–16 H` | Summer camps | Combine range + time regexes |
## Target Site HTML Structure
- **Platform:** WordPress + Elementor + ECS (Elementor Custom Skin)
- **Event cards:** `<article class="elementor-post elementor-grid-item ecs-post-loop post-{ID} ...">`
- **Pagination:** URL pattern `/program/deti-a-rodiny/{page}/` (pages 2-5)
- **Data per card:** title, date (with `●` prefix), venue name, thumbnail, link to detail page
- **Response size:** ~137KB per page (standard HTML, no JS rendering needed)
- **Static HTML:** Confirmed — `curl` retrieves all event data without JavaScript execution
## Installation
# Create virtual environment
# Core dependencies
# Dev dependencies
### pyproject.toml (recommended)
## Key API Patterns
### icalendar v7 Event Creation (verified from source)
### requests with polite delays
## Sources
- PyPI package metadata (requests, beautifulsoup4, lxml, icalendar, python-dateutil, httpx, pytz) — verified 2026-03-31
- icalendar GitHub source: `collective/icalendar` main branch — CHANGES.rst, cal/event.py, docs/how-to/usage.rst
- Target site HTML: live curl inspection of all 5 pages of moravska-galerie.cz/program/deti-a-rodiny/
- Python 3.14.3 stdlib documentation (zoneinfo, re, argparse, logging)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
