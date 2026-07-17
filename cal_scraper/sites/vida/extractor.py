"""HTML extraction for VIDA! Science Center listing and daily program."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from cal_scraper.models import Event

PRAGUE_TZ = ZoneInfo("Europe/Prague")
BASE_URL = "http://vida.cz"
DEFAULT_VENUE = "VIDA! science center, Křížkovského 554/12, 603 00 Brno"

_EVENT_DATE_RE = re.compile(
    r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})[,\s]*(\d{1,2}:\d{2})?(?:[,\s]+(.+))?"
)

def extract_events_from_listing(pages: list[str]) -> list[Event]:
    """Extract events from paginated listing HTML pages."""
    today = datetime.now(tz=PRAGUE_TZ).date()
    events: list[Event] = []
    has_program_items = False

    for html in pages:
        soup = BeautifulSoup(html, "lxml")
        cards = soup.select("div.program-item")
        if cards:
            has_program_items = True
        for card in cards:
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

    if not has_program_items:
        raise RuntimeError(
            "VIDA listing structure changed: missing 'div.program-item' cards"
        )

    return events


def extract_program_from_calendar(days: list[tuple[date, str]]) -> list[Event]:
    """Extract timed events from VIDA's daily calendar endpoint fragments."""
    today = datetime.now(tz=PRAGUE_TZ).date()
    events: list[Event] = []
    for day, html in days:
        soup = BeautifulSoup(html, "lxml")
        for item in soup.select("a.cal-item"):
            time_el = item.select_one("span.dp-item-date")
            title_el = item.select_one("h6")
            if time_el is None or title_el is None:
                continue

            time_text = time_el.get_text(strip=True)
            match = re.fullmatch(r"(\d{1,2}):(\d{2})", time_text)
            if not match:
                continue

            hour, minute = int(match.group(1)), int(match.group(2))
            title = title_el.get_text(strip=True)
            category_el = item.select_one("div.cal-item-detail span")
            category = category_el.get_text(strip=True) if category_el else ""

            if "after dark" in title.lower() or "after dark" in category.lower():
                continue

            dtstart = datetime(day.year, day.month, day.day, hour, minute, tzinfo=PRAGUE_TZ)
            if dtstart.date() < today:
                continue

            href = item.get("href", "").strip()
            if href.startswith("/"):
                url = f"https://vida.cz{href}"
            else:
                url = href

            # ponytail: 45-minute duration is an estimate; endpoint has no end times (detail page has precise duration).
            dtend = dtstart + timedelta(minutes=45)
            events.append(
                Event(
                    title=title,
                    dtstart=dtstart,
                    dtend=dtend,
                    all_day=False,
                    venue=DEFAULT_VENUE,
                    description=category,
                    url=url,
                    raw_date=f"{day.isoformat()} {hour:02d}:{minute:02d}",
                    price="",
                    reservation="",
                    sold_out=False,
                    estimated_end=True,
                )
            )

    return events
