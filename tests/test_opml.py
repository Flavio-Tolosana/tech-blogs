"""Tests for app.opml."""

from __future__ import annotations

from app.opml import ensure_opml, merge_opmls, parse_opml

OPML_A = b"""<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <head><title>A</title></head>
  <body>
    <outline text="Shared" xmlUrl="https://shared.example/rss"/>
    <outline text="OnlyInA" htmlUrl="https://a.example" xmlUrl="https://only-a.example/feed"/>
  </body>
</opml>
"""

OPML_B = b"""<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <head><title>B</title></head>
  <body>
    <outline text="Shared" xmlUrl="https://shared.example/rss"/>
    <outline text="OnlyInB" htmlUrl="https://b.example" xmlUrl="https://only-b.example/feed"/>
  </body>
</opml>
"""

CHILD_ONLY = b"""<opml version="2.0"><body>
  <outline text="Folder">
    <outline text="Child" xmlUrl="https://child.example/rss"/>
  </outline>
  <outline text="NoFeed"/>
</body></opml>"""

EXPECTED_A = {
    "name": "Blog A",
    "html_url": "https://a.example",
    "xml_url": "https://a.example/rss.xml",
}


def _write(tmp_path, name, data):
    path = tmp_path / name
    path.write_bytes(data)
    return path


def test_parse_opml_from_bytes(sample_opml_bytes):
    blogs = parse_opml(sample_opml_bytes)
    assert len(blogs) == 2
    assert blogs[0] == EXPECTED_A


def test_parse_opml_from_path(tmp_path):
    path = _write(tmp_path, "sample.opml", OPML_A)
    blogs = parse_opml(path)
    assert {b["name"] for b in blogs} == {"Shared", "OnlyInA"}


def test_parse_opml_ignores_outlines_without_xmlurl():
    blogs = parse_opml(CHILD_ONLY)
    assert [b["name"] for b in blogs] == ["Child"]


def test_merge_opmls_deduplicates_by_xml_url(tmp_path):
    a = _write(tmp_path, "a.opml", OPML_A)
    b = _write(tmp_path, "b.opml", OPML_B)
    merged = merge_opmls([a, b])
    blogs = parse_opml(merged)
    assert {b["name"] for b in blogs} == {"Shared", "OnlyInA", "OnlyInB"}
    shared = [b for b in blogs if b["name"] == "Shared"]
    assert len(shared) == 1
    assert shared[0]["xml_url"] == "https://shared.example/rss"


def test_ensure_opml_writes_then_skips_unchanged(tmp_path, tmp_config, monkeypatch):
    fake_source = _write(tmp_path, "source.opml", OPML_A)
    monkeypatch.setattr(
        "app.opml.download_all_opmls", lambda cfg: {"source": fake_source}
    )
    monkeypatch.setattr("app.opml.merge_opmls", lambda paths: OPML_A)

    assert not tmp_config.opml_file.exists()
    ensure_opml(tmp_config)
    assert tmp_config.opml_file.exists()
    mtime1 = tmp_config.opml_file.stat().st_mtime_ns

    ensure_opml(tmp_config)
    assert tmp_config.opml_file.stat().st_mtime_ns == mtime1


def test_ensure_opml_raises_when_no_sources_downloaded(tmp_config, monkeypatch):
    monkeypatch.setattr("app.opml.download_all_opmls", lambda cfg: {})
    try:
        ensure_opml(tmp_config)
    except RuntimeError as e:
        assert "OPML" in str(e)
    else:
        raise AssertionError("RuntimeError expected")