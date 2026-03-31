# Feature Landscape

**Domain:** Single-site web scraper → iCal feed (Moravská galerie children/family events)
**Researched:** 2025-07-14
**Overall confidence:** HIGH — based on direct site inspection + RFC 5545 spec + icalendar library docs

## Table Stakes

Features users expect. Missing = the tool doesn't do its job.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Paginated scraping** | Site has 5+ pages; missing any page = missing events | Low | Clean URL pattern: `/deti-a-rodiny/2/` through `/5/`. Detect last page from pagination nav, don't hardcode count. |
| **Event title extraction** | Core identity of each event | Low | Text within the post-title Elementor widget. Includes Czech diacritics — must preserve. |
| **Date/time parsing (all observed formats)** | Dates are the entire point of a calendar | High | **6 distinct formats observed** — see Date Format Matrix below. This is the hardest feature. |
| **Venue extraction** | Users need to know where to go | Low | Displayed on listing page. Some have sub-locations (e.g., "Pražákův palác, Knihovna"). Map to iCal LOCATION. |
| **Short description extraction** | Context for what the event is | Low | Truncated on listing pages (ends with `…`). Sufficient for v1; detail pages have full text. |
| **Event URL link** | Users need to click through for full info/tickets | Low | Each card links to detail page. Map to iCal URL property. |
| **Valid .ics generation (RFC 5545)** | File must actually import into calendar apps | Medium | Requires: VCALENDAR (VERSION, PRODID), VEVENT (UID, DTSTART, SUMMARY). Should also set DTEND, DESCRIPTION, LOCATION, URL, DTSTAMP. |
| **Stable UIDs** | Re-running script and re-importing shouldn't duplicate events | Medium | Generate deterministic UIDs from post ID or URL slug (e.g., `post-19256@cal-scraper.local`). WordPress post IDs are in the HTML class attributes. |
| **Europe/Prague timezone** | All events are in CET/CEST; floating times would be wrong for travelers | Medium | Use `zoneinfo.ZoneInfo("Europe/Prague")` with icalendar library. VTIMEZONE component should be included. |
| **Multi-day event support** | Summer camps are 5-day events (e.g., "7/7 – 11/7/2026") | Medium | Use DTSTART/DTEND spanning multiple days. For all-day multi-day events, use DATE value type (not DATE-TIME). |
| **Graceful error handling** | Network failures, site changes shouldn't crash silently | Low | Retry on transient errors, log warnings on parse failures, continue processing remaining events. |
| **CLI with configurable output path** | Users need to control where the file goes | Low | Argparse with `--output` flag, default to `./moravska-galerie-deti.ics`. |

### Date Format Matrix

Observed on the actual site (HIGH confidence — directly scraped):

| Format | Example | Interpretation | iCal Mapping |
|--------|---------|----------------|--------------|
| Single day + hour | `31/3/2026, 15 H` | March 31, 2026 at 15:00 | DTSTART: 20260331T150000, DTEND: +1h or +2h default |
| Single day + hour.min | `8/4/2026, 16.30 H` | April 8, 2026 at 16:30 | DTSTART: 20260408T163000 |
| Single day, no time | `23/5/2026` | May 23, 2026 all day | DTSTART;VALUE=DATE:20260523, DTEND;VALUE=DATE:20260524 |
| Single day + multiple times | `24/5/2026, 15 H / 16 H / 17 H` | Three separate time slots on May 24 | Best as single event: DTSTART at first slot (15:00), note slots in DESCRIPTION |
| Multi-day + time range | `27/7 – 31/7/2026, 9–16 H` | July 27–31, daily 9:00–16:00 | DTSTART: first day 09:00, DTEND: last day 16:00 |
| Multi-day, no time | `7/7 – 11/7/2026` | July 7–11 all day | DTSTART;VALUE=DATE, DTEND;VALUE=DATE (end = day after last) |

**Key parsing challenges:**
- Day/month order is D/M (European), not M/D
- The `–` separator is an en-dash (U+2013), not a hyphen
- Hours use `H` suffix and `.` for minutes (not `:`)
- Multi-day ranges have the year only on the end date
- The `●` bullet character precedes all dates

## Differentiators

Features that add real value beyond the basics but aren't blocking for v1.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Detail page scraping** | Full description + price info instead of truncated listing text | Medium | Detail pages have: full description, price ("50 jednotlivec / 120 Kč rodinné"), reservation info. Adds ~15 HTTP requests (3 events × 5 pages). Respect rate limits. |
| **Price in description** | Parents want to know cost before clicking through | Low (if detail scraping exists) | Append price line to DESCRIPTION field. Format observed: "V – 50 jednotlivec / 120 Kč rodinné". |
| **Reservation/ticket type indicator** | Tells user how to book (phone, email, online) | Low | Listing pages show "Koupit vstupenky" / "Rezervace přes telefon" / "Rezervace přes e-mail". Include in DESCRIPTION. |
| **Sold-out status** | Don't waste time on unavailable events | Low | "VYPRODÁNO" appears in title. Can flag in DESCRIPTION or set STATUS:CANCELLED (debatable — sold out ≠ cancelled). Better: prepend "[VYPRODÁNO]" to SUMMARY. |
| **CATEGORIES property** | Calendar apps can filter by category/venue | Low | Set CATEGORIES to venue name and/or "Děti a rodiny". Some apps support filtering. |
| **Calendar subscription URL** | Auto-updating feed instead of manual re-import | High | Requires hosting (GitHub Pages, static file server, or cron + upload). Huge UX improvement — webcal:// protocol. |
| **Automated scheduling** | Keep .ics fresh without manual runs | Medium | Cron job or GitHub Actions workflow. Pairs with subscription URL for full automation. |
| **VALARM reminders** | Remind users before events | Low | Add VALARM component with configurable lead time (e.g., 1 day before). Some calendar apps ignore imported alarms. |
| **Venue-based filtering** | Users may only care about one museum | Low | CLI flag like `--venue "Pražákův palác"` to filter output. |
| **JSON/structured output** | Debugging + alternative consumption | Low | `--format json` alongside ics. Useful for debugging date parsing. |

## Anti-Features

Features to explicitly NOT build. These add complexity without value for this use case.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Translation** | Project spec says Czech stays Czech. Translation quality for cultural event descriptions is poor via automation. Users read Czech or use their own tools. | Preserve original Czech text verbatim. Set LANGUAGE=cs property on text fields. |
| **General-purpose scraper config** | This scrapes ONE site. YAML/JSON selector configs add complexity for zero benefit — if the site changes, the selectors change, and code is easier to update than config. | Hardcode selectors in code. Document them clearly so they're easy to update. |
| **GUI or web interface** | CLI script is the spec. A GUI adds deployment complexity for a personal/small-audience tool. | Keep it a clean CLI script. If hosting is needed later, a GitHub Actions workflow is simpler than a web app. |
| **Database / state management** | No need to track what changed between runs. The .ics file IS the state — calendar apps handle dedup via UIDs. | Generate full .ics from scratch each run. Deterministic UIDs ensure calendar apps merge correctly. |
| **Headless browser / JS rendering** | The site serves static HTML via WordPress/Elementor. No JavaScript rendering needed. A headless browser would be 10x slower and add heavy dependencies. | Use requests + BeautifulSoup. Verified: all event data is in the initial HTML response. |
| **Recurring event detection** | The site lists each occurrence separately. Trying to detect recurrence patterns (e.g., "Barevné dopoledne" series) adds fragile heuristics for minimal calendar benefit. | Each event is a standalone VEVENT. Simpler, more reliable. |
| **Notification system** | Out of scope. Calendar apps already handle notifications via VALARM or their own settings. | If VALARM is added as a differentiator, that's sufficient. Don't build push notifications. |
| **Multi-site support** | Scope is Moravská galerie only. Abstracting for multiple sites front-loads complexity that may never be needed. | Single-site scraper. If a second site is ever needed, fork or refactor then. |
| **Image downloading** | Event thumbnails exist but calendar apps have poor image support in events. Large downloads for little benefit. | Include the event URL — users can see images on the website. |
| **Price tracking / comparison** | The tool generates a calendar, not a price aggregator. Prices rarely change for gallery events. | Include current price in description (if detail page scraping is added). No history needed. |

## Feature Dependencies

```
                  ┌─────────────────────┐
                  │ Paginated Scraping   │
                  │ (listing pages)      │
                  └────────┬────────────┘
                           │
              ┌────────────┼──────────────┐
              ▼            ▼              ▼
    ┌─────────────┐ ┌───────────┐ ┌──────────────┐
    │ Date Parsing │ │ Data      │ │ Detail Page  │
    │ (all formats)│ │ Extraction│ │ Scraping     │
    └──────┬──────┘ └─────┬─────┘ └──────┬───────┘
           │              │              │
           ▼              ▼              ▼
    ┌─────────────────────────────┐ ┌─────────────┐
    │ .ics Generation             │ │ Price Info   │
    │ (valid RFC 5545 + timezone) │ │ Full Desc    │
    └──────────┬──────────────────┘ └─────────────┘
               │
    ┌──────────┼───────────────┐
    ▼          ▼               ▼
┌────────┐ ┌──────────┐ ┌──────────────┐
│ CLI    │ │ VALARM   │ │ Subscription │
│ Output │ │ Reminders│ │ URL (hosted) │
│ Config │ └──────────┘ └──────┬───────┘
└────────┘                     │
                               ▼
                        ┌──────────────┐
                        │ Automated    │
                        │ Scheduling   │
                        └──────────────┘
```

**Key dependency chains:**
- Everything depends on paginated scraping working first
- Date parsing is the critical-path risk — if parsing fails, the calendar is useless
- Detail page scraping is independent of .ics generation (can be added later without refactoring)
- Calendar subscription requires both .ics generation AND a hosting/automation solution
- VALARM, CATEGORIES, sold-out status are additive — they layer onto existing VEVENT objects

## MVP Recommendation

**Prioritize (Phase 1 — core script):**

1. **Paginated scraping** — fetch all listing pages, extract event cards
2. **Date/time parsing** — handle all 6 observed formats correctly (this is the hard part)
3. **Data extraction** — title, date, venue, description, URL from listing pages
4. **Valid .ics generation** — proper VCALENDAR/VEVENT structure with timezone
5. **Stable UIDs** — use WordPress post IDs from HTML classes
6. **CLI output** — write .ics to configurable path

**Defer to Phase 2:**
- **Detail page scraping** — nice but doubles HTTP requests and adds complexity
- **Price info** — requires detail page scraping
- **Sold-out status** — low value, events are still useful to know about
- **Reservation type** — low value for calendar context

**Defer to Phase 3 (if ever):**
- **Calendar subscription URL** — requires hosting infrastructure
- **Automated scheduling** — pairs with subscription URL
- **VALARM reminders** — low value, calendar apps handle this

**Rationale:** The date parsing is the crux of this project. Get that right with comprehensive tests, and the rest is straightforward plumbing. Don't expand scope until the core loop (scrape → parse → generate) is solid and tested.

## Site-Specific Intelligence

Gathered from direct inspection of moravska-galerie.cz (2025-07-14):

| Observation | Implication |
|-------------|-------------|
| WordPress + Elementor with ECS (Elementor Custom Skin) | Event cards are in `article.elementor-post` elements. Custom loop template (ID 1575). Selectors may change if they update their Elementor template. |
| Post IDs in HTML classes | `post-19256`, `post-19582`, etc. — stable identifiers for UID generation. |
| Pagination uses clean URLs | `/deti-a-rodiny/2/` not query params. Last page detectable from `nav.pagination` links. |
| Some events have no time | All-day events (e.g., festivals). Must use DATE value type, not DATE-TIME. |
| Multiple time slots on one event | "15 H / 16 H / 17 H" — these are session times, not a range. Best treated as a single event starting at the first time. |
| En-dash (–) not hyphen (-) | Date ranges use U+2013. Parser must handle this specific character. |
| "H" suffix for hours | "15 H", "16.30 H", "9–16 H". Non-standard but consistent. |
| Categories in HTML classes | `category-deti-a-rodiny`, `tag-muzeum-josefa-hoffmanna` — could extract venue from classes as well as from visible text. |
| ~3 events per page × 5 pages | ~15 events total currently. Small dataset — no performance optimization needed. |
| Detail pages have price info | "V – 50 jednotlivec / 120 Kč rodinné" format. Not on listing pages. |

## Sources

- **Direct site inspection** of moravska-galerie.cz/program/deti-a-rodiny/ (pages 1, 3, 5) and detail page — HIGH confidence
- **RFC 5545** (iCalendar specification) — VEVENT requirements for DTSTART, UID, SUMMARY, DTEND, LOCATION, URL, DESCRIPTION, CATEGORIES, VALARM — HIGH confidence
- **Python icalendar library** v7.0.3 — supports zoneinfo timezone, RFC 5545 compliant generation — HIGH confidence (verified via PyPI + README)
- **PROJECT.md** — requirements, constraints, out-of-scope decisions — HIGH confidence
