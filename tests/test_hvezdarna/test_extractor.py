"""Tests for cal_scraper.sites.hvezdarna.extractor — show parsing."""

from datetime import date, datetime, timedelta

import pytest

from cal_scraper.models import PRAGUE_TZ
from cal_scraper.sites.hvezdarna.extractor import (
    _parse_date_header,
    _parse_duration,
    extract_events,
)

# ---------------------------------------------------------------------------
# Fixture HTML
# ---------------------------------------------------------------------------

WEEK_HEADER_HTML = '<h1 class="main-program-datum">14. týden 2026</h1>'

FULL_PAGE_HTML = """
<html><body>
<!-- Week header — should be skipped -->
<h1 class="main-program-datum">14. týden 2026</h1>

<!-- Date header -->
<h1 class="main-program-datum">Čtvrtek 2. dubna</h1>

<!-- Public show with all metadata -->
<div class="main-program-porad typ2 porad-thumb">
  <h2 class="main-program-cas">10:00</h2>
  <a href="/porad/astro-show"><h3 class="main-program-title">Astro Show 2D</h3></a>
  <h4 class="main-program-typ">veřejný</h4>
  <div class="main-program-desc">
    <p>A fascinating astronomy show.</p>
    <div class="main-program-tecky">digitárium - veřejnost</div>
    <div class="main-program-tecky">vhodné od 5 let</div>
    <div class="main-program-tecky">délka představení 55 minut</div>
    <div class="main-program-tecky">cena: 170/120</div>
    <div class="main-program-tlacitka">
      <a href="https://www.brnoid.cz/cs/hvezdarna-vstupenky?e=32157" class="main-program-vstupenky">Vstupenky</a>
      <a href="/porad/astro-show" class="main-program-informace desktopOnly">Více informací</a>
    </div>
  </div>
</div>

<!-- School show — should be skipped -->
<div class="main-program-porad typ1">
  <h2 class="main-program-cas">08:00</h2>
  <h3 class="main-program-title">Školní planetárium</h3>
  <h4 class="main-program-typ">školní</h4>
  <div class="main-program-desc">
    <p>School programme.</p>
  </div>
</div>

<!-- Another date -->
<h1 class="main-program-datum">Sobota 4. dubna</h1>

<!-- Show without a link (no URL) -->
<div class="main-program-porad typ2">
  <h2 class="main-program-cas">14:30</h2>
  <h3 class="main-program-title">Noční obloha</h3>
  <h4 class="main-program-typ">veřejný</h4>
  <div class="main-program-desc">
    <p>Look at the stars.</p>
    <div class="main-program-tecky">planetárium - veřejnost</div>
    <div class="main-program-tecky">délka představení 45 minut</div>
    <div class="main-program-tecky">cena: 150/100</div>
  </div>
</div>

<!-- English audio show with 3D -->
<div class="main-program-porad typ2 porad-english">
  <h2 class="main-program-cas">16:00</h2>
  <a href="/porad/space-3d"><h3 class="main-program-title">Space Adventure 3D</h3></a>
  <h4 class="main-program-typ">veřejný</h4>
  <div class="main-program-desc">
    <p>An immersive 3D space journey.</p>
    <div class="main-program-tecky">digitárium - veřejnost</div>
    <div class="main-program-tecky">English audio available</div>
    <div class="main-program-tecky">3D představení</div>
    <div class="main-program-tecky">vhodné od 8 let</div>
    <div class="main-program-tecky">délka představení 60 minut</div>
    <div class="main-program-tecky">cena: 200/150</div>
    <div class="main-program-tlacitka">
      <a href="https://www.brnoid.cz/cs/hvezdarna-vstupenky?e=99999" class="main-program-vstupenky">Vstupenky</a>
    </div>
  </div>
</div>

</body></html>
"""

DUPLICATE_PAGE_HTML = """
<html><body>
<h1 class="main-program-datum">Čtvrtek 2. dubna</h1>
<div class="main-program-porad typ2">
  <h2 class="main-program-cas">10:00</h2>
  <a href="/porad/astro-show"><h3 class="main-program-title">Astro Show 2D</h3></a>
  <h4 class="main-program-typ">veřejný</h4>
  <div class="main-program-desc">
    <p>A fascinating astronomy show.</p>
    <div class="main-program-tecky">digitárium - veřejnost</div>
    <div class="main-program-tecky">délka představení 55 minut</div>
    <div class="main-program-tecky">cena: 170/120</div>
  </div>
</div>
</body></html>
"""


# ---------------------------------------------------------------------------
# _parse_date_header tests
# ---------------------------------------------------------------------------


class TestParseDateHeader:
    def test_standard_date(self):
        """Parses 'Čtvrtek 2. dubna' correctly."""
        assert _parse_date_header("Čtvrtek 2. dubna", 2026) == date(2026, 4, 2)

    def test_sobota(self):
        """Parses 'Sobota 4. dubna'."""
        assert _parse_date_header("Sobota 4. dubna", 2026) == date(2026, 4, 4)

    def test_week_header_skipped(self):
        """Week header '14. týden 2026' returns None."""
        assert _parse_date_header("14. týden 2026", 2026) is None

    def test_all_months_genitive(self):
        """All 12 Czech genitive month names are recognized."""
        months = [
            ("1. ledna", 1, 1),
            ("15. února", 2, 15),
            ("3. března", 3, 3),
            ("2. dubna", 4, 2),
            ("10. května", 5, 10),
            ("20. června", 6, 20),
            ("7. července", 7, 7),
            ("31. srpna", 8, 31),
            ("1. září", 9, 1),
            ("12. října", 10, 12),
            ("5. listopadu", 11, 5),
            ("24. prosince", 12, 24),
        ]
        for text, expected_month, expected_day in months:
            result = _parse_date_header(f"Pondělí {text}", 2026)
            assert result is not None, f"Failed to parse: {text}"
            assert result.month == expected_month
            assert result.day == expected_day

    def test_unknown_month_returns_none(self):
        """Unknown month word returns None."""
        assert _parse_date_header("Pondělí 1. foobar", 2026) is None


# ---------------------------------------------------------------------------
# _parse_duration tests
# ---------------------------------------------------------------------------


class TestParseDuration:
    def test_standard(self):
        """Parses '55 minut'."""
        assert _parse_duration("délka představení 55 minut") == 55

    def test_with_extra_text(self):
        """Parses '60 minut' from longer text."""
        assert _parse_duration("délka představení 60 minut (přibližně)") == 60

    def test_no_match(self):
        """Returns None when no minute pattern is found."""
        assert _parse_duration("no duration here") is None

    def test_large_duration(self):
        """Handles 120 minut."""
        assert _parse_duration("délka představení 120 minut") == 120


# ---------------------------------------------------------------------------
# extract_events tests — full page
# ---------------------------------------------------------------------------


class TestExtractEvents:
    @pytest.fixture
    def events(self):
        """Extract events from the test fixture page."""
        pages = [(FULL_PAGE_HTML, date(2026, 3, 30))]  # Monday of that week
        return extract_events(pages)

    def test_public_shows_extracted(self, events):
        """Only public shows are extracted (school show filtered out)."""
        titles = [e.title for e in events]
        assert "Astro Show 2D" in titles
        assert "Noční obloha" in titles
        assert "Space Adventure 3D" in titles
        assert "Školní planetárium" not in titles

    def test_event_count(self, events):
        """3 public shows from the fixture (school show excluded)."""
        assert len(events) == 3

    def test_astro_show_fields(self, events):
        """The first public show has correct fields."""
        ev = events[0]
        assert ev.title == "Astro Show 2D"
        assert ev.dtstart == datetime(2026, 4, 2, 10, 0, tzinfo=PRAGUE_TZ)
        assert ev.dtend == datetime(2026, 4, 2, 10, 55, tzinfo=PRAGUE_TZ)
        assert ev.all_day is False
        assert ev.venue == "digitárium - veřejnost"
        assert ev.url == "https://www.hvezdarna.cz/porad/astro-show"
        assert ev.price == "cena: 170/120"

    def test_description_contains_age(self, events):
        """Description includes age info."""
        ev = events[0]
        assert "vhodné od 5 let" in ev.description

    def test_description_contains_ticket_url(self, events):
        """Description includes ticket URL."""
        ev = events[0]
        assert "brnoid.cz" in ev.description

    def test_show_without_url(self, events):
        """Show without <a> wrapper has empty URL."""
        ev = next(e for e in events if e.title == "Noční obloha")
        assert ev.url == ""

    def test_duration_45_min(self, events):
        """'Noční obloha' has 45-minute duration."""
        ev = next(e for e in events if e.title == "Noční obloha")
        expected_end = datetime(2026, 4, 4, 14, 30, tzinfo=PRAGUE_TZ) + timedelta(
            minutes=45
        )
        assert ev.dtend == expected_end

    def test_english_audio_in_description(self, events):
        """English audio note appears in description."""
        ev = next(e for e in events if e.title == "Space Adventure 3D")
        assert "English audio" in ev.description

    def test_3d_format_in_description(self, events):
        """3D format note appears in description."""
        ev = next(e for e in events if e.title == "Space Adventure 3D")
        assert "3D" in ev.description

    def test_60_min_duration(self, events):
        """Space Adventure has 60 minute duration."""
        ev = next(e for e in events if e.title == "Space Adventure 3D")
        expected_end = datetime(2026, 4, 4, 16, 0, tzinfo=PRAGUE_TZ) + timedelta(
            minutes=60
        )
        assert ev.dtend == expected_end

    def test_raw_date_format(self, events):
        """raw_date has expected format."""
        ev = events[0]
        assert ev.raw_date == "2/4/2026, 10:00"

    def test_date_header_april_4(self, events):
        """Events on Sobota 4. dubna have correct date."""
        ev = next(e for e in events if e.title == "Noční obloha")
        assert ev.dtstart.date() == date(2026, 4, 4)


# ---------------------------------------------------------------------------
# Deduplication tests
# ---------------------------------------------------------------------------


class TestDeduplication:
    def test_duplicate_events_removed(self):
        """Same show on overlapping weeks is deduplicated by (url, dtstart)."""
        pages = [
            (FULL_PAGE_HTML, date(2026, 3, 30)),
            (DUPLICATE_PAGE_HTML, date(2026, 3, 30)),
        ]
        events = extract_events(pages)
        astro_events = [e for e in events if e.title == "Astro Show 2D"]
        assert len(astro_events) == 1

    def test_different_times_not_deduplicated(self):
        """Same show at different times is NOT deduplicated."""
        html2 = DUPLICATE_PAGE_HTML.replace("10:00", "14:00")
        pages = [
            (FULL_PAGE_HTML, date(2026, 3, 30)),
            (html2, date(2026, 3, 30)),
        ]
        events = extract_events(pages)
        astro_events = [e for e in events if e.title == "Astro Show 2D"]
        assert len(astro_events) == 2


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_page(self):
        """Empty HTML returns no events."""
        pages = [("<html><body></body></html>", date(2026, 4, 6))]
        assert extract_events(pages) == []

    def test_no_date_header_before_show(self):
        """Show without preceding date header is skipped."""
        html = """
        <html><body>
        <div class="main-program-porad typ2">
          <h2 class="main-program-cas">10:00</h2>
          <h3 class="main-program-title">Orphan Show</h3>
          <h4 class="main-program-typ">veřejný</h4>
        </div>
        </body></html>
        """
        pages = [(html, date(2026, 4, 6))]
        assert extract_events(pages) == []

    def test_show_without_time_skipped(self):
        """Show missing time element is skipped."""
        html = """
        <html><body>
        <h1 class="main-program-datum">Pondělí 6. dubna</h1>
        <div class="main-program-porad typ2">
          <h3 class="main-program-title">No Time Show</h3>
          <h4 class="main-program-typ">veřejný</h4>
        </div>
        </body></html>
        """
        pages = [(html, date(2026, 4, 6))]
        assert extract_events(pages) == []

    def test_default_duration_when_missing(self):
        """Default 55 min duration used when tecky has no délka."""
        html = """
        <html><body>
        <h1 class="main-program-datum">Pondělí 6. dubna</h1>
        <div class="main-program-porad typ2">
          <h2 class="main-program-cas">10:00</h2>
          <h3 class="main-program-title">Short Show</h3>
          <h4 class="main-program-typ">veřejný</h4>
          <div class="main-program-desc">
            <p>Some description.</p>
          </div>
        </div>
        </body></html>
        """
        pages = [(html, date(2026, 4, 6))]
        events = extract_events(pages)
        assert len(events) == 1
        expected_end = datetime(2026, 4, 6, 10, 0, tzinfo=PRAGUE_TZ) + timedelta(
            minutes=55
        )
        assert events[0].dtend == expected_end
