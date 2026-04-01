"""Tests for IKEA Brno event fetcher."""

import logging

import pytest
import responses

from cal_scraper.sites.ikea_brno.fetcher import API_URL, fetch_events


class TestFetchEvents:
    """Tests for fetch_events function."""

    @responses.activate
    def test_fetch_returns_events(self):
        """Successful fetch returns list of event dicts."""
        mock_data = [{"id": "1"}, {"id": "2"}]
        responses.add(responses.GET, API_URL, json=mock_data, status=200)

        result = fetch_events()
        assert result == mock_data

    @responses.activate
    def test_request_headers(self):
        """Request includes required REQUEST-ORIGIN header."""
        responses.add(responses.GET, API_URL, json=[], status=200)

        fetch_events()

        assert len(responses.calls) == 1
        assert responses.calls[0].request.headers["REQUEST-ORIGIN"] == "iert-customer-fe"

    @responses.activate
    def test_error_handling(self):
        """Non-200 response raises HTTPError."""
        responses.add(responses.GET, API_URL, json={}, status=500)

        with pytest.raises(Exception):
            fetch_events()

    @responses.activate
    def test_verbose_logging(self, caplog):
        """Verbose mode logs event count."""
        mock_data = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        responses.add(responses.GET, API_URL, json=mock_data, status=200)

        with caplog.at_level(logging.INFO, logger="cal_scraper.sites.ikea_brno.fetcher"):
            fetch_events(verbose=True)

        assert "3" in caplog.text

    @responses.activate
    def test_empty_response(self):
        """API returning empty list works correctly."""
        responses.add(responses.GET, API_URL, json=[], status=200)

        result = fetch_events()
        assert result == []
