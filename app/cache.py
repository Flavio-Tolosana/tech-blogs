"""JSON post cache with incremental updates."""

from __future__ import annotations

import json
from pathlib import Path


def load_cache(cache_file: Path) -> dict[str, dict[str, str | None]]:
    """Load the post cache as {link: post_dict} for O(1) lookups."""
    if not cache_file.exists():
        return {}
    data = json.loads(cache_file.read_text(encoding="utf-8"))
    return {p["link"]: p for p in data}


def sort_posts(cache: dict[str, dict[str, str | None]]) -> list[dict[str, str | None]]:
    """Return the cached posts sorted by published date descending."""
    return sorted(
        cache.values(),
        key=lambda p: p.get("published") or "",
        reverse=True,
    )


def save_cache(cache: dict[str, dict[str, str | None]], cache_file: Path) -> dict[str, dict[str, str | None]]:
    """Persist the cache to disk (sorted by published date descending)."""
    posts = sort_posts(cache)
    cache_file.write_text(
        json.dumps(posts, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    return cache


def merge_new_posts(
    cache: dict[str, dict[str, str | None]],
    fetched: list[dict[str, str | None]],
) -> int:
    """Add *fetched* posts to *cache*, skipping duplicates by link.

    Returns the number of new posts added.
    """
    new_count = 0
    for p in fetched:
        if p["link"] not in cache:
            cache[p["link"]] = p
            new_count += 1
    return new_count
