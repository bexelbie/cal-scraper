---
phase: 03-ics-generation-cli
plan: 02
subsystem: cli
tags: [cli, argparse, pipeline, entry-point, tdd]

# Dependency graph
requires:
  - phase: 03-ics-generation-cli
    plan: 01
    provides: "events_to_ics() ICS generation function"
  - phase: 02-web-scraping
    provides: "fetch_all_pages(), extract_all_events(), ScrapingError"
provides:
  - "cal-scraper CLI command (console entry point)"
  - "main() pipeline orchestration function"
affects:
  - pyproject.toml (added [project.scripts] section)

# Tech stack
tech_stack:
  added: []
  patterns: ["argparse CLI", "pipeline orchestration", "mock-based TDD"]

# Key files
key_files:
  created:
    - cal_scraper/cli.py
    - tests/test_cli.py
  modified:
    - pyproject.toml

# Key decisions
decisions:
  - id: CLI-ARGPARSE
    summary: "argparse with --output/-o and --verbose/-v flags — stdlib, no extra deps"
  - id: CLI-PIPELINE
    summary: "main() wires fetch → extract → ICS → write as linear pipeline"
  - id: CLI-SUMMARY
    summary: "Prints event count, date range (min/max dtstart), output path to stdout"

# Metrics
metrics:
  duration: "3min"
  completed: "2026-04-01"
  tasks: 2
  files: 3
  test_count: 14
  total_tests: 95
---

# Phase 03 Plan 02: CLI & Pipeline Wiring Summary

CLI entry point with argparse flags wiring fetch→extract→ICS→write pipeline, registered as `cal-scraper` console command.

## What Was Built

### cal_scraper/cli.py (108 lines)
- `main(argv)` — parses `--output/-o` (default: `moravska-galerie-deti.ics`) and `--verbose/-v` flags
- Calls `fetch_all_pages()` → `extract_all_events(pages)` → `events_to_ics(events)` → writes file
- `_summarize()` prints event count, date range (min/max of dtstart dates), and output path to stdout
- Handles `ScrapingError` gracefully: prints to stderr, returns exit code 1
- Zero events: prints "No events found." message

### pyproject.toml
- Added `[project.scripts]` section: `cal-scraper = "cal_scraper.cli:main"`
- `cal-scraper --help` verified working after `pip install -e .`

### tests/test_cli.py (293 lines, 14 tests)
- `TestCliArgParsing` (4 tests): default path, --output, -o, --verbose
- `TestCliPipeline` (4 tests): call order, file content, extract receives pages, ICS receives events
- `TestCliSummary` (3 tests): event count + date range, output path, no-events message
- `TestCliErrorHandling` (3 tests): ScrapingError returns 1, prints to stderr, no output file

## TDD Execution

| Phase    | Tests | Outcome |
|----------|-------|---------|
| RED      | 14    | All failed (cli.py not yet created) |
| GREEN    | 14    | All passed after implementing cli.py |
| REFACTOR | —     | No refactoring needed |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed verbose test mocking approach**
- **Found during:** Task 1 GREEN phase
- **Issue:** Test mocked entire `logging` module, making `logging.DEBUG` a MagicMock instead of integer 10
- **Fix:** Changed to `patch("logging.basicConfig")` instead of `patch("cal_scraper.cli.logging")`
- **Files modified:** tests/test_cli.py
- **Commit:** c60277a

**2. [Rule 1 - Bug] Fixed ICS mock string line endings**
- **Found during:** Task 1 GREEN phase
- **Issue:** Mock ICS used `\r\n` line endings, but Python text-mode write converts to `\n`
- **Fix:** Changed MOCK_ICS to use `\n` line endings
- **Files modified:** tests/test_cli.py
- **Commit:** c60277a

## Verification

```
Full test suite: 95 passed in 8.68s
CLI tests: 14 passed
cal-scraper --help: exits 0 with usage showing --output flag
CLI importable: from cal_scraper.cli import main ✓
```

## Known Stubs

None — all functionality is fully wired.
