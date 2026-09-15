"""OPML download, parsing and merging."""

from __future__ import annotations

import io
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from app.config import (
    DOWNLOAD_TIMEOUT,
    OPML_SOURCES,
    USER_AGENT,
    Config,
)


def download_opml(url: str, dest: Path) -> None:
    """Download an OPML file from *url* and write it to *dest*."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT) as resp:
        dest.write_bytes(resp.read())


def download_all_opmls(config: Config) -> dict[str, Path]:
    """Download every configured OPML source. Returns {filename: path}."""
    config.opml_dir.mkdir(parents=True, exist_ok=True)
    downloaded: dict[str, Path] = {}
    for i, source in enumerate(OPML_SOURCES, 1):
        dest = config.opml_dir / source["filename"]
        print(f"Descargando OPML {i}/{len(OPML_SOURCES)}: {source['url']}", flush=True)
        try:
            download_opml(source["url"], dest)
            downloaded[source["filename"]] = dest
        except Exception as e:
            print(f"  Error descargando {source['url']}: {e}", flush=True)
    return downloaded


def parse_opml(data: Path | bytes) -> list[dict[str, str]]:
    """Parse an OPML file (Path or raw bytes) into a list of blog dicts."""
    if isinstance(data, bytes):
        root = ET.fromstring(data)
    else:
        root = ET.parse(data).getroot()  # type: ignore[union-attr]

    blogs: list[dict[str, str]] = []
    for outline in root.iter("outline"):
        xml_url = outline.get("xmlUrl")
        if xml_url:
            blogs.append(
                {
                    "name": outline.get("text", ""),
                    "html_url": outline.get("htmlUrl", ""),
                    "xml_url": xml_url,
                }
            )
    return blogs


def merge_opmls(opml_paths: list[Path]) -> bytes:
    """Merge multiple OPML files, deduplicating by xmlUrl.

    Returns the merged XML as bytes.
    """
    seen: set[str] = set()
    merged: list[dict[str, str]] = []

    for path in opml_paths:
        for blog in parse_opml(path):
            if blog["xml_url"] not in seen:
                seen.add(blog["xml_url"])
                merged.append(blog)

    return _build_opml_xml(merged)


def _build_opml_xml(blogs: list[dict[str, str]]) -> bytes:
    """Build an OPML 2.0 XML document from a list of blog dicts."""
    opml = ET.Element("opml", version="2.0")
    head = ET.SubElement(opml, "head")
    ET.SubElement(head, "title").text = "Engineering Blogs"
    body = ET.SubElement(opml, "body")
    outline = ET.SubElement(body, "outline", text="Engineering Blogs")

    for blog in blogs:
        ET.SubElement(
            outline,
            "outline",
            type="rss",
            text=blog["name"],
            htmlUrl=blog["html_url"],
            xmlUrl=blog["xml_url"],
        )

    ET.indent(opml, space="  ")
    buf = io.BytesIO()
    ET.ElementTree(opml).write(buf, encoding="utf-8", xml_declaration=True)
    return buf.getvalue()


def ensure_opml(config: Config) -> Path:
    """Download sources, merge, and persist only if content changed.

    Returns the path to the merged OPML file.
    """
    downloaded = download_all_opmls(config)
    if not downloaded:
        raise RuntimeError("No se pudo descargar ningún OPML.")

    print(f"Mergeando {len(downloaded)} OPMLs...", flush=True)
    merged_bytes = merge_opmls(list(downloaded.values()))
    merged_count = len(parse_opml(merged_bytes))
    print(f"  {merged_count} feeds únicos en el OPML mergeado.", flush=True)

    new_hash = _sha256_hex(merged_bytes)

    prev_hash: str | None = None
    if config.opml_file.exists():
        prev_hash = _sha256_hex(config.opml_file.read_bytes())

    if prev_hash != new_hash:
        config.opml_dir.mkdir(parents=True, exist_ok=True)
        config.opml_file.write_bytes(merged_bytes)
        print("  OPML mergeado actualizado.", flush=True)
    else:
        print("  Sin cambios en el OPML mergeado.", flush=True)

    return config.opml_file


def _sha256_hex(data: bytes) -> str:
    """Return the hex-encoded SHA-256 digest of *data*."""
    import hashlib

    return hashlib.sha256(data).hexdigest()
