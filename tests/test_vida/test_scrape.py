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

    @patch("cal_scraper.sites.vida.fetcher.fetch_workshops_page")
    @patch("cal_scraper.sites.vida.fetcher.fetch_events_pages")
    @patch("cal_scraper.sites.vida.extractor.extract_workshops")
    @patch("cal_scraper.sites.vida.extractor.extract_events_from_listing")
    def test_returns_combined_events_and_workshops(
        self, mock_extract_events, mock_extract_workshops,
        mock_fetch_events, mock_fetch_workshops,
    ):
        """scrape() returns combined events + workshops."""
        ev1 = _make_event("Event", datetime(2026, 6, 15, 10, 0, tzinfo=PRAGUE_TZ))
        ws1 = _make_event("Workshop", datetime(2026, 6, 14, 12, 0, tzinfo=PRAGUE_TZ))

        mock_fetch_events.return_value = ["<html>events</html>"]
        mock_fetch_workshops.return_value = "<html>workshops</html>"
        mock_extract_events.return_value = [ev1]
        mock_extract_workshops.return_value = [ws1]

        result = scrape()

        assert len(result) == 2
        assert result[0].title == "Workshop"
        assert result[1].title == "Event"

    @patch("cal_scraper.sites.vida.fetcher.fetch_workshops_page")
    @patch("cal_scraper.sites.vida.fetcher.fetch_events_pages")
    @patch("cal_scraper.sites.vida.extractor.extract_workshops")
    @patch("cal_scraper.sites.vida.extractor.extract_events_from_listing")
    def test_events_sorted_by_dtstart(
        self, mock_extract_events, mock_extract_workshops,
        mock_fetch_events, mock_fetch_workshops,
    ):
        """scrape() returns events sorted by dtstart."""
        ev_late = _make_event("Late", datetime(2026, 7, 1, 10, 0, tzinfo=PRAGUE_TZ))
        ev_early = _make_event("Early", datetime(2026, 5, 1, 10, 0, tzinfo=PRAGUE_TZ))
        ws_mid = _make_event("Mid", datetime(2026, 6, 1, 12, 0, tzinfo=PRAGUE_TZ))

        mock_fetch_events.return_value = ["<html></html>"]
        mock_fetch_workshops.return_value = "<html></html>"
        mock_extract_events.return_value = [ev_late, ev_early]
        mock_extract_workshops.return_value = [ws_mid]

        result = scrape()

        assert len(result) == 3
        assert result[0].title == "Early"
        assert result[1].title == "Mid"
        assert result[2].title == "Late"

    @patch("cal_scraper.sites.vida.fetcher.fetch_workshops_page")
    @patch("cal_scraper.sites.vida.fetcher.fetch_events_pages")
    @patch("cal_scraper.sites.vida.extractor.extract_workshops")
    @patch("cal_scraper.sites.vida.extractor.extract_events_from_listing")
    def test_empty_results(
        self, mock_extract_events, mock_extract_workshops,
        mock_fetch_events, mock_fetch_workshops,
    ):
        """scrape() returns empty list when no events found."""
        mock_fetch_events.return_value = ["<html></html>"]
        mock_fetch_workshops.return_value = "<html></html>"
        mock_extract_events.return_value = []
        mock_extract_workshops.return_value = []

        result = scrape()

        assert result == []
