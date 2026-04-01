"""Tests for cal_scraper.extractor — HTML event extraction from Elementor cards."""

import logging
from datetime import date, datetime
from pathlib import Path

import pytest

from cal_scraper.sites.moravska_galerie.extractor import extract_all_events, extract_events_from_html
from cal_scraper.models import PRAGUE_TZ, Event

# ---------------------------------------------------------------------------
# Fixture data
# ---------------------------------------------------------------------------

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "event_page.html"
FIXTURE_HTML = FIXTURE_PATH.read_text(encoding="utf-8")


@pytest.fixture
def events():
    """Extract events from the standard fixture page."""
    return extract_events_from_html(FIXTURE_HTML)


# ---------------------------------------------------------------------------
# Field extraction tests
# ---------------------------------------------------------------------------


def test_extract_single_event(events):
    """Article 1 produces an Event with expected title."""
    assert len(events) >= 1
    assert events[0].title == "Rodinné odpoledne: S úsměvem"


def test_title_preserves_diacritics(events):
    """Czech diacritics (ú, ě) survive extraction (SCRP-02)."""
    assert "ú" in events[0].title
    assert "ě" in events[0].title  # úsměvem


def test_venue_with_sublocation(events):
    """Venue includes comma-separated sub-location (SCRP-03)."""
    assert events[0].venue == "Pražákův palác, Knihovna"


def test_venue_simple(events):
    """Simple venue without sub-location (SCRP-03)."""
    assert events[1].venue == "Jurkovičova vila"


def test_description_extracted(events):
    """Description from listing page excerpt (SCRP-04)."""
    assert events[0].description == "Zima je pryč, hurá!"


def test_event_url_extracted(events):
    """Event detail URL extracted from title link (SCRP-05)."""
    assert events[0].url == "https://www.moravska-galerie.cz/program/rodinne-odpoledne/"


def test_date_parsed_into_event(events):
    """Date parser integration: dtstart is timezone-aware datetime for timed events."""
    assert isinstance(events[0].dtstart, datetime)
    assert events[0].all_day is False


def test_raw_date_preserved(events):
    """Raw date string preserved after bullet stripping."""
    assert events[0].raw_date == "31/3/2026, 15 H"


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


def test_skip_event_missing_title(caplog):
    """Article 4 (missing title) is skipped; warning logged (D-02)."""
    with caplog.at_level(logging.WARNING):
        result = extract_events_from_html(FIXTURE_HTML)
    assert len(result) == 3  # 4 articles but only 3 valid
    assert any("title" in rec.message.lower() for rec in caplog.records
               if rec.levelno >= logging.WARNING)


def test_skip_event_missing_date(caplog):
    """Article with title but no date widget is skipped with warning (D-02)."""
    html = """
    <html><body>
    <article class="elementor-post ecs-post-loop post-99999">
      <div data-elementor-type="loop">
        <div data-id="ff31590">
          <h2 class="elementor-heading-title">
            <a href="https://example.com/">Test Event</a>
          </h2>
        </div>
        <!-- No date widget (data-id="fe5263e") -->
      </div>
    </article>
    </body></html>
    """
    result = extract_events_from_html(html)
    assert len(result) == 0
    assert any("date" in rec.message.lower() for rec in caplog.records
               if rec.levelno >= logging.WARNING)


# ---------------------------------------------------------------------------
# Multi-event and entity tests
# ---------------------------------------------------------------------------


def test_multiple_events_from_page(events):
    """Fixture has 3 valid + 1 invalid articles → returns 3 Events."""
    assert len(events) == 3


def test_html_entity_decoded(events):
    """HTML &nbsp; entity decoded to regular space, not \xa0 (Pitfall 11)."""
    desc = events[1].description
    assert "\xa0" not in desc
    assert "nbsp" not in desc
    assert desc == "V rámci letního programu"


def test_extract_all_events_multi_page():
    """extract_all_events combines events from multiple HTML pages."""
    combined = extract_all_events([FIXTURE_HTML, FIXTURE_HTML])
    assert len(combined) == 6  # 3 valid per page × 2 pages


def test_multi_time_slot_produces_multiple_events():
    """Article with '15 H / 16 H / 17 H' produces three separate Events."""
    html = """
    <html><body>
    <article class="elementor-post ecs-post-loop post-88888">
      <div data-elementor-type="loop">
        <div data-id="ff31590">
          <h2 class="elementor-heading-title">
            <a href="https://example.com/multi/">Multi Slot Event</a>
          </h2>
        </div>
        <div data-id="fe5263e">
          <div class="elementor-widget-container">● 24/5/2026, 15 H / 16 H / 17 H</div>
        </div>
        <div data-id="d2f8856">
          <div class="elementor-widget-container">Some Venue</div>
        </div>
        <div data-id="16d0837">
          <div class="elementor-widget-container">Description text</div>
        </div>
      </div>
    </article>
    </body></html>
    """
    events = extract_events_from_html(html)
    assert len(events) == 3
    hours = [e.dtstart.hour for e in events]
    assert hours == [15, 16, 17]
    # All share the same title, venue, description
    assert all(e.title == "Multi Slot Event" for e in events)
    assert all(e.venue == "Some Venue" for e in events)


# ---------------------------------------------------------------------------
# ENHN-01: Sold-out detection (VYPRODÁNO in title)
# ---------------------------------------------------------------------------


def test_sold_out_detected():
    """Title containing 'VYPRODÁNO' sets sold_out=True (ENHN-01)."""
    html = """
    <html><body>
    <article class="elementor-post ecs-post-loop post-77777">
      <div data-elementor-type="loop">
        <div data-id="ff31590">
          <h2 class="elementor-heading-title">
            <a href="https://example.com/sold/">Workshop – VYPRODÁNO</a>
          </h2>
        </div>
        <div data-id="fe5263e">
          <div class="elementor-widget-container">● 15/6/2026, 10 H</div>
        </div>
        <div data-id="d2f8856">
          <div class="elementor-widget-container">Venue</div>
        </div>
        <div data-id="16d0837">
          <div class="elementor-widget-container">Desc</div>
        </div>
      </div>
    </article>
    </body></html>
    """
    events = extract_events_from_html(html)
    assert len(events) == 1
    assert events[0].sold_out is True


def test_sold_out_false_when_absent():
    """Title without 'VYPRODÁNO' sets sold_out=False (ENHN-01)."""
    html = """
    <html><body>
    <article class="elementor-post ecs-post-loop post-66666">
      <div data-elementor-type="loop">
        <div data-id="ff31590">
          <h2 class="elementor-heading-title">
            <a href="https://example.com/avail/">Available Workshop</a>
          </h2>
        </div>
        <div data-id="fe5263e">
          <div class="elementor-widget-container">● 15/6/2026, 10 H</div>
        </div>
        <div data-id="d2f8856">
          <div class="elementor-widget-container">Venue</div>
        </div>
        <div data-id="16d0837">
          <div class="elementor-widget-container">Desc</div>
        </div>
      </div>
    </article>
    </body></html>
    """
    events = extract_events_from_html(html)
    assert len(events) == 1
    assert events[0].sold_out is False


def test_sold_out_case_insensitive():
    """VYPRODÁNO detection is case insensitive (ENHN-01)."""
    html = """
    <html><body>
    <article class="elementor-post ecs-post-loop post-55555">
      <div data-elementor-type="loop">
        <div data-id="ff31590">
          <h2 class="elementor-heading-title">
            <a href="https://example.com/case/">Event Vyprodáno</a>
          </h2>
        </div>
        <div data-id="fe5263e">
          <div class="elementor-widget-container">● 15/6/2026, 10 H</div>
        </div>
        <div data-id="d2f8856">
          <div class="elementor-widget-container">Venue</div>
        </div>
        <div data-id="16d0837">
          <div class="elementor-widget-container">Desc</div>
        </div>
      </div>
    </article>
    </body></html>
    """
    events = extract_events_from_html(html)
    assert len(events) == 1
    assert events[0].sold_out is True


def test_no_articles_warns(caplog):
    """A page with no article elements logs a warning about template changes."""
    html = "<html><body><p>No events here</p></body></html>"
    with caplog.at_level(logging.WARNING, logger="cal_scraper.extractor"):
        events = extract_events_from_html(html)
    assert events == []
    assert any("template" in r.message.lower() for r in caplog.records)
