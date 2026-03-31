# Domain Pitfalls

**Domain:** Web scraper → iCal (.ics) generator for Czech gallery events
**Target:** moravska-galerie.cz (WordPress + Elementor)
**Researched:** 2026-03-31
**Method:** Live analysis of all 5 paginated listing pages, WP REST API inspection, icalendar library testing

## Critical Pitfalls

Mistakes that cause wrong event data, broken calendar files, or missed events.

### Pitfall 1: Date Format Complexity Far Exceeds Initial Spec

**What goes wrong:** PROJECT.md lists 2 date formats ("31/3/2026, 15 H" and "7/7 – 11/7/2026"). The actual site has **at least 7 distinct formats**. A parser built for only 2 will silently drop or mangle events.

**Evidence from live scraping (all 5 pages):**

| Format | Example | Where Found | Notes |
|--------|---------|-------------|-------|
| `D/M/YYYY, HH H` | `31/3/2026, 15 H` | Page 1 | Whole-hour time |
| `D/M/YYYY, HH.MM H` | `8/4/2026, 16.30 H` | Page 1, 3 | **Dot** for minutes, not colon |
| `D/M/YYYY` | `23/5/2026` | Page 3 | No time at all (all-day event) |
| `D/M/YYYY, HH H / HH H / HH H` | `24/5/2026, 15 H / 16 H / 17 H` | Page 3 | Multiple time slots |
| `D/M – D/M/YYYY` | `7/7 – 11/7/2026` | Page 4 | Multi-day, no time, no year on first date |
| `D/M – D/M/YYYY, H–H H` | `13/7 – 17/7/2026, 9–16 H` | Page 4, 5 | Multi-day with daily time range |
| `D/M/YYYY, HH H` (new venue) | `30/5/2026, 10 H` | Page 4 | Same format but venue outside expected list |

**Why it happens:** Date formats come from human-entered Elementor text widgets, not a structured date field. Staff use whatever notation fits the event.

**Consequences:** Events with unrecognized formats silently fail to parse. User thinks they have all events but misses summer camps (the multi-day formats are exclusively summer camp events).

**Prevention:**
1. Build the date parser with ALL 7 formats from day one, not incrementally
2. Add a fallback that logs unparsable dates with the raw text so no event is silently dropped
3. Include the raw date string in the iCal description as a safety net
4. Test parser against ALL current pages, not just page 1

**Detection:** Any event article that produces no parsed date = bug. Count parsed events vs. total articles scraped. If they don't match, parser is incomplete.

**Phase relevance:** Must be addressed in the initial scraping/parsing phase. This is the core logic.

### Pitfall 2: En-dash (U+2013) vs Hyphen-minus (U+002D) in Date Ranges

**What goes wrong:** Date ranges use the Unicode en-dash `–` (U+2013), not a regular hyphen `-` (U+002D). Time ranges within dates also use en-dash. A regex matching `-` will miss all multi-day events and time ranges.

**Evidence:**
```
Raw: '● 13/7 – 17/7/2026, 9–16 H'
  Position 7: U+2013 = – (en-dash, between date range)
  Position 21: U+2013 = – (en-dash, between time range)
```

Both the date separator (`7/7 – 11/7`) and the time range (`9–16 H`) use en-dash. The date separator has surrounding spaces; the time range does not.

**Consequences:** All multi-day events (summer camps = ~8 events on pages 4-5) are missed entirely.

**Prevention:** Match `\u2013` (or `–`) explicitly in regex patterns. Don't use `-` for range matching. Consider normalizing en-dashes to hyphens early in the pipeline, but document this decision.

**Detection:** If regex uses `-` for ranges and returns 0 multi-day events, this is the cause.

**Phase relevance:** Core parsing phase. Must be correct from first implementation.

### Pitfall 3: No Structured Event Date in WordPress — Must Scrape HTML

**What goes wrong:** Developer sees WP REST API (`/wp-json/wp/v2/posts`) and assumes event dates are available as structured data. They aren't.

**Evidence:**
```
REST API date field: "2026-01-06T11:00:00"  (WordPress publish date)
Actual event date:   "31/3/2026, 15 H"      (in Elementor text widget)
```

The REST API has ACF (Advanced Custom Fields) installed but event dates are NOT exposed through it (`acf: []`). The `date` and `date_gmt` fields are WordPress publication timestamps, which are months before the actual event. There's no custom field, no meta field, no structured source for event dates.

**Consequences:** Building against the REST API wastes days and produces a calendar with wrong dates for every event. Using REST API `date` would show events happening in January when they're actually in March-August.

**Prevention:** Scrape the HTML listing pages. The event date lives in the Elementor text-editor widget with `data-id="fe5263e"` inside each `<article>` element. This data-id is consistent across ALL articles on ALL pages (verified across 28 events on 5 pages).

**Detection:** If any event date is before the current date when the events section shows future events, dates are from the wrong source.

**Phase relevance:** Architecture decision — must be made before any code is written.

### Pitfall 4: Missing VTIMEZONE Component in Generated .ics

**What goes wrong:** The `icalendar` Python library adds `TZID=Europe/Prague` to DTSTART but does NOT automatically include a `VTIMEZONE` component defining what Europe/Prague means. Some calendar apps (notably Outlook and older Android clients) cannot resolve the timezone without it.

**Evidence from library testing (icalendar 7.0.3):**
```ics
BEGIN:VEVENT
DTSTART;TZID=Europe/Prague:20260331T150000
END:VEVENT
```
No `BEGIN:VTIMEZONE` block is generated unless explicitly added.

**Consequences:** Events import at the wrong time in some calendar apps — typically off by 1-2 hours (the CET/CEST offset difference).

**Prevention:** Manually construct and add a VTIMEZONE component for Europe/Prague with both STANDARD (CET, UTC+1) and DAYLIGHT (CEST, UTC+2) definitions. Also add `X-WR-TIMEZONE:Europe/Prague` as a calendar-level property (Apple Calendar uses this).

**Detection:** Import .ics into Outlook and a non-default-timezone device. If event times differ between apps, VTIMEZONE is missing.

**Phase relevance:** iCal generation phase. Template this once, reuse for all events.

### Pitfall 5: Single Events With No End Time

**What goes wrong:** Most events show only a start time ("15 H") with no end time. The iCal spec says DTEND is optional, but calendar apps render events with no duration as zero-length or use varying defaults (some show 1 hour, some show 0 minutes, some show the rest of the day).

**Evidence:** All single-day events on pages 1-3 show only start time. No end time is present on listing pages or in the visible card content.

**Consequences:** Events appear as instantaneous points or fill the entire day in some calendar views, making the calendar hard to use.

**Prevention:** Set a sensible default duration (e.g., 2 hours for workshop-type events) and document this assumption. Include the original time text in the description so users can see the raw data. Consider making the default duration configurable.

**Detection:** Check calendar app rendering — if events show as 0-minute blocks, this is the issue.

**Phase relevance:** iCal generation phase. Design decision needed before generating output.

## Moderate Pitfalls

### Pitfall 6: Pagination Redirects to Page 1 Instead of 404

**What goes wrong:** Requesting page 6 (beyond the 5 existing pages) returns a 301 redirect to page 1 (`/program/deti-a-rodiny/`), not a 404. A naive "fetch until 404" pagination strategy creates an infinite loop, re-scraping page 1 forever.

**Evidence:**
```
GET /program/deti-a-rodiny/6/ → 301 → /program/deti-a-rodiny/ (page 1)
```

**Prevention:** Two strategies (use both):
1. Parse the `<nav class="elementor-pagination">` element to discover the actual page count (links to pages 1-5 are present on every page)
2. Track seen article IDs (`post-XXXXX` from article element) and stop when all articles on a page have been seen before

**Detection:** If scraper runs for more than ~10 pages or takes unusually long, it's looping.

**Phase relevance:** Pagination/scraping phase. Must be in the initial implementation.

### Pitfall 7: CTA Text Before Event Title Confused as Title

**What goes wrong:** Each event card has a heading widget _above_ the title that contains action text. If the scraper grabs "the first heading" as the title, it gets "Koupit vstupenky" or "Rezervace přes telefon" instead of the event name.

**Evidence — CTA variants observed:**

| CTA Text | Meaning | Where |
|----------|---------|-------|
| `Koupit vstupenky` | Buy tickets (links to goout.net) | Most events |
| `Rezervace přes telefon` | Reserve by phone | Page 1, article 1 |
| `Přihláška` | Application/registration | Page 4, article 2 |
| `Vstupné dobrovolné` | Voluntary admission | Page 4, article 1 |
| `Rezervace přes formulář` | Reserve via form | Page 4, article 5 |
| _(none)_ | No CTA | Page 3, article 3; page 4, articles 4 & 6 |

**Prevention:** Use the specific Elementor widget type to distinguish: the title is in `theme-post-title.default` (data-id `ff31590`), while the CTA is in the first `heading.default` (data-id `87e5159`). Never rely on element order or text content to identify the title.

**Detection:** If any event title is "Koupit vstupenky", the wrong element is being scraped.

**Phase relevance:** HTML parsing phase. Selector strategy must target correct widget.

### Pitfall 8: Multiple Time Slots ≠ One Multi-Hour Event

**What goes wrong:** "24/5/2026, 15 H / 16 H / 17 H" looks like a time range but is actually 3 separate time slots for the same activity (families can attend at 15:00, 16:00, or 17:00). Creating one event from 15:00-17:00 is semantically wrong.

**Evidence:** "Tajemství pavučiny" at Jurkovičova vila offers 3 separate guided experiences for groups.

**Prevention:** Design decision needed:
- **Option A (recommended for v1):** Create a single event at the first time slot (15:00) with description noting "Also available at 16 H and 17 H"
- **Option B:** Create 3 separate calendar events, one per slot
- **Option C:** Create one event at first slot with 1-hour duration

Document the chosen behavior. Detect the `HH H / HH H` pattern explicitly.

**Detection:** Look for `/` separating `H` patterns in the time portion.

**Phase relevance:** Date parsing phase. Requires explicit design decision.

### Pitfall 9: Venue Names Are Inconsistent in Source Data

**What goes wrong:** The source data has spelling inconsistencies for the same venue. A venue normalization or matching strategy that relies on exact strings will treat them as different venues.

**Evidence:**
```
Page 4, Article 4: "Muzeum Josefa Hoffmanna"  (double n)
Page 4, Article 6: "Muzeum Josefa Hoffmana"   (single n)
```

Both are the same physical museum — the double-n is the correct Czech spelling.

**Prevention:** For v1, pass through venue names as-is from the source. Don't attempt normalization. The venue field in iCal is just a text string; inconsistency in the source is the gallery's problem, not ours. If venue matching becomes important later, use fuzzy matching.

**Detection:** Diff all venue strings across all pages. If near-duplicates appear, this is the issue.

**Phase relevance:** Not blocking for v1. Note for future venue-based features.

### Pitfall 10: Venues Extend Beyond the Expected List

**What goes wrong:** PROJECT.md lists 3 venues (Muzeum Josefa Hoffmanna, Uměleckoprůmyslové muzeum, Pražákův palác). The actual site has at least 7.

**Evidence — complete venue list from all 5 pages:**

| Venue | Sub-location | Pages |
|-------|-------------|-------|
| Muzeum Josefa Hoffmanna | — | 1, 4, 5 |
| Uměleckoprůmyslové muzeum | — | 1, 2, 3 |
| Pražákův palác | Knihovna | 1, 3 |
| Místodržitelský palác | Besední dům | 4, 5 |
| Jurkovičova vila | — | 3, 5 |
| Káznice | — | 4 |
| Otevřený depozitář | — | 3 |

**Prevention:** Don't hardcode venue lists. Parse the venue text widget (data-id `d2f8856`) as free text. Venues with comma-separated sub-locations (e.g., "Pražákův palác, Knihovna") need the comma escaped in iCal LOCATION (`\,`).

**Detection:** If any event has an empty venue when the listing page shows one, the venue parser doesn't recognize it.

**Phase relevance:** HTML parsing phase. Use flexible text extraction, not venue matching.

### Pitfall 11: HTML Entities and Non-breaking Spaces in Content

**What goes wrong:** Event descriptions contain HTML entities that, if not decoded, appear as literal `&nbsp;`, `&#8230;`, `&amp;` in the calendar.

**Evidence:**
```
HTML: "V&nbsp;rámci celostátní akce..."     → Should be "V rámci..."
HTML: "...výtvarné kreacemi&#8230;"          → Should be "...výtvarné kreacemi…"
HTML: "Story &amp;?"                         → Should be "Story &?"
Non-breaking space: \xa0 (U+00A0)           → Should become regular space
```

**Prevention:** Use BeautifulSoup's `.get_text()` which decodes HTML entities automatically. Then normalize Unicode: replace `\xa0` with regular space. Don't use regex-based HTML stripping (misses entities).

**Detection:** Search output .ics for `&nbsp;`, `&#`, or `&amp;` — any occurrence means entities aren't decoded.

**Phase relevance:** Text extraction phase. BeautifulSoup handles this if used correctly.

## Minor Pitfalls

### Pitfall 12: Multi-day Date Ranges Have Implicit Year on First Date

**What goes wrong:** "7/7 – 11/7/2026" — the first date `7/7` has no year. The year must be inferred from the second date. A parser that requires year on both dates will fail.

**Prevention:** When parsing `D/M – D/M/YYYY`, apply the year from the second date to the first date. Also verify: if the first month is December and second is January, the first date's year should be one less (cross-year range) — though this is unlikely for gallery events.

**Phase relevance:** Date parsing.

### Pitfall 13: Dot-Separated Minutes (16.30 not 16:30)

**What goes wrong:** Czech time formatting uses a dot for minutes: `16.30 H` not `16:30`. A parser expecting colon-separated time will fail.

**Prevention:** Match both `\d{1,2}:\d{2}` and `\d{1,2}\.\d{2}` in time parsing, or specifically match the dot pattern since that's what this site uses. The `H` suffix is a constant — always present, always uppercase.

**Phase relevance:** Date parsing.

### Pitfall 14: UID Generation for Deduplication on Re-import

**What goes wrong:** Each iCal event needs a globally unique `UID` field. If UIDs are random (e.g., UUID4), re-importing the .ics file creates duplicate events in the user's calendar. If UIDs are deterministic but based on content that changes (like description text), the same event gets a new UID when the gallery updates the description.

**Prevention:** Generate UIDs from stable, unique identifiers: the WordPress post ID from the article element (`post-19256` → UID `19256@moravska-galerie.cz`). This is stable across scrapes and unique per event.

**Detection:** Import the .ics file twice. If events duplicate, UIDs aren't deterministic.

**Phase relevance:** iCal generation phase.

### Pitfall 15: "VYPRODÁNO" (Sold Out) Suffix in Titles

**What goes wrong:** Some events have "– VYPRODÁNO" appended to the title, e.g., "LETNÍ ARTCAMP: Legenda o Brtnici – VYPRODÁNO". This is operational status, not part of the event name, and may appear/disappear between scrapes.

**Prevention:** For v1, preserve the title as-is including the sold-out status — it's useful information for the user. But use the post ID (not the title) for UID generation, since "VYPRODÁNO" may be added after the event was first scraped.

**Phase relevance:** Minor concern. Note for UID strategy.

### Pitfall 16: Elementor Template Updates Can Break Selectors

**What goes wrong:** The event cards use an Elementor loop template (ID 1575) with consistent widget data-ids (`fe5263e` for date, `d2f8856` for venue, etc.). If the gallery redesigns the template, all data-ids change simultaneously.

**Prevention:**
1. Use the data-id selectors (they're the most stable for Elementor templates)
2. Add a "canary check": verify the first article has the expected widget structure before processing. If the structure doesn't match, fail loudly rather than producing garbage
3. Keep selectors in a config/constants section for easy updates

**Detection:** If the scraper returns articles with all-empty fields, the template has changed.

**Phase relevance:** Maintenance concern. Build validation into the scraping phase.

### Pitfall 17: iCal Commas in LOCATION Field

**What goes wrong:** Several venues contain commas: "Pražákův palác, Knihovna" and "Místodržitelský palác, Besední dům". Per RFC 5545, commas in text values must be escaped as `\,`. Unescaped commas can cause parsers to misinterpret the field.

**Prevention:** The `icalendar` Python library handles this automatically — verified in testing: `LOCATION:Místodržitelský palác\, Besední dům`. Use the library's `.add('location', text)` method; don't construct raw iCal strings manually.

**Detection:** Open the .ics in a text editor and search for unescaped commas in LOCATION lines.

**Phase relevance:** iCal generation. Use the library correctly and this is a non-issue.

### Pitfall 18: Multi-day Events With Time Ranges → Calendar Representation

**What goes wrong:** "13/7 – 17/7/2026, 9–16 H" is a 5-day camp running 9:00-16:00 each day. There's no single iCal representation that cleanly shows "9-16 each day for 5 days" — DTSTART to DTEND would show as one continuous 5-day block.

**Prevention:** Design decision needed:
- **Option A (recommended for v1):** Create one event spanning the full range (DTSTART Monday 9:00, DTEND Friday 16:00). Calendar apps show this as a multi-day block. Add "Daily: 9–16 H" in description.
- **Option B:** Create 5 separate daily events (Mon-Fri, each 9:00-16:00). More accurate but clutters the calendar with near-duplicates.
- **Option C:** Create one all-day event (DATE type, not DATETIME) spanning the range. Loses the time info.

**Phase relevance:** iCal generation phase. Requires design decision.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| HTML scraping setup | Pitfall 3 (REST API trap), Pitfall 7 (CTA vs title) | Target specific Elementor data-ids, not generic selectors |
| Date/time parsing | Pitfalls 1, 2, 12, 13 (format complexity) | Build complete format list from day one; log unparsable dates |
| Multi-day events | Pitfalls 8, 18 (time slots vs ranges) | Make explicit design decisions before coding |
| iCal generation | Pitfalls 4, 5, 14, 17 (timezone, duration, UIDs) | Add VTIMEZONE, set default duration, use post-ID UIDs |
| Pagination | Pitfall 6 (redirect loop) | Parse pagination nav, track seen post IDs |
| Text extraction | Pitfall 11 (HTML entities) | Use BeautifulSoup `.get_text()`, normalize Unicode |
| Maintenance | Pitfall 16 (template changes) | Validate page structure before processing |

## Reliable Selectors (Verified Across All 28 Events)

The Elementor loop template (ID 1575) uses these **consistent** data-ids on every event card across all 5 pages:

| Data | Selector | Widget Type |
|------|----------|-------------|
| Event image + link | `[data-id="491434eb"]` | `theme-post-featured-image` |
| CTA/action text | `[data-id="87e5159"]` | `heading.default` |
| Event title | `[data-id="ff31590"]` | `theme-post-title` |
| Date/time | `[data-id="fe5263e"]` | `text-editor.default` |
| Venue | `[data-id="d2f8856"]` | `text-editor.default` |
| Categories | `[data-id="aca18d5"]` | `heading.default` |
| Description | `[data-id="16d0837"]` | `text-editor.default` |

This is the most reliable scraping strategy. Alternative: use widget-type order within `<article>` elements, but data-id is more precise.

## Sources

- **Live site inspection:** All 5 pages of moravska-galerie.cz/program/deti-a-rodiny/ (2026-03-31)
- **WP REST API:** /wp-json/wp/v2/posts, /wp-json/wp/v2/categories, /wp-json/ root
- **robots.txt:** No restrictions on /program/ path
- **HTTP headers:** nginx/1.22.1, PHP/7.4.33, charset=UTF-8
- **icalendar library testing:** v7.0.3, VTIMEZONE generation, Czech character handling, comma escaping
- **Confidence:** HIGH — all findings verified against live site data
