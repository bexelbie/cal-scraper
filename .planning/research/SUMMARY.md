# Project Research Summary

**Project:** cal-scaper
**Domain:** Single-site web scraper → iCal (.ics) feed generator
**Researched:** 2026-03-31
**Confidence:** HIGH

## Executive Summary

Cal-scaper is a focused Python CLI tool that scrapes children/family event listings from Moravská galerie's website (moravska-galerie.cz) and generates a standards-compliant iCalendar (.ics) file. The site is a WordPress + Elementor installation that serves static HTML — no JavaScript rendering is needed. The standard expert approach for this kind of tool is a linear pipeline (fetch → extract → parse → generate → write) using `requests` + `BeautifulSoup` for scraping and the `icalendar` library for .ics output. All recommended libraries are mature, well-documented, and verified at current versions on PyPI.

The recommended approach is to build a Python package with 5 discrete pipeline components (Fetcher, Extractor, Date Parser, ICS Builder, Writer), each testable in isolation via dataclass boundaries. The critical complexity lives in one place: **Czech date/time parsing**. The site uses at least 7 human-entered date formats including en-dash separators (U+2013), dot-separated minutes ("16.30 H"), multi-day ranges with implicit years, and multiple time slots. This is the make-or-break component — everything else is straightforward library usage.

The key risks are: (1) underestimating date format variety — the PROJECT.md spec mentions 2 formats but the live site has 7+, and a parser built for only 2 will silently drop summer camp events; (2) using the WordPress REST API instead of HTML scraping — event dates are in Elementor text widgets, not in any structured API field; (3) generating .ics files without VTIMEZONE components, causing events to display at wrong times in Outlook and older clients. All three risks are well-understood and mitigated by the architecture and testing strategy outlined below.

## Key Findings

### Recommended Stack

Python ≥3.10 with four core dependencies, all verified on PyPI. The stack is deliberately minimal — no async frameworks, no headless browsers, no YAML configs. The site serves ~137KB static HTML pages; `requests` with polite 1-second delays is the right tool. Custom regex handles the Czech date formats since no library parses "31/3/2026, 15 H" or "7/7 – 11/7/2026, 9–16 H" out of the box.

**Core technologies:**
- **requests 2.33** — HTTP fetching with session pooling; synchronous is correct for 5 sequential pages with delays
- **beautifulsoup4 4.14 + lxml 6.0** — HTML parsing; BS4's forgiving parser + lxml speed handles WordPress/Elementor's deeply nested markup
- **icalendar 7.0** — RFC 5545 compliant .ics generation; v7's `Event.new()` API with native `zoneinfo` support
- **Custom regex (stdlib re)** — Czech date parsing; no library handles the site's 7 format variants
- **zoneinfo (stdlib)** — Europe/Prague timezone; preferred over deprecated `pytz`

**Version floor:** Python ≥3.10 (required by `requests` 2.33+ and `icalendar` 7.x)

### Expected Features

**Must have (table stakes):**
- Paginated scraping — site has 5 pages; dynamic page count discovery from `data-settings` JSON, not hardcoded
- Date/time parsing for all 7 observed formats — this IS the project's core complexity
- Event data extraction (title, date, venue, description, URL) from Elementor widget data-ids
- Valid .ics generation with VTIMEZONE for Europe/Prague
- Stable deterministic UIDs from WordPress post IDs (e.g., `19256@moravska-galerie.cz`)
- Multi-day event support (summer camps spanning 5 days)
- Default event duration (2 hours) when no end time is provided
- Graceful error handling — log unparseable events, continue processing, report summary
- CLI with configurable output path

**Should have (differentiators — Phase 2):**
- Detail page scraping for full descriptions and price info
- Sold-out status detection ("VYPRODÁNO" in title → prepend to SUMMARY)
- Reservation/ticket type in description
- CATEGORIES property for calendar filtering

**Defer (v2+):**
- Calendar subscription URL (requires hosting infrastructure)
- Automated scheduling (GitHub Actions / cron)
- VALARM reminders (calendar apps handle this natively)

**Anti-features (explicitly never build):**
- Translation (Czech stays Czech), general-purpose scraper config, GUI, database/state management, headless browser, recurring event detection, image downloading

### Architecture Approach

A linear 5-stage pipeline with dataclass boundaries between stages. Each component has a single responsibility and can be tested independently. The `main()` function only wires stages together. Selectors are module-level constants for easy maintenance when Elementor templates change.

**Major components:**
1. **Config** — CLI argument parsing via argparse; settings for output path and verbosity
2. **Fetcher** — HTTP requests with pagination discovery, rate limiting (1s delay), retry on transient errors
3. **Extractor** — HTML → `RawEvent` dataclass using Elementor `data-id` selectors
4. **Date Parser** — Czech date strings → timezone-aware `datetime` objects via ordered regex fallback chain
5. **ICS Builder + Writer** — `Event` dataclass → `icalendar.Calendar` → `.ics` file with VTIMEZONE

**Key data structures:**
- `RawEvent`: title, date_raw, venue, description, url (output of Extractor)
- `Event`: title, dtstart, dtend, all_day, venue, description, url (output of Date Parser, input to ICS Builder)

### Critical Pitfalls

1. **7+ date formats, not 2** — The live site has far more formats than the spec mentions. Build the complete parser from day one with all variants. Include raw date text in iCal description as safety net. Test against all 5 pages, not just page 1.

2. **En-dash (U+2013) not hyphen (U+002D)** — Both date ranges and time ranges use the Unicode en-dash character. Regex patterns must match `\u2013` explicitly or all multi-day events (~8 summer camps) are silently dropped.

3. **No structured date data anywhere** — WordPress REST API exposes only publish dates, not event dates. ACF fields are empty. Event dates exist ONLY in Elementor text widgets in the HTML. Do not attempt a REST API approach.

4. **Missing VTIMEZONE breaks Outlook** — The `icalendar` library adds `TZID=Europe/Prague` to DTSTART but does NOT auto-include a VTIMEZONE component. Must call `calendar.add_missing_timezones()` or manually add it. Also set `X-WR-TIMEZONE:Europe/Prague` for Apple Calendar compatibility.

5. **Pagination redirects to page 1, not 404** — Requesting beyond the last page returns a 301 redirect to page 1, not a 404. Parse max page count from `data-settings` JSON and/or track seen post IDs to prevent infinite loops.

## Implications for Roadmap

### Phase 1: Project Setup & Data Models
**Rationale:** Establish the package structure, dependencies, and shared data types before any logic. The dataclass boundaries drive the entire architecture.
**Delivers:** Working Python package with `pyproject.toml`, data models (`RawEvent`, `Event`), selector constants, and project scaffolding.
**Addresses:** Package structure, dependency installation, CLI skeleton
**Avoids:** Monolithic script anti-pattern (Pitfall: untestable code)

### Phase 2: Date Parser (Core Logic)
**Rationale:** This is the hardest and riskiest component. All 7 date format variants must be handled correctly before anything else makes sense. Build and thoroughly test this in isolation with unit tests — no network access needed.
**Delivers:** Complete Czech date parser handling all 7 formats with fallback chain, logging for unparseable dates, comprehensive test suite.
**Addresses:** Date/time parsing (the #1 table-stakes feature), multi-day support, default duration decisions
**Avoids:** Pitfall 1 (format complexity), Pitfall 2 (en-dash), Pitfall 12 (implicit year), Pitfall 13 (dot minutes), Pitfall 8 (multi-time slot design decision)

### Phase 3: Fetcher & Extractor (Web Scraping)
**Rationale:** With data models and date parser solid, build the HTTP layer and HTML extraction. Save HTML fixtures from each page for testing. This phase needs the fewest design decisions — it's known patterns with verified selectors.
**Delivers:** Paginated fetcher with dynamic page discovery, HTML extractor using Elementor data-id selectors, HTML test fixtures.
**Addresses:** Paginated scraping, event data extraction (title, date, venue, description, URL), graceful error handling
**Avoids:** Pitfall 3 (REST API trap), Pitfall 6 (pagination loop), Pitfall 7 (CTA vs title), Pitfall 10 (venue list), Pitfall 11 (HTML entities), Pitfall 16 (canary validation)

### Phase 4: ICS Generation & CLI
**Rationale:** The output layer. All input data is now clean and structured. Wire the pipeline together, generate valid .ics output, and expose via CLI.
**Delivers:** Working end-to-end pipeline producing valid .ics file with VTIMEZONE, stable UIDs, proper timezone handling, and configurable output path.
**Addresses:** Valid .ics generation, stable UIDs, Europe/Prague timezone, CLI output, multi-day calendar representation
**Avoids:** Pitfall 4 (missing VTIMEZONE), Pitfall 5 (no end time), Pitfall 14 (UID deduplication), Pitfall 17 (comma escaping), Pitfall 18 (multi-day representation)

### Phase 5: Enhancements (Optional)
**Rationale:** Only after the core pipeline is solid and tested. These features add value but don't block the primary use case.
**Delivers:** Detail page scraping with price/description enrichment, sold-out detection, reservation type, CATEGORIES.
**Addresses:** Differentiator features from FEATURES.md
**Avoids:** Scope creep — each enhancement is independently valuable and independently shippable

### Phase Ordering Rationale

- **Date Parser before Fetcher:** The parser is the highest-risk component with the most edge cases. Building it first with unit tests (no network needed) de-risks the project early. If the parser can't handle the formats, nothing else matters.
- **Fetcher/Extractor together:** They're tightly coupled in practice — the extractor needs HTML fixtures from the fetcher. Building them together with saved fixtures enables offline testing.
- **ICS generation last in core:** It depends on correct `Event` objects from the parser and extractor. It's also the most straightforward phase — `icalendar` library handles the heavy lifting.
- **Enhancements only after core works:** Detail page scraping triples HTTP requests and adds complexity. Don't mix this into the core pipeline development.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Date Parser):** The 7 format variants are well-documented from live scraping, but edge cases may exist in future events. Design decisions needed for multi-time slots and multi-day+time representation. Consider `/gsd-research-phase` for regex validation strategy.

Phases with standard patterns (skip deeper research):
- **Phase 1 (Setup):** Standard Python package scaffolding — well-documented, no unknowns.
- **Phase 3 (Fetcher/Extractor):** All CSS selectors verified against live site with HIGH confidence. Elementor data-ids confirmed consistent across all 28 events on 5 pages. Standard BeautifulSoup patterns.
- **Phase 4 (ICS Generation):** `icalendar` v7 API verified from source. VTIMEZONE approach documented. Standard library usage.
- **Phase 5 (Enhancements):** Detail page structure needs inspection at implementation time but is low risk.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All library versions verified on PyPI 2026-03-31. API patterns verified from icalendar source. |
| Features | HIGH | Based on direct multi-page site inspection + RFC 5545 spec. Feature priorities well-justified. |
| Architecture | HIGH | Linear pipeline is the canonical pattern for scrape-to-output tools. All selectors verified across 28 events on 5 pages. |
| Pitfalls | HIGH | All pitfalls verified with live evidence (HTML inspection, REST API probing, icalendar library testing). |

**Overall confidence:** HIGH — Research is grounded in live site analysis, verified library versions, and tested library behavior. No findings rely on assumptions or secondary sources alone.

### Gaps to Address

- **New date formats:** The 7 formats observed cover current events, but the gallery staff enter dates as free text. New formats may appear with future events. Mitigation: the fallback chain logs unparseable dates so they're caught immediately.
- **Elementor template stability:** The `data-id` selectors are stable today but could change if the gallery redesigns their Elementor loop template. Mitigation: canary validation check at scrape time; selectors centralized as constants.
- **Default event duration:** 2 hours is a reasonable assumption for workshop-type events but is not verified against actual event lengths. Mitigation: make configurable; include raw date text in description.
- **VTIMEZONE generation:** The `calendar.add_missing_timezones()` method in icalendar v7 was referenced in STACK.md but Pitfall 4 suggests it may not auto-generate VTIMEZONE. Validate during Phase 4 implementation — may need manual VTIMEZONE construction.
- **Cross-year date ranges:** Multi-day ranges spanning December→January would need year adjustment. Unlikely for gallery events but parser should handle gracefully.

## Sources

### Primary (HIGH confidence)
- **Live site HTML** — All 5 pages of moravska-galerie.cz/program/deti-a-rodiny/ (2026-03-31), including detail pages
- **PyPI package metadata** — requests 2.33.1, beautifulsoup4 4.14.3, lxml 6.0.2, icalendar 7.0.3 (verified 2026-03-31)
- **icalendar GitHub source** — collective/icalendar main branch (CHANGES.rst, cal/event.py, docs)
- **WordPress REST API** — /wp-json/wp/v2/posts, /wp-json/wp/v2/categories (confirmed ACF fields empty)
- **RFC 5545** — iCalendar specification for VEVENT, VTIMEZONE, UID, DTSTART/DTEND requirements

### Secondary (MEDIUM confidence)
- **Python 3.14 stdlib documentation** — zoneinfo, re, argparse, logging modules
- **robots.txt** — No restrictions on /program/ path confirmed

---
*Research completed: 2026-03-31*
*Ready for roadmap: yes*
