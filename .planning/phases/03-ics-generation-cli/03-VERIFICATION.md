---
phase: 03-ics-generation-cli
verified: 2026-04-01T10:44:01Z
status: passed
score: 10/10 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "Import generated .ics file into Google Calendar, Apple Calendar, or Outlook"
    expected: "Events appear with correct titles, dates/times, venues, descriptions, and clickable URLs"
    why_human: "Requires real calendar application to verify rendering and import compatibility"
  - test: "Re-import the same .ics file"
    expected: "No duplicate events are created (stable UIDs prevent duplicates)"
    why_human: "Requires real calendar application to verify deduplication behavior"
  - test: "Run cal-scraper against live site and inspect output"
    expected: "Produces .ics with real events from moravska-galerie.cz"
    why_human: "Requires network access to live site; events may change over time"
---

# Phase 3: ICS Generation & CLI Verification Report

**Phase Goal:** Users can run a single command to produce a valid .ics calendar file of all upcoming children/family events from the gallery
**Verified:** 2026-04-01T10:44:01Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | events_to_ics(events) returns a string containing BEGIN:VCALENDAR and BEGIN:VEVENT | ✓ VERIFIED | Smoke test: `events_to_ics([event])` output starts with `BEGIN:VCALENDAR` and contains `BEGIN:VEVENT`; tests `test_empty_list_has_vcalendar`, `test_multiple_events_vevent_count` pass |
| 2 | Timed events produce DTSTART with DATE-TIME value; all-day events produce DTSTART with DATE value | ✓ VERIFIED | Timed event VEVENT shows `DTSTART;TZID=Europe/Prague:20260408T163000`; all-day event shows `DTSTART;VALUE=DATE:20260707`; round-trip tests confirm type correctness |
| 3 | generate_uid(url) returns identical UID for identical URL across multiple calls | ✓ VERIFIED | Behavioral spot-check: `generate_uid('https://example.com/event-1/')` → `78a67c18dd6b76a9@cal-scraper` both times; `TestGenerateUid::test_determinism` passes |
| 4 | Multi-day all-day events produce a single VEVENT with DTSTART on start date and DTEND on exclusive end date | ✓ VERIFIED | Spot-check: multi-day event produces exactly 1 VEVENT with `DTSTART;VALUE=DATE:20260707` and `DTEND;VALUE=DATE:20260712`; `test_multiday_allday_single_vevent` passes |
| 5 | Generated calendar includes VTIMEZONE for Europe/Prague when timed events are present | ✓ VERIFIED | Smoke test output contains `BEGIN:VTIMEZONE` and `Europe/Prague`; `test_timed_events_include_vtimezone` and `test_round_trip_vtimezone_present` pass |
| 6 | Each VEVENT contains SUMMARY, LOCATION, DESCRIPTION, URL, UID, and DTSTAMP | ✓ VERIFIED | Behavioral spot-check of VEVENT section confirms all 6 fields present; `TestEventToVevent` class (11 tests) covers each field individually; round-trip test verifies all fields survive serialization |
| 7 | Running cal-scraper --output /path/to/file.ics produces a .ics file at that path | ✓ VERIFIED | `TestCliArgParsing::test_long_output_flag` and `test_short_output_flag` both pass (assert file exists at specified path) |
| 8 | Running cal-scraper without --output saves to ./moravska-galerie-deti.ics | ✓ VERIFIED | `TestCliArgParsing::test_default_output_path` passes; `DEFAULT_OUTPUT = "moravska-galerie-deti.ics"` in cli.py |
| 9 | CLI prints event count and date range summary to stdout | ✓ VERIFIED | `TestCliSummary::test_summary_with_events` verifies count ("2") and dates ("2026-04-08", "2026-07-07") in stdout; `test_summary_no_events` verifies "No events found" message |
| 10 | cal-scraper --help shows usage with --output flag | ✓ VERIFIED | Direct behavioral check: `cal-scraper --help` exits 0 and shows `--output, -o OUTPUT  Output .ics file path (default: moravska-galerie-deti.ics)` |

**Score:** 10/10 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `cal_scraper/ics_generator.py` | ICS calendar generation from Event objects; exports generate_uid, event_to_vevent, events_to_ics | ✓ VERIFIED | 96 lines, 3 public functions, SHA-256 UID generation, icalendar v7 integration, add_missing_timezones() |
| `tests/test_ics_generator.py` | Test coverage for all ICS generation behaviors; min_lines: 80 | ✓ VERIFIED | 283 lines, 27 tests across 4 classes (TestGenerateUid, TestEventToVevent, TestEventsToIcs, TestIcsRoundTrip) |
| `cal_scraper/cli.py` | CLI entry point with argparse and pipeline orchestration; exports main | ✓ VERIFIED | 108 lines, main() with --output/-o and --verbose/-v flags, full pipeline wiring, _summarize() helper |
| `tests/test_cli.py` | Test coverage for CLI; min_lines: 50 | ✓ VERIFIED | 293 lines, 14 tests across 4 classes (TestCliArgParsing, TestCliPipeline, TestCliSummary, TestCliErrorHandling) |
| `pyproject.toml` | Script entry point; contains "cal-scraper" | ✓ VERIFIED | `[project.scripts]` section with `cal-scraper = "cal_scraper.cli:main"` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `cal_scraper/ics_generator.py` | `cal_scraper/models.py` | `from cal_scraper.models import DEFAULT_DURATION, PRAGUE_TZ, Event` | ✓ WIRED | Import confirmed; all three symbols used in function bodies |
| `cal_scraper/ics_generator.py` | `icalendar` | `from icalendar import Calendar, Event as IcsEvent` | ✓ WIRED | Calendar and IcsEvent used in event_to_vevent and events_to_ics |
| `cal_scraper/cli.py` | `cal_scraper/fetcher.py` | `from cal_scraper.fetcher import ScrapingError, fetch_all_pages` | ✓ WIRED | fetch_all_pages() called in main(); ScrapingError caught in try/except |
| `cal_scraper/cli.py` | `cal_scraper/extractor.py` | `from cal_scraper.extractor import extract_all_events` | ✓ WIRED | extract_all_events(pages) called in main() |
| `cal_scraper/cli.py` | `cal_scraper/ics_generator.py` | `from cal_scraper.ics_generator import events_to_ics` | ✓ WIRED | events_to_ics(events) called in main() |
| `pyproject.toml` | `cal_scraper/cli.py` | `cal-scraper = "cal_scraper.cli:main"` | ✓ WIRED | `cal-scraper --help` exits 0 confirming script entry point works |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `cal_scraper/cli.py` | `pages` | `fetch_all_pages()` → HTTP GET to live site | Yes (fetches real HTML from moravska-galerie.cz) | ✓ FLOWING |
| `cal_scraper/cli.py` | `events` | `extract_all_events(pages)` → HTML parsing | Yes (extracts Event objects from real HTML) | ✓ FLOWING |
| `cal_scraper/cli.py` | `ics_content` | `events_to_ics(events)` → icalendar library | Yes (generates RFC 5545 output from Event objects) | ✓ FLOWING |
| `cal_scraper/ics_generator.py` | VEVENT fields | `event.title`, `event.dtstart`, etc. from Event dataclass | Yes (fields populated by extractor + date parser pipeline) | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `cal-scraper --help` works | `cal-scraper --help` | Shows usage with --output flag, exits 0 | ✓ PASS |
| ICS output is valid VCALENDAR | `events_to_ics([event])` | Output starts with `BEGIN:VCALENDAR`, contains `BEGIN:VEVENT` | ✓ PASS |
| UID determinism | `generate_uid(url)` called twice | Same URL → same UID (`78a67c18dd6b76a9@cal-scraper`); different URL → different UID | ✓ PASS |
| Multi-day event single VEVENT | `events_to_ics([multi_day])` | 1 VEVENT, `DTSTART;VALUE=DATE:20260707`, `DTEND;VALUE=DATE:20260712` | ✓ PASS |
| Timed event has TZID | `events_to_ics([timed])` | `DTSTART;TZID=Europe/Prague:20260408T163000` | ✓ PASS |
| VTIMEZONE present | `events_to_ics([timed])` | Contains `BEGIN:VTIMEZONE` and `Europe/Prague` | ✓ PASS |
| Full test suite | `python -m pytest tests/ -v` | 95 passed in 8.66s | ✓ PASS |
| Module exports | Import check | All expected functions callable from their modules | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| ICAL-01 | 03-01 | Generate valid RFC 5545 .ics file with VCALENDAR and VEVENT components | ✓ SATISFIED | `events_to_ics()` produces `BEGIN:VCALENDAR`/`END:VCALENDAR` with nested `BEGIN:VEVENT`/`END:VEVENT`; round-trip test parses back with `Calendar.from_ical()` |
| ICAL-02 | 03-01 | Include DTSTART, DTEND, SUMMARY, DESCRIPTION, LOCATION, URL, UID, DTSTAMP per event | ✓ SATISFIED | All 8 fields confirmed in VEVENT output; `TestEventToVevent` class tests each field individually |
| ICAL-03 | 03-01 | Generate stable deterministic UIDs from WordPress post IDs or URL slugs | ✓ SATISFIED | SHA-256 hash of URL, first 16 hex chars + `@cal-scraper`; determinism verified programmatically |
| ICAL-04 | 03-01 | Use DATE value type for all-day events, DATE-TIME for timed events | ✓ SATISFIED | All-day: `DTSTART;VALUE=DATE:20260707`; timed: `DTSTART;TZID=Europe/Prague:20260408T163000`; round-trip tests confirm types |
| ICAL-05 | 03-01 | Include VTIMEZONE component for Europe/Prague | ✓ SATISFIED | `cal.add_missing_timezones()` produces `BEGIN:VTIMEZONE` with `TZID:Europe/Prague`; verified in smoke test and tests |
| ICAL-06 | 03-01 | Represent multi-day events as single VEVENT spanning the date range | ✓ SATISFIED | Multi-day event: exactly 1 VEVENT with correct DTSTART/DTEND span; `test_multiday_allday_single_vevent` passes |
| CLI-01 | 03-02 | Accept --output flag for configurable output path (default: ./moravska-galerie-deti.ics) | ✓ SATISFIED | `--output/-o` flag in argparse; `DEFAULT_OUTPUT = "moravska-galerie-deti.ics"`; tests verify both custom and default paths |
| CLI-02 | 03-02 | Print summary of scraped events to stdout (count, date range) | ✓ SATISFIED | `_summarize()` prints `Scraped N events (min_date to max_date)` and `Written to path`; tested with capsys |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `cal_scraper/ics_generator.py` | 39 | "placeholder string" in docstring | ℹ️ Info | Docstring describes empty-URL fallback behavior — not a code placeholder. Refers to the literal string `"unknown-event"` used as hash input. No impact. |

No blocker or warning anti-patterns found. All functions have real implementations with proper logic. No TODO/FIXME/HACK comments. No empty return statements. No console.log-only handlers.

### Human Verification Required

### 1. Calendar App Import Test

**Test:** Generate a .ics file by running `cal-scraper` against the live site, then import into Google Calendar, Apple Calendar, and/or Outlook.
**Expected:** Events appear with correct Czech titles (diacritics preserved), correct date/time in Europe/Prague timezone, venue names, descriptions with "Datum:" line, and clickable URLs to event detail pages.
**Why human:** Requires real calendar application to verify rendering, encoding, and import compatibility.

### 2. Duplicate Prevention Test

**Test:** Import the same .ics file twice into a calendar application.
**Expected:** No duplicate events are created — stable UIDs ensure the second import updates rather than duplicates.
**Why human:** Calendar app deduplication behavior varies by application and cannot be verified programmatically.

### 3. Live Site End-to-End Test

**Test:** Run `cal-scraper` (or `cal-scraper --output test.ics`) with network access to moravska-galerie.cz.
**Expected:** Produces a .ics file with real events, stdout shows event count and date range summary, exit code 0.
**Why human:** Requires network access to live site; event content changes over time; verifies full pipeline integration.

### Gaps Summary

No gaps found. All 10 observable truths verified. All 8 requirements (ICAL-01 through ICAL-06, CLI-01, CLI-02) satisfied. All artifacts exist, are substantive (not stubs), and are fully wired. Full test suite of 95 tests passes. CLI command registered and operational. Anti-pattern scan clean.

---

_Verified: 2026-04-01T10:44:01Z_
_Verifier: the agent (gsd-verifier)_
