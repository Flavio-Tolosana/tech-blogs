"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from app.config import Config

SAMPLE_OPML = b"""<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <head><title>Sample</title></head>
  <body>
    <outline text="Blog A" htmlUrl="https://a.example" xmlUrl="https://a.example/rss.xml"/>
    <outline text="Blog B" htmlUrl="https://b.example" xmlUrl="https://b.example/feed"/>
  </body>
</opml>
"""

SAMPLE_RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Blog A</title>
    <link>https://a.example</link>
    <description>desc</description>
    <item>
      <title>Post 1</title>
      <link>https://a.example/posts/1</link>
      <pubDate>Mon, 15 Sep 2025 10:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Post 2</title>
      <link>https://a.example/posts/2</link>
      <pubDate>Tue, 16 Sep 2025 12:30:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


@pytest.fixture
def sample_opml_bytes() -> bytes:
    return SAMPLE_OPML


@pytest.fixture
def sample_rss_bytes() -> bytes:
    return SAMPLE_RSS


@pytest.fixture
def tmp_config(tmp_path) -> Config:
    """Config whose output lives in a pytest tmp dir."""
    return Config(output_dir=tmp_path)