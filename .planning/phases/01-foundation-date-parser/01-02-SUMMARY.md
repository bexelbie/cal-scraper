---
phase: 01-foundation-date-parser
plan: 02
subsystem: date-parser
tags: [regex, czech-dates, timezone, zoneinfo, tdd]

# Dependency graph
requires:
  - phase: 01-foundation-date-parser/01
    provides: "ParsedDate dataclass, PRAGUE_TZ, DEFAULT_DURATION constants"
provides:
  - "parse_date() function — Czech date string → ParsedDate | None"
  - "6 regex patterns for all observed date format variants"
  - "Comprehensive test suite (28 tests) for date parser"
affects: [02-scraping, 03-ics-generation]

# Tech tracking
tech-stack:
  added: [re (stdlib), logging (stdlib), zoneinfo (stdlib)]
  patterns: [regex-fallback-chain, warn-and-skip, bullet-stripping, TDD]

key-files:
  created:
    - cal_scraper/date_parser.py
    - tests/test_date_parser.py
  modified: []

key-decisions:
  - "Regex pattern ordering most-specific-first prevents ambiguous partial matches"
  - "Direct function references in dispatch table (not globals() lookup)"
  - "En-dash U+2013 matched explicitly in regex — no normalization to ASCII hyphen"

patterns-established:
  - "Regex fallback chain: ordered (pattern, handler) tuples tried sequentially"
  - "Warn-and-skip: return None + logger.warning for unrecognized input"
  - "Bullet stripping: preprocess with re.sub before pattern matching"
  - "TDD cycle: RED failing tests → GREEN minimal impl → REFACTOR"

requirements-completed: [DATE-01, DATE-02, DATE-03, DATE-04, DATE-05, DATE-06]

# Metrics
duration: 3min
completed: 2026-04-01
---

# Phase 01 Plan 02: Czech Date Parser Summary

**Regex fallback chain parsing all 6 Czech date format variants into timezone-aware ParsedDate objects via TDD**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-01T06:42:10Z
- **Completed:** 2026-04-01T06:45:13Z
- **Tasks:** 2 (RED + GREEN TDD cycle, no refactor needed)
- **Files created:** 2

## Accomplishments
- Implemented `parse_date()` covering all 6+ date format variants from the Moravská galerie site
- 28 passing tests covering DATE-01 through DATE-06, multi-time slots, error handling, and preprocessing
- Correctly handles en-dash (U+2013) in date and time ranges — not ASCII hyphen
- Dot-separated minutes (16.30 H), bullet stripping, European D/M/Y order all working
- Warn-and-skip error handling: unrecognized formats return None with logged warning

## Task Commits

Each TDD phase was committed atomically:

1. **RED: Failing tests** - `e6772a0` (test) — 28 test cases for all format variants
2. **GREEN: Implementation** - `3220b2b` (feat) — date parser with 6 regex patterns, all 28 tests pass

_No refactor commit needed — implementation was clean on first pass._

**Plan metadata:** (pending — docs commit)

## Files Created/Modified
- `cal_scraper/date_parser.py` — Czech date parser with regex fallback chain (178 lines)
- `tests/test_date_parser.py` — Comprehensive test suite with 28 test cases (223 lines)

## Decisions Made
- **Pattern ordering:** Most specific first to prevent ambiguous partial matches (multi_day_time → multi_day → single_hm → multi_time → single_h → date_only)
- **Direct function references:** Dispatch table uses direct function references, not `globals()` string lookup — safer and more explicit
- **En-dash explicit match:** Used `\u2013` in regex rather than normalizing input to ASCII hyphen — preserves original semantics

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- **Venv required:** System Python (Homebrew) on macOS required a virtual environment (`python3 -m venv .venv`) — PEP 668 prevents direct pip install. Created `.venv/` and installed dependencies. Not a deviation — standard Python workflow.

## Known Stubs

None — all functionality is fully implemented and wired.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness
- Date parser is complete and ready for consumption by Phase 02 (scraping)
- `from cal_scraper.date_parser import parse_date` is the public API
- Input: raw date string (with or without `●` bullet prefix)
- Output: `ParsedDate` object or `None` (with warning log)
- Phase 01 is now fully complete (Plan 01: models, Plan 02: date parser)

## Self-Check: PASSED

- ✅ cal_scraper/date_parser.py exists (178 lines)
- ✅ tests/test_date_parser.py exists (223 lines)
- ✅ 01-02-SUMMARY.md exists
- ✅ Commit e6772a0 (RED) found
- ✅ Commit 3220b2b (GREEN) found
- ✅ 28/28 tests pass

---
*Phase: 01-foundation-date-parser*
*Completed: 2026-04-01*
