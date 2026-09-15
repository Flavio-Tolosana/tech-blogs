"""Tests for app.config."""

from __future__ import annotations

from pathlib import Path

from app.config import DIST_DIR, MERGED_FILENAME, Config


def test_local_config_points_to_dist_dir():
    cfg = Config.from_local()
    assert isinstance(cfg.output_dir, Path)
    assert cfg.output_dir == DIST_DIR
    assert cfg.output_dir.name == "dist"


def test_env_config_uses_output_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))
    cfg = Config.from_env()
    assert cfg.output_dir == tmp_path


def test_env_config_falls_back_to_dist_dir(monkeypatch):
    monkeypatch.delenv("OUTPUT_DIR", raising=False)
    cfg = Config.from_env()
    assert cfg.output_dir == DIST_DIR


def test_config_properties(tmp_path):
    cfg = Config(output_dir=tmp_path)
    assert cfg.opml_dir == tmp_path / "opml"
    assert cfg.opml_file == tmp_path / "opml" / MERGED_FILENAME
    assert cfg.output_file == tmp_path / "index.html"
    assert cfg.cache_file == tmp_path / "posts_cache.json"
    assert cfg.template_dir.name == "templates"