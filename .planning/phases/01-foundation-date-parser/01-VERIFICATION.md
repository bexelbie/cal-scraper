---
phase: 01-foundation-date-parser
verified: 2026-04-01T07:00:00Z
status: passed
score: 5/5 must-haves verified
---

# Phase 1: Foundation & Date Parser Verification Report

**Phase Goal:** The project has a working package structure with data models, and can correctly parse all Czech date/time formats from the gallery site into timezone-aware datetime objects
**Verified:** 2026-04-01T07:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

Truths sourced from ROADMAP.md Success Criteria + PLAN must_haves.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Running `pip install -e .` installs the package and all dependencies (requests, beautifulsoup4, lxml, icalendar) | ✓ VERIFIED | `pip install -e ".[dev]"` exits 0; "Successfully installed cal-scraper-0.1.0" |
| 2 | Parser correctly converts single-day formats like "31/3/2026, 15 H" and "8/4/2026, 16.30 H" to timezone-aware datetimes in Europe/Prague | ✓ VERIFIED | Spot-check: `parse_date("● 31/3/2026, 15 H")` → `datetime(2026,3,31,15,0,tzinfo=Prague)`; `parse_date("● 8/4/2026, 16.30 H")` → `datetime(2026,4,8,16,30,tzinfo=Prague)` |
| 3 | Parser correctly converts multi-day ranges like "7/7 – 11/7/2026" and "27/7 – 31/7/2026, 9–16 H" to start/end datetime pairs | ✓ VERIFIED | Spot-check: `parse_date("● 7/7 – 11/7/2026")` → `date(2026,7,7)..date(2026,7,12)`; `parse_date("● 27/7 – 31/7/2026, 9–16 H")` → `datetime(2026,7,27,9,0)..datetime(2026,7,31,16,0)` |
| 4 | Parser correctly identifies all-day events (no time component) vs timed events | ✓ VERIFIED | DATE-03: `all_day=True`, `type(dtstart) is date`; DATE-01/02/05: `all_day=False`, `type(dtstart) is datetime` |
| 5 | All date formats use D/M/Y European order and produce Europe/Prague timezone-aware results | ✓ VERIFIED | 31/3 → day=31, month=3 (not month=31). `PRAGUE_TZ == ZoneInfo("Europe/Prague")`. All datetimes carry tzinfo. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pyproject.toml` | Package metadata with all core and dev dependencies | ✓ VERIFIED | 27 lines. Contains `name = "cal-scraper"`, all 4 core deps (requests, beautifulsoup4, lxml, icalendar), dev deps (pytest, ruff), `requires-python = ">=3.10"` |
| `cal_scraper/__init__.py` | Package marker with version | ✓ VERIFIED | Contains `__version__ = "0.1.0"`. Importable: `from cal_scraper import __version__` works. |
| `cal_scraper/models.py` | ParsedDate and Event dataclasses, PRAGUE_TZ constant | ✓ VERIFIED | 42 lines. Exports ParsedDate, Event, PRAGUE_TZ, DEFAULT_DURATION. Union types `datetime \| date`. |
| `cal_scraper/date_parser.py` | Czech date string parser with regex fallback chain | ✓ VERIFIED | 178 lines (≥80 min). 6 `re.compile` patterns, 6 handler functions, `parse_date()` public API. Uses `\u2013` en-dash. No pytz. |
| `tests/test_date_parser.py` | Comprehensive test suite for all 6+ date format variants | ✓ VERIFIED | 223 lines (≥80 min). 28 test cases across 8 test classes. All pass. |
| `tests/__init__.py` | Test package marker | ✓ VERIFIED | Exists (empty file). |
| `.gitignore` | Python gitignore | ✓ VERIFIED | Contains `__pycache__/`, `.venv/`, `*.ics`, etc. |
| `README.md` | Basic project description | ✓ VERIFIED | Contains project description and install instructions. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `cal_scraper/date_parser.py` | `cal_scraper/models.py` | `from cal_scraper.models import DEFAULT_DURATION, PRAGUE_TZ, ParsedDate` | ✓ WIRED | Line 19: imports all three symbols, uses them throughout |
| `tests/test_date_parser.py` | `cal_scraper/date_parser.py` | `from cal_scraper.date_parser import parse_date` | ✓ WIRED | Line 7: imports parse_date, used in all 28 tests |
| `tests/test_date_parser.py` | `cal_scraper/models.py` | `from cal_scraper.models import PRAGUE_TZ` | ✓ WIRED | Line 8: imports PRAGUE_TZ, used in assertions |
| `cal_scraper/date_parser.py` | regex patterns | Ordered fallback chain with `re.compile` | ✓ WIRED | 6 compiled patterns in `_PATTERNS` list, most-specific-first order |
| `cal_scraper/models.py` | `zoneinfo` | `ZoneInfo("Europe/Prague")` assigned to `PRAGUE_TZ` | ✓ WIRED | Line 7: `PRAGUE_TZ = ZoneInfo("Europe/Prague")` |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Package installs | `pip install -e ".[dev]"` | "Successfully installed cal-scraper-0.1.0" | ✓ PASS |
| Models importable | `from cal_scraper.models import ParsedDate, Event, PRAGUE_TZ, DEFAULT_DURATION` | All model checks passed | ✓ PASS |
| DATE-01: single day + hour | `parse_date("● 31/3/2026, 15 H")` | dtstart=2026-03-31T15:00 Prague, dtend=+2h | ✓ PASS |
| DATE-02: hour.minutes | `parse_date("● 8/4/2026, 16.30 H")` | dtstart=2026-04-08T16:30 Prague | ✓ PASS |
| DATE-03: all-day | `parse_date("● 23/5/2026")` | all_day=True, dtstart=date(2026,5,23), dtend=date(2026,5,24) | ✓ PASS |
| DATE-04: multi-day range | `parse_date("● 7/7 – 11/7/2026")` | dtstart=date(2026,7,7), dtend=date(2026,7,12) | ✓ PASS |
| DATE-05: multi-day + time | `parse_date("● 27/7 – 31/7/2026, 9–16 H")` | dtstart=09:00, dtend=16:00 | ✓ PASS |
| DATE-06: D/M/Y order | 31/3 → day=31, month=3 | Correct European order | ✓ PASS |
| DATE-07: Europe/Prague TZ | `PRAGUE_TZ == ZoneInfo("Europe/Prague")` | True | ✓ PASS |
| D-04: error handling | `parse_date("not a date")` / `parse_date("")` | Returns None, logs warning | ✓ PASS |
| Multi-time slots | `parse_date("● 24/5/2026, 15 H / 16 H / 17 H")` | Uses first slot, hour=15 | ✓ PASS |
| Test suite | `pytest tests/test_date_parser.py -v` | 28 passed in 0.06s | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| DATE-01 | 01-02 | Parse single day + hour format ("31/3/2026, 15 H") | ✓ SATISFIED | TestSingleDayHour (4 tests pass); spot-check returns correct datetime |
| DATE-02 | 01-02 | Parse single day + hour.minutes format ("8/4/2026, 16.30 H") | ✓ SATISFIED | TestSingleDayHourMinutes (3 tests pass); dot-separated minutes work |
| DATE-03 | 01-02 | Parse single day with no time (all-day event) | ✓ SATISFIED | TestDateOnly (2 tests pass); returns `date` object with `all_day=True` |
| DATE-04 | 01-02 | Parse multi-day date ranges with en-dash separator | ✓ SATISFIED | TestMultiDayRange (3 tests pass); en-dash required, ASCII hyphen rejected |
| DATE-05 | 01-02 | Parse multi-day + time range ("27/7 – 31/7/2026, 9–16 H") | ✓ SATISFIED | TestMultiDayTimeRange (4 tests pass); correct start/end hours |
| DATE-06 | 01-02 | Handle D/M/Y European date order | ✓ SATISFIED | TestEuropeanDateOrder (2 tests pass); 31/3 → March 31 confirmed |
| DATE-07 | 01-01 | Apply Europe/Prague timezone to all parsed dates | ✓ SATISFIED | `PRAGUE_TZ = ZoneInfo("Europe/Prague")` in models.py; all datetimes use it |

No orphaned requirements — all 7 DATE-* requirements from REQUIREMENTS.md Phase 1 are accounted for in plans 01-01 and 01-02.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `README.md` | 16 | "Coming soon — see Phase 3." | ℹ️ Info | Expected — usage docs deferred to Phase 3 when CLI exists. Not a stub. |

No TODOs, FIXMEs, placeholders, empty returns, or stub implementations found in any production or test code.

### Human Verification Required

None required. All phase outputs are programmatically verifiable (package installation, imports, function return values, test execution). No UI, visual, or external-service components in this phase.

### Gaps Summary

No gaps found. All 5 observable truths verified. All 8 artifacts exist, are substantive, and are wired. All 5 key links confirmed. All 7 requirements (DATE-01 through DATE-07) satisfied with test evidence. 28/28 tests pass. No blocker or warning anti-patterns. Behavioral spot-checks pass for all date format variants.

---

_Verified: 2026-04-01T07:00:00Z_
_Verifier: the agent (gsd-verifier)_
