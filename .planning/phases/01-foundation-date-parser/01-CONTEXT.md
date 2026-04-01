# Phase 1: Foundation & Date Parser - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a working Python package structure with data models and a Czech date/time parser that correctly handles all observed format variants from the Moravská galerie website, producing timezone-aware datetime objects in Europe/Prague.

</domain>

<decisions>
## Implementation Decisions

### Default Event Duration
- **D-01:** When only a start time is given (e.g., "15 H"), default event duration is **2 hours**. DTEND = DTSTART + 2h.

### Multi-Day Event Representation
- **D-02:** Multi-day events (e.g., "7/7 – 11/7/2026") are represented as **single spanning all-day events**, not individual daily entries. Use DATE value type with DTEND = day after last day.
- **D-03:** Multi-day events with time ranges (e.g., "27/7 – 31/7/2026, 9–16 H") are also single spanning events. Use DTSTART at first day's start time, DTEND at last day's end time.

### Error Handling
- **D-04:** Unknown or unparseable date formats produce a **warning log message** and the event is **skipped** — processing continues for remaining events. Never crash on a single bad date.

### Agent's Discretion
- **Package layout:** Agent decides — keep it simple, YAGNI applies. This is a focused single-site scraper, not a generalized parsing framework. A flat module structure or minimal package is fine.
- **Data model design:** Agent decides — dataclasses or similar, whatever fits the scope.
- **Test framework:** Agent decides — pytest is the obvious choice.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Site Structure
- `.planning/research/ARCHITECTURE.md` — HTML selectors, page structure, date format matrix
- `.planning/research/FEATURES.md` — Date Format Matrix section with all 6+ observed formats and parsing challenges
- `.planning/research/PITFALLS.md` — Czech date parsing pitfalls and prevention strategies

### Standards
- No external specs — requirements fully captured in decisions above and REQUIREMENTS.md (DATE-01 through DATE-07)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project, no existing code

### Established Patterns
- None — first phase establishes patterns

### Integration Points
- Date parser output (parsed datetime objects) feeds into Phase 2 (scraping) and Phase 3 (ICS generation)
- Data models defined here will be used by all subsequent phases

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Keep it simple and focused.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-foundation-date-parser*
*Context gathered: 2026-03-31*
