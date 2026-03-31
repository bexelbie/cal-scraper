# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-31)

**Core value:** Reliably extract all upcoming children/family events from moravska-galerie.cz and produce a valid .ics file that any calendar app can import.
**Current focus:** Phase 1: Foundation & Date Parser

## Current Position

Phase: 1 of 3 (Foundation & Date Parser)
Plan: 0 of ? in current phase
Status: Ready to plan
Last activity: 2026-03-31 — Roadmap created

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: —
- Trend: —

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: 3-phase coarse structure — date parser first (highest risk, no network needed), then scraping, then ICS+CLI
- [Research]: Custom regex for Czech dates — no library handles "31/3/2026, 15 H" or en-dash ranges

### Pending Todos

None yet.

### Blockers/Concerns

- [Research]: 7+ date formats observed but more may appear from future events — parser needs fallback logging for unparseable dates
- [Research]: En-dash (U+2013) not hyphen — regex must match explicitly or multi-day events are silently dropped

## Session Continuity

Last session: 2026-03-31
Stopped at: Roadmap created, ready to plan Phase 1
Resume file: None
