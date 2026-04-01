"""IKEA Brno — kids events scraper."""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from cal_scraper.models import Event
from cal_scraper.sites import SiteConfig, register

logger = logging.getLogger(__name__)

PRAGUE_TZ = ZoneInfo("Europe/Prague")
SOURCE_URL = "https://www.ikea.com/cz/cs/stores/brno/"

SITE_CONFIG = SiteConfig(
    name="ikea-brno",
    cal_name="IKEA Brno – Akce pro děti (unofficial)",
    source_url=SOURCE_URL,
    prodid="-//cal-scraper//ikea-brno//CS",
    default_filename="ikea-brno.ics",
)
register(SITE_CONFIG)


def _strip_html(text: str) -> str:
    """Remove HTML tags from a string."""
    return re.sub(r"<[^>]+>", "", text)


def _build_venue(event: dict) -> str:
    """Build venue string from event location data."""
    loc = event.get("location", {}).get("store", {})
    parts = [
        loc.get("storeName", ""),
        loc.get("street", ""),
        loc.get("city", ""),
    ]
    return ", ".join(p for p in parts if p)


def _build_description(details: dict) -> str:
    """Build plain-text description from event details."""
    intro = _strip_html(details.get("eventIntroduction", "") or "")
    desc = _strip_html(details.get("eventDescription", "") or "")
    if intro and desc:
        return f"{intro}\n\n{desc}"
    return intro or desc


def _build_url(event: dict) -> str:
    """Build event URL from actualUrl or fall back to source URL."""
    actual = event.get("actualUrl", "")
    if actual:
        return "https://www.ikea.com" + actual
    return SOURCE_URL


def _format_price(event: dict) -> str:
    """Format price from event-level price data."""
    price_info = event.get("price", {})
    amount = price_info.get("amount", 0)
    if amount and amount > 0:
        currency = price_info.get("currencyCode") or "CZK"
        return f"{amount:g} {currency}"
    return "zdarma"


def _format_reservation(slot: dict) -> str:
    """Format reservation status from slot data."""
    if slot.get("registrationClosed"):
        return "Registrace uzavřena"
    reg = slot.get("registrationSettings", {})
    max_reg = reg.get("maxRegistrationCount", 0)
    if max_reg and max_reg > 0:
        current = slot.get("currentRegistrationCount", 0)
        return f"Registrace otevřena ({current}/{max_reg})"
    return ""


def _is_sold_out(slot: dict) -> bool:
    """Check if a slot is sold out."""
    reg = slot.get("registrationSettings", {})
    max_reg = reg.get("maxRegistrationCount", 0)
    return bool(
        slot.get("registrationClosed")
        and max_reg > 0
        and slot.get("currentRegistrationCount", 0) >= max_reg
    )


def _event_duration_days(slot: dict) -> int:
    """Calculate event duration in days from UTC timestamps."""
    utc_start = slot.get("utcStartDate", 0)
    utc_end = slot.get("utcEndDate", 0)
    if not utc_start or not utc_end:
        return 0
    start_dt = datetime.fromtimestamp(utc_start, tz=PRAGUE_TZ)
    end_dt = datetime.fromtimestamp(utc_end, tz=PRAGUE_TZ)
    return (end_dt.date() - start_dt.date()).days


def _slot_to_event(event: dict, slot: dict, details: dict) -> Event:
    """Convert a single timeslot into an Event object."""
    utc_start = slot["utcStartDate"]
    utc_end = slot["utcEndDate"]
    start_dt = datetime.fromtimestamp(utc_start, tz=PRAGUE_TZ)
    end_dt = datetime.fromtimestamp(utc_end, tz=PRAGUE_TZ)
    duration_days = (end_dt.date() - start_dt.date()).days

    if duration_days > 0:
        # Multi-day event → all-day with exclusive end date
        dtstart: datetime | date = start_dt.date()
        dtend: datetime | date | None = end_dt.date() + timedelta(days=1)
        all_day = True
    else:
        # Same-day timed event
        dtstart = start_dt
        dtend = end_dt
        all_day = False

    return Event(
        title=details.get("eventName", ""),
        dtstart=dtstart,
        dtend=dtend,
        all_day=all_day,
        venue=_build_venue(event),
        description=_build_description(details),
        url=_build_url(event),
        raw_date=slot.get("startDate", ""),
        price=_format_price(event),
        reservation=_format_reservation(slot),
        sold_out=_is_sold_out(slot),
    )


def scrape(verbose: bool = False, **kwargs) -> list[Event]:
    """Scrape kids events from IKEA Brno store events API."""
    from cal_scraper.sites.ikea_brno.fetcher import fetch_events
    from cal_scraper.sites.ikea_brno.classifier import filter_kids_events

    raw_events = fetch_events(verbose=verbose)
    kids_events = filter_kids_events(raw_events)

    if verbose:
        logger.info(
            "Filtered %d kids events from %d total",
            len(kids_events),
            len(raw_events),
        )

    events: list[Event] = []
    for ev in kids_events:
        details = ev.get("eventDetails", {}).get("cs", {})
        for slot in ev.get("timeSlots", []):
            events.append(_slot_to_event(ev, slot, details))

    return events
