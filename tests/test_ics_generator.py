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

    def test_sold_out_in_description(self):
        """sold_out=True adds [VYPRODÁNO / SOLD OUT] to description (ENHN-01)."""
        event = _timed_event()
        event.sold_out = True
        vevent = event_to_vevent(event)
        desc = str(vevent.get("description"))
        assert "[VYPRODÁNO / SOLD OUT]" in desc

    def test_no_sold_out_in_description(self):
        """sold_out=False does not add sold-out marker to description."""
        event = _timed_event()
        event.sold_out = False
        vevent = event_to_vevent(event)
        desc = str(vevent.get("description"))
        assert "VYPRODÁNO" not in desc

    def test_price_in_description(self):
        """Event with price includes 'Cena:' line in description (DETL-02)."""
        event = _timed_event()
        event.price = "V – 100 Kč"
        vevent = event_to_vevent(event)
        desc = str(vevent.get("description"))
        assert "Cena: V – 100 Kč" in desc

    def test_no_price_in_description(self):
        """Event without price does not include 'Cena:' in description."""
        event = _timed_event()
        event.price = ""
        vevent = event_to_vevent(event)
        desc = str(vevent.get("description"))
        assert "Cena:" not in desc

    def test_reservation_in_description(self):
        """Event with reservation includes 'Rezervace:' in description (DETL-03)."""
        event = _timed_event()
        event.reservation = "info@gallery.cz, 724 543 722"
        vevent = event_to_vevent(event)
        desc = str(vevent.get("description"))
        assert "Rezervace: info@gallery.cz, 724 543 722" in desc

    def test_no_reservation_in_description(self):
        """Event without reservation does not include 'Rezervace:' in description."""
        event = _timed_event()
        event.reservation = ""
        vevent = event_to_vevent(event)
        desc = str(vevent.get("description"))
        assert "Rezervace:" not in desc

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


# ---------------------------------------------------------------------------
# Round-trip: generate ICS → parse back → verify structure
# ---------------------------------------------------------------------------

class TestIcsRoundTrip:
    """Parse generated ICS back with icalendar and verify structure."""

    @staticmethod
    def _build_mixed_events() -> list[Event]:
        """Three events: timed single-day, all-day single-day, multi-day all-day."""
        timed = Event(
            title="Výtvarná dílna",
            dtstart=datetime(2026, 5, 10, 14, 0, tzinfo=PRAGUE_TZ),
            dtend=datetime(2026, 5, 10, 16, 0, tzinfo=PRAGUE_TZ),
            all_day=False,
            venue="Uměleckoprůmyslové muzeum",
            description="Odpolední workshop",
            url="https://www.moravska-galerie.cz/vytvarna-dilna/",
            raw_date="10/5/2026, 14 H",
        )
        allday_single = Event(
            title="Den otevřených dveří",
            dtstart=date(2026, 6, 1),
            dtend=None,
            all_day=True,
            venue="Pražákův palác",
            description="Vstup zdarma",
            url="https://www.moravska-galerie.cz/den-otevrenych-dveri/",
            raw_date="1/6/2026",
        )
        allday_multi = Event(
            title="Letní výtvarný tábor",
            dtstart=date(2026, 7, 13),
            dtend=date(2026, 7, 18),
            all_day=True,
            venue="Místodržitelský palác",
            description="Pětidenní kreativní tábor",
            url="https://www.moravska-galerie.cz/letni-tabor-2/",
            raw_date="13/7 – 17/7/2026",
        )
        return [timed, allday_single, allday_multi]

    def test_round_trip_vevent_count(self):
        """Parsed calendar contains exactly 3 VEVENTs."""
        events = self._build_mixed_events()
        ics = events_to_ics(events)
        cal = Calendar.from_ical(ics)
        vevents = [c for c in cal.walk() if c.name == "VEVENT"]
        assert len(vevents) == 3

    def test_round_trip_timed_event_types(self):
        """Timed event round-trips as datetime for DTSTART and DTEND."""
        events = self._build_mixed_events()
        ics = events_to_ics(events)
        cal = Calendar.from_ical(ics)
        vevents = [c for c in cal.walk() if c.name == "VEVENT"]
        # Find the timed event by summary
        timed = [v for v in vevents if str(v.get("summary")) == "Výtvarná dílna"][0]
        assert isinstance(timed.get("dtstart").dt, datetime)
        assert isinstance(timed.get("dtend").dt, datetime)

    def test_round_trip_allday_event_types(self):
        """All-day single-day event round-trips as date for DTSTART and DTEND."""
        events = self._build_mixed_events()
        ics = events_to_ics(events)
        cal = Calendar.from_ical(ics)
        vevents = [c for c in cal.walk() if c.name == "VEVENT"]
        allday = [v for v in vevents if str(v.get("summary")) == "Den otevřených dveří"][0]
        dt = allday.get("dtstart").dt
        assert isinstance(dt, date) and not isinstance(dt, datetime)

    def test_round_trip_multiday_span(self):
        """Multi-day event has correct DTSTART and DTEND range."""
        events = self._build_mixed_events()
        ics = events_to_ics(events)
        cal = Calendar.from_ical(ics)
        vevents = [c for c in cal.walk() if c.name == "VEVENT"]
        multi = [v for v in vevents if str(v.get("summary")) == "Letní výtvarný tábor"][0]
        assert multi.get("dtstart").dt == date(2026, 7, 13)
        assert multi.get("dtend").dt == date(2026, 7, 18)

    def test_round_trip_required_fields(self):
        """All VEVENTs have non-empty SUMMARY, LOCATION, UID, DTSTAMP."""
        events = self._build_mixed_events()
        ics = events_to_ics(events)
        cal = Calendar.from_ical(ics)
        vevents = [c for c in cal.walk() if c.name == "VEVENT"]
        for vevent in vevents:
            assert str(vevent.get("summary")), "SUMMARY must be non-empty"
            assert str(vevent.get("location")), "LOCATION must be non-empty"
            assert str(vevent.get("uid")), "UID must be non-empty"
            assert vevent.get("dtstamp") is not None, "DTSTAMP must be present"

    def test_round_trip_vtimezone_present(self):
        """Generated ICS with timed events contains VTIMEZONE for Europe/Prague."""
        events = self._build_mixed_events()
        ics = events_to_ics(events)
        assert "VTIMEZONE" in ics
        assert "Europe/Prague" in ics

    def test_round_trip_prodid_present(self):
        """Parsed calendar has PRODID."""
        events = self._build_mixed_events()
        ics = events_to_ics(events)
        cal = Calendar.from_ical(ics)
        assert cal.get("prodid") is not None
