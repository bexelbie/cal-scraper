# Requirements: Cal-Scraper

**Defined:** 2026-03-31
**Core Value:** Reliably extract all upcoming children/family events from moravska-galerie.cz and produce a valid .ics file that any calendar app can import.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Scraping

- [ ] **SCRP-01**: Scrape all paginated pages of /program/deti-a-rodiny/ (detect last page dynamically, not hardcoded)
- [ ] **SCRP-02**: Extract event title preserving Czech diacritics and special characters
- [ ] **SCRP-03**: Extract venue name including sub-locations (e.g., "Pražákův palác, Knihovna")
- [ ] **SCRP-04**: Extract short description text from listing pages
- [ ] **SCRP-05**: Extract event detail page URL for each event
- [ ] **SCRP-06**: Handle network errors gracefully (retry transient failures, log warnings, continue processing)
- [ ] **SCRP-07**: Use respectful scraping practices (delays between requests, proper User-Agent header)

### Date Parsing

- [ ] **DATE-01**: Parse single day + hour format ("31/3/2026, 15 H")
- [ ] **DATE-02**: Parse single day + hour.minutes format ("8/4/2026, 16.30 H")
- [ ] **DATE-03**: Parse single day with no time (all-day event)
- [ ] **DATE-04**: Parse multi-day date ranges ("7/7 – 11/7/2026") using en-dash separator
- [ ] **DATE-05**: Parse multi-day + time range ("27/7 – 31/7/2026, 9–16 H")
- [ ] **DATE-06**: Handle D/M/Y European date order (not M/D/Y)
- [ ] **DATE-07**: Apply Europe/Prague timezone to all parsed dates

### iCal Generation

- [ ] **ICAL-01**: Generate valid RFC 5545 .ics file with VCALENDAR and VEVENT components
- [ ] **ICAL-02**: Include DTSTART, DTEND, SUMMARY, DESCRIPTION, LOCATION, URL, UID, DTSTAMP per event
- [ ] **ICAL-03**: Generate stable deterministic UIDs from WordPress post IDs or URL slugs (re-import won't duplicate)
- [ ] **ICAL-04**: Use DATE value type for all-day events, DATE-TIME for timed events
- [ ] **ICAL-05**: Include VTIMEZONE component for Europe/Prague
- [ ] **ICAL-06**: Represent multi-day events as single VEVENT spanning the date range

### CLI

- [ ] **CLI-01**: Accept --output flag for configurable output path (default: ./moravska-galerie-deti.ics)
- [ ] **CLI-02**: Print summary of scraped events to stdout (count, date range)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Detail Page Scraping

- **DETL-01**: Visit each event's detail page for full description text
- **DETL-02**: Extract price information (e.g., "50 jednotlivec / 120 Kč rodinné")
- **DETL-03**: Extract reservation method (phone, email, online)

### Enhanced Output

- **ENHN-01**: Detect and flag sold-out events ("[VYPRODÁNO]" in title)
- **ENHN-02**: Add CATEGORIES property (venue name, "Děti a rodiny")
- **ENHN-03**: Add configurable VALARM reminders
- **ENHN-04**: Support --venue flag to filter by venue
- **ENHN-05**: Support --format json for structured output

### Automation

- **AUTO-01**: Calendar subscription URL (webcal:// protocol)
- **AUTO-02**: GitHub Actions workflow for automated .ics updates

## Out of Scope

| Feature | Reason |
|---------|--------|
| Translation of Czech text | User specified — events stay in Czech, external translation if needed |
| GUI or web interface | CLI script only — keeps it simple |
| Headless browser / JS rendering | Site serves static HTML, no JavaScript rendering needed |
| Database / state management | .ics file IS the state — calendar apps handle dedup via UIDs |
| Recurring event detection | Site lists each occurrence separately — standalone VEVENTs are simpler and more reliable |
| Multi-site support | Scope is Moravská galerie only |
| Image downloading | Calendar apps have poor image support — users can see images via event URL |
| General-purpose scraper config | One site, hardcode selectors — code is easier to update than config |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SCRP-01 | — | Pending |
| SCRP-02 | — | Pending |
| SCRP-03 | — | Pending |
| SCRP-04 | — | Pending |
| SCRP-05 | — | Pending |
| SCRP-06 | — | Pending |
| SCRP-07 | — | Pending |
| DATE-01 | — | Pending |
| DATE-02 | — | Pending |
| DATE-03 | — | Pending |
| DATE-04 | — | Pending |
| DATE-05 | — | Pending |
| DATE-06 | — | Pending |
| DATE-07 | — | Pending |
| ICAL-01 | — | Pending |
| ICAL-02 | — | Pending |
| ICAL-03 | — | Pending |
| ICAL-04 | — | Pending |
| ICAL-05 | — | Pending |
| ICAL-06 | — | Pending |
| CLI-01 | — | Pending |
| CLI-02 | — | Pending |

**Coverage:**
- v1 requirements: 22 total
- Mapped to phases: 0
- Unmapped: 22 ⚠️

---
*Requirements defined: 2026-03-31*
*Last updated: 2026-03-31 after initial definition*
