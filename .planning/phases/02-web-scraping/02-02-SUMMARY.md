---
phase: 02-web-scraping
plan: 02
subsystem: scraping
tags: [beautifulsoup, lxml, elementor, html-extraction, css-selectors]

requires:
  - phase: 01-foundation
    provides: "ParsedDate model, parse_date() Czech date parser, Event dataclass"
provides:
  - "extract_events_from_html() — HTML → list[Event] extraction"
  - "extract_all_events() — multi-page extraction combining results"
  - "Elementor CSS selector constants for event card fields"
  - "HTML test fixture with realistic Elementor event cards"
affects: [03-ics-generation, 02-web-scraping]

tech-stack:
  added: [beautifulsoup4, lxml]
  patterns: [css-selector-constants, warn-and-skip-on-missing-fields, clean-text-normalization]

key-files:
  created:
    - cal_scraper/extractor.py
    - tests/test_extractor.py
    - tests/fixtures/event_page.html
  modified: []

key-decisions:
  - "CSS selectors use Elementor data-id attributes (ff31590, fe5263e, d2f8856, 16d0837) not class names"
  - "Missing title or date → skip event with warning; missing venue or description → empty string fallback"
  - "Non-breaking space (U+00A0) replaced with regular space in _clean_text() for entity normalization"
  - "caplog-based tests call extraction directly (not via fixture) to capture warning logs in test body"

patterns-established:
  - "Selector constants: module-level ARTICLE_SELECTOR, TITLE_SELECTOR etc. for single-point-of-change"
  - "Warn-and-skip: critical fields (title, date) cause skip; non-critical (venue, desc) use empty fallback"
  - "HTML fixture: realistic multi-article HTML in tests/fixtures/ for integration-style tests"

requirements-completed: [SCRP-02, SCRP-03, SCRP-04, SCRP-05]

duration: 3min
completed: 2026-04-01
---

# Phase 02 Plan 02: HTML Event Extractor Summary

**Elementor HTML event card extraction using data-id CSS selectors with BeautifulSoup/lxml, preserving Czech diacritics and integrating Phase 1 date parser**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-01T10:14:17Z
- **Completed:** 2026-04-01T10:17:01Z
- **Tasks:** 2/2 (TDD RED→GREEN cycle)
- **Files created:** 3
- **Tests added:** 13 (54 total project tests pass)

## Accomplishments

### Task 1: RED — HTML fixture + failing tests
- Created `tests/fixtures/event_page.html` with 4 Elementor article elements (3 valid, 1 missing title)
- Created `tests/test_extractor.py` with 13 test functions covering field extraction, diacritics, error handling
- All tests failed with ImportError (module doesn't exist) — proper RED state
- **Commit:** `12b6291`

### Task 2: GREEN — Implement extractor.py
- Created `cal_scraper/extractor.py` with `extract_events_from_html()` and `extract_all_events()` public API
- Module-level selector constants from verified Elementor data-id attributes
- `_clean_text()` normalizes non-breaking spaces (U+00A0) and strips whitespace
- `_extract_single_event()` extracts all fields, integrates with `parse_date()`, skips invalid events
- All 13 extractor tests pass; 54 total project tests pass (zero regressions)
- **Commit:** `a67bfe1`

## Key Files

- `cal_scraper/extractor.py` — HTML event extraction module (public: extract_events_from_html, extract_all_events)
- `tests/test_extractor.py` — 13 tests for extraction, diacritics, error handling, multi-page
- `tests/fixtures/event_page.html` — Realistic Elementor HTML fixture with 4 articles

## Decisions Made

- CSS selectors use Elementor `data-id` attributes (not class names) — stable identifiers verified from site research
- Missing title or date → skip event with warning log; missing venue or description → empty string fallback
- Non-breaking space (U+00A0) replaced in `_clean_text()` — handles HTML entity artifacts from BS4's `.get_text()`
- Test for warning log capture: `caplog`-based tests call extraction directly (not via pytest fixture) to capture logs in test body scope

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed caplog test capturing logs in setup instead of test body**
- **Found during:** Task 2 (GREEN phase — test_skip_event_missing_title failed)
- **Issue:** The `events` pytest fixture ran extraction during setup phase; `caplog` only captures logs during the test body, so warning records were empty in assertions
- **Fix:** Changed `test_skip_event_missing_title` to call `extract_events_from_html()` directly within the test body instead of using the `events` fixture
- **Files modified:** tests/test_extractor.py
- **Commit:** a67bfe1

---

**Total deviations:** 1 auto-fixed (bug in test structure)
**Impact on plan:** Minimal — same test coverage, slightly different invocation pattern for one test

## Issues Encountered

None beyond the caplog fixture scope issue (auto-fixed above).

## Known Stubs

None — all extraction paths are fully wired to date parser and Event model.

## Next Phase Readiness

- Extractor module ready for integration with fetcher (02-01) to build the full scraping pipeline
- `extract_all_events(pages)` accepts list of HTML strings from fetcher's `fetch_all_pages()`
- Phase 3 (ICS generation) can consume `list[Event]` output directly
