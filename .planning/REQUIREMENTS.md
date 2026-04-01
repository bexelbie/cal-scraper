# Requirements: Cal-Scraper

**Defined:** 2026-03-31
**Core Value:** Reliably extract all upcoming children/family events from moravska-galerie.cz and produce a valid .ics file that any calendar app can import.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Scraping

- [x] **SCRP-01**: Scrape all paginated pages of /program/deti-a-rodiny/ (detect last page dynamically, not hardcoded)
- [x] **SCRP-02**: Extract event title preserving Czech diacritics and special characters
- [x] **SCRP-03**: Extract venue name including sub-locations (e.g., "Pražákův palác, Knihovna")
- [x] **SCRP-04**: Extract short description text from listing pages
- [x] **SCRP-05**: Extract event detail page URL for each event
- [x] **SCRP-06**: Handle network errors gracefully (retry transient failures, log warnings, continue processing)
- [x] **SCRP-07**: Use respectful scraping practices (delays between requests, proper User-Agent header)

### Date Parsing

- [x] **DATE-01**: Parse single day + hour format ("31/3/2026, 15 H")
- [x] **DATE-02**: Parse single day + hour.minutes format ("8/4/2026, 16.30 H")
- [x] **DATE-03**: Parse single day with no time (all-day event)
- [x] **DATE-04**: Parse multi-day date ranges ("7/7 – 11/7/2026") using en-dash separator
- [x] **DATE-05**: Parse multi-day + time range ("27/7 – 31/7/2026, 9–16 H")
- [x] **DATE-06**: Handle D/M/Y European date order (not M/D/Y)
- [x] **DATE-07**: Apply Europe/Prague timezone to all parsed dates

### iCal Generation

- [x] **ICAL-01**: Generate valid RFC 5545 .ics file with VCALENDAR and VEVENT components
- [x] **ICAL-02**: Include DTSTART, DTEND, SUMMARY, DESCRIPTION, LOCATION, URL, UID, DTSTAMP per event
- [x] **ICAL-03**: Generate stable deterministic UIDs from WordPress post IDs or URL slugs (re-import won't duplicate)
- [x] **ICAL-04**: Use DATE value type for all-day events, DATE-TIME for timed events
- [x] **ICAL-05**: Include VTIMEZONE component for Europe/Prague
- [x] **ICAL-06**: Represent multi-day events as single VEVENT spanning the date range

### CLI

- [x] **CLI-01**: Accept --output flag for configurable output path (default: ./moravska-galerie-deti.ics)
- [x] **CLI-02**: Print summary of scraped events to stdout (count, date range)

## v2 Requirements

Completed or explicitly deferred. Updated 2026-04-01.

### Detail Page Scraping

- [x] **DETL-01**: Visit each event's detail page for full description text
- [x] **DETL-02**: Extract price information (e.g., "50 jednotlivec / 120 Kč rodinné")
- [x] **DETL-03**: Extract reservation method (phone, email, online)

### Enhanced Output

- [x] **ENHN-01**: Detect and flag sold-out events ("[VYPRODÁNO]" in title)
- ~~**ENHN-02**: Add CATEGORIES property~~ — Won't do (low value for calendar readers)
- ~~**ENHN-03**: Add configurable VALARM reminders~~ — Won't do (calendar apps handle this natively)
- ~~**ENHN-04**: Support --venue flag to filter by venue~~ — Won't do (superseded by multi-site --site flag)
- ~~**ENHN-05**: Support --format json for structured output~~ — Won't do (no identified use case)

### Automation

- ~~**AUTO-01**: Calendar subscription URL (webcal:// protocol)~~ — Won't do (requires hosting)
- ~~**AUTO-02**: GitHub Actions workflow for automated .ics updates~~ — Won't do (user runs locally)

### Multi-site (added post-v1)

- [x] Multi-site architecture with `--site` flag and per-site .ics output
- [x] Hvězdárna Brno (planetarium public shows)
- [x] IKEA Brno (kids events via JSON API)
- [x] VIDA! Science Center (family events + lab workshops)
- [x] English calendar names with "(unofficial, in CZ)" suffix
- [x] Per-site X-WR-CALDESC with filtering descriptions
- [x] Estimated end time notes in event descriptions
- ~~Detail page scraping for hvězdárna~~ — Won't do (listing already has all data)
- ~~Detail page scraping for VIDA~~ — Won't do (detail pages are day guides, not structured event data)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Translation of Czech text | User specified — events stay in Czech, external translation if needed |
| GUI or web interface | CLI script only — keeps it simple |
| Headless browser / JS rendering | Sites serve static HTML or JSON APIs, no JavaScript rendering needed |
| Database / state management | .ics file IS the state — calendar apps handle dedup via UIDs |
| Recurring event detection | Sites list each occurrence separately — standalone VEVENTs are simpler and more reliable |
| Image downloading | Calendar apps have poor image support — users can see images via event URL |
| Hosted calendar server | No webcal:// hosting — user runs locally and imports .ics files |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATE-01 | Phase 1 | Complete |
| DATE-02 | Phase 1 | Complete |
| DATE-03 | Phase 1 | Complete |
| DATE-04 | Phase 1 | Complete |
| DATE-05 | Phase 1 | Complete |
| DATE-06 | Phase 1 | Complete |
| DATE-07 | Phase 1 | Complete |
| SCRP-01 | Phase 2 | Complete |
| SCRP-02 | Phase 2 | Complete |
| SCRP-03 | Phase 2 | Complete |
| SCRP-04 | Phase 2 | Complete |
| SCRP-05 | Phase 2 | Complete |
| SCRP-06 | Phase 2 | Complete |
| SCRP-07 | Phase 2 | Complete |
| ICAL-01 | Phase 3 | Complete |
| ICAL-02 | Phase 3 | Complete |
| ICAL-03 | Phase 3 | Complete |
| ICAL-04 | Phase 3 | Complete |
| ICAL-05 | Phase 3 | Complete |
| ICAL-06 | Phase 3 | Complete |
| CLI-01 | Phase 3 | Complete |
| CLI-02 | Phase 3 | Complete |

**Coverage:**
- v1 requirements: 22 total
- Mapped to phases: 22 ✓
- Unmapped: 0

---
*Requirements defined: 2026-03-31*
*Last updated: 2026-03-31 after roadmap creation*
