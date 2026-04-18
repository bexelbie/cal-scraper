"""Tests for Czech date/time parser — all 6+ format variants + LLM fallback."""

import json
from datetime import date, datetime, timedelta
from unittest.mock import patch


from cal_scraper.sites.moravska_galerie.date_parser import parse_date, parse_dates
from cal_scraper.models import PRAGUE_TZ


# ---------------------------------------------------------------------------
# DATE-01: Single day + whole hour ("31/3/2026, 15 H")
# ---------------------------------------------------------------------------

class TestSingleDayHour:
    """DATE-01: D/M/YYYY, HH H → timed event with 2h default duration."""

    def test_basic(self):
        result = parse_date("● 31/3/2026, 15 H")
        assert result is not None
        assert result.dtstart == datetime(2026, 3, 31, 15, 0, tzinfo=PRAGUE_TZ)
        assert result.dtend == datetime(2026, 3, 31, 17, 0, tzinfo=PRAGUE_TZ)
        assert result.all_day is False
        assert result.raw_text == "31/3/2026, 15 H"

    def test_no_space_after_bullet(self):
        """Bullet with no trailing space must also work."""
        result = parse_date("●16/4/2026, 16 H")
        assert result is not None
        assert result.dtstart == datetime(2026, 4, 16, 16, 0, tzinfo=PRAGUE_TZ)

    def test_morning_time(self):
        result = parse_date("● 30/5/2026, 10 H")
        assert result is not None
        assert result.dtstart == datetime(2026, 5, 30, 10, 0, tzinfo=PRAGUE_TZ)
        assert result.dtend == datetime(2026, 5, 30, 12, 0, tzinfo=PRAGUE_TZ)

    def test_default_duration_is_2_hours(self):
        result = parse_date("● 2/4/2026, 10 H")
        assert result.dtend - result.dtstart == timedelta(hours=2)


# ---------------------------------------------------------------------------
# DATE-02: Single day + hour.minutes ("8/4/2026, 16.30 H")
# ---------------------------------------------------------------------------

class TestSingleDayHourMinutes:
    """DATE-02: D/M/YYYY, HH.MM H → timed event with dot-separated minutes."""

    def test_basic(self):
        result = parse_date("● 8/4/2026, 16.30 H")
        assert result is not None
        assert result.dtstart == datetime(2026, 4, 8, 16, 30, tzinfo=PRAGUE_TZ)
        assert result.dtend == datetime(2026, 4, 8, 18, 30, tzinfo=PRAGUE_TZ)
        assert result.all_day is False

    def test_minute_value(self):
        result = parse_date("● 8/4/2026, 16.30 H")
        assert result.dtstart.minute == 30

    def test_default_duration(self):
        result = parse_date("● 8/4/2026, 16.30 H")
        assert result.dtend - result.dtstart == timedelta(hours=2)


# ---------------------------------------------------------------------------
# DATE-03: Single day, no time — all-day event ("23/5/2026")
# ---------------------------------------------------------------------------

class TestDateOnly:
    """DATE-03: D/M/YYYY → all-day event."""

    def test_basic(self):
        result = parse_date("● 23/5/2026")
        assert result is not None
        assert result.dtstart == date(2026, 5, 23)
        assert result.dtend == date(2026, 5, 24)  # exclusive end
        assert result.all_day is True

    def test_dtstart_is_date_not_datetime(self):
        result = parse_date("● 23/5/2026")
        assert type(result.dtstart) is date


# ---------------------------------------------------------------------------
# DATE-04: Multi-day range, no time ("7/7 – 11/7/2026")
# ---------------------------------------------------------------------------

class TestMultiDayRange:
    """DATE-04: D/M – D/M/YYYY → all-day spanning event with en-dash."""

    def test_basic(self):
        result = parse_date("● 7/7 – 11/7/2026")
        assert result is not None
        assert result.dtstart == date(2026, 7, 7)
        assert result.dtend == date(2026, 7, 12)  # exclusive end: 11 + 1
        assert result.all_day is True

    def test_year_inferred_from_end_date(self):
        """Start date has no year — inferred from end date."""
        result = parse_date("● 7/7 – 11/7/2026")
        assert result.dtstart == date(2026, 7, 7)

    def test_en_dash_required(self):
        """Must use en-dash U+2013, not hyphen U+002D."""
        result = parse_date("● 7/7 - 11/7/2026")  # ASCII hyphen
        # This should NOT match the multi-day pattern
        assert result is None


# ---------------------------------------------------------------------------
# DATE-05: Multi-day + time range ("27/7 – 31/7/2026, 9–16 H")
# ---------------------------------------------------------------------------

class TestMultiDayTimeRange:
    """DATE-05: D/M – D/M/YYYY, H–H H → all-day spanning event (camp-style)."""

    def test_basic(self):
        result = parse_date("● 27/7 – 31/7/2026, 9–16 H")
        assert result is not None
        assert result.dtstart == date(2026, 7, 27)
        assert result.dtend == date(2026, 8, 1)  # exclusive DTEND
        assert result.all_day is True

    def test_is_date_not_datetime(self):
        result = parse_date("● 27/7 – 31/7/2026, 9–16 H")
        assert isinstance(result.dtstart, date)
        assert not isinstance(result.dtstart, datetime)

    def test_exclusive_dtend(self):
        result = parse_date("● 27/7 – 31/7/2026, 9–16 H")
        # DTEND is exclusive: 31st + 1 day = Aug 1
        assert result.dtend == date(2026, 8, 1)

    def test_different_dates(self):
        result = parse_date("● 13/7 – 17/7/2026, 9–16 H")
        assert result is not None
        assert result.dtstart == date(2026, 7, 13)
        assert result.dtend == date(2026, 7, 18)  # exclusive DTEND


# ---------------------------------------------------------------------------
# DATE-06: European date order (D/M/Y — day first, month second)
# ---------------------------------------------------------------------------

class TestEuropeanDateOrder:
    """DATE-06: Day extracted first, month second — verified by 31/3 = March 31."""

    def test_day_month_order(self):
        result = parse_date("● 31/3/2026, 15 H")
        assert result.dtstart.day == 31
        assert result.dtstart.month == 3

    def test_single_digit_day_month(self):
        result = parse_date("● 8/4/2026, 16.30 H")
        assert result.dtstart.day == 8
        assert result.dtstart.month == 4


# ---------------------------------------------------------------------------
# Multiple time slots ("24/5/2026, 15 H / 16 H / 17 H")
# ---------------------------------------------------------------------------

class TestMultipleTimeSlots:
    """Bonus format: multiple time slots — one ParsedDate per slot."""

    def test_returns_all_time_slots(self):
        results = parse_date("● 24/5/2026, 15 H / 16 H / 17 H")
        assert results is not None
        assert results.dtstart.hour == 15

    def test_parse_dates_returns_three(self):
        from cal_scraper.sites.moravska_galerie.date_parser import parse_dates
        results = parse_dates("● 24/5/2026, 15 H / 16 H / 17 H")
        assert len(results) == 3

    def test_parse_dates_hours(self):
        from cal_scraper.sites.moravska_galerie.date_parser import parse_dates
        results = parse_dates("● 24/5/2026, 15 H / 16 H / 17 H")
        hours = [r.dtstart.hour for r in results]
        assert hours == [15, 16, 17]

    def test_each_slot_has_default_duration(self):
        from cal_scraper.sites.moravska_galerie.date_parser import parse_dates
        results = parse_dates("● 24/5/2026, 15 H / 16 H / 17 H")
        for r in results:
            assert r.dtend - r.dtstart == timedelta(hours=2)

    def test_each_slot_is_timed(self):
        from cal_scraper.sites.moravska_galerie.date_parser import parse_dates
        results = parse_dates("● 24/5/2026, 15 H / 16 H / 17 H")
        for r in results:
            assert r.all_day is False

    def test_two_slots(self):
        from cal_scraper.sites.moravska_galerie.date_parser import parse_dates
        results = parse_dates("● 24/5/2026, 10 H / 14 H")
        assert len(results) == 2
        assert results[0].dtstart.hour == 10
        assert results[1].dtstart.hour == 14


# ---------------------------------------------------------------------------
# D-04: Error handling — warn and skip
# ---------------------------------------------------------------------------

class TestErrorHandling:
    """D-04: Unknown formats return None with logged warning."""

    def test_not_a_date(self):
        assert parse_date("not a date") is None

    def test_empty_string(self):
        assert parse_date("") is None

    def test_random_text_with_year(self):
        assert parse_date("some random text 2026") is None

    def test_logs_warning(self, caplog):
        """Warning should be logged for unrecognized formats."""
        import logging
        with caplog.at_level(logging.WARNING):
            parse_date("not a date")
        assert "Unrecognized date format" in caplog.text
        assert "not a date" in caplog.text


# ---------------------------------------------------------------------------
# Preprocessing: bullet stripping
# ---------------------------------------------------------------------------

class TestPreprocessing:
    """Bullet prefix stripped, whitespace normalized."""

    def test_bullet_with_space(self):
        result = parse_date("● 31/3/2026, 15 H")
        assert result is not None

    def test_bullet_without_space(self):
        result = parse_date("●31/3/2026, 15 H")
        assert result is not None

    def test_leading_trailing_whitespace(self):
        result = parse_date("  ● 31/3/2026, 15 H  ")
        assert result is not None

    def test_raw_text_is_cleaned(self):
        """raw_text should be the cleaned version (without bullet)."""
        result = parse_date("● 31/3/2026, 15 H")
        assert result.raw_text == "31/3/2026, 15 H"


# ---------------------------------------------------------------------------
# DATE-07: Single day + time range ("23/5/2026, 13–22 H")
# ---------------------------------------------------------------------------

class TestSingleDayTimeRange:
    """DATE-07: D/M/YYYY, HH–HH H → timed event with explicit start/end hours."""

    def test_basic(self):
        result = parse_date("● 23/5/2026, 13\u201322 H")
        assert result is not None
        assert result.dtstart == datetime(2026, 5, 23, 13, 0, tzinfo=PRAGUE_TZ)
        assert result.dtend == datetime(2026, 5, 23, 22, 0, tzinfo=PRAGUE_TZ)
        assert result.all_day is False
        assert result.raw_text == "23/5/2026, 13\u201322 H"

    def test_not_estimated_end(self):
        """End time is explicit, so estimated_end should be False."""
        result = parse_date("23/5/2026, 13\u201322 H")
        assert result.estimated_end is False

    def test_short_range(self):
        """Single-hour range like 9–10 H."""
        result = parse_date("1/6/2026, 9\u201310 H")
        assert result is not None
        assert result.dtstart == datetime(2026, 6, 1, 9, 0, tzinfo=PRAGUE_TZ)
        assert result.dtend == datetime(2026, 6, 1, 10, 0, tzinfo=PRAGUE_TZ)


# ---------------------------------------------------------------------------
# LLM fallback tests
# ---------------------------------------------------------------------------

def _mock_openai_response(content: str) -> dict:
    """Build a fake Azure OpenAI chat completion response."""
    return {"choices": [{"message": {"content": content}}]}


class TestLlmFallback:
    """LLM fallback activates when no regex matches."""

    def _patch_llm(self, json_content):
        """Patch Azure OpenAI to return the given JSON content."""
        resp_body = _mock_openai_response(json.dumps(json_content))
        return patch(
            "cal_scraper.translator._call_azure_openai",
            return_value=resp_body,
        )

    def _patch_config(self):
        """Patch load_azure_config to return dummy creds."""
        return patch(
            "cal_scraper.translator.load_azure_config",
            return_value={
                "azure_openai_endpoint": "https://fake",
                "azure_openai_key": "fake",
                "azure_openai_deployment": "fake",
                "azure_openai_api_version": "2024-01-01",
            },
        )

    def test_llm_parses_timed_event(self):
        """LLM returns a timed event with explicit start and end."""
        llm_response = [{
            "start_day": 23, "start_month": 5, "start_year": 2026,
            "start_hour": 13, "start_minute": 0,
            "end_day": None, "end_month": None, "end_year": None,
            "end_hour": 22, "end_minute": 0,
            "all_day": False,
        }]
        # Use a format no regex handles — e.g. "23. května 2026, 13–22h"
        with self._patch_config(), self._patch_llm(llm_response):
            results = parse_dates("23. května 2026, 13–22h")
        assert len(results) == 1
        assert results[0].dtstart == datetime(2026, 5, 23, 13, 0, tzinfo=PRAGUE_TZ)
        assert results[0].dtend == datetime(2026, 5, 23, 22, 0, tzinfo=PRAGUE_TZ)
        assert results[0].all_day is False

    def test_llm_parses_all_day_event(self):
        """LLM returns an all-day event."""
        llm_response = [{
            "start_day": 1, "start_month": 6, "start_year": 2026,
            "start_hour": None, "start_minute": None,
            "end_day": None, "end_month": None, "end_year": None,
            "end_hour": None, "end_minute": None,
            "all_day": True,
        }]
        with self._patch_config(), self._patch_llm(llm_response):
            results = parse_dates("1. června 2026")
        assert len(results) == 1
        assert results[0].dtstart == date(2026, 6, 1)
        assert results[0].all_day is True

    def test_llm_parses_multi_day_range(self):
        """LLM returns a multi-day all-day range."""
        llm_response = [{
            "start_day": 7, "start_month": 7, "start_year": 2026,
            "start_hour": None, "start_minute": None,
            "end_day": 11, "end_month": 7, "end_year": 2026,
            "end_hour": None, "end_minute": None,
            "all_day": True,
        }]
        with self._patch_config(), self._patch_llm(llm_response):
            results = parse_dates("7.–11. července 2026")
        assert len(results) == 1
        assert results[0].dtstart == date(2026, 7, 7)
        # End is exclusive (day after last day)
        assert results[0].dtend == date(2026, 7, 12)
        assert results[0].all_day is True

    def test_llm_start_only_uses_default_duration(self):
        """When LLM gives start time but no end, default 2h duration applies."""
        llm_response = [{
            "start_day": 15, "start_month": 8, "start_year": 2026,
            "start_hour": 19, "start_minute": 30,
            "end_day": None, "end_month": None, "end_year": None,
            "end_hour": None, "end_minute": None,
            "all_day": False,
        }]
        with self._patch_config(), self._patch_llm(llm_response):
            results = parse_dates("15. srpna 2026 v 19:30")
        assert len(results) == 1
        assert results[0].dtstart == datetime(2026, 8, 15, 19, 30, tzinfo=PRAGUE_TZ)
        assert results[0].dtend == datetime(2026, 8, 15, 21, 30, tzinfo=PRAGUE_TZ)
        assert results[0].estimated_end is True

    def test_llm_not_called_when_regex_matches(self):
        """LLM should never be called for a known regex format."""
        with patch(
            "cal_scraper.sites.moravska_galerie.date_parser._llm_parse_date"
        ) as mock_llm:
            result = parse_date("31/3/2026, 15 H")
            mock_llm.assert_not_called()
            assert result is not None

    def test_no_credentials_returns_empty(self):
        """When Azure creds are missing, fallback returns empty (no crash)."""
        from cal_scraper.translator import TranslationError
        with patch(
            "cal_scraper.translator.load_azure_config",
            side_effect=TranslationError("no creds"),
        ):
            results = parse_dates("something totally unknown")
        assert results == []

    def test_llm_bad_json_returns_empty(self):
        """When LLM returns garbage, fallback returns empty (no crash)."""
        bad_resp = _mock_openai_response("this is not json at all")
        with self._patch_config(), patch(
            "cal_scraper.translator._call_azure_openai",
            return_value=bad_resp,
        ):
            results = parse_dates("something totally unknown")
        assert results == []

    def test_llm_markdown_fences_stripped(self):
        """LLM sometimes wraps JSON in markdown code fences."""
        llm_response = [{
            "start_day": 5, "start_month": 5, "start_year": 2026,
            "start_hour": 10, "start_minute": 0,
            "end_hour": 12, "end_minute": 0,
            "all_day": False,
        }]
        fenced = f"```json\n{json.dumps(llm_response)}\n```"
        resp = _mock_openai_response(fenced)
        with self._patch_config(), patch(
            "cal_scraper.translator._call_azure_openai",
            return_value=resp,
        ):
            results = parse_dates("5. května 2026, 10–12h")
        assert len(results) == 1
        assert results[0].dtstart == datetime(2026, 5, 5, 10, 0, tzinfo=PRAGUE_TZ)
