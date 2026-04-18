"""Tests for Czech date/time parser — all 6+ format variants."""

from datetime import date, datetime, timedelta


from cal_scraper.sites.moravska_galerie.date_parser import parse_date
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
