"""Tests for ICS calendar generation from Event objects."""

from datetime import date, datetime, timedelta

import pytest
from icalendar import Calendar

from cal_scraper.ics_generator import event_to_vevent, events_to_ics, generate_uid
from cal_scraper.models import DEFAULT_DURATION, PRAGUE_TZ, Event


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _timed_event() -> Event:
    """Timed single-day event fixture."""
    return Event(
        title="Workshop keramiky",
        dtstart=datetime(2026, 4, 8, 16, 30, tzinfo=PRAGUE_TZ),
        dtend=datetime(2026, 4, 8, 18, 30, tzinfo=PRAGUE_TZ),
        all_day=False,
        venue="Pražákův palác",
        description="Tvořivá dílna pro děti",
        url="https://www.moravska-galerie.cz/workshop-keramiky/",
        raw_date="8/4/2026, 16.30 H",
    )


def _allday_event() -> Event:
    """All-day multi-day event fixture."""
    return Event(
        title="Letní tábor",
        dtstart=date(2026, 7, 7),
        dtend=date(2026, 7, 12),
        all_day=True,
        venue="Místodržitelský palác",
        description="Týdenní výtvarný tábor",
        url="https://www.moravska-galerie.cz/letni-tabor/",
        raw_date="7/7 – 11/7/2026",
    )


# ---------------------------------------------------------------------------
# ICAL-03: generate_uid — deterministic UID from URL
# ---------------------------------------------------------------------------

class TestGenerateUid:
    """generate_uid produces deterministic, unique UIDs from event URLs."""

    def test_determinism(self):
        """Same URL produces identical UID on repeated calls."""
        url = "https://www.moravska-galerie.cz/event-1/"
        assert generate_uid(url) == generate_uid(url)

    def test_uniqueness(self):
        """Different URLs produce different UIDs."""
        uid1 = generate_uid("https://www.moravska-galerie.cz/event-1/")
        uid2 = generate_uid("https://www.moravska-galerie.cz/event-2/")
        assert uid1 != uid2

    def test_empty_url(self):
        """Empty URL does not crash — returns a valid UID string."""
        uid = generate_uid("")
        assert isinstance(uid, str)
        assert len(uid) > 0

    def test_format_pattern(self):
        """UID matches hex-hash@cal-scraper pattern."""
        import re

        uid = generate_uid("https://example.com/test/")
        assert re.match(r"[a-f0-9]+@cal-scraper", uid)


# ---------------------------------------------------------------------------
# ICAL-02 / ICAL-04 / ICAL-06: event_to_vevent — single event conversion
# ---------------------------------------------------------------------------

class TestEventToVevent:
    """event_to_vevent converts an Event to an icalendar VEVENT."""

    def test_timed_event_dtstart_is_datetime(self):
        """Timed event DTSTART is a datetime (DATE-TIME), not a date."""
        vevent = event_to_vevent(_timed_event())
        dt = vevent.get("dtstart").dt
        assert isinstance(dt, datetime)

    def test_allday_event_dtstart_is_date(self):
        """All-day event DTSTART is a date (DATE), not datetime."""
        vevent = event_to_vevent(_allday_event())
        dt = vevent.get("dtstart").dt
        assert isinstance(dt, date) and not isinstance(dt, datetime)

    def test_summary_mapping(self):
        vevent = event_to_vevent(_timed_event())
        assert str(vevent.get("summary")) == "Workshop keramiky"

    def test_location_mapping(self):
        vevent = event_to_vevent(_timed_event())
        assert str(vevent.get("location")) == "Pražákův palác"

    def test_url_mapping(self):
        vevent = event_to_vevent(_timed_event())
        assert str(vevent.get("url")) == "https://www.moravska-galerie.cz/workshop-keramiky/"

    def test_uid_mapping(self):
        vevent = event_to_vevent(_timed_event())
        uid = str(vevent.get("uid"))
        expected_uid = generate_uid("https://www.moravska-galerie.cz/workshop-keramiky/")
        assert uid == expected_uid

    def test_dtstamp_present(self):
        vevent = event_to_vevent(_timed_event())
        assert vevent.get("dtstamp") is not None

    def test_description_includes_event_text(self):
        vevent = event_to_vevent(_timed_event())
        desc = str(vevent.get("description"))
        assert "Tvořivá dílna pro děti" in desc

    def test_description_includes_raw_date(self):
        vevent = event_to_vevent(_timed_event())
        desc = str(vevent.get("description"))
        assert "Datum: 8/4/2026, 16.30 H" in desc

    def test_timed_event_none_dtend_uses_default_duration(self):
        """When dtend is None for a timed event, uses DEFAULT_DURATION."""
        event = _timed_event()
        event.dtend = None
        vevent = event_to_vevent(event)
        dtend = vevent.get("dtend").dt
        assert dtend == event.dtstart + DEFAULT_DURATION

    def test_allday_event_none_dtend_uses_plus_one_day(self):
        """When dtend is None for an all-day event, uses start + 1 day."""
        event = _allday_event()
        event.dtend = None
        vevent = event_to_vevent(event)
        dtend = vevent.get("dtend").dt
        assert dtend == event.dtstart + timedelta(days=1)


# ---------------------------------------------------------------------------
# ICAL-01 / ICAL-05: events_to_ics — full calendar output
# ---------------------------------------------------------------------------

class TestEventsToIcs:
    """events_to_ics produces a valid iCal calendar string."""

    def test_empty_list_has_vcalendar(self):
        ics = events_to_ics([])
        assert "BEGIN:VCALENDAR" in ics
        assert "END:VCALENDAR" in ics

    def test_empty_list_has_version_and_prodid(self):
        ics = events_to_ics([])
        assert "VERSION:2.0" in ics
        assert "PRODID:" in ics

    def test_timed_events_include_vtimezone(self):
        ics = events_to_ics([_timed_event()])
        assert "VTIMEZONE" in ics
        assert "Europe/Prague" in ics

    def test_multiple_events_vevent_count(self):
        events = [_timed_event(), _allday_event()]
        ics = events_to_ics(events)
        assert ics.count("BEGIN:VEVENT") == 2

    def test_multiday_allday_single_vevent(self):
        """Multi-day all-day event produces a single VEVENT."""
        event = _allday_event()
        ics = events_to_ics([event])
        assert ics.count("BEGIN:VEVENT") == 1
