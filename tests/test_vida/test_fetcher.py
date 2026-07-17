"""Tests for VIDA! fetcher module."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from cal_scraper.sites.vida.fetcher import (
    CALENDAR_URL,
    EVENTS_URL,
    EMPTY_STREAK_STOP,
    MAX_CALENDAR_DAYS,
    fetch_calendar_days,
    fetch_events_pages,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PAGE1_HTML = """
<html><body>
<div class="pagination">
  <a href="/doprovodny-program?start=12">2</a>
  <a href="/doprovodny-program?start=24">3</a>
</div>
<div class="program-item">page 1</div>
</body></html>
"""

PAGE2_HTML = "<html><body><div class='program-item'>page 2</div></body></html>"
PAGE3_HTML = "<html><body><div class='program-item'>page 3</div></body></html>"

CALENDAR_NONEMPTY_HTML = (
    "<html><body><a class='cal-item' href='/doprovodny-program/test'>"
    "<span class='dp-item-date'>10:30</span><div class='cal-item-detail'><h6>T</h6></div>"
    "</a></body></html>"
)
CALENDAR_EMPTY_HTML = "<html><body></body></html>"


def _mock_response(text: str) -> MagicMock:
    resp = MagicMock()
    resp.text = text
    resp.raise_for_status = MagicMock()
    return resp


_real_datetime = datetime


class _FrozenDatetime(_real_datetime):
    @classmethod
    def now(cls, tz=None):
        return _real_datetime(2026, 7, 15, 0, 0, tzinfo=tz)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFetchEventsPages:
    """Tests for fetch_events_pages."""

    @patch("cal_scraper.sites.vida.fetcher.time.sleep")
    @patch("cal_scraper.sites.vida.fetcher.fetch")
    def test_fetches_all_paginated_pages(self, mock_fetch, mock_sleep):
        """Fetcher discovers pagination and fetches all pages."""
        mock_fetch.side_effect = [
            _mock_response(PAGE1_HTML),
            _mock_response(PAGE2_HTML),
            _mock_response(PAGE3_HTML),
        ]

        pages = fetch_events_pages()

        assert len(pages) == 3
        assert "page 1" in pages[0]
        assert "page 2" in pages[1]
        assert "page 3" in pages[2]

        # Verify URLs
        mock_fetch.assert_any_call(EVENTS_URL, timeout=30, verify=False)
        mock_fetch.assert_any_call(f"{EVENTS_URL}?start=12", timeout=30, verify=False)
        mock_fetch.assert_any_call(f"{EVENTS_URL}?start=24", timeout=30, verify=False)

    @patch("cal_scraper.sites.vida.fetcher.time.sleep")
    @patch("cal_scraper.sites.vida.fetcher.fetch")
    def test_single_page_no_pagination(self, mock_fetch, mock_sleep):
        """Single-page result with no pagination links."""
        html = "<html><body><div class='program-item'>only page</div></body></html>"
        mock_fetch.return_value = _mock_response(html)

        pages = fetch_events_pages()

        assert len(pages) == 1
        mock_fetch.assert_called_once_with(EVENTS_URL, timeout=30, verify=False)
        mock_sleep.assert_not_called()

    @patch("cal_scraper.sites.vida.fetcher.time.sleep")
    @patch("cal_scraper.sites.vida.fetcher.fetch")
    def test_delay_between_pages(self, mock_fetch, mock_sleep):
        """1 second delay between paginated requests."""
        mock_fetch.side_effect = [
            _mock_response(PAGE1_HTML),
            _mock_response(PAGE2_HTML),
            _mock_response(PAGE3_HTML),
        ]

        fetch_events_pages()

        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(1)

    @patch("cal_scraper.sites.vida.fetcher.time.sleep")
    @patch("cal_scraper.sites.vida.fetcher.fetch")
    def test_verbose_logging(self, mock_fetch, mock_sleep, caplog):
        """Verbose mode logs page fetches."""
        mock_fetch.side_effect = [
            _mock_response(PAGE1_HTML),
            _mock_response(PAGE2_HTML),
            _mock_response(PAGE3_HTML),
        ]

        import logging
        with caplog.at_level(logging.INFO, logger="cal_scraper.sites.vida.fetcher"):
            fetch_events_pages(verbose=True)

        assert any("page 1" in r.message.lower() or EVENTS_URL in r.message for r in caplog.records)


class TestFetchCalendarDays:
    @patch("cal_scraper.sites.vida.fetcher.fetch")
    @patch("cal_scraper.sites.vida.fetcher.time.sleep")
    @patch("cal_scraper.sites.vida.fetcher.datetime", _FrozenDatetime)
    def test_stops_after_consecutive_empty_days(self, mock_sleep, mock_fetch):
        """Fetcher stops after EMPTY_STREAK_STOP consecutive empty responses."""
        mock_fetch.side_effect = [
            _mock_response(CALENDAR_NONEMPTY_HTML),
            _mock_response(CALENDAR_NONEMPTY_HTML),
            *[_mock_response(CALENDAR_EMPTY_HTML) for _ in range(EMPTY_STREAK_STOP)],
        ]

        days = fetch_calendar_days()

        assert len(days) == 2 + EMPTY_STREAK_STOP
        assert mock_fetch.call_count == 2 + EMPTY_STREAK_STOP
        first_call = mock_fetch.call_args_list[0]
        assert first_call.args[0] == f"{CALENDAR_URL}?tmpl=raw&day=2026-07-15"
        assert first_call.kwargs["timeout"] == 30
        assert first_call.kwargs["verify"] is False
        assert mock_sleep.call_count == (2 + EMPTY_STREAK_STOP - 1)

    @patch("cal_scraper.sites.vida.fetcher.fetch")
    @patch("cal_scraper.sites.vida.fetcher.time.sleep")
    @patch("cal_scraper.sites.vida.fetcher.datetime", _FrozenDatetime)
    def test_hard_cap_limits_total_days(self, mock_sleep, mock_fetch):
        """Fetcher respects MAX_CALENDAR_DAYS hard cap."""
        mock_fetch.side_effect = [_mock_response(CALENDAR_NONEMPTY_HTML)] * MAX_CALENDAR_DAYS
        days = fetch_calendar_days()
        assert len(days) == MAX_CALENDAR_DAYS
        assert mock_fetch.call_count == MAX_CALENDAR_DAYS
        assert mock_sleep.call_count == MAX_CALENDAR_DAYS - 1

    @patch("cal_scraper.sites.vida.fetcher.fetch")
    @patch("cal_scraper.sites.vida.fetcher.time.sleep")
    @patch("cal_scraper.sites.vida.fetcher.datetime", _FrozenDatetime)
    def test_verbose_logging(self, mock_sleep, mock_fetch, caplog):
        """Verbose mode logs daily calendar requests."""
        mock_fetch.side_effect = [
            _mock_response(CALENDAR_NONEMPTY_HTML),
            *[_mock_response(CALENDAR_EMPTY_HTML) for _ in range(EMPTY_STREAK_STOP)],
        ]

        import logging
        with caplog.at_level(logging.INFO, logger="cal_scraper.sites.vida.fetcher"):
            fetch_calendar_days(verbose=True)

        assert any(CALENDAR_URL in r.message for r in caplog.records)
