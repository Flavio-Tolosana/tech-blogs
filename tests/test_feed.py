"""Tests for app.feed."""

from __future__ import annotations

import time
import urllib.request
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.feed import _extract_date, fetch_all_feeds, fetch_feed

BLOG = {
    "name": "Blog A",
    "html_url": "https://a.example",
    "xml_url": "https://a.example/rss.xml",
}


class FakeResponse:
    def __init__(self, data: bytes):
        self._data = data

    def read(self) -> bytes:
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _mock_urlopen(data: bytes) -> MagicMock:
    mock = MagicMock(return_value=FakeResponse(data))
    return mock


def test_fetch_feed_parses_entries(sample_rss_bytes):
    with patch("app.feed.urllib.request.urlopen", _mock_urlopen(sample_rss_bytes)):
        posts = fetch_feed(BLOG)

    assert len(posts) == 2
    assert posts[0]["blog_name"] == "Blog A"
    assert posts[0]["link"] == "https://a.example/posts/1"
    assert posts[0]["published"] == "2025-09-15T10:00:00"


def test_fetch_feed_returns_empty_on_network_error():
    with patch("app.feed.urllib.request.urlopen", side_effect=OSError("boom")):
        assert fetch_feed(BLOG) == []


def test_fetch_feed_handles_missing_title(tmp_path):
    rss = b"""<?xml version="1.0"?><rss version="2.0"><channel>
      <title>X</title><link>https://x.example</link><description>d</description>
      <item><link>https://x.example/1</link></item>
    </channel></rss>"""
    with patch("app.feed.urllib.request.urlopen", _mock_urlopen(rss)):
        posts = fetch_feed(BLOG)
    assert posts[0]["title"] == "Sin titulo"
    assert posts[0]["published"] is None


def test_fetch_feed_limits_to_5_entries(tmp_path):
    items = "".join(
        f"<item><title>Post {i}</title><link>https://a.example/{i}</link></item>"
        for i in range(10)
    )
    rss = (
        b'<?xml version="1.0"?><rss version="2.0"><channel>'
        b"<title>X</title><link>https://a.example</link><description>d</description>"
        + items.encode()
        + b"</channel></rss>"
    )
    with patch("app.feed.urllib.request.urlopen", _mock_urlopen(rss)):
        posts = fetch_feed(BLOG)
    assert len(posts) == 5


def test_extract_date_uses_published_first():
    t = (2025, 9, 15, 10, 30, 45)
    entry = SimpleNamespace(
        published_parsed=t,
        updated_parsed=(2020, 1, 1, 0, 0, 0),
    )
    assert _extract_date(entry) == datetime(2025, 9, 15, 10, 30, 45)


def test_extract_date_falls_back_to_updated():
    entry = SimpleNamespace(
        published_parsed=None,
        updated_parsed=(2025, 9, 15, 10, 30, 45),
    )
    assert _extract_date(entry) == datetime(2025, 9, 15, 10, 30, 45)


def test_extract_date_returns_none_when_all_missing():
    assert _extract_date(SimpleNamespace()) is None


def test_fetch_all_feeds_returns_flat_list(sample_rss_bytes):
    with patch("app.feed.fetch_feed", return_value=[{"title": "p1"}, {"title": "p2"}]):
        posts = fetch_all_feeds([BLOG, BLOG])

    assert len(posts) == 4