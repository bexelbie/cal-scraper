# Architecture Patterns

**Domain:** Python web scraper → iCal (.ics) generator
**Researched:** 2026-03-31
**Overall confidence:** HIGH — based on direct HTML analysis of target site plus well-established library patterns

## Recommended Architecture

A **linear pipeline** of 5 discrete components, each with a single responsibility. This is the standard pattern for scrape-to-output tools: fetch → parse → normalize → generate → write. No need for async, queuing, or microservices — this is a one-shot CLI script processing ~50 events across 5 pages.

```
┌──────────┐    ┌────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────┐
│  Fetcher │───▶│  Extractor │───▶│ Date Parser  │───▶│ ICS Builder  │───▶│  Writer  │
│ (HTTP)   │    │ (HTML→data)│    │ (Czech→dt)   │    │ (data→ical)  │    │ (file)   │
└──────────┘    └────────────┘    └──────────────┘    └──────────────┘    └──────────┘
     │                                                                         │
     │               ┌──────────┐                                              │
     └──────────────▶│  Config  │◀─────────────────────────────────────────────┘
                     │ (CLI args)│
                     └──────────┘
```

### Component Boundaries

| Component | Responsibility | Input | Output | Communicates With |
|-----------|---------------|-------|--------|-------------------|
| **Config** | CLI argument parsing, defaults | `sys.argv` | Settings dict/dataclass | All components read from it |
| **Fetcher** | HTTP requests with pagination, rate limiting, error handling | Base URL + page range | List of raw HTML strings (one per page) | Config (for URL, delays) |
| **Extractor** | Parse HTML, extract structured event data from Elementor cards | Raw HTML string | List of `RawEvent` dicts/dataclasses | Fetcher output |
| **Date Parser** | Parse Czech date/time strings into Python datetime objects | Czech date string (e.g., `"31/3/2026, 15 H"`) | `datetime` or `(start_dt, end_dt)` tuple | Extractor output |
| **ICS Builder** | Convert structured events into iCalendar objects | List of parsed `Event` objects | `icalendar.Calendar` object | Date Parser + Extractor output |
| **Writer** | Serialize calendar to .ics file | `icalendar.Calendar` + output path | `.ics` file on disk | ICS Builder output, Config (for path) |

### Data Flow

```
1. Config parses CLI args → settings (output path, verbosity, etc.)
2. Fetcher requests page 1..N of moravska-galerie.cz/program/deti-a-rodiny/page/{n}/
   - Respects delay between requests (1-2s)
   - Detects max pages from data-settings JSON in HTML: "max_num_pages":5
   - Returns list of HTML strings
3. Extractor processes each HTML page:
   - Finds all <article class="elementor-post ..."> elements
   - For each article, extracts:
     a. Title:       h2.elementor-heading-title > a (text + href)
     b. Date string: div[data-id="fe5263e"] .elementor-widget-container (text)
     c. Venue:       div[data-id="d2f8856"] .elementor-widget-container (text)
     d. Description: div[data-id="16d0837"] .elementor-widget-container (text)
     e. Link:        from title's <a href="...">
   - Returns list of RawEvent dicts
4. Date Parser normalizes each date string:
   - Single: "31/3/2026, 15 H" → datetime(2026,3,31,15,0) Europe/Prague
   - With minutes: "8/4/2026, 16.30 H" → datetime(2026,4,8,16,30)
   - Multi-day: "7/7 – 11/7/2026" → (date(2026,7,7), date(2026,7,11))
   - Multi-day+time: "13/7 – 17/7/2026, 9–16 H" → (dt(9:00), dt(16:00)) per day
   - Multi-time: "24/5/2026, 15 H / 16 H / 17 H" → single event, first time slot
   - No time: "23/5/2026" → all-day event
5. ICS Builder creates Calendar with VEVENT components
6. Writer serializes to .ics file
```

## Key Data Structures

### RawEvent (output of Extractor)

```python
@dataclass
class RawEvent:
    title: str              # "Rodinné odpoledne: S úsměvem"
    date_raw: str           # "● 31/3/2026, 15 H" (raw, before parsing)
    venue: str              # "Muzeum Josefa Hoffmanna"
    description: str        # "Zima je pryč, hurá! ..."
    url: str                # "https://moravska-galerie.cz/program/rodinne-odpoledne-s-usmevem/"
```

### Event (output of Date Parser, input to ICS Builder)

```python
@dataclass
class Event:
    title: str
    dtstart: datetime       # Timezone-aware (Europe/Prague)
    dtend: datetime | None  # None → use default duration (2h) or all-day
    all_day: bool           # True for date-only events
    venue: str
    description: str
    url: str
```

## HTML Structure Analysis (Verified Against Live Site)

**Confidence: HIGH** — All selectors verified against actual HTML fetched 2026-03-31.

The site uses **WordPress 6.9 + Elementor 3.33 + Ele Custom Skin 3.1** for templated post loops.

### Event Card Structure

Each event is an `<article>` within `div.ecs-posts`:

```
article.elementor-post.ecs-post-loop
├── div[data-elementor-type="loop"]
│   ├── section (two-column layout)
│   │   ├── column 50% (left)
│   │   │   └── featured image with link to detail page
│   │   └── column 50% (right)
│   │       ├── [optional] reservation link (data-id="87e5159")
│   │       ├── h2 post title with link (data-id="ff31590")
│   │       ├── date/time text (data-id="fe5263e")
│   │       ├── venue text (data-id="d2f8856")
│   │       ├── category tags (data-id="aca18d5")
│   │       ├── spacer
│   │       └── description excerpt (data-id="16d0837")
│   └── section (separator spacer)
```

### Pagination

- URL pattern: `/program/deti-a-rodiny/page/{n}/` (page 1 = no `/page/1/` suffix)
- Max pages embedded in `div.ecs-posts[data-settings]` JSON: `"max_num_pages":5`
- Currently 10 posts per page, ~46 total events across 5 pages
- Pagination uses `ele-custom-skin` AJAX plugin, but standard `/page/N/` URLs work for server-side rendering (verified: page/2/ returns full HTML)

### Date Format Variants (All Observed)

| Pattern | Example | Frequency | Parse Strategy |
|---------|---------|-----------|----------------|
| Single day + hour | `31/3/2026, 15 H` | Most common | `d/m/Y, H \H` |
| Single day + hour.min | `8/4/2026, 16.30 H` | Occasional | `d/m/Y, H.mm \H` |
| Date only (no time) | `23/5/2026` | Rare | All-day event |
| Multi-time slots | `24/5/2026, 15 H / 16 H / 17 H` | Rare | Use first time |
| Multi-day (no time) | `7/7 – 11/7/2026` | Summer camps | All-day multi-day |
| Multi-day + time range | `13/7 – 17/7/2026, 9–16 H` | Summer camps | Multi-day with daily times |

**Note:** Leading bullet `●` (with optional space) must be stripped before parsing. Some entries have inconsistent spacing (e.g., `●16/4/2026` vs `● 31/3/2026`).

## Patterns to Follow

### Pattern 1: Pipeline with Dataclasses

**What:** Each stage transforms data from one dataclass to another. No stage knows about another stage's internals.
**When:** Always — this is the core architectural pattern.
**Why:** Testable in isolation. Can unit-test the date parser without fetching HTML. Can test the extractor against saved HTML fixtures.

```python
def main():
    config = parse_args()
    pages = fetch_all_pages(config)        # → list[str]
    raw_events = extract_events(pages)      # → list[RawEvent]
    events = parse_events(raw_events)       # → list[Event]
    calendar = build_calendar(events)       # → icalendar.Calendar
    write_ics(calendar, config.output_path) # → file
```

### Pattern 2: Selector Constants

**What:** Define all CSS/HTML selectors as module-level constants, not inline strings.
**When:** Always — the site's Elementor data-ids are stable but arbitrary.
**Why:** When the site changes its template, all selectors are in one place.

```python
# selectors.py
ARTICLE_SELECTOR = "article.elementor-post"
TITLE_SELECTOR = '[data-id="ff31590"] a'
DATE_SELECTOR = '[data-id="fe5263e"] .elementor-widget-container'
VENUE_SELECTOR = '[data-id="d2f8856"] .elementor-widget-container'
DESCRIPTION_SELECTOR = '[data-id="16d0837"] .elementor-widget-container'
POSTS_CONTAINER = "div.ecs-posts"
```

### Pattern 3: Regex-Based Date Parser with Fallback Chain

**What:** Try each date pattern in order (most specific first), fall back gracefully.
**When:** For the Date Parser component.
**Why:** Czech date formats are non-standard and the site uses several variants.

```python
DATE_PATTERNS = [
    # Multi-day with time range: "13/7 – 17/7/2026, 9–16 H"
    (r'(\d{1,2}/\d{1,2})\s*–\s*(\d{1,2}/\d{1,2}/\d{4}),\s*(\d{1,2})–(\d{1,2})\s*H', 'multi_day_time'),
    # Multi-day no time: "7/7 – 11/7/2026"
    (r'(\d{1,2}/\d{1,2})\s*–\s*(\d{1,2}/\d{1,2}/\d{4})$', 'multi_day'),
    # Single day with hour.minutes: "8/4/2026, 16.30 H"
    (r'(\d{1,2}/\d{1,2}/\d{4}),\s*(\d{1,2})\.(\d{2})\s*H', 'single_hm'),
    # Single day with hour: "31/3/2026, 15 H"
    (r'(\d{1,2}/\d{1,2}/\d{4}),\s*(\d{1,2})\s*H', 'single_h'),
    # Multi-time: "24/5/2026, 15 H / 16 H / 17 H"
    (r'(\d{1,2}/\d{1,2}/\d{4}),\s*(\d{1,2})\s*H\s*/', 'multi_time'),
    # Date only: "23/5/2026"
    (r'(\d{1,2}/\d{1,2}/\d{4})$', 'date_only'),
]
```

### Pattern 4: Pagination Discovery (Not Hardcoded)

**What:** Read `max_num_pages` from the first page's `data-settings` JSON, don't hardcode `5`.
**When:** In the Fetcher component.
**Why:** Number of pages changes as events are added/removed.

```python
import json

def get_max_pages(html: str) -> int:
    soup = BeautifulSoup(html, 'html.parser')
    container = soup.select_one('div.ecs-posts')
    if container and container.get('data-settings'):
        settings = json.loads(container['data-settings'])
        return settings.get('max_num_pages', 1)
    return 1
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Hardcoded Elementor Data-IDs Without Fallback
**What:** Using `data-id="fe5263e"` as the only way to find elements.
**Why bad:** Elementor regenerates data-ids when templates are re-saved. These IDs are consistent now across all events (same loop template ID 1575), but could change if the site admin edits the template.
**Instead:** Use data-id as primary selector, but add fallback heuristics (e.g., the date field always starts with `●`, the venue widget follows the date widget). Log warnings when primary selectors fail so the user knows the site changed.

### Anti-Pattern 2: Monolithic Script
**What:** All logic in one function or one file with no separation.
**Why bad:** Impossible to test the date parser separately, impossible to reuse the fetcher for another section.
**Instead:** Separate modules or at minimum separate functions per pipeline stage. Even for a small script, `main.py` should only wire stages together.

### Anti-Pattern 3: Silent Failures on Parse Errors
**What:** Swallowing exceptions when a date doesn't parse or a field is missing.
**Why bad:** You get an .ics with silently missing events. The user thinks they have all events but they don't.
**Instead:** Log warnings per event, continue processing remaining events, print summary at end (e.g., "Processed 46 events, 2 skipped due to parse errors").

### Anti-Pattern 4: Storing Naive Datetimes
**What:** `datetime(2026, 3, 31, 15, 0)` without timezone.
**Why bad:** Calendar apps will interpret them in the user's local timezone, which may not be Europe/Prague. Events will be wrong for anyone not in CET/CEST.
**Instead:** Always use `zoneinfo.ZoneInfo("Europe/Prague")` to create aware datetimes. The `icalendar` library properly serializes timezone-aware datetimes with `TZID`.

## Component Dependencies and Build Order

```
Phase 1: Foundation
  ├── Config (CLI args) — no dependencies
  ├── Data models (RawEvent, Event dataclasses) — no dependencies
  └── Date Parser — depends only on data models (testable standalone)

Phase 2: Scraping
  ├── Fetcher (HTTP + pagination) — depends on Config
  └── Extractor (HTML → RawEvent) — depends on data models, needs saved HTML fixtures to test

Phase 3: Calendar Generation
  ├── ICS Builder — depends on data models, Date Parser
  └── Writer — depends on ICS Builder, Config

Phase 4: Integration
  └── main() wiring — depends on all above
```

**Build order rationale:**
1. **Date Parser first** — it's the hardest logic (6+ format variants, Czech conventions) and most likely to have bugs. Build it with unit tests before touching the network.
2. **Fetcher + Extractor second** — needs live site or saved fixtures. Save an HTML fixture from each page during development.
3. **ICS Builder third** — straightforward `icalendar` library usage, but depends on correct Event objects from steps 1+2.
4. **Wire everything in main()** — trivial once components work independently.

## Scalability Considerations

Not a concern for this project. ~50 events across 5 pages, run manually. But for reference:

| Concern | Current (~50 events) | If expanded (10 sections) | Notes |
|---------|---------------------|---------------------------|-------|
| HTTP requests | 5 sequential requests | 50 requests | Add async if >20 pages |
| Memory | <1MB HTML + objects | <10MB | Not a concern |
| File size | ~20KB .ics | ~200KB .ics | Not a concern |
| Parse time | <1 second | <5 seconds | Not a concern |

## File Structure Recommendation

```
cal-scaper/
├── cal_scraper/               # Package (note: corrected spelling internally)
│   ├── __init__.py
│   ├── __main__.py            # Entry point: python -m cal_scraper
│   ├── config.py              # CLI arg parsing, defaults
│   ├── fetcher.py             # HTTP requests, pagination
│   ├── extractor.py           # HTML parsing, data extraction
│   ├── date_parser.py         # Czech date string → datetime
│   ├── ics_builder.py         # Event objects → icalendar.Calendar
│   └── models.py              # RawEvent, Event dataclasses
├── tests/
│   ├── fixtures/              # Saved HTML pages for testing
│   │   ├── page_1.html
│   │   └── page_4.html        # Multi-day events
│   ├── test_date_parser.py    # Most critical tests
│   ├── test_extractor.py
│   └── test_ics_builder.py
├── pyproject.toml             # Project metadata, dependencies
├── README.md
└── .gitignore
```

**Why a package instead of a single script:** Testability. The date parser alone has 6+ format variants that need unit tests. A flat script makes this painful. A package with `python -m cal_scraper` entry point is equally easy to run but much easier to test and maintain.

## Sources

- **Target site HTML:** Direct `curl` analysis of `moravska-galerie.cz/program/deti-a-rodiny/` pages 1-5, fetched 2026-03-31 (HIGH confidence)
- **Elementor structure:** Verified from live HTML — WordPress 6.9.4 + Elementor 3.33.4 + Ele Custom Skin 3.1.9 (HIGH confidence)
- **Pagination:** Verified `/page/N/` URLs return server-rendered HTML with full event data (HIGH confidence)
- **Date formats:** All 6 variants catalogued from actual event data across 5 pages (HIGH confidence)
- **icalendar library:** Standard Python library for .ics generation, well-established (HIGH confidence, based on training data — library not installed in current env)
- **zoneinfo:** Available in Python 3.14 stdlib, preferred over pytz for timezone handling (HIGH confidence, verified in current env)
