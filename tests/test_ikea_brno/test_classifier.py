"""Tests for IKEA Brno event classifier."""

from cal_scraper.sites.ikea_brno.classifier import (
    classify_event,
    filter_kids_events,
    is_kids_event,
)


def _make_event(name="", intro="", desc="", duration_days=1):
    """Build a minimal event dict for classifier testing."""
    start = 1700000000
    end = start + duration_days * 86400
    return {
        "eventDetails": {
            "cs": {
                "eventName": name,
                "eventIntroduction": intro,
                "eventDescription": desc,
            }
        },
        "timeSlots": [
            {"utcStartDate": start, "utcEndDate": end},
        ],
    }


class TestClassifyEvent:
    """Tests for classify_event function."""

    def test_kids_short_event(self):
        ev = _make_event(name="Tvoření pro děti", duration_days=1)
        assert classify_event(ev) == "kids"

    def test_adult_event(self):
        ev = _make_event(name="Cooking workshop", duration_days=1)
        assert classify_event(ev) == "adult"

    def test_long_promo_no_kids(self):
        ev = _make_event(name="Velká sleva na kuchyně", duration_days=30)
        assert classify_event(ev) == "promo"

    def test_kids_promo_long(self):
        ev = _make_event(
            name="Akce pro děti - zdarma",
            duration_days=14,
        )
        assert classify_event(ev) == "kids-promo"

    def test_kids_ongoing_long(self):
        ev = _make_event(name="Småland otevřen", duration_days=30)
        assert classify_event(ev) == "kids-ongoing"

    def test_adult_with_promo_kw_short(self):
        """Short event with promo keywords but no kids keywords → adult."""
        ev = _make_event(name="Sleva na kuchyně", duration_days=1)
        assert classify_event(ev) == "adult"

    def test_kids_kw_in_intro(self):
        """Kids keyword in eventIntroduction is detected."""
        ev = _make_event(intro="Přijďte s dětmi na malování", duration_days=1)
        assert classify_event(ev) == "kids"

    def test_kids_kw_in_description(self):
        """Kids keyword in eventDescription is detected."""
        ev = _make_event(desc="Pohádkový svět pro děti", duration_days=1)
        assert classify_event(ev) == "kids"

    def test_empty_descriptions(self):
        """Event with all empty text fields → adult."""
        ev = _make_event(name="", intro="", desc="", duration_days=1)
        assert classify_event(ev) == "adult"

    def test_missing_event_details(self):
        """Event missing eventDetails entirely → adult."""
        ev = {"timeSlots": [{"utcStartDate": 1700000000, "utcEndDate": 1700086400}]}
        assert classify_event(ev) == "adult"

    def test_missing_timeslots(self):
        """Event with no timeslots (0 duration) uses ≤7 path."""
        ev = {"eventDetails": {"cs": {"eventName": "Malování pro děti"}}}
        assert classify_event(ev) == "kids"

    def test_exactly_7_days_with_kids_kw(self):
        """Event lasting exactly 7 days with kids kw → kids (≤7)."""
        ev = _make_event(name="Týden pro děti", duration_days=7)
        assert classify_event(ev) == "kids"

    def test_8_days_kids_ongoing(self):
        """Event lasting 8 days with kids kw, no promo → kids-ongoing."""
        ev = _make_event(name="Letní program pro děti", duration_days=8)
        assert classify_event(ev) == "kids-ongoing"


class TestIsKidsEvent:
    """Tests for is_kids_event function."""

    def test_kids_returns_true(self):
        ev = _make_event(name="Tvoření pro děti", duration_days=1)
        assert is_kids_event(ev) is True

    def test_kids_promo_returns_true(self):
        ev = _make_event(name="Akce pro děti - zdarma", duration_days=14)
        assert is_kids_event(ev) is True

    def test_kids_ongoing_returns_true(self):
        ev = _make_event(name="Småland otevřen", duration_days=30)
        assert is_kids_event(ev) is True

    def test_adult_returns_false(self):
        ev = _make_event(name="Workshop", duration_days=1)
        assert is_kids_event(ev) is False

    def test_promo_returns_false(self):
        ev = _make_event(name="Velká sleva", duration_days=30)
        assert is_kids_event(ev) is False


class TestFilterKidsEvents:
    """Tests for filter_kids_events function."""

    def test_filters_to_kids_only(self):
        events = [
            _make_event(name="Malování pro děti", duration_days=1),
            _make_event(name="Adult workshop", duration_days=1),
            _make_event(name="Velká sleva", duration_days=30),
            _make_event(name="Småland otevřen", duration_days=30),
        ]
        result = filter_kids_events(events)
        assert len(result) == 2

    def test_empty_list(self):
        assert filter_kids_events([]) == []

    def test_all_adult(self):
        events = [
            _make_event(name="Workshop A", duration_days=1),
            _make_event(name="Workshop B", duration_days=1),
        ]
        assert filter_kids_events(events) == []
