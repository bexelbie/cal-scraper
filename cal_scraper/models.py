"""Data models for cal-scraper pipeline."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

PRAGUE_TZ = ZoneInfo("Europe/Prague")
DEFAULT_DURATION = timedelta(hours=2)  # D-01: default event duration when only start time given


@dataclass
class ParsedDate:
    """Result of parsing a Czech date string from the gallery site.

    dtstart: timezone-aware datetime for timed events, or date for all-day events
    dtend: timezone-aware datetime/date for end, or None to use DEFAULT_DURATION
    all_day: True if this is an all-day event (no time component)
    raw_text: original date string for debugging and description inclusion
    """

    dtstart: datetime | date
    dtend: datetime | date | None
    all_day: bool
    raw_text: str


@dataclass
class Event:
    """Fully parsed event ready for ICS generation.

    Populated by the scraper (Phase 2) using ParsedDate from the date parser.
    Consumed by the ICS builder (Phase 3).
    """

    title: str
    dtstart: datetime | date
    dtend: datetime | date | None
    all_day: bool
    venue: str
    description: str
    url: str
    raw_date: str
