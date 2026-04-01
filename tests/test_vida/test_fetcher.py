"""Tests for VIDA! fetcher module."""

from unittest.mock import MagicMock, patch


from cal_scraper.sites.vida.fetcher import (
    fetch_events_pages,
    fetch_workshops_page,
    EVENTS_URL,
    WORKSHOPS_URL,
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

WORKSHOP_HTML = "<html><body><p>workshop content</p></body></html>"


def _mock_response(text: str) -> MagicMock:
    resp = MagicMock()
    resp.text = text
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFetchEventsPages:
    """Tests for fetch_events_pages."""

    @patch("cal_scraper.sites.vida.fetcher.time.sleep")
    @patch("cal_scraper.sites.vida.fetcher.requests.get")
    def test_fetches_all_paginated_pages(self, mock_get, mock_sleep):
        """Fetcher discovers pagination and fetches all pages."""
        mock_get.side_effect = [
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
        mock_get.assert_any_call(EVENTS_URL, timeout=30)
        mock_get.assert_any_call(f"{EVENTS_URL}?start=12", timeout=30)
        mock_get.assert_any_call(f"{EVENTS_URL}?start=24", timeout=30)

    @patch("cal_scraper.sites.vida.fetcher.time.sleep")
    @patch("cal_scraper.sites.vida.fetcher.requests.get")
    def test_single_page_no_pagination(self, mock_get, mock_sleep):
        """Single-page result with no pagination links."""
        html = "<html><body><div class='program-item'>only page</div></body></html>"
        mock_get.return_value = _mock_response(html)

        pages = fetch_events_pages()

        assert len(pages) == 1
        mock_get.assert_called_once_with(EVENTS_URL, timeout=30)
        mock_sleep.assert_not_called()

    @patch("cal_scraper.sites.vida.fetcher.time.sleep")
    @patch("cal_scraper.sites.vida.fetcher.requests.get")
    def test_delay_between_pages(self, mock_get, mock_sleep):
        """1 second delay between paginated requests."""
        mock_get.side_effect = [
            _mock_response(PAGE1_HTML),
            _mock_response(PAGE2_HTML),
            _mock_response(PAGE3_HTML),
        ]

        fetch_events_pages()

        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(1)

    @patch("cal_scraper.sites.vida.fetcher.time.sleep")
    @patch("cal_scraper.sites.vida.fetcher.requests.get")
    def test_verbose_logging(self, mock_get, mock_sleep, caplog):
        """Verbose mode logs page fetches."""
        mock_get.side_effect = [
            _mock_response(PAGE1_HTML),
            _mock_response(PAGE2_HTML),
            _mock_response(PAGE3_HTML),
        ]

        import logging
        with caplog.at_level(logging.INFO, logger="cal_scraper.sites.vida.fetcher"):
            fetch_events_pages(verbose=True)

        assert any("page 1" in r.message.lower() or EVENTS_URL in r.message for r in caplog.records)


class TestFetchWorkshopsPage:
    """Tests for fetch_workshops_page."""

    @patch("cal_scraper.sites.vida.fetcher.requests.get")
    def test_fetches_workshop_page(self, mock_get):
        """Workshop fetcher returns HTML string."""
        mock_get.return_value = _mock_response(WORKSHOP_HTML)

        result = fetch_workshops_page()

        assert result == WORKSHOP_HTML
        mock_get.assert_called_once_with(WORKSHOPS_URL, timeout=30)

    @patch("cal_scraper.sites.vida.fetcher.requests.get")
    def test_verbose_logging(self, mock_get, caplog):
        """Verbose mode logs workshop page fetch."""
        mock_get.return_value = _mock_response(WORKSHOP_HTML)

        import logging
        with caplog.at_level(logging.INFO, logger="cal_scraper.sites.vida.fetcher"):
            fetch_workshops_page(verbose=True)

        assert any(WORKSHOPS_URL in r.message for r in caplog.records)
