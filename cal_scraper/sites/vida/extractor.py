"""HTML extraction for VIDA! Science Center events and workshops."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from cal_scraper.models import Event

PRAGUE_TZ = ZoneInfo("Europe/Prague")
BASE_URL = "http://vida.cz"
DEFAULT_VENUE = "VIDA! science center, Křížkovského 554/12, 603 00 Brno"

_EVENT_DATE_RE = re.compile(
    r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})[,\s]*(\d{1,2}:\d{2})?(?:[,\s]+(.+))?"
)

_WORKSHOP_DATE_RE = re.compile(
    r"[a-záčďéěíňóřšťúůýž]+\s+"
    r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})\s*[/,]\s*(\d{1,2}):(\d{2})",
    re.IGNORECASE,
)


def extract_events_from_listing(pages: list[str]) -> list[Event]:
    """Extract events from paginated listing HTML pages."""
    today = datetime.now(tz=PRAGUE_TZ).date()
    events: list[Event] = []

    for html in pages:
        soup = BeautifulSoup(html, "lxml")
        for card in soup.select("div.program-item"):
            h3 = card.select_one("h3")
            if not h3:
                continue
            title = h3.get_text(strip=True)

            # Filter: skip After Dark events
            if "after dark" in title.lower():
                continue

            excerpt_el = card.select_one("p.work-excerpt")
            description = excerpt_el.get_text(strip=True) if excerpt_el else ""

            link = card.select_one("a.dla")
            href = link.get("href", "") if link else ""
            if href and not href.startswith("http"):
                href = BASE_URL + href
            url = href

            # Date/time/location from last <p> in div.pro-detail
            detail_div = card.select_one("div.pro-detail")
            date_p_list = detail_div.select("p") if detail_div else []
            # Last <p> that is NOT the excerpt
            date_text = ""
            for p in reversed(date_p_list):
                if "work-excerpt" not in (p.get("class") or []):
                    date_text = p.get_text(strip=True)
                    break

            m = _EVENT_DATE_RE.search(date_text)
            if not m:
                continue

            day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
            time_str = m.group(4)
            location_suffix = m.group(5)

            # Filter: non-Brno location
            if location_suffix and "brno" not in location_suffix.lower():
                continue

            # Venue
            if location_suffix and "brno" in location_suffix.lower():
                venue = location_suffix.strip()
            else:
                venue = DEFAULT_VENUE

            # Build datetime
            if time_str:
                hour, minute = (int(x) for x in time_str.split(":"))
            else:
                hour, minute = 10, 0

            dtstart = datetime(year, month, day, hour, minute, tzinfo=PRAGUE_TZ)

            # Skip past events
            if dtstart.date() < today:
                continue

            dtend = dtstart + timedelta(hours=2)

            events.append(
                Event(
                    title=title,
                    dtstart=dtstart,
                    dtend=dtend,
                    all_day=False,
                    venue=venue,
                    description=description,
                    url=url,
                    raw_date=date_text,
                    price="",
                    reservation="",
                    sold_out=False,
                    estimated_end=True,
                )
            )

    return events


def extract_workshops(html: str) -> list[Event]:
    """Extract lab workshop events from the workshops page."""
    today = datetime.now(tz=PRAGUE_TZ).date()
    events: list[Event] = []

    # Try to extract a description from the page
    soup = BeautifulSoup(html, "lxml")
    desc_text = ""
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        # Heuristic: pick the first paragraph with enough text that isn't a date
        if len(text) > 40 and not _WORKSHOP_DATE_RE.search(text):
            desc_text = text
            break
    if not desc_text:
        desc_text = "Víkendová laboratorní dílna pro děti"

    for m in _WORKSHOP_DATE_RE.finditer(html):
        day = int(m.group(1))
        month = int(m.group(2))
        year = int(m.group(3))
        hour = int(m.group(4))
        minute = int(m.group(5))

        dtstart = datetime(year, month, day, hour, minute, tzinfo=PRAGUE_TZ)

        if dtstart.date() < today:
            continue

        dtend = dtstart + timedelta(minutes=90)

        events.append(
            Event(
                title="VIDA! Labodílna",
                dtstart=dtstart,
                dtend=dtend,
                all_day=False,
                venue=DEFAULT_VENUE,
                description=desc_text,
                url=f"{BASE_URL}/doprovodny-program/labodilny",
                raw_date=m.group(0),
                price="",
                reservation="",
                sold_out=False,
                estimated_end=True,
            )
        )

    return events
