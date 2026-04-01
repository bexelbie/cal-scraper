---
phase: 01-foundation-date-parser
plan: 01
subsystem: infra
tags: [python, setuptools, dataclasses, zoneinfo, pyproject]

# Dependency graph
requires: []
provides:
  - "Installable cal-scraper Python package with pyproject.toml"
  - "ParsedDate and Event dataclasses for pipeline contracts"
  - "PRAGUE_TZ constant (Europe/Prague) for timezone-aware datetimes"
  - "DEFAULT_DURATION constant (2 hours) for events without end time"
  - "Test infrastructure (pytest configured, tests/ directory)"
affects: [01-02-date-parser, 02-scraping, 03-ics-cli]

# Tech tracking
tech-stack:
  added: [requests, beautifulsoup4, lxml, icalendar, pytest, ruff]
  patterns: [dataclass-pipeline-contracts, zoneinfo-timezone, pyproject-toml-packaging]

key-files:
  created:
    - pyproject.toml
    - cal_scraper/__init__.py
    - cal_scraper/models.py
    - tests/__init__.py
    - .gitignore
    - README.md
  modified: []

key-decisions:
  - "Fixed build-backend from invalid setuptools.backends._legacy:_Backend to setuptools.build_meta"

patterns-established:
  - "Dataclass contracts: ParsedDate for parser output, Event for full pipeline"
  - "Timezone handling: PRAGUE_TZ = ZoneInfo('Europe/Prague') as project-wide constant"
  - "Union types: datetime | date for flexible timed/all-day event representation"

requirements-completed: [DATE-07]

# Metrics
duration: 2min
completed: 2026-04-01
---

# Phase 01 Plan 01: Project Scaffolding Summary

**Installable Python package with ParsedDate/Event dataclass contracts and Europe/Prague timezone constant**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-01T06:37:07Z
- **Completed:** 2026-04-01T06:39:34Z
- **Tasks:** 2
- **Files created:** 6

## Accomplishments
- Installable Python package via `pip install -e ".[dev]"` with all core deps (requests, beautifulsoup4, lxml, icalendar) and dev deps (pytest, ruff)
- ParsedDate and Event dataclasses with datetime|date union types for flexible timed/all-day event handling
- PRAGUE_TZ constant (Europe/Prague) per DATE-07 requirement
- DEFAULT_DURATION constant (2 hours) per D-01 decision

## Task Commits

Each task was committed atomically:

1. **Task 1: Create project structure and pyproject.toml** - `8291dc9` (feat)
2. **Task 2: Create data models with timezone infrastructure** - `482e775` (feat)

## Files Created/Modified
- `pyproject.toml` - Package metadata with all core and dev dependencies
- `cal_scraper/__init__.py` - Package marker with __version__ = "0.1.0"
- `cal_scraper/models.py` - ParsedDate, Event dataclasses; PRAGUE_TZ, DEFAULT_DURATION constants
- `tests/__init__.py` - Test package marker (empty)
- `.gitignore` - Python-standard entries (__pycache__, .venv, *.ics, etc.)
- `README.md` - Project description with install instructions

## Decisions Made
- Fixed build-backend from `setuptools.backends._legacy:_Backend` (invalid, from plan) to `setuptools.build_meta` (standard setuptools backend)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed invalid setuptools build-backend**
- **Found during:** Task 1 (Create project structure and pyproject.toml)
- **Issue:** Plan specified `setuptools.backends._legacy:_Backend` as build-backend, which does not exist in setuptools
- **Fix:** Changed to `setuptools.build_meta` (the standard setuptools PEP 517 backend)
- **Files modified:** pyproject.toml
- **Verification:** `pip install -e ".[dev]"` succeeds with all deps installed
- **Committed in:** 8291dc9 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential fix — package would not install without correct build-backend. No scope creep.

## Issues Encountered
None beyond the build-backend fix documented above.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all code is functional, no placeholders or mock data.

## Next Phase Readiness
- Package structure complete, ready for date parser implementation (Plan 01-02)
- ParsedDate dataclass defines the contract the date parser will return
- Event dataclass defines the contract for scraper → ICS pipeline
- pytest configured and ready for TDD in Plan 01-02

## Self-Check: PASSED

All 7 files verified present. All 2 commit hashes verified in git log.

---
*Phase: 01-foundation-date-parser*
*Completed: 2026-04-01*
