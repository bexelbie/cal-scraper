"""HTML show extractor for Hvězdárna Brno weekly programme pages.

Parses date headers and show blocks, filters to public shows only,
and extracts metadata (duration, price, venue, age, ticket links).

Exports:
    extract_events — extract Event list from fetched weekly pages
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta

from bs4 import BeautifulSoup, Tag

from cal_scraper.models import Event, PRAGUE_TZ

logger = logging.getLogger(__name__)

DEFAULT_DURATION = 55  # minutes

CZECH_MONTHS_GENITIVE: dict[str, int] = {
    "ledna": 1,
    "února": 2,
    "března": 3,
    "dubna": 4,
    "května": 5,
    "června": 6,
    "července": 7,
    "srpna": 8,
    "září": 9,
    "října": 10,
    "listopadu": 11,
    "prosince": 12,
}


# ---------------------------------------------------------------------------
# Date parsing helpers
# ---------------------------------------------------------------------------


def _parse_date_header(text: str, year: int) -> date | None:
    """Parse a Czech date header like 'Čtvrtek 2. dubna' into a date.

    Returns None for week headers containing 'týden'.
    """
    if "týden" in text.lower():
        return None

    # Pattern: optional day-name, day number with dot, Czech month genitive
    m = re.search(r"(\d{1,2})\.\s*(\S+)", text)
    if not m:
        return None

    day = int(m.group(1))
    month_word = m.group(2).lower().rstrip(".,")
    month = CZECH_MONTHS_GENITIVE.get(month_word)
    if month is None:
        logger.warning("Unknown Czech month: %r in header %r", month_word, text)
        return None

    return date(year, month, day)


# ---------------------------------------------------------------------------
# Metadata extraction from tecky divs
# ---------------------------------------------------------------------------


def _parse_duration(text: str) -> int | None:
    """Extract minutes from a text like 'délka představení 55 minut'."""
    m = re.search(r"(\d+)\s*minut", text)
    return int(m.group(1)) if m else None


def _parse_show_metadata(desc_div: Tag) -> dict:
    """Extract structured metadata from the tecky divs inside a show block.

    Returns dict with keys: venue, age, duration, price, notes, ticket_url.
    """
    meta: dict = {
        "venue": "",
        "age": "",
        "duration": DEFAULT_DURATION,
        "duration_estimated": True,
        "price": "",
        "notes": [],
        "ticket_url": "",
    }

    tecky = desc_div.select("div.main-program-tecky")
    for i, div in enumerate(tecky):
        text = div.get_text(strip=True)
        lower = text.lower()

        if i == 0 and not any(
            kw in lower for kw in ("vhodné", "délka", "cena:", "3d", "2d", "english")
        ):
            # First tecky is typically the venue
            meta["venue"] = text
        elif "vhodné od" in lower:
            meta["age"] = text
        elif "délka představení" in lower or "délka" in lower:
            parsed = _parse_duration(text)
            if parsed:
                meta["duration"] = parsed
                meta["duration_estimated"] = False
        elif lower.startswith("cena:") or "cena:" in lower:
            meta["price"] = text
        elif "3d" in lower or "2d" in lower:
            meta["notes"].append(text)
        elif "english" in lower:
            meta["notes"].append(text)
        else:
            # Unknown tecky — preserve as note
            meta["notes"].append(text)

    # Ticket link
    ticket_el = desc_div.select_one("a.main-program-vstupenky")
    if ticket_el:
        meta["ticket_url"] = ticket_el.get("href", "")

    return meta


# ---------------------------------------------------------------------------
# Single-page extraction
# ---------------------------------------------------------------------------


def _extract_from_page(html: str, year: int) -> list[Event]:
    """Extract public show events from a single weekly page HTML."""
    soup = BeautifulSoup(html, "lxml")
    events: list[Event] = []
    current_date: date | None = None

    # Walk through all relevant elements in document order
    for el in soup.find_all(["h1", "div"]):
        # Date headers
        if el.name == "h1" and "main-program-datum" in el.get("class", []):
            parsed = _parse_date_header(el.get_text(strip=True), year)
            if parsed is not None:
                current_date = parsed
            continue

        # Show blocks
        if el.name == "div" and "main-program-porad" in el.get("class", []):
            if current_date is None:
                continue

            # Filter: keep only public shows
            typ_el = el.select_one("h4.main-program-typ")
            if typ_el:
                typ_text = typ_el.get_text(strip=True).lower()
                if "školní" in typ_text:
                    continue

            # Time
            time_el = el.select_one("h2.main-program-cas")
            if time_el is None:
                continue
            time_text = time_el.get_text(strip=True)
            time_match = re.match(r"(\d{1,2}):(\d{2})", time_text)
            if not time_match:
                logger.warning("Cannot parse time %r, skipping show", time_text)
                continue
            hour, minute = int(time_match.group(1)), int(time_match.group(2))

            # Title — may be wrapped in <a> or standalone
            title_el = el.select_one("h3.main-program-title")
            if title_el is None:
                continue
            title = title_el.get_text(strip=True)

            # URL from parent <a> if present
            show_url = ""
            parent_a = title_el.find_parent("a")
            if parent_a and parent_a.get("href"):
                href = parent_a["href"]
                if href.startswith("/"):
                    show_url = f"https://www.hvezdarna.cz{href}"
                else:
                    show_url = href

            # Description and metadata
            desc_div = el.select_one("div.main-program-desc")
            meta: dict = {
                "venue": "",
                "age": "",
                "duration": DEFAULT_DURATION,
                "duration_estimated": True,
                "price": "",
                "notes": [],
                "ticket_url": "",
            }
            description_parts: list[str] = []

            if desc_div:
                # Main description paragraph
                p = desc_div.find("p")
                if p:
                    desc_text = p.get_text(strip=True)
                    if desc_text:
                        description_parts.append(desc_text)

                meta = _parse_show_metadata(desc_div)

            # Build description string
            if meta["age"]:
                description_parts.append(meta["age"])
            for note in meta["notes"]:
                description_parts.append(note)
            if meta["ticket_url"]:
                description_parts.append(f"Vstupenky: {meta['ticket_url']}")

            description = "\n".join(description_parts)

            dtstart = datetime(
                current_date.year,
                current_date.month,
                current_date.day,
                hour,
                minute,
                tzinfo=PRAGUE_TZ,
            )
            dtend = dtstart + timedelta(minutes=meta["duration"])

            events.append(
                Event(
                    title=title,
                    dtstart=dtstart,
                    dtend=dtend,
                    all_day=False,
                    venue=meta["venue"],
                    description=description,
                    url=show_url,
                    raw_date=f"{current_date.day}/{current_date.month}/{current_date.year}, {hour}:{minute:02d}",
                    price=meta["price"],
                    estimated_end=meta["duration_estimated"],
                )
            )

    return events


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_events(pages: list[tuple[str, date]]) -> list[Event]:
    """Extract public planetarium events from weekly HTML pages.

    Args:
        pages: List of (html_content, week_start_date) tuples where
               week_start_date is the Monday used in the request URL.

    Deduplicates by (url, dtstart) to handle overlapping week boundaries.
    """
    all_events: list[Event] = []
    for html, week_start in pages:
        year = week_start.year
        all_events.extend(_extract_from_page(html, year))

    # Deduplicate by (url, dtstart) — keep first occurrence
    seen: set[tuple[str, datetime]] = set()
    unique: list[Event] = []
    for ev in all_events:
        key = (ev.url, ev.dtstart)
        if key not in seen:
            seen.add(key)
            unique.append(ev)

    return unique
