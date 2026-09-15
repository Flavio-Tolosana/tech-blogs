#!/usr/bin/env python3
"""Backward-compatible entry point (Docker CMD / script usage)."""

import sys
from pathlib import Path

# Allow running as `python app/fetch_blogs.py` by ensuring the parent is importable
_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from app.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())