"""Tests for app.cli / app.__main__."""

from __future__ import annotations

from app import __main__ as entry
from app.cli import build_parser, main, resolve_config
from app.config import DIST_DIR


def test_build_parser_defaults_to_container_mode():
    args = build_parser().parse_args([])
    assert args.local is False


def test_build_parser_local_flag():
    args = build_parser().parse_args(["--local"])
    assert args.local is True


def test_resolve_config_local():
    args = build_parser().parse_args(["--local"])
    cfg = resolve_config(args)
    assert cfg.output_dir == DIST_DIR


def test_resolve_config_env(monkeypatch, tmp_path):
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))
    args = build_parser().parse_args([])
    cfg = resolve_config(args)
    assert cfg.output_dir == tmp_path


def test_main_runs_pipeline_successfully(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))
    fake_opml = tmp_path / "fake.opml"
    fake_opml.write_bytes(b"<opml/>")

    monkeypatch.setattr("app.cli.opml.ensure_opml", lambda cfg: fake_opml)
    monkeypatch.setattr(
        "app.cli.opml.parse_opml",
        lambda path: [{"name": "B", "html_url": "https://b", "xml_url": "https://b/rss"}],
    )
    monkeypatch.setattr(
        "app.cli.feed.fetch_all_feeds",
        lambda blogs: [
            {
                "title": "P",
                "link": "https://b/p",
                "blog_name": "B",
                "blog_url": "https://b",
                "published": None,
            }
        ],
    )

    assert main([]) == 0
    assert (tmp_path / "index.html").exists()
    assert (tmp_path / "posts_cache.json").exists()


def test_main_returns_error_code_on_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))

    def boom(config):
        raise RuntimeError("no OPML")

    monkeypatch.setattr("app.cli.opml.ensure_opml", boom)
    assert main([]) == 1


def test_entry_modules_expose_same_main():
    assert entry.main is main