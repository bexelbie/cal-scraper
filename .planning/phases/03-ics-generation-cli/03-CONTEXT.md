# Phase 3: ICS Generation & CLI - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire the fetcher, extractor, date parser, and iCal generator into a single `cal-scraper` CLI command that produces a valid .ics calendar file of all upcoming children/family events. This is the final assembly phase.

</domain>

<decisions>
## Implementation Decisions

### Agent's Discretion — All Areas
User said "just build it" — agent has full discretion on all implementation details. Keep it simple.

Key constraints from prior phases and requirements:
- **D-01:** Output a valid .ics file importable by Google Calendar, Apple Calendar, Outlook
- **D-02:** Each VEVENT must have: SUMMARY (title), DTSTART/DTEND (from ParsedDate), LOCATION (venue), DESCRIPTION (description text), URL (detail page link)
- **D-03:** Multi-day events use single spanning VEVENT (from Phase 1 D-02/D-03)
- **D-04:** Stable deterministic UIDs based on WordPress post IDs — re-import must not create duplicates
- **D-05:** CLI supports `--output /path/to/file.ics` flag, defaults to stdout or reasonable default filename
- **D-06:** CLI shows event count and date range summary on stderr/stdout
- **D-07:** 2-hour default duration when only start time given (from Phase 1 D-01)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Code (Phase 1 & 2)
- `cal_scraper/models.py` — ParsedDate, Event dataclasses, PRAGUE_TZ, DEFAULT_DURATION
- `cal_scraper/date_parser.py` — `parse_date(text)` → ParsedDate or None
- `cal_scraper/fetcher.py` — `fetch_all_pages(base_url)` → list[str]
- `cal_scraper/extractor.py` — `extract_events_from_html(html)` → list[Event]

### Requirements
- `.planning/REQUIREMENTS.md` — ICAL-01 through ICAL-06, CLI-01, CLI-02

### Standards
- RFC 5545 (iCalendar) — VEVENT structure, DTEND exclusive for DATE values

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Full pipeline already exists: fetcher → extractor → date parser → Event objects
- `icalendar` library already installed in pyproject.toml
- `PRAGUE_TZ` and `DEFAULT_DURATION` constants ready to use

### Integration Points
- `fetch_all_pages()` → `extract_events_from_html()` for each page → collect all Events → generate iCal
- CLI entry point via `[project.scripts]` in pyproject.toml: `cal-scraper = "cal_scraper.cli:main"`

</code_context>

<specifics>
## Specific Ideas

- This is the "make it actually work end-to-end" phase
- User runs `cal-scraper` and gets a calendar file — that's the product

</specifics>

<deferred>
## Deferred Ideas

None — this is the final v1 phase

</deferred>

---

*Phase: 03-ics-generation-cli*
*Context gathered: 2026-04-01*
