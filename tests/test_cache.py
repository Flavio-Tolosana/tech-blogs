"""Tests for app.cache."""

from __future__ import annotations

import json

from app.cache import load_cache, merge_new_posts, save_cache

POST_A = {"title": "A", "link": "https://x.example/a", "published": "2025-09-15T10:00:00"}
POST_B = {"title": "B", "link": "https://x.example/b", "published": "2025-09-16T10:00:00"}
POST_C = {"title": "C", "link": "https://x.example/c", "published": "2025-09-17T10:00:00"}


def test_load_cache_returns_empty_when_missing(tmp_path):
    assert load_cache(tmp_path / "nope.json") == {}


def test_load_cache_indexes_by_link(tmp_path):
    cache_file = tmp_path / "cache.json"
    cache_file.write_text(json.dumps([POST_A, POST_B]), encoding="utf-8")
    cache = load_cache(cache_file)
    assert set(cache.keys()) == {POST_A["link"], POST_B["link"]}
    assert cache[POST_A["link"]] == POST_A


def test_save_cache_sorts_by_published_desc(tmp_path):
    cache = {p["link"]: p for p in [POST_A, POST_C, POST_B]}
    save_cache(cache, tmp_path / "cache.json")
    stored = json.loads((tmp_path / "cache.json").read_text(encoding="utf-8"))
    assert [p["title"] for p in stored] == ["C", "B", "A"]


def test_save_cache_roundtrip(tmp_path):
    cache_file = tmp_path / "cache.json"
    save_cache({POST_A["link"]: POST_A}, cache_file)
    reloaded = load_cache(cache_file)
    assert reloaded[POST_A["link"]] == POST_A


def test_merge_new_posts_counts_only_new(tmp_path):
    cache = {POST_A["link"]: POST_A}
    n = merge_new_posts(cache, [POST_A, POST_B, POST_C])
    assert n == 2
    assert set(cache.keys()) == {POST_A["link"], POST_B["link"], POST_C["link"]}


def test_merge_new_posts_keeps_existing_ordering(tmp_path):
    cache = {}
    assert merge_new_posts(cache, []) == 0
    assert cache == {}