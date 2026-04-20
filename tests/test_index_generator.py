"""Tests for index.html generation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from cal_scraper.index_generator import (
    CalendarInfo,
    _clean_group_title,
    _format_updated,
    _group_calendars,
    _is_translation,
    _strip_source_from_desc,
    discover_calendars,
    generate_index,
)


# ---------------------------------------------------------------------------
# ICS stubs — realistic headers read by discover_calendars
# ---------------------------------------------------------------------------

ICS_STUB_A = """\
BEGIN:VCALENDAR
VERSION:2.0
X-WR-CALNAME:Site A – Events
X-WR-CALDESC:Unofficial scrape of Site A events. Source: https://site-a.example.com/events
X-CAL-SOURCE-URL:https://site-a.example.com/events
BEGIN:VEVENT
SUMMARY:Test
END:VEVENT
END:VCALENDAR
"""

ICS_STUB_B = """\
BEGIN:VCALENDAR
VERSION:2.0
X-WR-CALNAME:Site B – Family Fun
X-CAL-SOURCE-URL:https://site-b.example.com/
BEGIN:VEVENT
SUMMARY:Test
END:VEVENT
END:VCALENDAR
"""


# ---------------------------------------------------------------------------
# discover_calendars
# ---------------------------------------------------------------------------


class TestDiscoverCalendars:
    """Directory scanning picks up all .ics files and reads metadata from headers."""

    def test_reads_calname_and_desc(self, tmp_path):
        (tmp_path / "site-a.ics").write_text(ICS_STUB_A)
        cals = discover_calendars(tmp_path)
        assert len(cals) == 1
        assert cals[0].cal_name == "Site A – Events"
        assert "Unofficial scrape of Site A events." in cals[0].cal_desc

    def test_reads_source_url(self, tmp_path):
        (tmp_path / "site-a.ics").write_text(ICS_STUB_A)
        cals = discover_calendars(tmp_path)
        assert cals[0].source_url == "https://site-a.example.com/events"

    def test_missing_source_url_is_empty(self, tmp_path):
        (tmp_path / "bare.ics").write_text(
            "BEGIN:VCALENDAR\nVERSION:2.0\nX-WR-CALNAME:Bare\nEND:VCALENDAR\n"
        )
        cals = discover_calendars(tmp_path)
        assert cals[0].source_url == ""

    def test_missing_calname_uses_filename(self, tmp_path):
        (tmp_path / "bare.ics").write_text("BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR\n")
        cals = discover_calendars(tmp_path)
        assert cals[0].cal_name == "bare.ics"

    def test_multiple_files_sorted_by_name(self, tmp_path):
        (tmp_path / "site-b.ics").write_text(ICS_STUB_B)
        (tmp_path / "site-a.ics").write_text(ICS_STUB_A)
        (tmp_path / "zzz.ics").write_text("BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR\n")
        cals = discover_calendars(tmp_path)
        assert len(cals) == 3
        assert cals[0].filename == "site-a.ics"
        assert cals[1].filename == "site-b.ics"
        assert cals[2].filename == "zzz.ics"

    def test_empty_directory(self, tmp_path):
        assert discover_calendars(tmp_path) == []

    def test_no_desc_in_ics(self, tmp_path):
        (tmp_path / "site-b.ics").write_text(ICS_STUB_B)
        cals = discover_calendars(tmp_path)
        assert cals[0].cal_desc == ""

    def test_folded_lines_reassembled(self, tmp_path):
        """RFC 5545 continuation lines (leading space) are unfolded."""
        ics = (
            "BEGIN:VCALENDAR\nVERSION:2.0\n"
            "X-WR-CALNAME:Long Name (unoffici\n"
            " al)\n"
            "X-WR-CALDESC:First part of descri\n"
            " ption here\n"
            "BEGIN:VEVENT\nEND:VEVENT\nEND:VCALENDAR\n"
        )
        (tmp_path / "folded.ics").write_text(ics)
        cals = discover_calendars(tmp_path)
        assert cals[0].cal_name == "Long Name (unofficial)"
        assert cals[0].cal_desc == "First part of description here"

    def test_escaped_commas_unescaped(self, tmp_path):
        """ICS \\, and \\; escapes are converted back to plain characters."""
        ics = (
            "BEGIN:VCALENDAR\nVERSION:2.0\n"
            "X-WR-CALNAME:Gallery (unofficial\\, in CZ)\n"
            "BEGIN:VEVENT\nEND:VEVENT\nEND:VCALENDAR\n"
        )
        (tmp_path / "escaped.ics").write_text(ics)
        cals = discover_calendars(tmp_path)
        assert cals[0].cal_name == "Gallery (unofficial, in CZ)"

    def test_updated_at_from_mtime(self, tmp_path):
        """discover_calendars reads file modification time into updated_at."""
        (tmp_path / "site-a.ics").write_text(ICS_STUB_A)
        cals = discover_calendars(tmp_path)
        assert cals[0].updated_at is not None
        # Should be timezone-aware
        assert cals[0].updated_at.tzinfo is not None


# ---------------------------------------------------------------------------
# _format_updated
# ---------------------------------------------------------------------------


class TestFormatUpdated:
    """Timestamp always shows human-readable date/time."""

    def test_recent_timestamp(self):
        result = _format_updated(datetime.now(tz=timezone.utc))
        assert "<time " in result
        assert "datetime=" in result

    def test_human_readable_format(self):
        ts = datetime(2026, 4, 10, 14, 30, tzinfo=timezone.utc)
        result = _format_updated(ts)
        assert "10 Apr 2026" in result
        assert "2:30 pm" in result

    def test_am_time(self):
        ts = datetime(2026, 4, 10, 2, 30, tzinfo=timezone.utc)
        result = _format_updated(ts)
        assert "2:30 am" in result


# ---------------------------------------------------------------------------
# _is_translation / _group_calendars
# ---------------------------------------------------------------------------


class TestCleanGroupTitle:
    """Strip language suffix from grouped card titles."""

    def test_strips_in_cz_suffix(self):
        assert _clean_group_title("Galerie – Výstavy (in CZ)", True) == "Galerie – Výstavy"

    def test_strips_cz_suffix(self):
        assert _clean_group_title("Galerie (CZ)", True) == "Galerie"

    def test_no_strip_when_ungrouped(self):
        assert _clean_group_title("Galerie (in CZ)", False) == "Galerie (in CZ)"

    def test_no_suffix_untouched(self):
        assert _clean_group_title("Just a Name", True) == "Just a Name"

    def test_strips_trailing_dash(self):
        assert _clean_group_title("Site – (in CZ)", True) == "Site"


class TestIsTranslation:
    """Detect auto-translated calendar variants."""

    def test_original_is_not_translation(self):
        cal = CalendarInfo("a.ics", "Site (in CZ)", "Desc", "https://x.com")
        assert not _is_translation(cal)

    def test_translated_name_detected(self):
        cal = CalendarInfo("a-en.ics", "Site (EN, auto-translated from CZ)", "", "")
        assert _is_translation(cal)

    def test_translated_desc_detected(self):
        cal = CalendarInfo("a-en.ics", "Site", "Auto-translated to English. Desc", "")
        assert _is_translation(cal)


class TestGroupCalendars:
    """Calendars with the same source_url are grouped together."""

    def test_same_source_url_grouped(self):
        cz = CalendarInfo("site.ics", "Site (in CZ)", "Desc", "https://x.com")
        en = CalendarInfo(
            "site-en.ics",
            "Site (EN, auto-translated from CZ)",
            "Auto-translated. Desc",
            "https://x.com",
        )
        groups = _group_calendars([cz, en])
        assert len(groups) == 1
        assert len(groups[0]) == 2
        assert groups[0][0] == cz  # original first
        assert groups[0][1] == en

    def test_different_source_urls_separate(self):
        a = CalendarInfo("a.ics", "A", "", "https://a.com")
        b = CalendarInfo("b.ics", "B", "", "https://b.com")
        groups = _group_calendars([a, b])
        assert len(groups) == 2

    def test_no_source_url_stays_ungrouped(self):
        a = CalendarInfo("a.ics", "A", "", "")
        b = CalendarInfo("b.ics", "B", "", "")
        groups = _group_calendars([a, b])
        assert len(groups) == 2

    def test_group_order_follows_first_file(self):
        a = CalendarInfo("a.ics", "A", "", "https://a.com")
        b = CalendarInfo("b.ics", "B", "", "https://b.com")
        b_en = CalendarInfo("b-en.ics", "B EN", "Auto-translated", "https://b.com")
        groups = _group_calendars([a, b, b_en])
        assert len(groups) == 2
        assert groups[0][0].filename == "a.ics"
        assert groups[1][0].filename == "b.ics"
        assert len(groups[1]) == 2


# ---------------------------------------------------------------------------
# _strip_source_from_desc
# ---------------------------------------------------------------------------


class TestStripSourceFromDesc:
    """Trailing 'Source: <url>' is removed for index display."""

    def test_strips_trailing_source(self):
        desc = "Unofficial scrape — kids events only. Source: https://example.com/"
        assert _strip_source_from_desc(desc, "https://example.com/") == (
            "Unofficial scrape — kids events only."
        )

    def test_preserves_desc_without_source(self):
        desc = "Just a description with no URL."
        assert _strip_source_from_desc(desc, "") == desc

    def test_empty_desc_stays_empty(self):
        assert _strip_source_from_desc("", "https://example.com") == ""

    def test_no_strip_when_source_url_empty(self):
        desc = "Has text Source: https://example.com/"
        assert _strip_source_from_desc(desc, "") == desc

    def test_strips_http_and_https(self):
        desc = "Events. Source: http://vida.cz/program"
        assert _strip_source_from_desc(desc, "http://vida.cz/program") == "Events."


# ---------------------------------------------------------------------------
# generate_index — content
# ---------------------------------------------------------------------------


class TestGenerateIndexContent:
    """Index generator renders calendar entries and template variables."""

    def test_contains_calendar_names(self, tmp_path):
        (tmp_path / "site-a.ics").write_text(ICS_STUB_A)
        html_out = generate_index(tmp_path)
        assert "Site A – Events" in html_out

    def test_contains_calendar_descriptions(self, tmp_path):
        (tmp_path / "site-a.ics").write_text(ICS_STUB_A)
        html_out = generate_index(tmp_path)
        assert "Unofficial scrape of Site A events." in html_out

    def test_description_strips_source_url(self, tmp_path):
        """The 'Source: <url>' tail is stripped since the URL gets its own link."""
        (tmp_path / "site-a.ics").write_text(ICS_STUB_A)
        html_out = generate_index(tmp_path)
        assert "Source: https://site-a.example.com/events" not in html_out
        assert 'href="https://site-a.example.com/events"' in html_out

    def test_omits_empty_description(self, tmp_path):
        (tmp_path / "site-b.ics").write_text(ICS_STUB_B)
        html_out = generate_index(tmp_path)
        assert "Site B – Family Fun" in html_out

    def test_contains_ics_link(self, tmp_path):
        (tmp_path / "site-a.ics").write_text(ICS_STUB_A)
        html_out = generate_index(tmp_path)
        assert 'href="site-a.ics"' in html_out

    def test_contains_source_link(self, tmp_path):
        (tmp_path / "site-a.ics").write_text(ICS_STUB_A)
        html_out = generate_index(tmp_path)
        assert 'href="https://site-a.example.com/events"' in html_out
        assert "🔗 Source" in html_out

    def test_no_source_link_when_missing(self, tmp_path):
        (tmp_path / "bare.ics").write_text(
            "BEGIN:VCALENDAR\nVERSION:2.0\nX-WR-CALNAME:Bare\nEND:VCALENDAR\n"
        )
        html_out = generate_index(tmp_path)
        assert "🔗 Source" not in html_out

    def test_multiple_calendars(self, tmp_path):
        (tmp_path / "site-a.ics").write_text(ICS_STUB_A)
        (tmp_path / "site-b.ics").write_text(ICS_STUB_B)
        html_out = generate_index(tmp_path)
        assert "Site A – Events" in html_out
        assert "Site B – Family Fun" in html_out

    def test_title_and_subtitle(self, tmp_path):
        (tmp_path / "site-a.ics").write_text(ICS_STUB_A)
        html_out = generate_index(tmp_path, title="My Calendars", subtitle="Updated daily")
        assert "My Calendars" in html_out
        assert "Updated daily" in html_out

    def test_default_title(self, tmp_path):
        (tmp_path / "site-a.ics").write_text(ICS_STUB_A)
        html_out = generate_index(tmp_path)
        assert "Calendar Feeds" in html_out

    def test_generated_at_timestamp(self, tmp_path):
        (tmp_path / "site-a.ics").write_text(ICS_STUB_A)
        html_out = generate_index(tmp_path)
        assert "Generated by cal-scraper on" in html_out

    def test_timezone_note_in_footer(self, tmp_path):
        (tmp_path / "site-a.ics").write_text(ICS_STUB_A)
        html_out = generate_index(tmp_path)
        assert "All times shown in" in html_out

    def test_updated_at_rendered(self, tmp_path):
        """Each calendar card shows its file's last-updated time."""
        (tmp_path / "site-a.ics").write_text(ICS_STUB_A)
        html_out = generate_index(tmp_path)
        assert "Updated " in html_out
        assert "<time " in html_out
        assert 'class="meta"' in html_out

    def test_html_escaping(self, tmp_path):
        """Special characters in ICS headers are HTML-escaped."""
        xss_ics = (
            "BEGIN:VCALENDAR\nVERSION:2.0\n"
            'X-WR-CALNAME:Events <script>alert("xss")</script>\n'
            'X-WR-CALDESC:Desc with "quotes" & <ampersands>\n'
            "END:VCALENDAR\n"
        )
        (tmp_path / "tricky.ics").write_text(xss_ics)
        html_out = generate_index(tmp_path)
        assert "<script>" not in html_out
        assert "&lt;script&gt;" in html_out
        assert "&amp;" in html_out

    def test_webcal_links_with_base_url(self, tmp_path):
        """CAL_BASE_URL produces webcal:// subscribe links."""
        (tmp_path / "site-a.ics").write_text(ICS_STUB_A)
        html_out = generate_index(tmp_path, base_url="cal.example.com")
        assert 'href="webcal://cal.example.com/site-a.ics"' in html_out

    def test_relative_links_without_base_url(self, tmp_path):
        """Without CAL_BASE_URL, links stay relative."""
        (tmp_path / "site-a.ics").write_text(ICS_STUB_A)
        html_out = generate_index(tmp_path, base_url="")
        assert 'href="site-a.ics"' in html_out
        assert "webcal://" not in html_out


# ---------------------------------------------------------------------------
# Custom template
# ---------------------------------------------------------------------------


class TestCustomTemplate:
    """Index generator uses custom template when provided."""

    def test_custom_template(self, tmp_path):
        tpl = tmp_path / "custom.html"
        tpl.write_text("<html>$title|$calendars|$generated_at</html>")
        out = tmp_path / "out"
        out.mkdir()
        (out / "site-a.ics").write_text(ICS_STUB_A)
        html_out = generate_index(out, template_path=tpl, title="Custom Title")
        assert html_out.startswith("<html>Custom Title|")
        assert "Site A" in html_out

    def test_safe_substitute_ignores_unknown_vars(self, tmp_path):
        """Unknown $variables are left as-is (safe_substitute)."""
        tpl = tmp_path / "custom.html"
        tpl.write_text("$title $unknown_var $calendars")
        out = tmp_path / "out"
        out.mkdir()
        (out / "site-a.ics").write_text(ICS_STUB_A)
        html_out = generate_index(out, template_path=tpl)
        assert "$unknown_var" in html_out


# ---------------------------------------------------------------------------
# CLI integration — --no-index, --index-template, directory scanning
# ---------------------------------------------------------------------------


MOCK_EVENTS = [
    pytest.importorskip("cal_scraper.models").Event(
        title="E1",
        dtstart=__import__("datetime").datetime(
            2026, 4, 8, 16, 0,
            tzinfo=pytest.importorskip("cal_scraper.models").PRAGUE_TZ,
        ),
        dtend=None,
        all_day=False,
        venue="V",
        description="D",
        url="https://example.com/1/",
        raw_date="8/4/2026",
    ),
]

MOCK_ICS = (
    "BEGIN:VCALENDAR\nVERSION:2.0\nX-WR-CALNAME:Mock\n"
    "X-CAL-SOURCE-URL:https://example.com\nEND:VCALENDAR\n"
)


@pytest.fixture(autouse=True)
def _mock_external_sites():
    """Prevent real HTTP during CLI tests."""
    with patch("cal_scraper.sites.hvezdarna.scrape", return_value=MOCK_EVENTS), \
         patch("cal_scraper.sites.ikea_brno.scrape", return_value=MOCK_EVENTS), \
         patch("cal_scraper.sites.vida.scrape", return_value=MOCK_EVENTS):
        yield


class TestCliIndexGeneration:
    """CLI generates index.html by default, scanning the output directory."""

    def test_index_generated_by_default(self, tmp_path):
        out = tmp_path / "out"
        out.mkdir()
        with patch("cal_scraper.sites.moravska_galerie.scrape", return_value=MOCK_EVENTS), \
             patch("cal_scraper.cli.events_to_ics", return_value=MOCK_ICS):
            from cal_scraper.cli import main
            result = main(["--site", "moravska-galerie", "-d", str(out)])
        assert result == 0
        index = out / "index.html"
        assert index.exists()
        content = index.read_text()
        assert "Mock" in content
        assert 'href="moravska-galerie.ics"' in content

    def test_no_index_flag(self, tmp_path):
        out = tmp_path / "out"
        out.mkdir()
        with patch("cal_scraper.sites.moravska_galerie.scrape", return_value=MOCK_EVENTS), \
             patch("cal_scraper.cli.events_to_ics", return_value=MOCK_ICS):
            from cal_scraper.cli import main
            result = main(["--site", "moravska-galerie", "--no-index", "-d", str(out)])
        assert result == 0
        assert not (out / "index.html").exists()

    def test_dry_run_skips_index(self, tmp_path):
        with patch("cal_scraper.sites.moravska_galerie.scrape", return_value=MOCK_EVENTS), \
             patch("cal_scraper.cli.events_to_ics", return_value=MOCK_ICS):
            from cal_scraper.cli import main
            result = main(["--site", "moravska-galerie", "--dry-run"])
        assert result == 0

    def test_custom_template_via_flag(self, tmp_path):
        out = tmp_path / "out"
        out.mkdir()
        tpl = tmp_path / "my.html"
        tpl.write_text("CUSTOM:$title|$calendars|$generated_at")
        with patch("cal_scraper.sites.moravska_galerie.scrape", return_value=MOCK_EVENTS), \
             patch("cal_scraper.cli.events_to_ics", return_value=MOCK_ICS):
            from cal_scraper.cli import main
            result = main([
                "--site", "moravska-galerie",
                "--index-template", str(tpl),
                "-d", str(out),
            ])
        assert result == 0
        content = (out / "index.html").read_text()
        assert content.startswith("CUSTOM:")

    def test_index_includes_suffix_filename(self, tmp_path):
        """Index links to suffixed filename when --filename-suffix is used."""
        out = tmp_path / "out"
        out.mkdir()
        with patch("cal_scraper.sites.moravska_galerie.scrape", return_value=MOCK_EVENTS), \
             patch("cal_scraper.cli.events_to_ics", return_value=MOCK_ICS):
            from cal_scraper.cli import main
            result = main([
                "--site", "moravska-galerie",
                "--filename-suffix=-en",
                "-d", str(out),
            ])
        assert result == 0
        content = (out / "index.html").read_text()
        assert 'href="moravska-galerie-en.ics"' in content

    def test_index_picks_up_preexisting_files(self, tmp_path):
        """Index includes .ics files from prior runs, not just the current one."""
        out = tmp_path / "out"
        out.mkdir()
        # Simulate a prior run that left a Czech file
        (out / "moravska-galerie.ics").write_text(MOCK_ICS)
        # Now run just the English variant
        with patch("cal_scraper.sites.moravska_galerie.scrape", return_value=MOCK_EVENTS), \
             patch("cal_scraper.cli.events_to_ics", return_value=MOCK_ICS):
            from cal_scraper.cli import main
            result = main([
                "--site", "moravska-galerie",
                "--filename-suffix=-en",
                "-d", str(out),
            ])
        assert result == 0
        content = (out / "index.html").read_text()
        # Both should be listed
        assert 'href="moravska-galerie.ics"' in content
        assert 'href="moravska-galerie-en.ics"' in content

    def test_index_only_generates_index_without_scraping(self, tmp_path):
        """--index-only regenerates index.html from existing .ics files, no scraping."""
        out = tmp_path / "out"
        out.mkdir()
        # Pre-populate with .ics files from a "prior run"
        (out / "moravska-galerie.ics").write_text(MOCK_ICS)
        from cal_scraper.cli import main
        # No scrape mock needed — scraping should not be called
        with patch("cal_scraper.sites.moravska_galerie.scrape") as mock_scrape:
            result = main(["--index-only", "-d", str(out)])
        assert result == 0
        mock_scrape.assert_not_called()
        index = out / "index.html"
        assert index.exists()
        content = index.read_text()
        assert 'href="moravska-galerie.ics"' in content

    def test_index_only_with_custom_template(self, tmp_path):
        """--index-only respects --index-template."""
        out = tmp_path / "out"
        out.mkdir()
        (out / "site.ics").write_text(MOCK_ICS)
        tpl = tmp_path / "custom.html"
        tpl.write_text("CUSTOM:$title|$calendars|$generated_at")
        from cal_scraper.cli import main
        result = main(["--index-only", "--index-template", str(tpl), "-d", str(out)])
        assert result == 0
        content = (out / "index.html").read_text()
        assert content.startswith("CUSTOM:")

    def test_index_only_and_no_index_mutually_exclusive(self):
        """--index-only and --no-index cannot be used together."""
        from cal_scraper.cli import main
        with pytest.raises(SystemExit):
            main(["--index-only", "--no-index"])
