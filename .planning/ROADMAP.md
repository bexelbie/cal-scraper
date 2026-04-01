# Roadmap: Cal-Scraper

## Overview

Cal-scraper is a 3-phase pipeline build: first we establish the project foundation and tackle the hardest problem (Czech date parsing) in isolation, then we build the web scraping layer to extract structured event data from the gallery site, and finally we wire everything together into a working CLI that produces a valid .ics calendar file. Each phase delivers a testable, coherent capability.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation & Date Parser** - Project scaffolding and Czech date/time parsing (the core complexity)
- [ ] **Phase 2: Web Scraping** - Paginated fetching and HTML event extraction from Moravská galerie
- [ ] **Phase 3: ICS Generation & CLI** - End-to-end pipeline producing importable .ics calendar file

## Phase Details

### Phase 1: Foundation & Date Parser
**Goal**: The project has a working package structure with data models, and can correctly parse all Czech date/time formats from the gallery site into timezone-aware datetime objects
**Depends on**: Nothing (first phase)
**Requirements**: DATE-01, DATE-02, DATE-03, DATE-04, DATE-05, DATE-06, DATE-07
**Success Criteria** (what must be TRUE):
  1. Running `pip install -e .` installs the package and all dependencies (requests, beautifulsoup4, lxml, icalendar)
  2. Parser correctly converts single-day formats like "31/3/2026, 15 H" and "8/4/2026, 16.30 H" to timezone-aware datetimes in Europe/Prague
  3. Parser correctly converts multi-day ranges like "7/7 – 11/7/2026" and "27/7 – 31/7/2026, 9–16 H" to start/end datetime pairs
  4. Parser correctly identifies all-day events (no time component) vs timed events
  5. All date formats use D/M/Y European order and produce Europe/Prague timezone-aware results
**Plans:** 2 plans

Plans:
- [x] 01-01-PLAN.md — Project foundation: package scaffolding, pyproject.toml, data models (ParsedDate, Event, PRAGUE_TZ)
- [x] 01-02-PLAN.md — Czech date parser (TDD): regex fallback chain for all 6 date format variants

### Phase 2: Web Scraping
**Goal**: The tool can fetch all paginated event listings from moravska-galerie.cz and extract structured event data with Czech text preserved
**Depends on**: Phase 1
**Requirements**: SCRP-01, SCRP-02, SCRP-03, SCRP-04, SCRP-05, SCRP-06, SCRP-07
**Success Criteria** (what must be TRUE):
  1. Running the fetcher retrieves all pages of events (dynamic page count discovery, not hardcoded)
  2. Each extracted event contains title, date text, venue (with sub-location), description, and detail URL — all with Czech diacritics preserved
  3. Network errors (timeout, connection refused) produce a warning and processing continues with remaining pages
  4. Requests include 1-second delays between pages and a descriptive User-Agent header
**Plans:** 2 plans

Plans:
- [ ] 02-01-PLAN.md — HTTP page fetcher with pagination discovery, rate limiting, and error handling
- [ ] 02-02-PLAN.md — HTML event extractor with Elementor selector-based field extraction

### Phase 3: ICS Generation & CLI
**Goal**: Users can run a single command to produce a valid .ics calendar file of all upcoming children/family events from the gallery
**Depends on**: Phase 2
**Requirements**: ICAL-01, ICAL-02, ICAL-03, ICAL-04, ICAL-05, ICAL-06, CLI-01, CLI-02
**Success Criteria** (what must be TRUE):
  1. Running `cal-scraper` produces a .ics file that imports into Google Calendar, Apple Calendar, or Outlook without errors
  2. Each calendar event shows correct title, date/time (in Europe/Prague timezone), venue, description, and a clickable link to the event detail page
  3. Multi-day events appear as spanning the full date range (single VEVENT, not separate per-day entries)
  4. Re-importing the .ics file does not create duplicate events (stable deterministic UIDs)
  5. Running `cal-scraper --output /path/to/file.ics` saves to the specified path, and stdout shows event count and date range summary
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Date Parser | 0/? | Not started | - |
| 2. Web Scraping | 0/? | Not started | - |
| 3. ICS Generation & CLI | 0/? | Not started | - |
