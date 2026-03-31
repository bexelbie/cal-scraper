# Cal-Scraper

## What This Is

A Python script that scrapes the Moravská galerie (Moravian Gallery in Brno) website's children and family events section and generates an iCal (.ics) feed. The events are in Czech and are not translated — the .ics file preserves the original Czech text. Users run the script manually to get a fresh calendar file.

## Core Value

Reliably extract all upcoming children/family events from moravska-galerie.cz and produce a valid .ics file that any calendar app can import.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Scrape all paginated pages of https://moravska-galerie.cz/program/deti-a-rodiny/
- [ ] Extract event title, date/time, venue, and short description from listing pages
- [ ] Include a URL link to each event's detail page in the calendar entry
- [ ] Parse Czech date formats (e.g., "31/3/2026, 15 H", "7/7 – 11/7/2026")
- [ ] Generate a valid .ics file importable by Google Calendar, Apple Calendar, Outlook
- [ ] Handle multi-day events (date ranges like "7/7 – 11/7/2026")
- [ ] Output the .ics file to a configurable path (default: current directory)
- [ ] Gracefully handle network errors and missing data

### Out of Scope

- Translation of Czech event text — user reads Czech or uses external translation
- Visiting individual event detail pages for full description/price — deferred to v2
- Live server or calendar subscription URL — one-shot script only for now
- Recurring event detection — each event is treated as a standalone occurrence
- GUI or web interface — CLI script only

## Context

- **Target site:** moravska-galerie.cz — a WordPress site using Elementor, serves standard HTML
- **Section URL:** https://moravska-galerie.cz/program/deti-a-rodiny/ (paginated, currently 5 pages)
- **Event data on listing pages:** title, date/time, venue name, short description, link to detail page
- **Date formats observed:** "31/3/2026, 15 H" (single day), "7/7 – 11/7/2026" (multi-day range), "2/4/2026, 10 H"
- **Venues:** Muzeum Josefa Hoffmanna, Uměleckoprůmyslové muzeum, Pražákův palác (+ sub-locations like "Knihovna")
- **Language:** Czech (cs) — all content stays in original language
- **Repo name:** cal-scaper (intentional spelling)

## Constraints

- **Language:** Python — good ecosystem for scraping (requests, BeautifulSoup) and iCal generation (icalendar)
- **No JS rendering:** The site serves static HTML, so no headless browser needed
- **Respectful scraping:** Include reasonable delays between page fetches, proper User-Agent header
- **Timezone:** Events are in Europe/Prague timezone (CET/CEST)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python over Node.js | Better scraping/ical libraries (requests, BeautifulSoup, icalendar) | — Pending |
| Listing-only scraping for v1 | Faster, simpler, detail pages can be added later | — Pending |
| One-shot script over live server | Simpler architecture, user runs when needed | — Pending |
| No translation | User specified — events stay in Czech | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-31 after initialization*
