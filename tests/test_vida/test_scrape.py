"""Tests for VIDA! scrape orchestration."""

from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo


from cal_scraper.models import Event
from cal_scraper.sites.vida import scrape
from cal_scraper.sites.vida.extractor import DEFAULT_VENUE

PRAGUE_TZ = ZoneInfo("Europe/Prague")


def _make_event(title: str, dtstart: datetime) -> Event:
    return Event(
        title=title,
        dtstart=dtstart,
        dtend=dtstart + timedelta(hours=2),
        all_day=False,
        venue=DEFAULT_VENUE,
        description="desc",
        url="http://vida.cz/test",
        raw_date="test",
        price="",
        reservation="",
        sold_out=False,
    )


class TestScrape:
    """Tests for scrape() orchestration."""

    @patch("cal_scraper.sites.vida.fetcher.fetch_calendar_days")
    @patch("cal_scraper.sites.vida.fetcher.fetch_events_pages")
    @patch("cal_scraper.sites.vida.extractor.extract_program_from_calendar")
    @patch("cal_scraper.sites.vida.extractor.extract_events_from_listing")
    def test_returns_combined_program_and_listing(
        self, mock_extract_listing, mock_extract_program,
        mock_fetch_events, mock_fetch_calendar,
    ):
        """scrape() returns combined program + listing events sorted by datetime."""
        listing_event = _make_event("Listing", datetime(2026, 6, 15, 10, 0, tzinfo=PRAGUE_TZ))
        program_event = _make_event("Program", datetime(2026, 6, 14, 12, 0, tzinfo=PRAGUE_TZ))

        mock_fetch_events.return_value = ["<html>events</html>"]
        mock_fetch_calendar.return_value = [(datetime(2026, 6, 14).date(), "<html></html>")]
        mock_extract_listing.return_value = [listing_event]
        mock_extract_program.return_value = [program_event]

        result = scrape()

        assert len(result) == 2
        assert result[0].title == "Program"
        assert result[1].title == "Listing"

    @patch("cal_scraper.sites.vida.fetcher.fetch_calendar_days")
    @patch("cal_scraper.sites.vida.fetcher.fetch_events_pages")
    @patch("cal_scraper.sites.vida.extractor.extract_program_from_calendar")
    @patch("cal_scraper.sites.vida.extractor.extract_events_from_listing")
    def test_events_sorted_by_dtstart(
        self, mock_extract_listing, mock_extract_program,
        mock_fetch_events, mock_fetch_calendar,
    ):
        """scrape() returns events sorted by dtstart."""
        ev_late = _make_event("Late", datetime(2026, 7, 1, 10, 0, tzinfo=PRAGUE_TZ))
        ev_early = _make_event("Early", datetime(2026, 5, 1, 10, 0, tzinfo=PRAGUE_TZ))
        program_mid = _make_event("Mid", datetime(2026, 6, 1, 12, 0, tzinfo=PRAGUE_TZ))

        mock_fetch_events.return_value = ["<html></html>"]
        mock_fetch_calendar.return_value = [(datetime(2026, 6, 1).date(), "<html></html>")]
        mock_extract_listing.return_value = [ev_late, ev_early]
        mock_extract_program.return_value = [program_mid]

        result = scrape()

        assert len(result) == 3
        assert result[0].title == "Early"
        assert result[1].title == "Mid"
        assert result[2].title == "Late"

    @patch("cal_scraper.sites.vida.fetcher.fetch_calendar_days")
    @patch("cal_scraper.sites.vida.fetcher.fetch_events_pages")
    @patch("cal_scraper.sites.vida.extractor.extract_program_from_calendar")
    @patch("cal_scraper.sites.vida.extractor.extract_events_from_listing")
    def test_empty_results(
        self, mock_extract_listing, mock_extract_program,
        mock_fetch_events, mock_fetch_calendar,
    ):
        """scrape() returns empty list when no events found."""
        mock_fetch_events.return_value = ["<html></html>"]
        mock_fetch_calendar.return_value = []
        mock_extract_listing.return_value = []
        mock_extract_program.return_value = []

        result = scrape()

        assert result == []

    @patch("cal_scraper.sites.vida.fetcher.fetch_calendar_days")
    @patch("cal_scraper.sites.vida.fetcher.fetch_events_pages")
    @patch("cal_scraper.sites.vida.extractor.extract_program_from_calendar")
    @patch("cal_scraper.sites.vida.extractor.extract_events_from_listing")
    def test_dedup_program_slug_date_over_listing(
        self, mock_extract_listing, mock_extract_program,
        mock_fetch_events, mock_fetch_calendar,
    ):
        """Program event wins when listing has same slug+date; distinct listing survives."""
        duplicate_listing = _make_event(
            "Listing duplicate", datetime(2026, 6, 20, 12, 0, tzinfo=PRAGUE_TZ)
        )
        duplicate_listing.url = "https://vida.cz/doprovodny-program/den-otcu"

        unique_listing = _make_event(
            "Listing unique", datetime(2026, 6, 20, 15, 0, tzinfo=PRAGUE_TZ)
        )
        unique_listing.url = "https://vida.cz/doprovodny-program/jina-akce"

        program = _make_event("Program", datetime(2026, 6, 20, 10, 0, tzinfo=PRAGUE_TZ))
        program.url = "https://vida.cz/doprovodny-program/den-otcu"

        mock_fetch_events.return_value = ["<html></html>"]
        mock_fetch_calendar.return_value = [(datetime(2026, 6, 20).date(), "<html></html>")]
        mock_extract_listing.return_value = [duplicate_listing, unique_listing]
        mock_extract_program.return_value = [program]

        result = scrape()

        titles = [ev.title for ev in result]
        assert titles == ["Program", "Listing unique"]
