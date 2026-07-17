"""Tests for VIDA! extractor module."""

from datetime import date, datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from cal_scraper.sites.vida.extractor import (
    DEFAULT_VENUE,
    extract_events_from_listing,
    extract_program_from_calendar,
)

PRAGUE_TZ = ZoneInfo("Europe/Prague")

# All fixture dates are in 2026.  Freeze "today" to 2026-01-01 so they
# remain in the future regardless of when the test suite actually runs.
_real_datetime = datetime


class _FrozenDatetime(_real_datetime):
    """datetime subclass whose .now() always returns 2026-01-01."""

    @classmethod
    def now(cls, tz=None):
        return _real_datetime(2026, 1, 1, 0, 0, tzinfo=tz)


@pytest.fixture(autouse=True)
def _freeze_today():
    with patch(
        "cal_scraper.sites.vida.extractor.datetime", _FrozenDatetime
    ):
        yield


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

def _card(title, date_text, description="Test description", href="/doprovodny-program/test"):
    """Build a realistic VIDA program-item card."""
    return f"""
    <div class="program-item col-md-6 col-lg-4 mb-4">
      <a class="dla p-3 h-100" href="{href}">
        <picture><img src="/images/test.jpg" alt="Test" /></picture>
        <div class="pro-detail pt-3">
          <h3>{title}</h3>
          <p class="work-excerpt">{description}</p>
          <p>{date_text}</p>
        </div>
      </a>
    </div>
    """


def _page(*cards):
    return f"<html><body>{''.join(cards)}</body></html>"


# ---------------------------------------------------------------------------
# Event listing tests
# ---------------------------------------------------------------------------


class TestExtractEventsFromListing:
    """Tests for extract_events_from_listing."""

    def test_parse_standard_card(self):
        """Parse a standard event card with title, date, description, URL."""
        html = _page(_card("Rodinná neděle", "neděle 14. 6. 2026, 10:00"))
        events = extract_events_from_listing([html])

        assert len(events) == 1
        ev = events[0]
        assert ev.title == "Rodinná neděle"
        assert ev.dtstart == datetime(2026, 6, 14, 10, 0, tzinfo=PRAGUE_TZ)
        assert ev.description == "Test description"
        assert ev.url == "http://vida.cz/doprovodny-program/test"

    def test_card_with_brno_location_kept(self):
        """Card with location suffix containing 'Brno' is kept; location used as venue."""
        html = _page(_card(
            "Věda v parku",
            "sobota 20. 6. 2026, 14:00, Park Lužánky, Brno",
        ))
        events = extract_events_from_listing([html])

        assert len(events) == 1
        assert events[0].venue == "Park Lužánky, Brno"

    def test_card_with_non_brno_location_skipped(self):
        """Card with non-Brno location suffix is skipped."""
        html = _page(_card(
            "Věda v Olomouci",
            "sobota 20. 6. 2026, 14:00, Olomouc",
        ))
        events = extract_events_from_listing([html])

        assert len(events) == 0

    def test_after_dark_event_skipped(self):
        """After Dark events are filtered out (case-insensitive)."""
        html = _page(_card("VIDA! After Dark", "pátek 19. 6. 2026, 19:00"))
        events = extract_events_from_listing([html])

        assert len(events) == 0

    def test_after_dark_case_insensitive(self):
        """After Dark filter is case-insensitive."""
        html = _page(_card("Speciální after dark noc", "pátek 19. 6. 2026, 19:00"))
        events = extract_events_from_listing([html])

        assert len(events) == 0

    def test_multiple_cards_on_one_page(self):
        """Multiple cards on a single page are all extracted."""
        html = _page(
            _card("Event A", "sobota 13. 6. 2026, 10:00"),
            _card("Event B", "neděle 14. 6. 2026, 14:00"),
            _card("Event C", "pondělí 15. 6. 2026, 16:00"),
        )
        events = extract_events_from_listing([html])

        assert len(events) == 3
        titles = {e.title for e in events}
        assert titles == {"Event A", "Event B", "Event C"}

    def test_date_without_time_defaults_to_10(self):
        """Date without time component defaults to 10:00."""
        html = _page(_card("Celý den", "neděle 14. 6. 2026"))
        events = extract_events_from_listing([html])

        assert len(events) == 1
        assert events[0].dtstart == datetime(2026, 6, 14, 10, 0, tzinfo=PRAGUE_TZ)

    def test_dtend_is_dtstart_plus_2_hours(self):
        """dtend is dtstart + 2 hours."""
        html = _page(_card("Dvouhodinová", "neděle 14. 6. 2026, 10:00"))
        events = extract_events_from_listing([html])

        assert len(events) == 1
        assert events[0].dtend == events[0].dtstart + timedelta(hours=2)

    def test_past_events_are_skipped(self):
        """Events with dates in the past are not included."""
        html = _page(_card("Staré", "pondělí 1. 1. 2020, 10:00"))
        events = extract_events_from_listing([html])

        assert len(events) == 0

    def test_default_venue_when_no_location_suffix(self):
        """Default VIDA! venue is used when no location suffix."""
        html = _page(_card("Běžná akce", "sobota 13. 6. 2026, 10:00"))
        events = extract_events_from_listing([html])

        assert len(events) == 1
        assert events[0].venue == DEFAULT_VENUE

    def test_all_day_is_false(self):
        """Events are never all-day."""
        html = _page(_card("Akce", "sobota 13. 6. 2026, 10:00"))
        events = extract_events_from_listing([html])

        assert events[0].all_day is False

    def test_multiple_pages(self):
        """Events from multiple pages are combined."""
        page1 = _page(_card("Event A", "sobota 13. 6. 2026, 10:00"))
        page2 = _page(_card("Event B", "neděle 14. 6. 2026, 14:00"))

        events = extract_events_from_listing([page1, page2])

        assert len(events) == 2

    def test_absolute_url_preserved(self):
        """Absolute URLs are preserved as-is."""
        html = _page(_card(
            "Ext Event", "sobota 13. 6. 2026, 10:00",
            href="http://vida.cz/doprovodny-program/ext",
        ))
        events = extract_events_from_listing([html])

        assert events[0].url == "http://vida.cz/doprovodny-program/ext"

    def test_missing_program_item_structure_raises(self):
        """Missing program cards is treated as structural breakage."""
        with pytest.raises(RuntimeError, match="div.program-item"):
            extract_events_from_listing(["<html><body><p>empty</p></body></html>"])

    def test_cards_present_but_no_matching_future_events_returns_empty(self):
        """Cards may exist even when no future/matching events are extracted."""
        html = _page(
            _card("VIDA! After Dark", "pátek 19. 6. 2026, 19:00"),
            _card("Minulá akce", "pondělí 1. 1. 2020, 10:00"),
        )
        events = extract_events_from_listing([html])
        assert events == []


# ---------------------------------------------------------------------------
# Daily program endpoint tests
# ---------------------------------------------------------------------------


class TestExtractProgramFromCalendar:
    """Tests for extract_program_from_calendar."""

    def test_extracts_calendar_items(self):
        """Calendar item maps to Event fields with 45-minute estimated duration."""
        html = """
        <html><body>
          <a class="cal-item mb-2 event-4228" href="/doprovodny-program/poklad-ve-vlnach" data-id="4228">
            <span class="dp-item-date">10:30</span>
            <div class="cal-item-detail cal-item-list px-3">
              <h6>Poklad ve vlnách</h6><span>Prázdninové dílny s pokusy</span>
            </div>
          </a>
        </body></html>
        """
        events = extract_program_from_calendar([(date(2026, 7, 16), html)])

        assert len(events) == 1
        ev = events[0]
        assert ev.title == "Poklad ve vlnách"
        assert ev.dtstart == datetime(2026, 7, 16, 10, 30, tzinfo=PRAGUE_TZ)
        assert ev.dtend == ev.dtstart + timedelta(minutes=45)
        assert ev.estimated_end is True
        assert ev.description == "Prázdninové dílny s pokusy"
        assert ev.url == "https://vida.cz/doprovodny-program/poklad-ve-vlnach"
        assert ev.venue == DEFAULT_VENUE
        assert ev.raw_date == "2026-07-16 10:30"

    def test_after_dark_filtered_by_title_or_category(self):
        """After Dark entries are excluded from daily program feed."""
        html = """
        <html><body>
          <a class="cal-item" href="/doprovodny-program/a"><span class="dp-item-date">12:00</span>
            <div class="cal-item-detail"><h6>VIDA! After Dark</h6><span>Program</span></div></a>
          <a class="cal-item" href="/doprovodny-program/b"><span class="dp-item-date">13:00</span>
            <div class="cal-item-detail"><h6>Jiný program</h6><span>After Dark speciál</span></div></a>
        </body></html>
        """
        events = extract_program_from_calendar([(date(2026, 7, 16), html)])
        assert events == []

    def test_past_date_skipped(self):
        """Calendar entries before today are skipped."""
        html = """
        <html><body>
          <a class="cal-item" href="/doprovodny-program/a"><span class="dp-item-date">12:00</span>
            <div class="cal-item-detail"><h6>Dávno</h6><span>Kat</span></div></a>
        </body></html>
        """
        events = extract_program_from_calendar([(date(2025, 12, 31), html)])
        assert events == []

    def test_empty_day_fragment_yields_no_events(self):
        """Endpoint day with no a.cal-item is a legitimate empty result."""
        events = extract_program_from_calendar([(date(2026, 7, 16), "<html><body></body></html>")])
        assert events == []
