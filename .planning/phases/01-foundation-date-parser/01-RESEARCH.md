# Phase 01: Foundation & Date Parser - Research

**Researched:** 2026-04-01
**Domain:** Python package scaffolding + Czech date/time string parsing
**Confidence:** HIGH

## Summary

This phase establishes the project's package structure and solves the project's core algorithmic challenge: parsing 6+ Czech date/time format variants from the Moravská galerie website into timezone-aware Python datetime objects. The project is greenfield — no existing code, no legacy constraints. The technology stack is well-established (Python stdlib `re` + `zoneinfo` + `dataclasses`), and the date formats have been exhaustively catalogued from the live site.

The date parser is the highest-risk component in the entire project. The gallery staff enter dates as free-form text in Elementor widgets, producing at least 6 distinct formats including en-dash (U+2013) range separators, dot-separated minutes ("16.30 H"), multi-day ranges with implicit years, and multiple time slots. No existing Python date parsing library handles these formats — custom regex is the only viable approach, verified by testing all 6 patterns against Python 3.14's `re` module.

**Primary recommendation:** Build a regex-based fallback chain parser that tries patterns from most-specific to least-specific, with explicit logging of any unmatched date strings. Test every format variant from day one — not incrementally. The package structure should be minimal (flat package with `models.py`, `date_parser.py`, and tests) following YAGNI principles.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** When only a start time is given (e.g., "15 H"), default event duration is **2 hours**. DTEND = DTSTART + 2h.
- **D-02:** Multi-day events (e.g., "7/7 – 11/7/2026") are represented as **single spanning all-day events**, not individual daily entries. Use DATE value type with DTEND = day after last day.
- **D-03:** Multi-day events with time ranges (e.g., "27/7 – 31/7/2026, 9–16 H") are also single spanning events. Use DTSTART at first day's start time, DTEND at last day's end time.
- **D-04:** Unknown or unparseable date formats produce a **warning log message** and the event is **skipped** — processing continues for remaining events. Never crash on a single bad date.

### Agent's Discretion
- **Package layout:** Agent decides — keep it simple, YAGNI applies. This is a focused single-site scraper, not a generalized parsing framework. A flat module structure or minimal package is fine.
- **Data model design:** Agent decides — dataclasses or similar, whatever fits the scope.
- **Test framework:** Agent decides — pytest is the obvious choice.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATE-01 | Parse single day + hour format ("31/3/2026, 15 H") | Regex pattern verified: `(\d{1,2})/(\d{1,2})/(\d{4}),\s*(\d{1,2})\s*H` — tested against Python 3.14 re module |
| DATE-02 | Parse single day + hour.minutes format ("8/4/2026, 16.30 H") | Regex pattern verified: `(\d{1,2})/(\d{1,2})/(\d{4}),\s*(\d{1,2})\.(\d{2})\s*H` — dot separator, not colon |
| DATE-03 | Parse single day with no time (all-day event) | Regex pattern verified: `^(\d{1,2})/(\d{1,2})/(\d{4})$` — produce `date` not `datetime` |
| DATE-04 | Parse multi-day date ranges ("7/7 – 11/7/2026") using en-dash separator | Regex verified with explicit `\u2013` match; year inferred from end date to start date |
| DATE-05 | Parse multi-day + time range ("27/7 – 31/7/2026, 9–16 H") | Regex verified; en-dash in both date AND time range; produces start datetime + end datetime |
| DATE-06 | Handle D/M/Y European date order (not M/D/Y) | All regex patterns extract day first, month second — D/M/Y order throughout |
| DATE-07 | Apply Europe/Prague timezone to all parsed dates | `zoneinfo.ZoneInfo("Europe/Prague")` verified working in Python 3.14; CET/CEST transitions handled automatically |

</phase_requirements>

## Project Constraints (from copilot-instructions.md)

- **Language:** Python with requests, BeautifulSoup, lxml, icalendar
- **No JS rendering:** Static HTML scraping only
- **Respectful scraping:** Delays between fetches, proper User-Agent
- **Timezone:** Europe/Prague (CET/CEST) for all events
- **GSD Workflow:** Use GSD commands for all file changes

## Standard Stack

### Core (Phase 1 — used directly)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **Python** | ≥3.10 (local: 3.14.3) | Runtime | `zoneinfo` stdlib since 3.9; `X \| None` union syntax since 3.10 |
| **re** (stdlib) | — | Czech date regex parsing | No library handles "31/3/2026, 15 H" or en-dash ranges; custom regex is the only option |
| **zoneinfo** (stdlib) | — | Europe/Prague timezone | Preferred over deprecated `pytz`; native `icalendar` v7 support |
| **dataclasses** (stdlib) | — | Data models (Event) | Clean, typed, minimal boilerplate for pipeline data structures |
| **logging** (stdlib) | — | Warnings for unparseable dates | Decision D-04 requires warn-and-skip behavior |
| **pytest** | 9.0.2 | Test framework | Standard Python test runner; already installed in environment |

### Dependencies to Install (for `pyproject.toml` but not used in Phase 1 code)

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| **requests** | 2.33.1 | HTTP fetching (Phase 2) | Listed in success criteria: `pip install -e .` must install all deps |
| **beautifulsoup4** | 4.14.3 | HTML parsing (Phase 2) | Listed in success criteria |
| **lxml** | 6.0.2 | BS4 parser backend (Phase 2) | Listed in success criteria |
| **icalendar** | 7.0.3 | iCal generation (Phase 3) | Listed in success criteria |

### Dev Dependencies

| Library | Version | Purpose |
|---------|---------|---------|
| **pytest** | 9.0.2 | Test runner (already installed) |
| **ruff** | 0.15.8 | Linting + formatting |

**Version verification (PyPI, 2026-04-01):**
- requests: 2.33.1 ✓
- beautifulsoup4: 4.14.3 ✓
- lxml: 6.0.2 ✓
- icalendar: 7.0.3 ✓
- pytest: 9.0.2 ✓
- ruff: 0.15.8 ✓

**Installation:**
```bash
pip install -e ".[dev]"
```

## Architecture Patterns

### Recommended Project Structure (Phase 1 scope)

```
cal-scaper/                       # Repo root (note: existing repo name spelling)
├── cal_scraper/                   # Python package
│   ├── __init__.py                # Package marker, version
│   ├── models.py                  # Event dataclass
│   └── date_parser.py             # Czech date string → datetime/date
├── tests/
│   ├── __init__.py
│   └── test_date_parser.py        # Comprehensive format tests
├── pyproject.toml                 # Package metadata, all deps
├── README.md                      # Basic project description
└── .gitignore                     # Python gitignore
```

**Rationale:** YAGNI — only the files needed for Phase 1. Future phases add `fetcher.py`, `extractor.py`, `ics_builder.py`, `__main__.py`, etc. No `config.py` or `cli.py` yet — those belong in Phase 3.

### Pattern 1: Dataclass Pipeline Boundaries

**What:** Each pipeline stage transforms data using typed dataclasses. Stages communicate only through these data structures.
**When to use:** Always — this is the core architectural pattern.
**Why:** Testable in isolation. The date parser can be tested without any HTML or network code.

```python
from dataclasses import dataclass
from datetime import datetime, date
from zoneinfo import ZoneInfo

PRAGUE_TZ = ZoneInfo("Europe/Prague")

@dataclass
class ParsedDate:
    """Result of parsing a Czech date string."""
    dtstart: datetime | date
    dtend: datetime | date | None  # None → use default duration
    all_day: bool
    raw_text: str                   # Original text for debugging/description
```

**Note on data model scope for Phase 1:** The `ParsedDate` dataclass above is the parser's output. The full `Event` dataclass (with title, venue, description, url) is also defined in Phase 1 to establish the contract for Phase 2, but only `ParsedDate` is actively used by the parser.

```python
@dataclass
class Event:
    """Fully parsed event ready for ICS generation."""
    title: str
    dtstart: datetime | date
    dtend: datetime | date | None
    all_day: bool
    venue: str
    description: str
    url: str
    raw_date: str                   # Original date text
```

### Pattern 2: Regex Fallback Chain (Most Specific First)

**What:** Ordered list of compiled regex patterns, tried from most specific to least specific. First match wins.
**When to use:** For the date parser — the core of Phase 1.
**Why:** Czech date formats overlap (e.g., "31/3/2026, 15 H" could partially match the date-only pattern). Most-specific-first avoids ambiguous matches.

```python
import re
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

PRAGUE_TZ = ZoneInfo("Europe/Prague")
DEFAULT_DURATION = timedelta(hours=2)  # Decision D-01

# Ordered: most specific first
_PATTERNS = [
    # Multi-day + time range: "27/7 – 31/7/2026, 9–16 H"
    (re.compile(
        r'(\d{1,2})/(\d{1,2})\s*\u2013\s*(\d{1,2})/(\d{1,2})/(\d{4}),\s*(\d{1,2})\u2013(\d{1,2})\s*H'
    ), '_parse_multi_day_time'),

    # Multi-day no time: "7/7 – 11/7/2026"
    (re.compile(
        r'(\d{1,2})/(\d{1,2})\s*\u2013\s*(\d{1,2})/(\d{1,2})/(\d{4})$'
    ), '_parse_multi_day'),

    # Single day + hour.minutes: "8/4/2026, 16.30 H"
    (re.compile(
        r'(\d{1,2})/(\d{1,2})/(\d{4}),\s*(\d{1,2})\.(\d{2})\s*H'
    ), '_parse_single_hm'),

    # Multiple time slots: "24/5/2026, 15 H / 16 H / 17 H"
    (re.compile(
        r'(\d{1,2})/(\d{1,2})/(\d{4}),\s*(\d{1,2})\s*H\s*/'
    ), '_parse_multi_time'),

    # Single day + hour: "31/3/2026, 15 H"
    (re.compile(
        r'(\d{1,2})/(\d{1,2})/(\d{4}),\s*(\d{1,2})\s*H$'
    ), '_parse_single_h'),

    # Date only: "23/5/2026"
    (re.compile(
        r'^(\d{1,2})/(\d{1,2})/(\d{4})$'
    ), '_parse_date_only'),
]
```

**Critical ordering notes:**
1. `multi_time` MUST come before `single_h` because "24/5/2026, 15 H / 16 H" would match `single_h` if tried first
2. `single_hm` MUST come before `single_h` because "16.30 H" contains "16" which matches the whole-hour pattern
3. `multi_day_time` MUST come before `multi_day` for the same reason
4. Use `$` anchors on `single_h` and `date_only` to prevent partial matches

### Pattern 3: Bullet Stripping Preprocessing

**What:** Strip the `●` bullet prefix (with variable spacing) before attempting regex parsing.
**When to use:** As the first step in the parse pipeline.
**Why:** The bullet is present on ALL date strings from the site but varies: `● 31/3/2026` vs `●16/4/2026`.

```python
def _clean_date_text(raw: str) -> str:
    """Strip bullet prefix and normalize whitespace."""
    text = raw.strip()
    text = re.sub(r'^●\s*', '', text)
    return text.strip()
```

### Pattern 4: Warn-and-Skip Error Handling (Decision D-04)

**What:** Return `None` for unparseable dates with a warning log. Never raise exceptions from the parser.
**When to use:** The parse function's top-level contract.
**Why:** Decision D-04: "Unknown or unparseable date formats produce a warning log message and the event is skipped."

```python
import logging

logger = logging.getLogger(__name__)

def parse_date(raw_text: str) -> ParsedDate | None:
    """Parse a Czech date string. Returns None if unrecognized (with warning)."""
    cleaned = _clean_date_text(raw_text)
    for pattern, handler_name in _PATTERNS:
        match = pattern.search(cleaned)
        if match:
            handler = globals()[handler_name]
            return handler(match, cleaned)
    logger.warning("Unrecognized date format: %r", raw_text)
    return None
```

### Anti-Patterns to Avoid

- **Naive datetimes:** Never create `datetime(2026, 3, 31, 15, 0)` without timezone. Always use `datetime(..., tzinfo=PRAGUE_TZ)`. Calendar apps interpret naive times in the user's local timezone, which breaks for non-CET users.
- **Hyphen instead of en-dash in regex:** `–` (U+2013) is NOT `-` (U+002D). Using `-` in range patterns silently drops ALL multi-day events (~8 summer camps).
- **Colon for minutes:** The site uses dot: `16.30 H` not `16:30`. Don't match `:` — it doesn't appear in these date strings.
- **Incremental format support:** Don't build for 2 formats and "add more later." All 6 formats must work from day one — summer camp events (multi-day) are only on pages 4-5 and are easy to miss in superficial testing.
- **Overly complex data model:** Don't build `RawEvent` in Phase 1. That belongs in Phase 2 (extraction). Phase 1 only needs `ParsedDate` and the future `Event` contract.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Timezone handling | Manual UTC offset calculation | `zoneinfo.ZoneInfo("Europe/Prague")` | CET↔CEST transitions are complex (last Sunday of March/October). Stdlib handles this with IANA timezone database. |
| Date arithmetic | Manual day-of-month calculations | `datetime` + `timedelta` | Leap years, month boundaries, etc. |
| Package metadata | Manual `setup.py` | `pyproject.toml` with `[build-system]` | PEP 621 standard; `pip install -e .` just works |
| Test discovery | Manual test runner | `pytest` | Already installed, zero config needed for simple test files |

**Key insight:** The only custom code needed is the regex patterns and their handler functions. Everything else — timezone, date math, packaging, testing — has battle-tested stdlib or ecosystem solutions.

## Common Pitfalls

### Pitfall 1: En-dash (U+2013) vs Hyphen (U+002D)
**What goes wrong:** Regex patterns use `-` (ASCII hyphen) for date and time ranges. The site uses `–` (Unicode en-dash U+2013) for BOTH date separators ("7/7 – 11/7") AND time ranges ("9–16 H").
**Why it happens:** They look identical in many fonts. Copy-paste from requirements may preserve or not preserve the character.
**How to avoid:** Use `\u2013` explicitly in regex patterns. Add a test case that verifies the actual Unicode character is matched. Consider also accepting hyphen as a fallback (normalize en-dash → hyphen before parsing).
**Warning signs:** Parser returns 0 multi-day events when the site has ~8.

### Pitfall 2: Implicit Year on Multi-Day Start Date
**What goes wrong:** "7/7 – 11/7/2026" — the start date `7/7` has no year. Parser crashes or uses year 0.
**Why it happens:** The regex captures `D/M` for start but `D/M/YYYY` for end. Forgetting to transfer the year from end date to start date.
**How to avoid:** In the multi-day handler, always apply the year from the second (end) date to the first (start) date. Edge case: cross-year ranges (December→January) where start year = end year - 1 — unlikely for gallery events but handle gracefully.
**Warning signs:** `ValueError` on datetime construction with year=0 or events in wrong year.

### Pitfall 3: Multi-day All-day DTEND Off-by-One
**What goes wrong:** "7/7 – 11/7/2026" should span July 7-11 inclusive. In iCal, all-day events use exclusive DTEND, so DTEND must be July **12** (day after last day), not July 11.
**Why it happens:** RFC 5545 all-day events: DTEND is exclusive (the event runs up-to-but-not-including DTEND date).
**How to avoid:** For all-day multi-day events (Decision D-02): `dtend = last_day + timedelta(days=1)`. Document this in the code.
**Warning signs:** Multi-day events appear one day short in calendar apps.

### Pitfall 4: Pattern Ordering Causes Wrong Match
**What goes wrong:** "24/5/2026, 15 H / 16 H / 17 H" matches the `single_h` pattern (grabs "15 H" and ignores the rest) instead of `multi_time`.
**Why it happens:** Less-specific patterns tried first.
**How to avoid:** Strict ordering: most specific first. Use `$` end-anchor on `single_h` so it only matches when there's nothing after "H". Multi-time pattern matches the presence of `/` after "H".
**Warning signs:** Multi-time events parsed as single-time (losing time slot info).

### Pitfall 5: CET/CEST Ambiguity During DST Transition
**What goes wrong:** On the last Sunday of March, 2:00 AM becomes 3:00 AM. An event at "2 H" on that day is ambiguous.
**Why it happens:** Gallery events at 2 AM are essentially impossible, but the parser should not crash if handed such a time.
**How to avoid:** Use `datetime(fold=0)` default behavior. In practice, no gallery event occurs at 2 AM, so this is theoretical. The `zoneinfo` module handles the transition correctly — `fold=0` gives the pre-transition (CET) interpretation.
**Warning signs:** No warning signs in practice — this is defensive.

## Code Examples

### Complete Date Parser Skeleton

Verified patterns tested against Python 3.14.3 `re` module:

```python
"""Czech date/time parser for Moravská galerie event listings."""

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

PRAGUE_TZ = ZoneInfo("Europe/Prague")
DEFAULT_DURATION = timedelta(hours=2)  # D-01: default when only start time given

@dataclass
class ParsedDate:
    """Result of parsing a Czech date string."""
    dtstart: datetime | date
    dtend: datetime | date | None
    all_day: bool
    raw_text: str

def _clean(raw: str) -> str:
    """Strip ● bullet prefix and normalize whitespace."""
    return re.sub(r'^●\s*', '', raw.strip()).strip()

def _make_dt(day: int, month: int, year: int, hour: int, minute: int = 0) -> datetime:
    """Create timezone-aware datetime in Europe/Prague."""
    return datetime(year, month, day, hour, minute, tzinfo=PRAGUE_TZ)

def _make_date(day: int, month: int, year: int) -> date:
    """Create a date object."""
    return date(year, month, day)

def parse_date(raw_text: str) -> ParsedDate | None:
    """Parse Czech date string → ParsedDate or None (with warning)."""
    cleaned = _clean(raw_text)

    # Try each pattern, most specific first
    # ... (ordered pattern matching as shown in Architecture Patterns)

    logger.warning("Unrecognized date format: %r", raw_text)
    return None
```

### Multi-Day Handler (Decisions D-02, D-03)

```python
def _parse_multi_day(m: re.Match, raw: str) -> ParsedDate:
    """'7/7 – 11/7/2026' → all-day spanning event."""
    sd, sm = int(m.group(1)), int(m.group(2))
    ed, em, year = int(m.group(3)), int(m.group(4)), int(m.group(5))
    start = _make_date(sd, sm, year)       # Year from end date applied to start
    end = _make_date(ed, em, year) + timedelta(days=1)  # Exclusive DTEND (D-02)
    return ParsedDate(dtstart=start, dtend=end, all_day=True, raw_text=raw)

def _parse_multi_day_time(m: re.Match, raw: str) -> ParsedDate:
    """'27/7 – 31/7/2026, 9–16 H' → spanning timed event (D-03)."""
    sd, sm = int(m.group(1)), int(m.group(2))
    ed, em, year = int(m.group(3)), int(m.group(4)), int(m.group(5))
    start_hour, end_hour = int(m.group(6)), int(m.group(7))
    start = _make_dt(sd, sm, year, start_hour)
    end = _make_dt(ed, em, year, end_hour)
    return ParsedDate(dtstart=start, dtend=end, all_day=False, raw_text=raw)
```

### Single-Day Handlers (Decision D-01)

```python
def _parse_single_h(m: re.Match, raw: str) -> ParsedDate:
    """'31/3/2026, 15 H' → timed event with 2h default duration."""
    d, mo, y, h = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
    start = _make_dt(d, mo, y, h)
    end = start + DEFAULT_DURATION  # D-01: 2 hours
    return ParsedDate(dtstart=start, dtend=end, all_day=False, raw_text=raw)

def _parse_single_hm(m: re.Match, raw: str) -> ParsedDate:
    """'8/4/2026, 16.30 H' → timed event with minutes."""
    d, mo, y, h, mi = (int(m.group(1)), int(m.group(2)), int(m.group(3)),
                        int(m.group(4)), int(m.group(5)))
    start = _make_dt(d, mo, y, h, mi)
    end = start + DEFAULT_DURATION
    return ParsedDate(dtstart=start, dtend=end, all_day=False, raw_text=raw)

def _parse_date_only(m: re.Match, raw: str) -> ParsedDate:
    """'23/5/2026' → all-day event."""
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    start = _make_date(d, mo, y)
    end = start + timedelta(days=1)  # All-day: exclusive end
    return ParsedDate(dtstart=start, dtend=end, all_day=True, raw_text=raw)
```

### pyproject.toml Template

```toml
[build-system]
requires = ["setuptools>=75.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "cal-scraper"
version = "0.1.0"
description = "Scrapes Moravská galerie children/family events → iCal feed"
requires-python = ">=3.10"
dependencies = [
    "requests>=2.31",
    "beautifulsoup4>=4.12",
    "lxml>=5.0",
    "icalendar>=7.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "ruff>=0.4",
]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
target-version = "py310"
line-length = 100
```

### Test Examples (pytest)

```python
"""Tests for Czech date parser — covers all 6 observed format variants."""

import pytest
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

from cal_scraper.date_parser import parse_date, PRAGUE_TZ

class TestSingleDayHour:
    def test_basic(self):
        result = parse_date("● 31/3/2026, 15 H")
        assert result is not None
        assert result.dtstart == datetime(2026, 3, 31, 15, 0, tzinfo=PRAGUE_TZ)
        assert result.dtend == datetime(2026, 3, 31, 17, 0, tzinfo=PRAGUE_TZ)  # +2h
        assert result.all_day is False

    def test_no_space_after_bullet(self):
        result = parse_date("●16/4/2026, 16 H")
        assert result is not None
        assert result.dtstart == datetime(2026, 4, 16, 16, 0, tzinfo=PRAGUE_TZ)

class TestSingleDayHourMinutes:
    def test_dot_minutes(self):
        result = parse_date("● 8/4/2026, 16.30 H")
        assert result is not None
        assert result.dtstart == datetime(2026, 4, 8, 16, 30, tzinfo=PRAGUE_TZ)
        assert result.all_day is False

class TestDateOnly:
    def test_all_day(self):
        result = parse_date("● 23/5/2026")
        assert result is not None
        assert result.dtstart == date(2026, 5, 23)
        assert result.dtend == date(2026, 5, 24)  # Exclusive end
        assert result.all_day is True

class TestMultiDay:
    def test_no_time(self):
        """'7/7 – 11/7/2026' → July 7-11 inclusive (D-02)."""
        result = parse_date("● 7/7 – 11/7/2026")
        assert result is not None
        assert result.dtstart == date(2026, 7, 7)
        assert result.dtend == date(2026, 7, 12)  # Exclusive: day after last
        assert result.all_day is True

    def test_en_dash_not_hyphen(self):
        """Verify the actual en-dash character (U+2013) is matched."""
        result = parse_date("● 7/7 – 11/7/2026")  # Contains U+2013
        assert result is not None
        # Hyphen version should NOT match multi-day pattern
        result_hyphen = parse_date("● 7/7 - 11/7/2026")  # ASCII hyphen
        # This should either not match or match differently
        # (depends on whether we normalize)

class TestMultiDayTime:
    def test_time_range(self):
        """'27/7 – 31/7/2026, 9–16 H' → spanning timed event (D-03)."""
        result = parse_date("● 27/7 – 31/7/2026, 9–16 H")
        assert result is not None
        assert result.dtstart == datetime(2026, 7, 27, 9, 0, tzinfo=PRAGUE_TZ)
        assert result.dtend == datetime(2026, 7, 31, 16, 0, tzinfo=PRAGUE_TZ)
        assert result.all_day is False

class TestMultiTime:
    def test_uses_first_slot(self):
        """'24/5/2026, 15 H / 16 H / 17 H' → single event at first time."""
        result = parse_date("● 24/5/2026, 15 H / 16 H / 17 H")
        assert result is not None
        assert result.dtstart == datetime(2026, 5, 24, 15, 0, tzinfo=PRAGUE_TZ)

class TestErrorHandling:
    def test_unknown_format_returns_none(self):
        result = parse_date("not a date")
        assert result is None

    def test_empty_string_returns_none(self):
        result = parse_date("")
        assert result is None
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pytz` for timezones | `zoneinfo` (stdlib) | Python 3.9 (2020) | No `.localize()` needed; direct `tzinfo=` parameter |
| `setup.py` packaging | `pyproject.toml` (PEP 621) | Python 3.11+ ecosystem standard | Declarative config; `pip install -e .` works natively |
| `unittest` test framework | `pytest` ecosystem standard | ~2018+ | Less boilerplate; better assertions; fixtures |
| `pytz` as explicit dep | `zoneinfo` + automatic `tzdata` | icalendar 7.x | `icalendar` v7 uses `zoneinfo` natively |

## Open Questions

1. **Cross-year multi-day ranges (December → January)**
   - What we know: All observed multi-day ranges are within the same month (July summer camps).
   - What's unclear: If a Dec 28 – Jan 2 range ever appears, the year inference logic needs adjustment (start year = end year - 1).
   - Recommendation: Handle defensively — if start_date > end_date after applying end year, subtract 1 from start year. Log a warning. Low priority since gallery events are seasonal.

2. **Hyphen normalization fallback**
   - What we know: The site uses en-dash (U+2013) exclusively today.
   - What's unclear: If staff ever use a regular hyphen in a date range.
   - Recommendation: Match en-dash (`\u2013`) as primary. Optionally also accept hyphen-minus (`-`) as a fallback to be robust. Or normalize both to en-dash before pattern matching.

3. **Future date format variants**
   - What we know: 6 formats cover all ~46 current events across 5 pages.
   - What's unclear: What formats future events may use (staff enter dates as free text).
   - Recommendation: The warn-and-skip behavior (D-04) handles this. The parser logs unrecognized formats so they're caught on first run. No action needed now.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3 | Runtime | ✓ | 3.14.3 | — |
| pip | Package install | ✓ | 26.0 | — |
| pytest | Testing | ✓ | 9.0.2 (installed) | — |
| ruff | Linting (optional) | ✗ | not installed | Install via `pip install ruff`; non-blocking |
| zoneinfo | Timezone | ✓ | stdlib | — |
| git | Version control | ✓ | available | — |

**Missing dependencies with no fallback:** None — all critical dependencies available.

**Missing dependencies with fallback:**
- `ruff`: Not installed but easily installable via dev dependencies. Non-blocking for Phase 1.

## Sources

### Primary (HIGH confidence)
- **Python 3.14.3 stdlib** — `re`, `zoneinfo`, `dataclasses`, `datetime` — tested directly in environment
- **Live regex validation** — All 6 format patterns tested against actual date strings from the site using Python 3.14 `re` module (2026-04-01)
- **PyPI package metadata** — requests 2.33.1, beautifulsoup4 4.14.3, lxml 6.0.2, icalendar 7.0.3, pytest 9.0.2, ruff 0.15.8 (verified 2026-04-01)
- **Project research files** — `.planning/research/FEATURES.md`, `ARCHITECTURE.md`, `PITFALLS.md`, `SUMMARY.md` — based on live site inspection (2026-03-31)

### Secondary (MEDIUM confidence)
- **RFC 5545** — iCal all-day event DTEND exclusivity rule (referenced for multi-day handling)
- **icalendar v7 API** — `add_missing_timezones()` referenced in STACK.md (not yet validated firsthand; Phase 3 concern)

### Tertiary (LOW confidence)
- None — all findings verified against live environment or primary sources.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified on PyPI; Python stdlib modules verified in local environment
- Architecture: HIGH — patterns verified from project research files based on live site analysis; regex patterns tested
- Pitfalls: HIGH — pitfalls sourced from comprehensive live site analysis documented in PITFALLS.md

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (30 days — stable domain, stdlib-only phase)
