"""Tests for VIDA! extractor module."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


from cal_scraper.sites.vida.extractor import (
    extract_events_from_listing,
    extract_workshops,
    DEFAULT_VENUE,
)

PRAGUE_TZ = ZoneInfo("Europe/Prague")


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


# ---------------------------------------------------------------------------
# Workshop tests
# ---------------------------------------------------------------------------


class TestExtractWorkshops:
    """Tests for extract_workshops."""

    WORKSHOP_HTML = """
    <html><body>
    <h1>Labodílny</h1>
    <p>Přijďte s dětmi na víkendové laboratorní dílny, kde si vyzkoušíte zajímavé pokusy.</p>
    <p>pátek 3. 4. 2026 / 12:00</p>
    <p>pátek 3. 4. 2026 / 14:00</p>
    <p>sobota 4. 4. 2026 / 12:00</p>
    </body></html>
    """

    def test_parse_workshop_timeslots(self):
        """Workshop dates with / separator are parsed correctly."""
        events = extract_workshops(self.WORKSHOP_HTML)

        assert len(events) == 3
        assert events[0].dtstart == datetime(2026, 4, 3, 12, 0, tzinfo=PRAGUE_TZ)
        assert events[1].dtstart == datetime(2026, 4, 3, 14, 0, tzinfo=PRAGUE_TZ)
        assert events[2].dtstart == datetime(2026, 4, 4, 12, 0, tzinfo=PRAGUE_TZ)

    def test_workshop_duration_90_minutes(self):
        """Workshop duration is 90 minutes."""
        events = extract_workshops(self.WORKSHOP_HTML)

        for ev in events:
            assert ev.dtend == ev.dtstart + timedelta(minutes=90)

    def test_workshop_title(self):
        """Workshop title is 'VIDA! Labodílna'."""
        events = extract_workshops(self.WORKSHOP_HTML)

        for ev in events:
            assert ev.title == "VIDA! Labodílna"

    def test_workshop_venue(self):
        """Workshop venue is the default VIDA! venue."""
        events = extract_workshops(self.WORKSHOP_HTML)

        for ev in events:
            assert ev.venue == DEFAULT_VENUE

    def test_workshop_url(self):
        """Workshop URL points to labodilny page."""
        events = extract_workshops(self.WORKSHOP_HTML)

        for ev in events:
            assert ev.url == "http://vida.cz/doprovodny-program/labodilny"

    def test_past_workshop_dates_skipped(self):
        """Past workshop dates are excluded."""
        html = """
        <html><body>
        <p>pátek 1. 1. 2020 / 12:00</p>
        <p>sobota 2. 1. 2020 / 14:00</p>
        </body></html>
        """
        events = extract_workshops(html)

        assert len(events) == 0

    def test_workshop_description_extracted(self):
        """Workshop description is extracted from page content."""
        events = extract_workshops(self.WORKSHOP_HTML)

        assert len(events) > 0
        # The long paragraph should be used as description
        assert "laboratorní dílny" in events[0].description

    def test_workshop_default_description(self):
        """Fallback description when no descriptive text found."""
        html = """
        <html><body>
        <p>pátek 3. 4. 2026 / 12:00</p>
        </body></html>
        """
        events = extract_workshops(html)

        assert len(events) == 1
        assert events[0].description == "Víkendová laboratorní dílna pro děti"
