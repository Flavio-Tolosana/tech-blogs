"""RSS feed fetching."""

from __future__ import annotations

import concurrent.futures
import urllib.request
from datetime import datetime

import feedparser

from app.config import DEFAULT_MAX_WORKERS, DEFAULT_TIMEOUT, USER_AGENT

_DATE_ATTRS = ("published_parsed", "updated_parsed", "created_parsed")


def fetch_feed(blog: dict[str, str], timeout: int = DEFAULT_TIMEOUT) -> list[dict[str, str | None]]:
    """Fetch a single RSS feed and return the latest posts.

    Each post is a dict with keys: blog_name, blog_url, title, link, published.
    Returns an empty list on any error.
    """
    try:
        req = urllib.request.Request(
            blog["xml_url"],
            headers={"User-Agent": USER_AGENT},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()

        feed = feedparser.parse(data)
        if not feed.entries:
            return []

        posts: list[dict[str, str | None]] = []
        for entry in feed.entries[:5]:
            published = _extract_date(entry)
            posts.append(
                {
                    "blog_name": blog["name"],
                    "blog_url": blog["html_url"],
                    "title": getattr(entry, "title", "Sin titulo"),
                    "link": getattr(entry, "link", blog["html_url"]),
                    "published": published.isoformat() if published else None,
                }
            )
        return posts
    except Exception:
        return []


def fetch_all_feeds(
    blogs: list[dict[str, str]],
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> list[dict[str, str | None]]:
    """Fetch all blogs concurrently and return a flat list of posts."""
    all_posts: list[dict[str, str | None]] = []
    done = 0
    total = len(blogs)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(fetch_feed, b): b for b in blogs}
        for future in concurrent.futures.as_completed(futures):
            done += 1
            if done % 50 == 0:
                print(f"  {done}/{total}...", flush=True)
            all_posts.extend(future.result())

    return all_posts


def _extract_date(entry: feedparser.FeedParserDict) -> datetime | None:
    """Extract the first available date from a feed entry."""
    for attr in _DATE_ATTRS:
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6])  # type: ignore[arg-type]
            except Exception:
                continue
    return None
