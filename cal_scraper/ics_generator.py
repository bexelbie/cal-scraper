"""ICS calendar generation from Event objects.

Converts cal_scraper Event objects into RFC 5545 .ics calendar output
using the icalendar library.

Public API:
    generate_uid(url)      — deterministic UID from event URL
    event_to_vevent(event) — convert Event to icalendar VEVENT
    events_to_ics(events)  — convert list of Events to .ics string
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta

from icalendar import Calendar
from icalendar import Event as IcsEvent

from cal_scraper.models import DEFAULT_DURATION, PRAGUE_TZ, Event

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_uid(url: str) -> str:
    """Generate a deterministic UID from an event URL.

    Uses SHA-256 hash of the URL (first 16 hex chars) with @cal-scraper suffix.
    If url is empty, hashes the placeholder string "unknown-event".
    """
    source = url if url else "unknown-event"
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
    return f"{digest}@cal-scraper"


def event_to_vevent(event: Event, dtstamp: datetime | None = None) -> IcsEvent:
    """Convert an Event dataclass to an icalendar VEVENT component.

    Timed events (all_day=False) produce DATE-TIME values.
    All-day events (all_day=True) produce DATE values.
    """
    if dtstamp is None:
        dtstamp = datetime.now(tz=PRAGUE_TZ)

    vevent = IcsEvent()

    vevent.add("summary", event.title)
    vevent.add("dtstart", event.dtstart)

    # Calculate dtend
    if event.dtend is not None:
        dtend = event.dtend
    elif event.all_day:
        dtend = event.dtstart + timedelta(days=1)
    else:
        dtend = event.dtstart + DEFAULT_DURATION
    vevent.add("dtend", dtend)

    vevent.add("location", event.venue)

    # Build description with enriched fields
    desc_parts: list[str] = []
    if event.sold_out:
        desc_parts.append("[VYPRODÁNO / SOLD OUT]")
    desc_parts.append(event.description)
    if event.price:
        desc_parts.append(f"Cena: {event.price}")
    if event.reservation:
        desc_parts.append(f"Rezervace: {event.reservation}")
    desc_parts.append(f"Datum: {event.raw_date}")
    description = "\n".join(desc_parts)
    vevent.add("description", description)

    vevent.add("url", event.url)
    vevent.add("uid", generate_uid(event.url))
    vevent.add("dtstamp", dtstamp)

    return vevent


def events_to_ics(
    events: list[Event],
    cal_name: str = "cal-scraper (unofficial)",
    source_url: str = "",
    prodid: str = "-//cal-scraper//unknown//CS",
) -> str:
    """Convert a list of Events to an RFC 5545 .ics calendar string.

    Returns a UTF-8 string suitable for writing to a .ics file.
    Includes VTIMEZONE for Europe/Prague when timed events are present.
    Uses a single DTSTAMP for all events so output is stable within a run.
    """
    cal = Calendar()
    cal.add("prodid", prodid)
    cal.add("version", "2.0")
    cal.add("x-wr-calname", cal_name)
    if source_url:
        cal.add(
            "x-wr-caldesc",
            f"Unofficial scrape of {source_url} — not affiliated with the venue.",
        )

    dtstamp = datetime.now(tz=PRAGUE_TZ)
    for event in events:
        cal.add_component(event_to_vevent(event, dtstamp=dtstamp))

    # Add VTIMEZONE definitions for any referenced timezones
    cal.add_missing_timezones()

    return cal.to_ical().decode("utf-8")
