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
    _build_translation_request,
    _format_duration,
    _parse_translation_response,
    load_azure_config,
    translate_events,
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
# _build_translation_request
# ---------------------------------------------------------------------------


class TestBuildTranslationRequest:
    def test_builds_json_array(self):
        items = _build_translation_request([SAMPLE_EVENT, SAMPLE_EVENT_ESTIMATED])
        assert len(items) == 2
        assert items[0]["id"] == 0
        assert items[0]["title"] == "Tvořivá dílna pro rodiny"
        assert items[1]["id"] == 1
        assert items[1]["description"] == "Animovaný příběh o kotěti."


# ---------------------------------------------------------------------------
# _parse_translation_response
# ---------------------------------------------------------------------------


class TestParseTranslationResponse:
    def test_parses_valid_json(self):
        raw = json.dumps([
            {"id": 0, "title": "Workshop", "description": "Come create."},
            {"id": 1, "title": "Cat Adventure", "description": "Animated story."},
        ])
        result = _parse_translation_response(raw, 2)
        assert len(result) == 2
        assert result[0]["title"] == "Workshop"

    def test_strips_markdown_fences(self):
        inner = json.dumps([{"id": 0, "title": "Test", "description": "Desc"}])
        raw = f"```json\n{inner}\n```"
        result = _parse_translation_response(raw, 1)
        assert len(result) == 1

    def test_returns_empty_on_invalid_json(self):
        result = _parse_translation_response("not json", 1)
        assert result == []

    def test_returns_empty_on_wrong_count(self):
        raw = json.dumps([{"id": 0, "title": "Test", "description": "Desc"}])
        result = _parse_translation_response(raw, 2)
        assert result == []


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
        assert lines[0] == "---"

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
# translate_events (integration with mock)
# ---------------------------------------------------------------------------


class TestTranslateEvents:
    FAKE_CONFIG = {
        "azure_openai_endpoint": "https://test.openai.azure.com",
        "azure_openai_key": "fake",
        "azure_openai_deployment": "gpt-4o-mini",
        "azure_openai_api_version": "2025-01-01",
    }

    def _mock_response(self, translations):
        """Build a mock Azure OpenAI response."""
        return {
            "choices": [{
                "message": {
                    "content": json.dumps(translations, ensure_ascii=False)
                }
            }]
        }

    @patch("cal_scraper.translator._call_azure_openai")
    def test_bilingual_title(self, mock_call):
        mock_call.return_value = self._mock_response([
            {"id": 0, "title": "Creative Workshop for Families",
             "description": "Come create with kids in the gallery."},
        ])
        result, ok = translate_events([SAMPLE_EVENT], self.FAKE_CONFIG)
        assert ok is True
        assert len(result) == 1
        assert result[0].title == "Creative Workshop for Families / Tvořivá dílna pro rodiny"
        assert result[0].translated is True

    @patch("cal_scraper.translator._call_azure_openai")
    def test_identical_title_no_duplication(self, mock_call):
        """If title is already English, don't duplicate it."""
        mock_call.return_value = self._mock_response([
            {"id": 0, "title": "Småland otevřen",
             "description": ""},
        ])
        result, ok = translate_events([SAMPLE_EVENT_EMPTY_DESC], self.FAKE_CONFIG)
        assert ok is True
        assert result[0].title == "Småland otevřen"

    @patch("cal_scraper.translator._call_azure_openai")
    def test_bilingual_description_layout(self, mock_call):
        mock_call.return_value = self._mock_response([
            {"id": 0, "title": "Creative Workshop",
             "description": "Come create with kids."},
        ])
        result, ok = translate_events([SAMPLE_EVENT], self.FAKE_CONFIG)
        assert ok is True
        desc = result[0].description
        assert "Come create with kids." in desc
        assert "Price/Cena: 50 Kč" in desc
        assert "Přijďte tvořit s dětmi v galerii." in desc

    @patch("cal_scraper.translator._call_azure_openai")
    def test_fallback_on_api_error(self, mock_call):
        mock_call.side_effect = TranslationError("API down")
        result, ok = translate_events([SAMPLE_EVENT], self.FAKE_CONFIG)
        assert ok is False
        assert result[0].title == SAMPLE_EVENT.title
        assert result[0].translated is False

    @patch("cal_scraper.translator._call_azure_openai")
    def test_fallback_on_bad_json(self, mock_call):
        mock_call.return_value = {
            "choices": [{"message": {"content": "not valid json"}}]
        }
        result, ok = translate_events([SAMPLE_EVENT], self.FAKE_CONFIG)
        assert ok is False
        assert result[0].title == SAMPLE_EVENT.title

    @patch("cal_scraper.translator._call_azure_openai")
    def test_empty_events_list(self, mock_call):
        result, ok = translate_events([], self.FAKE_CONFIG)
        assert ok is True
        assert result == []
        mock_call.assert_not_called()

    @patch("cal_scraper.translator._call_azure_openai")
    def test_multiple_events_batched(self, mock_call):
        mock_call.return_value = self._mock_response([
            {"id": 0, "title": "Workshop", "description": "Come create."},
            {"id": 1, "title": "Cat Adventure", "description": "A story."},
        ])
        events = [SAMPLE_EVENT, SAMPLE_EVENT_ESTIMATED]
        result, ok = translate_events(events, self.FAKE_CONFIG)
        assert ok is True
        assert len(result) == 2
        # Single API call for both events
        mock_call.assert_called_once()
