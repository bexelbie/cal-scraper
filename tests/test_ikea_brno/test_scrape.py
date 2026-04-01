"""Tests for IKEA Brno scrape() pipeline."""

from datetime import date, datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from cal_scraper.sites.ikea_brno import scrape

PRAGUE_TZ = ZoneInfo("Europe/Prague")

# UTC timestamps for a same-day event: 2026-03-19 09:00 → 11:00 UTC
# Prague = UTC+1 in March → 10:00 → 12:00
SAME_DAY_START = 1773910800  # 2026-03-19T09:00:00 UTC
SAME_DAY_END = 1773918000    # 2026-03-19T11:00:00 UTC

# Multi-day event spanning 30 days
MULTI_START = 1773910800       # 2026-03-19
MULTI_END = 1773910800 + 30 * 86400  # 2026-04-18


def _make_raw_event(
    name="Tvoření pro děti",
    intro="Přijďte s dětmi",
    desc="",
    utc_start=SAME_DAY_START,
    utc_end=SAME_DAY_END,
    start_date="2026-03-19T10:00:00",
    price_amount=0,
    reg_closed=False,
    max_reg=0,
    current_reg=0,
    actual_url="/cz/cs/stores/brno/events/test-123/",
    store_name="IKEA Brno",
    street="Skandinávská 1",
    city="Brno",
    extra_slots=None,
):
    """Build a raw API event dict for testing."""
    slots = [
        {
            "utcStartDate": utc_start,
            "utcEndDate": utc_end,
            "startDate": start_date,
            "registrationClosed": reg_closed,
            "registrationSettings": {
                "maxRegistrationCount": max_reg,
            },
            "currentRegistrationCount": current_reg,
        }
    ]
    if extra_slots:
        slots.extend(extra_slots)

    return {
        "eventDetails": {
            "cs": {
                "eventName": name,
                "eventIntroduction": intro,
                "eventDescription": desc,
            }
        },
        "timeSlots": slots,
        "actualUrl": actual_url,
        "price": {"amount": price_amount, "currencyCode": "CZK"},
        "location": {
            "store": {
                "storeName": store_name,
                "street": street,
                "city": city,
            }
        },
    }


def _mock_scrape(raw_events):
    """Patch fetcher and run scrape with given raw events."""
    with patch(
        "cal_scraper.sites.ikea_brno.fetcher.fetch_events",
        return_value=raw_events,
    ):
        return scrape(verbose=False)


class TestScrapeBasic:
    """Basic scrape pipeline tests."""

    def test_single_same_day_event(self):
        """Same-day event produces timed Event."""
        raw = [_make_raw_event()]
        events = _mock_scrape(raw)

        assert len(events) == 1
        ev = events[0]
        assert ev.title == "Tvoření pro děti"
        assert ev.all_day is False
        assert isinstance(ev.dtstart, datetime)
        assert ev.dtstart.tzinfo is not None

    def test_multi_slot_expansion(self):
        """One event with 2 slots produces 2 Events."""
        extra = {
            "utcStartDate": SAME_DAY_START + 86400,
            "utcEndDate": SAME_DAY_END + 86400,
            "startDate": "2026-03-20T10:00:00",
            "registrationClosed": False,
            "registrationSettings": {"maxRegistrationCount": 0},
            "currentRegistrationCount": 0,
        }
        raw = [_make_raw_event(extra_slots=[extra])]
        events = _mock_scrape(raw)

        assert len(events) == 2
        assert events[0].raw_date == "2026-03-19T10:00:00"
        assert events[1].raw_date == "2026-03-20T10:00:00"

    def test_filters_non_kids_events(self):
        """Non-kids events are filtered out."""
        raw = [
            _make_raw_event(name="Tvoření pro děti"),
            _make_raw_event(name="Adult cooking class", intro=""),
        ]
        events = _mock_scrape(raw)
        assert len(events) == 1
        assert events[0].title == "Tvoření pro děti"


class TestAllDayConversion:
    """Tests for multi-day / all-day event conversion."""

    def test_long_event_all_day(self):
        """Event >7 days is converted to all-day with exclusive end."""
        raw = [_make_raw_event(
            name="Småland program pro děti",
            intro="",
            utc_start=MULTI_START,
            utc_end=MULTI_END,
        )]
        events = _mock_scrape(raw)

        assert len(events) == 1
        ev = events[0]
        assert ev.all_day is True
        assert isinstance(ev.dtstart, date)
        assert not isinstance(ev.dtstart, datetime)
        # End should be exclusive: event ends 2026-04-18 → dtend = 2026-04-19
        expected_end = datetime.fromtimestamp(MULTI_END, tz=PRAGUE_TZ).date()
        assert ev.dtend == expected_end + __import__("datetime").timedelta(days=1)

    def test_multi_day_short_span(self):
        """Event spanning 2 days is all-day."""
        two_day_end = SAME_DAY_START + 2 * 86400
        raw = [_make_raw_event(
            name="Víkend pro děti",
            intro="",
            utc_start=SAME_DAY_START,
            utc_end=two_day_end,
        )]
        events = _mock_scrape(raw)

        ev = events[0]
        assert ev.all_day is True
        assert isinstance(ev.dtstart, date)

    def test_same_day_timed(self):
        """Same-day event has timezone-aware datetime."""
        raw = [_make_raw_event()]
        events = _mock_scrape(raw)

        ev = events[0]
        assert ev.all_day is False
        assert isinstance(ev.dtstart, datetime)
        assert ev.dtstart.tzinfo is not None
        # Prague is UTC+1 in March
        assert ev.dtstart.hour == 10


class TestPriceFormatting:
    """Tests for price formatting."""

    def test_free_event(self):
        raw = [_make_raw_event(price_amount=0)]
        events = _mock_scrape(raw)
        assert events[0].price == "zdarma"

    def test_paid_event(self):
        raw = [_make_raw_event(price_amount=99)]
        events = _mock_scrape(raw)
        assert events[0].price == "99 CZK"


class TestReservationStatus:
    """Tests for reservation status formatting."""

    def test_no_registration(self):
        raw = [_make_raw_event()]
        events = _mock_scrape(raw)
        assert events[0].reservation == ""

    def test_registration_open(self):
        raw = [_make_raw_event(max_reg=20, current_reg=5)]
        events = _mock_scrape(raw)
        assert events[0].reservation == "Registrace otevřena (5/20)"

    def test_registration_closed(self):
        raw = [_make_raw_event(reg_closed=True)]
        events = _mock_scrape(raw)
        assert events[0].reservation == "Registrace uzavřena"


class TestSoldOut:
    """Tests for sold_out detection."""

    def test_not_sold_out(self):
        raw = [_make_raw_event()]
        events = _mock_scrape(raw)
        assert events[0].sold_out is False

    def test_sold_out(self):
        raw = [_make_raw_event(reg_closed=True, max_reg=20, current_reg=20)]
        events = _mock_scrape(raw)
        assert events[0].sold_out is True

    def test_closed_but_not_full(self):
        """Closed registration with spots remaining is not sold out."""
        raw = [_make_raw_event(reg_closed=True, max_reg=20, current_reg=5)]
        events = _mock_scrape(raw)
        assert events[0].sold_out is False


class TestUrlConstruction:
    """Tests for URL construction."""

    def test_url_with_actual_url(self):
        raw = [_make_raw_event(actual_url="/cz/cs/stores/brno/events/test/")]
        events = _mock_scrape(raw)
        assert events[0].url == "https://www.ikea.com/cz/cs/stores/brno/events/test/"

    def test_url_fallback(self):
        raw = [_make_raw_event(actual_url="")]
        events = _mock_scrape(raw)
        assert events[0].url == "https://www.ikea.com/cz/cs/stores/brno/"


class TestVenueAndDescription:
    """Tests for venue building and description handling."""

    def test_venue_format(self):
        raw = [_make_raw_event()]
        events = _mock_scrape(raw)
        assert events[0].venue == "IKEA Brno, Skandinávská 1, Brno"

    def test_description_intro_only(self):
        raw = [_make_raw_event(intro="Přijďte s dětmi", desc="")]
        events = _mock_scrape(raw)
        assert events[0].description == "Přijďte s dětmi"

    def test_description_with_both(self):
        raw = [_make_raw_event(intro="Intro text", desc="Detail text")]
        events = _mock_scrape(raw)
        assert events[0].description == "Intro text\n\nDetail text"

    def test_html_stripping(self):
        raw = [_make_raw_event(
            intro="<p>Přijďte <strong>s dětmi</strong></p>",
            desc="<br/>Více info <a href='#'>zde</a>",
        )]
        events = _mock_scrape(raw)
        assert "<" not in events[0].description
        assert "Přijďte s dětmi" in events[0].description
        assert "Více info zde" in events[0].description

    def test_empty_description(self):
        raw = [_make_raw_event(intro="", desc="")]
        events = _mock_scrape(raw)
        assert events[0].description == ""
