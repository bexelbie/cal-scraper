"""Tests for the translator module."""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import patch

import pytest

from cal_scraper.models import PRAGUE_TZ, Event
from cal_scraper.translator import (
    TranslationError,
    _build_bilingual_description,
    _format_duration,
    _parse_single_response,
    load_azure_config,
    translate_events,
    translate_single_event,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_EVENT = Event(
    title="Tvořivá dílna pro rodiny",
    dtstart=datetime(2026, 5, 10, 14, 0, tzinfo=PRAGUE_TZ),
    dtend=datetime(2026, 5, 10, 16, 0, tzinfo=PRAGUE_TZ),
    all_day=False,
    venue="Moravská galerie",
    description="Přijďte tvořit s dětmi v galerii.",
    url="https://moravska-galerie.cz/event/1",
    raw_date="10. 5. 2026, 14:00–16:00",
    price="50 Kč",
    reservation="online",
)

SAMPLE_EVENT_ESTIMATED = Event(
    title="Kočičí dobrodružství",
    dtstart=datetime(2026, 5, 10, 10, 0, tzinfo=PRAGUE_TZ),
    dtend=datetime(2026, 5, 10, 10, 55, tzinfo=PRAGUE_TZ),
    all_day=False,
    venue="Hvězdárna Brno",
    description="Animovaný příběh o kotěti.",
    url="https://hvezdarna.cz/show/1",
    raw_date="10. 5. 2026, 10:00",
    estimated_end=True,
)

SAMPLE_EVENT_SOLD_OUT = Event(
    title="[VYPRODÁNO] Rodinná neděle",
    dtstart=datetime(2026, 5, 10, 10, 0, tzinfo=PRAGUE_TZ),
    dtend=datetime(2026, 5, 10, 12, 0, tzinfo=PRAGUE_TZ),
    all_day=False,
    venue="Moravská galerie",
    description="Speciální program.",
    url="https://moravska-galerie.cz/event/2",
    raw_date="10. 5. 2026, 10:00–12:00",
    sold_out=True,
)

SAMPLE_EVENT_EMPTY_DESC = Event(
    title="Småland otevřen",
    dtstart=datetime(2026, 5, 10, 10, 0, tzinfo=PRAGUE_TZ),
    dtend=datetime(2026, 5, 10, 18, 0, tzinfo=PRAGUE_TZ),
    all_day=False,
    venue="IKEA Brno",
    description="",
    url="https://ikea.com/event/1",
    raw_date="10. 5. 2026",
)


# ---------------------------------------------------------------------------
# load_azure_config
# ---------------------------------------------------------------------------


class TestLoadAzureConfig:
    def test_loads_from_env(self, monkeypatch):
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com")
        monkeypatch.setenv("AZURE_OPENAI_KEY", "test-key")
        monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
        monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2025-01-01")

        cfg = load_azure_config()
        assert cfg["azure_openai_endpoint"] == "https://test.openai.azure.com"
        assert cfg["azure_openai_key"] == "test-key"
        assert cfg["azure_openai_deployment"] == "gpt-4o-mini"

    def test_raises_on_missing_vars(self, monkeypatch):
        monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_KEY", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_DEPLOYMENT", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_API_VERSION", raising=False)

        with pytest.raises(TranslationError, match="AZURE_OPENAI_ENDPOINT"):
            load_azure_config()


# ---------------------------------------------------------------------------
# _parse_single_response
# ---------------------------------------------------------------------------


class TestParseSingleResponse:
    def test_parses_valid_json_object(self):
        raw = json.dumps({"title": "Workshop", "description": "Come create."})
        result = _parse_single_response(raw)
        assert result == {"title": "Workshop", "description": "Come create."}

    def test_strips_markdown_fences(self):
        inner = json.dumps({"title": "Test", "description": "Desc"})
        raw = f"```json\n{inner}\n```"
        result = _parse_single_response(raw)
        assert result is not None
        assert result["title"] == "Test"

    def test_returns_none_on_invalid_json(self):
        result = _parse_single_response("not json")
        assert result is None

    def test_returns_none_on_array(self):
        raw = json.dumps([{"title": "Test", "description": "Desc"}])
        result = _parse_single_response(raw)
        assert result is None

    def test_returns_none_on_missing_keys(self):
        raw = json.dumps({"title": "Test"})
        result = _parse_single_response(raw)
        assert result is None


# ---------------------------------------------------------------------------
# _format_duration
# ---------------------------------------------------------------------------


class TestFormatDuration:
    def test_exact_hours(self):
        ev = Event(
            title="t", dtstart=datetime(2026, 1, 1, 10, 0, tzinfo=PRAGUE_TZ),
            dtend=datetime(2026, 1, 1, 12, 0, tzinfo=PRAGUE_TZ),
            all_day=False, venue="", description="", url="", raw_date="",
            estimated_end=True,
        )
        assert _format_duration(ev) == "2h"

    def test_hours_and_minutes(self):
        ev = Event(
            title="t", dtstart=datetime(2026, 1, 1, 10, 0, tzinfo=PRAGUE_TZ),
            dtend=datetime(2026, 1, 1, 11, 30, tzinfo=PRAGUE_TZ),
            all_day=False, venue="", description="", url="", raw_date="",
            estimated_end=True,
        )
        assert _format_duration(ev) == "1h 30min"

    def test_minutes_only(self):
        ev = Event(
            title="t", dtstart=datetime(2026, 1, 1, 10, 0, tzinfo=PRAGUE_TZ),
            dtend=datetime(2026, 1, 1, 10, 55, tzinfo=PRAGUE_TZ),
            all_day=False, venue="", description="", url="", raw_date="",
            estimated_end=True,
        )
        assert _format_duration(ev) == "55min"

    def test_not_estimated(self):
        assert _format_duration(SAMPLE_EVENT) == ""


# ---------------------------------------------------------------------------
# _build_bilingual_description
# ---------------------------------------------------------------------------


class TestBuildBilingualDescription:
    def test_full_layout(self):
        desc = _build_bilingual_description(
            english_desc="Come create with kids.",
            czech_desc="Přijďte tvořit s dětmi v galerii.",
            event=SAMPLE_EVENT,
            estimated_dur_str="",
        )
        assert "Come create with kids." in desc
        assert "---" in desc
        assert "Price/Cena: 50 Kč" in desc
        assert "Reservation: online" in desc
        assert "Datum: 10. 5. 2026, 14:00–16:00" in desc
        assert "Přijďte tvořit s dětmi v galerii." in desc

        # English should come before Czech
        en_pos = desc.index("Come create")
        cz_pos = desc.index("Přijďte tvořit")
        assert en_pos < cz_pos

    def test_estimated_end_note(self):
        desc = _build_bilingual_description(
            english_desc="A story about a kitten.",
            czech_desc="Animovaný příběh o kotěti.",
            event=SAMPLE_EVENT_ESTIMATED,
            estimated_dur_str="55min",
        )
        assert "End time is approximate (duration estimated at 55min)" in desc

    def test_sold_out_note(self):
        desc = _build_bilingual_description(
            english_desc="Special program.",
            czech_desc="Speciální program.",
            event=SAMPLE_EVENT_SOLD_OUT,
            estimated_dur_str="",
        )
        assert "[VYPRODÁNO / SOLD OUT]" in desc

    def test_empty_descriptions(self):
        desc = _build_bilingual_description(
            english_desc="",
            czech_desc="",
            event=SAMPLE_EVENT_EMPTY_DESC,
            estimated_dur_str="",
        )
        # Should still have the details block
        assert "Datum:" in desc
        # Should not have empty sections with trailing whitespace
        lines = desc.split("\n\n")
        # First part is the English disclaimer (no English desc to precede it)
        assert "Unofficial source" in lines[0]

    def test_details_between_english_and_czech(self):
        desc = _build_bilingual_description(
            english_desc="English text here.",
            czech_desc="Czech text here.",
            event=SAMPLE_EVENT,
            estimated_dur_str="",
        )
        parts = desc.split("---")
        assert len(parts) == 3
        assert "English text here." in parts[0]
        assert "Price/Cena:" in parts[1]
        assert "Czech text here." in parts[2]


# ---------------------------------------------------------------------------
# translate_single_event
# ---------------------------------------------------------------------------


class TestTranslateSingleEvent:
    FAKE_CONFIG = {
        "azure_openai_endpoint": "https://test.openai.azure.com",
        "azure_openai_key": "fake",
        "azure_openai_deployment": "gpt-4o-mini",
        "azure_openai_api_version": "2025-01-01",
    }

    def _mock_response(self, title, description):
        """Build a mock Azure OpenAI response for a single event."""
        return {
            "choices": [{
                "message": {
                    "content": json.dumps(
                        {"title": title, "description": description},
                        ensure_ascii=False,
                    )
                },
                "finish_reason": "stop",
            }]
        }

    @patch("cal_scraper.translator._call_azure_openai")
    def test_returns_translated_pair(self, mock_call):
        mock_call.return_value = self._mock_response(
            "Creative Workshop", "Come create with kids."
        )
        result = translate_single_event(SAMPLE_EVENT, self.FAKE_CONFIG)
        assert result == ("Creative Workshop", "Come create with kids.")

    @patch("cal_scraper.translator._call_azure_openai")
    def test_returns_none_on_api_error(self, mock_call):
        mock_call.side_effect = TranslationError("API down")
        result = translate_single_event(SAMPLE_EVENT, self.FAKE_CONFIG)
        assert result is None

    @patch("cal_scraper.translator._call_azure_openai")
    def test_returns_none_on_bad_json(self, mock_call):
        mock_call.return_value = {
            "choices": [{"message": {"content": "not json"}, "finish_reason": "stop"}]
        }
        result = translate_single_event(SAMPLE_EVENT, self.FAKE_CONFIG)
        assert result is None

    @patch("cal_scraper.translator._call_azure_openai")
    def test_returns_none_on_truncation(self, mock_call):
        mock_call.return_value = {
            "choices": [{
                "message": {"content": '{"title": "T", "description":'},
                "finish_reason": "length",
            }]
        }
        result = translate_single_event(SAMPLE_EVENT, self.FAKE_CONFIG)
        assert result is None


# ---------------------------------------------------------------------------
# translate_events (integration with mock)
# ---------------------------------------------------------------------------


class TestTranslateEvents:
    FAKE_CONFIG = {
        "azure_openai_endpoint": "https://test.openai.azure.com",
        "azure_openai_key": "fake",
        "azure_openai_deployment": "gpt-4o-mini",
        "azure_openai_api_version": "2025-01-01",
    }

    def _mock_response(self, title, description):
        """Build a mock Azure OpenAI response for a single event."""
        return {
            "choices": [{
                "message": {
                    "content": json.dumps(
                        {"title": title, "description": description},
                        ensure_ascii=False,
                    )
                },
                "finish_reason": "stop",
            }]
        }

    @patch("cal_scraper.translator._call_azure_openai")
    def test_bilingual_title(self, mock_call):
        mock_call.return_value = self._mock_response(
            "Creative Workshop for Families",
            "Come create with kids in the gallery.",
        )
        result, ok = translate_events([SAMPLE_EVENT], self.FAKE_CONFIG)
        assert ok is True
        assert len(result) == 1
        assert result[0].title == "Creative Workshop for Families / Tvořivá dílna pro rodiny"
        assert result[0].translated is True

    @patch("cal_scraper.translator._call_azure_openai")
    def test_identical_title_no_duplication(self, mock_call):
        """If title is already English, don't duplicate it."""
        mock_call.return_value = self._mock_response("Småland otevřen", "")
        result, ok = translate_events([SAMPLE_EVENT_EMPTY_DESC], self.FAKE_CONFIG)
        assert ok is True
        assert result[0].title == "Småland otevřen"

    @patch("cal_scraper.translator._call_azure_openai")
    def test_bilingual_description_layout(self, mock_call):
        mock_call.return_value = self._mock_response(
            "Creative Workshop", "Come create with kids."
        )
        result, ok = translate_events([SAMPLE_EVENT], self.FAKE_CONFIG)
        assert ok is True
        desc = result[0].description
        assert "Come create with kids." in desc
        assert "Price/Cena: 50 Kč" in desc
        assert "Přijďte tvořit s dětmi v galerii." in desc

    @patch("cal_scraper.translator._call_azure_openai")
    def test_per_event_fallback_on_api_error(self, mock_call):
        """Individual failures fall back to Czech, don't block others."""
        mock_call.side_effect = TranslationError("API down")
        result, ok = translate_events([SAMPLE_EVENT], self.FAKE_CONFIG)
        assert ok is False
        assert result[0].title == SAMPLE_EVENT.title
        assert result[0].translated is False

    @patch("cal_scraper.translator._call_azure_openai")
    def test_empty_events_list(self, mock_call):
        result, ok = translate_events([], self.FAKE_CONFIG)
        assert ok is True
        assert result == []
        mock_call.assert_not_called()

    @patch("cal_scraper.translator._call_azure_openai")
    def test_multiple_events_one_call_each(self, mock_call):
        """Each event gets its own API call."""
        mock_call.side_effect = [
            self._mock_response("Workshop", "Come create."),
            self._mock_response("Cat Adventure", "A story."),
        ]
        events = [SAMPLE_EVENT, SAMPLE_EVENT_ESTIMATED]
        result, ok = translate_events(events, self.FAKE_CONFIG)
        assert ok is True
        assert len(result) == 2
        assert mock_call.call_count == 2

    @patch("cal_scraper.translator._call_azure_openai")
    def test_retry_on_failure(self, mock_call):
        """A failed translation is retried once."""
        call_count = {"n": 0}

        def side_effect(config, messages, **kw):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return {"choices": [{"message": {"content": "oops"}, "finish_reason": "stop"}]}
            return self._mock_response("Workshop", "Come create.")

        mock_call.side_effect = side_effect
        result, ok = translate_events([SAMPLE_EVENT], self.FAKE_CONFIG)
        assert ok is True
        assert len(result) == 1
        assert mock_call.call_count == 2  # initial + retry

    @patch("cal_scraper.translator._call_azure_openai")
    def test_partial_failure_mixed_results(self, mock_call):
        """If one event fails after retry, others still translate."""
        calls = {"n": 0}

        def side_effect(config, messages, **kw):
            calls["n"] += 1
            # First event: succeed
            if calls["n"] == 1:
                return self._mock_response("Workshop", "Come create.")
            # Second event: fail both attempts
            return {"choices": [{"message": {"content": "bad"}, "finish_reason": "stop"}]}

        mock_call.side_effect = side_effect
        events = [SAMPLE_EVENT, SAMPLE_EVENT_ESTIMATED]
        result, ok = translate_events(events, self.FAKE_CONFIG)
        assert ok is False  # not all succeeded
        assert len(result) == 2
        # First event translated
        assert "Workshop" in result[0].title
        assert result[0].translated is True
        # Second event fell back to Czech
        assert result[1].title == SAMPLE_EVENT_ESTIMATED.title
        assert result[1].translated is False

    @patch("cal_scraper.translator._call_azure_openai")
    def test_duplicate_titles_translated_independently(self, mock_call):
        """Events with identical titles each get their own translation call."""
        dup_event_a = Event(
            title="Tajemství pavučiny",
            dtstart=datetime(2026, 5, 24, 10, 0, tzinfo=PRAGUE_TZ),
            dtend=datetime(2026, 5, 24, 12, 0, tzinfo=PRAGUE_TZ),
            all_day=False, venue="Moravská galerie",
            description="Workshop pro děti 4-6 let.",
            url="https://moravska-galerie.cz/event/a",
            raw_date="24. 5. 2026, 10:00–12:00",
        )
        dup_event_b = Event(
            title="Tajemství pavučiny",
            dtstart=datetime(2026, 5, 31, 10, 0, tzinfo=PRAGUE_TZ),
            dtend=datetime(2026, 5, 31, 12, 0, tzinfo=PRAGUE_TZ),
            all_day=False, venue="Moravská galerie",
            description="Workshop pro děti 4-6 let.",
            url="https://moravska-galerie.cz/event/b",
            raw_date="31. 5. 2026, 10:00–12:00",
        )

        mock_call.return_value = self._mock_response(
            "Mystery of the Spider Web", "Workshop for children 4-6 years."
        )
        events = [dup_event_a, dup_event_b]
        result, ok = translate_events(events, self.FAKE_CONFIG)
        assert ok is True
        assert len(result) == 2
        # Both events translated (even though same title)
        assert result[0].translated is True
        assert result[1].translated is True
        assert "Mystery of the Spider Web" in result[0].title
        assert "Mystery of the Spider Web" in result[1].title

    @patch("cal_scraper.translator._call_azure_openai")
    def test_truncated_response_detected(self, mock_call):
        """finish_reason=length signals truncation — should fail."""
        mock_call.return_value = {
            "choices": [{
                "message": {"content": '{"title": "T", "description":'},
                "finish_reason": "length",
            }]
        }
        result, ok = translate_events([SAMPLE_EVENT], self.FAKE_CONFIG)
        assert ok is False
        # Truncation detected on first call + retry
        assert mock_call.call_count == 2
