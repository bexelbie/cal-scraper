"""Tests for the translation_cache module."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from cal_scraper.models import PRAGUE_TZ, Event
from cal_scraper.translation_cache import TranslationCache, _content_hash


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

SAMPLE_EVENT_DIFFERENT_DESC = Event(
    title="Tvořivá dílna pro rodiny",
    dtstart=datetime(2026, 5, 10, 14, 0, tzinfo=PRAGUE_TZ),
    dtend=datetime(2026, 5, 10, 16, 0, tzinfo=PRAGUE_TZ),
    all_day=False,
    venue="Moravská galerie",
    description="Nový popis workshopu.",
    url="https://moravska-galerie.cz/event/1",
    raw_date="10. 5. 2026, 14:00–16:00",
    price="50 Kč",
    reservation="online",
)


@pytest.fixture
def cache(tmp_path):
    """Create a fresh cache in a temporary directory."""
    db_path = tmp_path / "translations.db"
    c = TranslationCache(db_path)
    yield c
    c.close()


# ---------------------------------------------------------------------------
# _content_hash
# ---------------------------------------------------------------------------


class TestContentHash:
    def test_deterministic(self):
        h1 = _content_hash("moravska-galerie", SAMPLE_EVENT)
        h2 = _content_hash("moravska-galerie", SAMPLE_EVENT)
        assert h1 == h2

    def test_different_site_different_hash(self):
        h1 = _content_hash("moravska-galerie", SAMPLE_EVENT)
        h2 = _content_hash("hvezdarna", SAMPLE_EVENT)
        assert h1 != h2

    def test_different_description_different_hash(self):
        h1 = _content_hash("moravska-galerie", SAMPLE_EVENT)
        h2 = _content_hash("moravska-galerie", SAMPLE_EVENT_DIFFERENT_DESC)
        assert h1 != h2

    def test_hash_is_hex_string(self):
        h = _content_hash("test", SAMPLE_EVENT)
        assert len(h) == 64  # SHA-256 hex
        assert all(c in "0123456789abcdef" for c in h)


# ---------------------------------------------------------------------------
# TranslationCache
# ---------------------------------------------------------------------------


class TestTranslationCache:
    def test_miss_returns_none(self, cache):
        result = cache.get("moravska-galerie", SAMPLE_EVENT)
        assert result is None

    def test_put_and_get(self, cache):
        cache.put("moravska-galerie", SAMPLE_EVENT, "Creative Workshop", "Come create.")
        result = cache.get("moravska-galerie", SAMPLE_EVENT)
        assert result == ("Creative Workshop", "Come create.")

    def test_different_site_is_separate(self, cache):
        cache.put("moravska-galerie", SAMPLE_EVENT, "Workshop MG", "MG desc")
        result = cache.get("hvezdarna", SAMPLE_EVENT)
        assert result is None

    def test_changed_description_is_cache_miss(self, cache):
        cache.put("moravska-galerie", SAMPLE_EVENT, "Workshop", "Desc")
        result = cache.get("moravska-galerie", SAMPLE_EVENT_DIFFERENT_DESC)
        assert result is None

    def test_put_overwrites_existing(self, cache):
        cache.put("moravska-galerie", SAMPLE_EVENT, "Old title", "Old desc")
        cache.put("moravska-galerie", SAMPLE_EVENT, "New title", "New desc")
        result = cache.get("moravska-galerie", SAMPLE_EVENT)
        assert result == ("New title", "New desc")

    def test_creates_parent_directories(self, tmp_path):
        db_path = tmp_path / "sub" / "dir" / "translations.db"
        c = TranslationCache(db_path)
        c.put("test", SAMPLE_EVENT, "Title", "Desc")
        result = c.get("test", SAMPLE_EVENT)
        assert result == ("Title", "Desc")
        c.close()

    def test_persists_across_instances(self, tmp_path):
        db_path = tmp_path / "translations.db"
        c1 = TranslationCache(db_path)
        c1.put("site", SAMPLE_EVENT, "Cached Title", "Cached Desc")
        c1.close()

        c2 = TranslationCache(db_path)
        result = c2.get("site", SAMPLE_EVENT)
        assert result == ("Cached Title", "Cached Desc")
        c2.close()
