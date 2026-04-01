"""Tests for cal_scraper.detail_parser — detail page parsing and event enrichment."""

from datetime import datetime

import responses

from cal_scraper.detail_parser import _extract_detail, enrich_events
from cal_scraper.models import PRAGUE_TZ, Event


# ---------------------------------------------------------------------------
# Helper: build a detail page HTML snippet
# ---------------------------------------------------------------------------

def _detail_html(body_text: str) -> str:
    """Wrap body_text in the expected Elementor detail page structure."""
    return f"""
    <html><body>
    <div data-widget_type="theme-post-content.default">
      <div class="elementor-widget-container">
        {body_text}
      </div>
    </div>
    </body></html>
    """


def _make_event(url: str = "https://example.com/event/", title: str = "Test") -> Event:
    return Event(
        title=title,
        dtstart=datetime(2026, 5, 1, 15, 0, tzinfo=PRAGUE_TZ),
        dtend=datetime(2026, 5, 1, 17, 0, tzinfo=PRAGUE_TZ),
        all_day=False,
        venue="Venue",
        description="Listing excerpt",
        url=url,
        raw_date="1/5/2026, 15 H",
    )


# ---------------------------------------------------------------------------
# _extract_detail — unit tests
# ---------------------------------------------------------------------------


class TestExtractDetail:
    """_extract_detail parses description, price, and reservation from HTML."""

    def test_full_extraction(self):
        """Extract description, price, and reservation from typical detail page."""
        html = _detail_html("""
            <p>Fun workshop for kids and families.</p>
            <p>V\u00a0\u2013 100 / 50 Kč sourozenec</p>
            <p>Rezervace: info@moravska-galerie.cz, 724 543 722</p>
        """)
        desc, price, reservation = _extract_detail(html)
        assert "Fun workshop" in desc
        assert "100 / 50 Kč" in price
        assert "info@moravska-galerie.cz" in reservation
        assert "724 543 722" in reservation

    def test_no_price(self):
        """No price line → empty price string."""
        html = _detail_html("<p>A free event with no price info.</p>")
        desc, price, reservation = _extract_detail(html)
        assert desc == "A free event with no price info."
        assert price == ""

    def test_no_reservation(self):
        """No email or phone → empty reservation string."""
        html = _detail_html("<p>Just a description, no contact info.</p>")
        desc, price, reservation = _extract_detail(html)
        assert reservation == ""

    def test_multiple_emails_and_phones(self):
        """Multiple emails and phones are all captured."""
        html = _detail_html("""
            <p>Contact us at info@gallery.cz or edu@gallery.cz</p>
            <p>Phone: 724 543 722 or 602 111 222</p>
        """)
        _, _, reservation = _extract_detail(html)
        assert "info@gallery.cz" in reservation
        assert "edu@gallery.cz" in reservation
        assert "724 543 722" in reservation
        assert "602 111 222" in reservation

    def test_price_with_parenthetical(self):
        """Price with parenthetical suffix like '(na den)'."""
        html = _detail_html("<p>V – 250 Kč (na den)</p>")
        _, price, _ = _extract_detail(html)
        assert "250 Kč (na den)" in price

    def test_no_content_widget(self):
        """Missing content widget returns all empty strings."""
        html = "<html><body><p>No widget here</p></body></html>"
        desc, price, reservation = _extract_detail(html)
        assert desc == ""
        assert price == ""
        assert reservation == ""

    def test_price_removed_from_description(self):
        """Price line is stripped from the returned description."""
        html = _detail_html("""
            <p>Great event.</p>
            <p>V – 100 Kč</p>
            <p>See you there!</p>
        """)
        desc, price, _ = _extract_detail(html)
        assert "100 Kč" in price
        assert "V – 100 Kč" not in desc
        assert "Great event." in desc
        assert "See you there!" in desc

    def test_nbsp_cleaned(self):
        """Non-breaking spaces in content are replaced with regular spaces."""
        html = _detail_html("<p>Hello\xa0world</p>")
        desc, _, _ = _extract_detail(html)
        assert "\xa0" not in desc
        assert "Hello world" in desc


# ---------------------------------------------------------------------------
# enrich_events — integration tests with mocked HTTP
# ---------------------------------------------------------------------------


class TestEnrichEvents:
    """enrich_events fetches detail pages and updates event fields."""

    @responses.activate
    def test_enriches_single_event(self):
        """Single event gets description, price, reservation from detail page."""
        detail_html = _detail_html("""
            <p>Full description from detail page.</p>
            <p>V – 150 Kč</p>
            <p>Contact: edu@gallery.cz</p>
        """)
        responses.add(responses.GET, "https://example.com/event/", body=detail_html)

        events = [_make_event()]
        result = enrich_events(events, delay=0)

        assert len(result) == 1
        assert "Full description from detail page" in result[0].description
        assert "150 Kč" in result[0].price
        assert "edu@gallery.cz" in result[0].reservation

    @responses.activate
    def test_multi_slot_fetches_once(self):
        """Events sharing same URL only trigger one HTTP request."""
        detail_html = _detail_html("<p>Shared detail.</p>")
        responses.add(responses.GET, "https://example.com/shared/", body=detail_html)

        events = [
            _make_event(url="https://example.com/shared/", title="Slot 1"),
            _make_event(url="https://example.com/shared/", title="Slot 2"),
        ]
        result = enrich_events(events, delay=0)

        assert len(responses.calls) == 1
        assert result[0].description == result[1].description
        assert "Shared detail" in result[0].description

    @responses.activate
    def test_failed_fetch_keeps_original(self):
        """Failed HTTP request preserves original event description."""
        responses.add(
            responses.GET, "https://example.com/event/", status=500
        )

        events = [_make_event()]
        result = enrich_events(events, delay=0)

        assert result[0].description == "Listing excerpt"
        assert result[0].price == ""

    @responses.activate
    def test_no_url_skipped(self):
        """Event with empty URL is skipped entirely."""
        event = _make_event(url="")
        result = enrich_events([event], delay=0)
        assert len(responses.calls) == 0
        assert result[0].description == "Listing excerpt"

    @responses.activate
    def test_multiple_different_urls(self):
        """Events with different URLs each get their own fetch."""
        html1 = _detail_html("<p>Detail one.</p>")
        html2 = _detail_html("<p>Detail two.</p><p>V – 200 Kč</p>")
        responses.add(responses.GET, "https://example.com/a/", body=html1)
        responses.add(responses.GET, "https://example.com/b/", body=html2)

        events = [
            _make_event(url="https://example.com/a/"),
            _make_event(url="https://example.com/b/"),
        ]
        result = enrich_events(events, delay=0)

        assert len(responses.calls) == 2
        assert "Detail one" in result[0].description
        assert "Detail two" in result[1].description
        assert result[0].price == ""
        assert "200 Kč" in result[1].price
