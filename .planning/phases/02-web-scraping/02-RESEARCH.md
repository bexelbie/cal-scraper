# Phase 2: Web Scraping - Research

**Researched:** 2026-04-01
**Domain:** Python web scraping (requests + BeautifulSoup) against WordPress/Elementor site
**Confidence:** HIGH

## Summary

Phase 2 builds the HTTP fetcher and HTML extractor for moravska-galerie.cz/program/deti-a-rodiny/. The target site serves static HTML via WordPress 6.9 + Elementor 3.33 + Ele Custom Skin, with paginated event listings across 5 pages (28 events currently). All data is in the initial HTML response — no JavaScript rendering needed.

Live verification on 2026-04-01 confirms: all CSS selectors from prior research are still valid, the pagination `data-settings` JSON approach works reliably, and the Phase 1 date parser handles all 28 current date strings without modification. The scraper needs two new modules (`fetcher.py` and `extractor.py`) plus the `responses` library for HTTP mocking in tests.

**Primary recommendation:** Build fetcher (HTTP + pagination discovery) and extractor (HTML → Event objects) as separate modules. Use Elementor `data-id` selectors as primary extraction strategy. Save HTML fixtures from the live site for deterministic testing.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01 (Pagination):** Agent's discretion — do the right thing. Parse `data-settings` JSON from `div.ecs-posts` for `max_num_pages`, or follow next-page links. Use dynamic page count discovery, never hardcode page count.
- **D-02 (Extraction Completeness):** If an event card is missing critical fields, **warn and skip** the event. Log what was missing. Continue processing remaining events. Consistent with Phase 1's D-04 error handling philosophy.
- **D-03 (Request Resilience):** This is a one-shot script that runs daily. Warn on individual failures, produce whatever output we can. If we're getting a LOT of failures (e.g., majority of pages failing), bail on the entire run with a clear error — something is fundamentally wrong (site down, structure changed). Don't overcomplicate retry logic.
- **D-04 (Polite Scraping):** 1-second delay between page fetches. Descriptive User-Agent header. Be a polite scraper.

### Agent's Discretion
- **Retry strategy:** Agent decides how many retries per page (if any) — keep it simple.
- **Failure threshold:** Agent decides what "a lot of failures" means — use reasonable judgment.
- **HTML selector strategy:** Agent decides Elementor CSS selectors based on research. Selectors may change when site updates — that's expected and acceptable.
- **Integration with date parser:** Agent decides how scraper feeds raw date text to the Phase 1 date parser.

### Deferred Ideas (OUT OF SCOPE)
- Detail page scraping (full descriptions, images) — v2 requirement, not Phase 2
- Caching/conditional requests (If-Modified-Since) — unnecessary for daily one-shot

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SCRP-01 | Scrape all paginated pages of /program/deti-a-rodiny/ (detect last page dynamically) | `data-settings` JSON on `div.ecs-posts` contains `max_num_pages` (verified: currently 5). Pagination URLs use `/deti-a-rodiny/{n}/` pattern. Page beyond max returns 301 redirect to page 1. |
| SCRP-02 | Extract event title preserving Czech diacritics and special characters | `[data-id="ff31590"] a` selector returns title text; BS4's `.get_text()` handles HTML entity decoding (e.g., `&amp;` → `&`). UTF-8 encoding confirmed. |
| SCRP-03 | Extract venue name including sub-locations | `[data-id="d2f8856"] .elementor-widget-container` returns venue; 9 unique venues found including comma-separated sub-locations (e.g., "Pražákův palác, Knihovna"). |
| SCRP-04 | Extract short description text from listing pages | `[data-id="16d0837"] .elementor-widget-container` returns truncated description. Contains `\xa0` non-breaking spaces that need normalization. |
| SCRP-05 | Extract event detail page URL for each event | URL is in the `href` attribute of `[data-id="ff31590"] a`. All URLs are absolute (`https://moravska-galerie.cz/program/...`). |
| SCRP-06 | Handle network errors gracefully (retry transient failures, log warnings, continue) | Use `requests.Session` with timeout; catch `RequestException`; warn-and-continue per page, bail if majority fail. |
| SCRP-07 | Use respectful scraping practices (delays, User-Agent) | 1-second `time.sleep()` between fetches; descriptive `User-Agent` header on session. |

</phase_requirements>

## Standard Stack

### Core (already installed in project venv)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| requests | 2.33.1 | HTTP fetching | Already installed. Session support for connection pooling + shared headers across paginated fetches. |
| beautifulsoup4 | 4.14.3 | HTML parsing | Already installed. CSS selector support, `.get_text()` handles entity decoding, forgiving of malformed HTML. |
| lxml | 6.0.2 | BS4 parser backend | Already installed. Use `BeautifulSoup(html, 'lxml')` — faster and more tolerant than html.parser. |

### Supporting (stdlib)
| Library | Purpose | When to Use |
|---------|---------|-------------|
| time | `time.sleep(1)` between requests | Every page fetch (SCRP-07) |
| json | Parse `data-settings` JSON for pagination | Pagination discovery (SCRP-01) |
| logging | Structured warnings for skipped events/failed pages | Error reporting (SCRP-06, D-02) |
| re | Extract post-ID from article class attribute | UID extraction for Phase 3 |

### Dev Dependencies (needed for testing)
| Library | Version | Purpose |
|---------|---------|---------|
| responses | 0.26.0 | Mock `requests` calls in tests — avoids hitting live site |
| pytest | (already installed) | Test runner |

**Installation:**
```bash
.venv/bin/pip install responses
```

Note: `responses` should also be added to `pyproject.toml` `[project.optional-dependencies] dev` list.

## Architecture Patterns

### New Module Structure
```
cal_scraper/
├── __init__.py          # existing
├── models.py            # existing (Event, ParsedDate)
├── date_parser.py       # existing (parse_date)
├── fetcher.py           # NEW — HTTP requests + pagination
└── extractor.py         # NEW — HTML parsing → Event objects

tests/
├── test_date_parser.py  # existing
├── test_fetcher.py      # NEW
├── test_extractor.py    # NEW
└── fixtures/            # NEW — saved HTML for deterministic tests
    ├── page_1.html
    └── page_5_last.html
```

### Pattern 1: Fetcher Module — HTTP + Pagination Discovery
**What:** A `fetch_all_pages()` function that discovers page count from page 1 then fetches all pages sequentially with delays.
**When:** Called from the main pipeline.
**Why:** Separates HTTP concerns from HTML parsing. Testable with mocked responses.

```python
# cal_scraper/fetcher.py
import json
import logging
import time

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://moravska-galerie.cz/program/deti-a-rodiny/"
USER_AGENT = "cal-scraper/0.1 (+https://github.com/bexelbie/cal-scraper)"
REQUEST_DELAY = 1  # seconds between requests
REQUEST_TIMEOUT = 30  # seconds

def _get_max_pages(html: str) -> int:
    """Extract max_num_pages from div.ecs-posts data-settings JSON."""
    soup = BeautifulSoup(html, "lxml")
    container = soup.select_one("div.ecs-posts")
    if container and container.get("data-settings"):
        settings = json.loads(container["data-settings"])
        return settings.get("max_num_pages", 1)
    return 1

def _page_url(page_num: int) -> str:
    """Build URL for a page number. Page 1 = base URL (no suffix)."""
    if page_num <= 1:
        return BASE_URL
    return f"{BASE_URL}{page_num}/"

def fetch_all_pages() -> list[str]:
    """Fetch all paginated event listing pages. Returns list of HTML strings."""
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    # Fetch page 1 to discover total pages
    resp = session.get(_page_url(1), timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    pages = [resp.text]
    max_pages = _get_max_pages(resp.text)
    logger.info("Discovered %d pages of events", max_pages)

    # Fetch remaining pages
    failed = 0
    for page_num in range(2, max_pages + 1):
        time.sleep(REQUEST_DELAY)
        try:
            resp = session.get(_page_url(page_num), timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            pages.append(resp.text)
        except requests.RequestException as e:
            failed += 1
            logger.warning("Failed to fetch page %d: %s", page_num, e)
            # Bail if majority of pages fail
            if failed > max_pages // 2:
                raise RuntimeError(
                    f"Too many failures ({failed}/{max_pages}): site may be down or changed"
                ) from e

    logger.info("Fetched %d/%d pages successfully", len(pages), max_pages)
    return pages
```

### Pattern 2: Extractor Module — HTML → Event Objects
**What:** An `extract_events()` function that parses HTML pages into Event objects using Elementor data-id selectors.
**When:** Called after fetching all pages.
**Why:** Pure function (HTML in → Events out), easily testable with saved fixtures.

```python
# cal_scraper/extractor.py
import logging
import re

from bs4 import BeautifulSoup, Tag

from cal_scraper.date_parser import parse_date
from cal_scraper.models import Event

logger = logging.getLogger(__name__)

# Elementor widget data-id selectors (from loop template ID 1575)
ARTICLE_SELECTOR = "article.elementor-post"
TITLE_SELECTOR = '[data-id="ff31590"] a'
DATE_SELECTOR = '[data-id="fe5263e"] .elementor-widget-container'
VENUE_SELECTOR = '[data-id="d2f8856"] .elementor-widget-container'
DESCRIPTION_SELECTOR = '[data-id="16d0837"] .elementor-widget-container'

_POST_ID_RE = re.compile(r"post-(\d+)")

def _extract_post_id(article: Tag) -> str | None:
    """Extract WordPress post ID from article class list."""
    classes = article.get("class", [])
    for cls in classes:
        m = _POST_ID_RE.match(cls)
        if m:
            return m.group(1)
    return None

def _normalize_text(text: str) -> str:
    """Normalize non-breaking spaces and whitespace."""
    return text.replace("\xa0", " ").strip()

def extract_events_from_html(html: str) -> list[Event]:
    """Extract Event objects from a single page's HTML."""
    soup = BeautifulSoup(html, "lxml")
    articles = soup.select(ARTICLE_SELECTOR)
    events = []

    for article in articles:
        # Title + URL
        title_el = article.select_one(TITLE_SELECTOR)
        if not title_el:
            logger.warning("Skipping article: no title found")
            continue
        title = _normalize_text(title_el.get_text())
        url = title_el.get("href", "")

        # Date
        date_el = article.select_one(DATE_SELECTOR)
        if not date_el:
            logger.warning("Skipping '%s': no date found", title)
            continue
        raw_date = date_el.get_text(strip=True)
        parsed = parse_date(raw_date)
        if parsed is None:
            logger.warning("Skipping '%s': unparseable date %r", title, raw_date)
            continue

        # Venue (optional but expected)
        venue_el = article.select_one(VENUE_SELECTOR)
        venue = _normalize_text(venue_el.get_text()) if venue_el else ""

        # Description (optional)
        desc_el = article.select_one(DESCRIPTION_SELECTOR)
        description = _normalize_text(desc_el.get_text()) if desc_el else ""

        events.append(Event(
            title=title,
            dtstart=parsed.dtstart,
            dtend=parsed.dtend,
            all_day=parsed.all_day,
            venue=venue,
            description=description,
            url=url,
            raw_date=parsed.raw_text,
        ))

    return events

def extract_events(pages: list[str]) -> list[Event]:
    """Extract events from all fetched pages."""
    all_events = []
    for i, html in enumerate(pages, 1):
        page_events = extract_events_from_html(html)
        logger.info("Page %d: extracted %d events", i, len(page_events))
        all_events.extend(page_events)
    return all_events
```

### Pattern 3: Selector Constants at Module Top
**What:** All Elementor data-id selectors as named constants.
**Why:** When the gallery re-saves their Elementor template, all data-ids change simultaneously. Having them at the top of `extractor.py` means one-place updates.

### Pattern 4: Test Fixtures from Live HTML
**What:** Save actual page HTML as test fixtures for deterministic extractor tests.
**Why:** Tests don't hit the network, run fast, are reproducible, and can detect regressions if selectors change.

```python
# tests/test_extractor.py — example
def test_extract_events_page1(page1_fixture):
    events = extract_events_from_html(page1_fixture)
    assert len(events) == 6
    assert events[0].title == "Rodinné odpoledne: S úsměvem"
    assert events[0].venue == "Muzeum Josefa Hoffmanna"
```

### Anti-Patterns to Avoid
- **Hardcoded page count:** Never `for page in range(1, 6)`. Use `max_num_pages` from `data-settings`.
- **Generic CSS selectors:** Don't use `h2 > a` or `article p`. Use specific `data-id` selectors.
- **Silent swallowing of parse errors:** Always log what was skipped and why.
- **Grabbing CTA text as title:** `[data-id="87e5159"]` is the CTA widget ("Koupit vstupenky"), NOT the title. Title is `[data-id="ff31590"]`.
- **REST API for dates:** WP REST API `date` field is the *publish date*, not the event date. Event dates are only in the HTML text widgets.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML entity decoding | Manual regex `&amp;` → `&` | BS4's `.get_text()` | Handles all HTML entities automatically including numeric (`&#8230;`) and named |
| HTTP session management | Manual cookie/header tracking | `requests.Session()` | Connection pooling, persistent headers, cookie jar |
| HTML parsing | Regex-based HTML extraction | BeautifulSoup + lxml | Handles malformed HTML, nested elements, attribute parsing correctly |
| JSON parsing of data-settings | String manipulation | `json.loads()` | Handles escaping, nested values, edge cases |
| HTTP response mocking | Custom test doubles | `responses` library | Intercepts `requests` calls cleanly, supports status codes, timeouts, exceptions |

## Common Pitfalls

### Pitfall 1: Page Beyond Max Returns 301 Redirect (Not 404)
**What goes wrong:** Fetching page 6 (beyond 5 existing) returns `301 → /program/deti-a-rodiny/` (page 1), not 404. A "fetch until error" loop creates an infinite loop re-scraping page 1.
**Why it happens:** WordPress rewrite rules redirect invalid pagination to the base URL.
**How to avoid:** Use `max_num_pages` from `data-settings` JSON to know exactly how many pages to fetch. Never rely on "fetch until 404".
**Warning signs:** Scraper runs unusually long; duplicate events appear in output.

### Pitfall 2: CTA Widget Confused With Title
**What goes wrong:** Each event card has a CTA widget (`data-id="87e5159"`) above the title with text like "Koupit vstupenky" or "Rezervace přes telefon". Grabbing "first heading in article" gets the CTA, not the title.
**Why it happens:** Both CTA and title are heading-level elements in the DOM.
**How to avoid:** Always use the specific `data-id="ff31590"` selector for the title widget.
**Warning signs:** If any event title is "Koupit vstupenky", the wrong selector is being used.

### Pitfall 3: Non-Breaking Spaces in Descriptions
**What goes wrong:** Descriptions contain `\xa0` (U+00A0 non-breaking space) from the CMS. If not normalized, text comparison and display may behave unexpectedly.
**Why it happens:** WordPress/Elementor inserts `&nbsp;` in content, BS4 decodes to `\xa0`.
**How to avoid:** Replace `\xa0` with regular space after `.get_text()`: `text.replace('\xa0', ' ')`.
**Warning signs:** Descriptions look right but string comparisons fail in tests.

### Pitfall 4: Bullet Without Space Before Date
**What goes wrong:** Most dates have `● 31/3/2026` (bullet + space + date), but P2A1 has `●16/4/2026` (no space). The Phase 1 parser's `_clean()` function already handles this via `re.sub(r"^●\s*", "", text)`.
**Why it happens:** Inconsistent data entry in the CMS.
**How to avoid:** Already handled by Phase 1 parser. Just pass the raw text from BS4 directly to `parse_date()`.
**Warning signs:** Events from page 2 are unexpectedly skipped.

### Pitfall 5: HTML Entity in Titles (e.g., `&amp;` → `&`)
**What goes wrong:** Raw HTML has `Story &amp;?` but the actual title is `Story &?`. If using regex extraction instead of BS4, entities remain encoded.
**Why it happens:** HTML entity encoding in the source.
**How to avoid:** Use BS4's `.get_text()` which automatically decodes entities.
**Warning signs:** Titles contain `&amp;` or `&#` literals.

### Pitfall 6: Event Model Missing `post_id` Field
**What goes wrong:** The current `Event` dataclass has no `post_id` or `uid` field, but Phase 3 needs WordPress post IDs (e.g., `post-19256`) for stable UID generation.
**Why it happens:** Phase 1 created the model for date parsing only.
**How to avoid:** Add `post_id: str` field to the `Event` model in this phase. Extract from article class attribute using `re.compile(r"post-(\d+)")`.
**Warning signs:** Phase 3 has no stable identifier for UID generation.

## Code Examples

### Pagination Discovery (verified against live site)
```python
# div.ecs-posts has data-settings='{"current_page":1,"max_num_pages":5,...}'
import json
from bs4 import BeautifulSoup

soup = BeautifulSoup(html, "lxml")
container = soup.select_one("div.ecs-posts")
settings = json.loads(container["data-settings"])
max_pages = settings["max_num_pages"]  # 5
```
Source: Live site inspection, all 5 pages have identical structure.

### Event Field Extraction (verified against live site)
```python
article = soup.select_one("article.elementor-post")

# Title + URL
title_el = article.select_one('[data-id="ff31590"] a')
title = title_el.get_text(strip=True)        # "Rodinné odpoledne: S úsměvem"
url = title_el["href"]                        # "https://moravska-galerie.cz/program/..."

# Date text (pass directly to parse_date)
date_el = article.select_one('[data-id="fe5263e"] .elementor-widget-container')
raw_date = date_el.get_text(strip=True)       # "● 31/3/2026, 15 H"

# Venue
venue_el = article.select_one('[data-id="d2f8856"] .elementor-widget-container')
venue = venue_el.get_text(strip=True)         # "Muzeum Josefa Hoffmanna"

# Description
desc_el = article.select_one('[data-id="16d0837"] .elementor-widget-container')
desc = desc_el.get_text(strip=True)           # Truncated listing text

# Post ID (from article class)
import re
classes = article.get("class", [])
post_id_match = re.search(r"post-(\d+)", " ".join(classes))
post_id = post_id_match.group(1) if post_id_match else None  # "19256"
```
Source: BeautifulSoup extraction verified against all 28 events on live site.

### Polite HTTP Session
```python
import time
import requests

session = requests.Session()
session.headers["User-Agent"] = "cal-scraper/0.1 (+https://github.com/bexelbie/cal-scraper)"

for page_num in range(1, max_pages + 1):
    if page_num > 1:
        time.sleep(1)  # 1-second delay between requests
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
```

### Testing with `responses` Library
```python
import responses

@responses.activate
def test_fetch_page1():
    responses.add(
        responses.GET,
        "https://moravska-galerie.cz/program/deti-a-rodiny/",
        body=open("tests/fixtures/page_1.html").read(),
        status=200,
    )
    pages = fetch_all_pages()
    assert len(pages) >= 1
```

## Verified Live Site Data (2026-04-01)

### Pagination
- **URL pattern:** `https://moravska-galerie.cz/program/deti-a-rodiny/{n}/` (page 1 has no suffix)
- **Total pages:** 5 (from `data-settings.max_num_pages`)
- **Events per page:** 6, 6, 6, 6, 4 = **28 total events**
- **Page 6 behavior:** 301 redirect to page 1 (confirmed)
- **Response size:** ~124-137 KB per page
- **Content-Type:** text/html; charset=UTF-8

### Selector Verification (all 28 events)
| Selector | Target | Success Rate | Notes |
|----------|--------|-------------|-------|
| `article.elementor-post` | Event card container | 28/28 ✓ | All have `post-{id}` class |
| `[data-id="ff31590"] a` | Title + URL | 28/28 ✓ | BS4 decodes HTML entities |
| `[data-id="fe5263e"] .elementor-widget-container` | Date text | 28/28 ✓ | All parse with Phase 1 parser |
| `[data-id="d2f8856"] .elementor-widget-container` | Venue | 28/28 ✓ | 9 unique venues found |
| `[data-id="16d0837"] .elementor-widget-container` | Description | 28/28 ✓ | Contains `\xa0`, needs normalization |
| `div.ecs-posts[data-settings]` | Pagination JSON | 5/5 ✓ | Present on every page |

### Date Format Distribution (all 28 events)
| Format | Count | Example |
|--------|-------|---------|
| Single day + hour (`D/M/YYYY, HH H`) | 17 | `31/3/2026, 15 H` |
| Single day + hour.min (`D/M/YYYY, HH.MM H`) | 2 | `8/4/2026, 16.30 H` |
| Date only (`D/M/YYYY`) | 1 | `23/5/2026` |
| Multiple time slots (`D/M/YYYY, HH H / HH H / HH H`) | 1 | `24/5/2026, 15 H / 16 H / 17 H` |
| Multi-day no time (`D/M – D/M/YYYY`) | 1 | `7/7 – 11/7/2026` |
| Multi-day + time (`D/M – D/M/YYYY, H–H H`) | 6 | `13/7 – 17/7/2026, 9–16 H` |
| **All 28 parse successfully with Phase 1 parser** | | |

### Post IDs (for Phase 3 UID generation)
All 28 articles have unique post IDs in their class attributes: `post-19187` through `post-19734`.

### Venue List (9 unique)
- Jurkovičova vila
- Káznice
- Muzeum Josefa Hoffmana (note: single n — spelling inconsistency)
- Muzeum Josefa Hoffmanna (double n — correct spelling)
- Místodržitelský palác, Besední dům
- Otevřený depozitář
- Pražákův palác
- Pražákův palác, Knihovna
- Uměleckoprůmyslové muzeum

## Model Extension Required

The `Event` dataclass needs a `post_id` field added for WordPress post ID extraction. This is needed by Phase 3 for stable UID generation (`{post_id}@moravska-galerie.cz`).

**Current model:**
```python
@dataclass
class Event:
    title: str
    dtstart: datetime | date
    dtend: datetime | date | None
    all_day: bool
    venue: str
    description: str
    url: str
    raw_date: str
```

**Required addition:**
```python
@dataclass
class Event:
    title: str
    dtstart: datetime | date
    dtend: datetime | date | None
    all_day: bool
    venue: str
    description: str
    url: str
    raw_date: str
    post_id: str  # WordPress post ID (e.g., "19256") for stable UID generation
```

This is a backward-compatible addition — Phase 1 tests don't construct Event objects.

## Open Questions

1. **Retry strategy — how many retries?**
   - What we know: D-03 says keep it simple, daily one-shot script
   - Recommendation: 1 retry per page with 2-second backoff. Simple, handles transient blips. No exponential backoff needed.

2. **Failure threshold — what is "a lot"?**
   - What we know: D-03 says bail on mass failures
   - Recommendation: If more than half of pages fail (i.e., `failed > max_pages // 2`), bail. For 5 pages, that means 3+ failures = abort.

3. **Should test fixtures be committed to git?**
   - Recommendation: Yes — save page_1.html (representative single-day events) and page_5.html (multi-day events) as test fixtures. They're ~130KB each but essential for deterministic tests.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | ✓ | 3.14.3 | — |
| requests | HTTP fetching | ✓ | 2.33.1 | — |
| beautifulsoup4 | HTML parsing | ✓ | 4.14.3 | — |
| lxml | BS4 parser backend | ✓ | 6.0.2 | — |
| responses | HTTP mocking in tests | ✗ | — | Install: `pip install responses` |
| pytest | Test runner | ✓ | (installed) | — |
| moravska-galerie.cz | Target site | ✓ | HTTP 200 | — |

**Missing dependencies with no fallback:** None

**Missing dependencies with fallback:**
- `responses` — not installed, needs `pip install responses` and addition to pyproject.toml dev deps

## Sources

### Primary (HIGH confidence)
- **Live site HTML** — All 5 pages fetched and analyzed 2026-04-01, all selectors verified against 28 events
- **Phase 1 code** — `cal_scraper/models.py` and `cal_scraper/date_parser.py` reviewed, all 28 live date strings verified to parse correctly
- **Project venv** — Library versions verified: requests 2.33.1, beautifulsoup4 4.14.3, lxml 6.0.2

### Secondary (MEDIUM confidence)
- **Research docs** — `.planning/research/ARCHITECTURE.md`, `FEATURES.md`, `PITFALLS.md` — findings confirmed still accurate against live site

### Tertiary (LOW confidence)
- None — all findings verified against live data

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed and verified
- Architecture: HIGH — selectors verified against all 28 live events, patterns follow Phase 1 conventions
- Pitfalls: HIGH — all pitfalls from research docs confirmed against live site data

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (site structure could change if gallery updates Elementor template, but historically stable)
