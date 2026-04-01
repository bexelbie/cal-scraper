---
phase: 03-ics-generation-cli
plan: 01
subsystem: ics-generation
tags: [icalendar, rfc5545, vtimezone, sha256, tdd]

# Dependency graph
requires:
  - phase: 01-foundation-date-parser
    provides: "Event, ParsedDate, PRAGUE_TZ, DEFAULT_DURATION data models"
provides:
  - "generate_uid(url) — deterministic UID from event URL via SHA-256"
  - "event_to_vevent(event) — Event → icalendar VEVENT conversion"
  - "events_to_ics(events) — list[Event] → RFC 5545 .ics string"
affects: [03-02-cli, future-output-phases]

# Tech tracking
tech-stack:
  added: [icalendar v7]
  patterns: [TDD red-green-refactor, round-trip validation, deterministic UID generation]

key-files:
  created:
    - cal_scraper/ics_generator.py
    - tests/test_ics_generator.py
  modified: []

key-decisions:
  - "SHA-256 first 16 hex chars + @cal-scraper for deterministic UIDs"
  - "Description field combines event.description + Datum: raw_date"
  - "icalendar add_missing_timezones() for automatic VTIMEZONE inclusion"

patterns-established:
  - "Round-trip testing: generate ICS → parse with from_ical → verify structure"
  - "Deterministic UID generation: hash(url)@domain for stable calendar entries"

requirements-completed: [ICAL-01, ICAL-02, ICAL-03, ICAL-04, ICAL-05, ICAL-06]

# Metrics
duration: 3min
completed: 2026-04-01
---

# Phase 03 Plan 01: ICS Generator Summary

**RFC 5545 calendar generation from Event objects using icalendar v7 — TDD with 27 tests including round-trip validation**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-01T10:32:05Z
- **Completed:** 2026-04-01T10:35:14Z
- **Tasks:** 2/2
- **Files created:** 2

## Accomplishments

### Task 1: ICS generator module — TDD core functions

**TDD RED:** Wrote 20 failing tests across 3 test classes (TestGenerateUid, TestEventToVevent, TestEventsToIcs) covering determinism, uniqueness, field mapping, DATE vs DATE-TIME types, VTIMEZONE inclusion, and multi-day event handling.

**TDD GREEN:** Implemented `cal_scraper/ics_generator.py` with three public functions:
- `generate_uid(url)` — SHA-256 hash (16 hex chars) + `@cal-scraper` suffix; handles empty URL gracefully
- `event_to_vevent(event)` — Converts Event to icalendar VEVENT with all required fields (SUMMARY, LOCATION, DESCRIPTION, URL, UID, DTSTAMP, DTSTART, DTEND)
- `events_to_ics(events)` — Produces complete RFC 5545 calendar string with PRODID, VERSION, X-WR-CALNAME, VTIMEZONE

All 20 tests passed on first GREEN run. No refactoring needed.

**Commits:**
- `4f784c6` test(03-01): add failing tests for ICS generator module
- `2c671b9` feat(03-01): implement ICS generator module

### Task 2: Round-trip validation tests

Added `TestIcsRoundTrip` class with 7 tests that generate ICS output, parse it back with `Calendar.from_ical()`, and verify:
- Correct VEVENT count (3 mixed events)
- Timed events round-trip as datetime (DATE-TIME)
- All-day events round-trip as date (DATE)
- Multi-day span preserved correctly
- All VEVENTs have required fields (SUMMARY, LOCATION, UID, DTSTAMP)
- VTIMEZONE present for Europe/Prague
- PRODID present in parsed calendar

**Commit:** `32ad20d` test(03-01): add round-trip validation tests for ICS output

## Key Files

- `cal_scraper/ics_generator.py` — ICS calendar generation (96 lines, 3 public functions)
- `tests/test_ics_generator.py` — 27 tests across 4 test classes (283 lines)

## Decisions Made

- **SHA-256 for UIDs:** First 16 hex chars of SHA-256(url) + `@cal-scraper` — deterministic, unique, collision-resistant
- **Description field format:** `{event.description}\nDatum: {event.raw_date}` — preserves original Czech date text for human reference
- **add_missing_timezones():** Leverages icalendar v7's built-in VTIMEZONE generation rather than manual timezone definitions
- **Empty URL handling:** Hashes `"unknown-event"` placeholder instead of crashing

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Known Stubs

None — all functions are fully implemented with real logic.

## Next Phase Readiness

- ICS generator ready for CLI integration in plan 03-02
- All three public functions tested and working
- Full test suite: 74 tests passing (27 ICS + 28 date-parser + 13 fetcher + 6 extractor)
