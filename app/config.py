"""Application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DIST_DIR = REPO_ROOT / "dist"

MERGED_FILENAME = "engineering_blogs.opml"

OPML_SOURCES: list[dict[str, str]] = [
    {
        "url": "https://raw.githubusercontent.com/kilimchoi/engineering-blogs/master/engineering_blogs.opml",
        "filename": "kilimchoi.opml",
    },
    {
        "url": "https://engineeringblogs.xyz/engblogs.opml",
        "filename": "engineeringblogs_xyz.opml",
    },
]

DEFAULT_TIMEOUT = 5
DEFAULT_MAX_WORKERS = 25
USER_AGENT = "EngineeringBlogsAggregator/1.0"
DOWNLOAD_TIMEOUT = 30


@dataclass
class Config:
    """Runtime configuration resolved from CLI args and environment."""

    output_dir: Path

    @property
    def opml_dir(self) -> Path:
        return self.output_dir / "opml"

    @property
    def opml_file(self) -> Path:
        return self.opml_dir / MERGED_FILENAME

    @property
    def output_file(self) -> Path:
        return self.output_dir / "index.html"

    @property
    def sources_file(self) -> Path:
        return self.output_dir / "sources.html"

    @property
    def cache_file(self) -> Path:
        return self.output_dir / "posts_cache.json"

    @property
    def template_dir(self) -> Path:
        return Path(__file__).parent / "templates"

    @classmethod
    def from_local(cls) -> Config:
        """Config for local execution (output to the repo's dist/ dir)."""
        return cls(output_dir=DIST_DIR)

    @classmethod
    def from_env(cls) -> Config:
        """Config for container execution (uses OUTPUT_DIR env var)."""
        output_dir = Path(os.environ.get("OUTPUT_DIR", str(DIST_DIR)))
        return cls(output_dir=output_dir)
