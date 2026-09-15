#!/usr/bin/env python3
"""
Fetch engineering blog RSS feeds and generate a static HTML page.
Uses a JSON cache to accumulate posts across runs (incremental).
Downloads and merges multiple OPML sources.
"""

import argparse
import hashlib
import io
import json
import os
import xml.etree.ElementTree as ET
import feedparser
import concurrent.futures
import html
import urllib.request
from datetime import datetime
from pathlib import Path

TIMEOUT = 5
MAX_WORKERS = 25  # max concurrent RSS fetches

REPO_ROOT = Path(__file__).parent.parent

OPML_SOURCES = [
    {
        "url": "https://raw.githubusercontent.com/kilimchoi/engineering-blogs/master/engineering_blogs.opml",
        "filename": "download_1.opml",
    },
    {
        "url": "https://engineeringblogs.xyz/engblogs.opml",
        "filename": "download_2.opml",
    },
]

MERGED_FILENAME = "engineering_blogs.opml"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fetch_blogs",
        description="Genera index.html a partir de OPMLs descargados y mergeados.",
        epilog=(
            "Modo contenedor (por defecto): usa la variable de entorno OUTPUT_DIR. "
            "Modo local: usa --local."
        ),
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Ejecutar en local: la salida se escribe en la raíz de tech-blogs.",
    )
    return parser


def resolve_paths() -> tuple[Path, Path]:
    """Devuelve (opml_file, output_dir) según el modo de ejecución."""
    args = build_parser().parse_args()

    if args.local:
        output_dir = REPO_ROOT
    else:
        output_dir = Path(os.environ.get("OUTPUT_DIR", REPO_ROOT))

    opml = output_dir / "opml" / MERGED_FILENAME

    return opml, output_dir


OPML_FILE, OUTPUT_DIR = resolve_paths()
OUTPUT_FILE = OUTPUT_DIR / "index.html"
CACHE_FILE = OUTPUT_DIR / "posts_cache.json"
OPML_DIR = OUTPUT_DIR / "opml"


def download_opml(url: str, dest: Path) -> None:
    """Descarga un OPML desde una URL y lo guarda en dest."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "EngineeringBlogsAggregator/1.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        dest.write_bytes(resp.read())


def download_all_opmls() -> dict[str, Path]:
    """Descarga todas las fuentes OPML y devuelve {filename: path}."""
    OPML_DIR.mkdir(parents=True, exist_ok=True)
    downloaded = {}
    for i, source in enumerate(OPML_SOURCES, 1):
        dest = OPML_DIR / source["filename"]
        print(f"Descargando OPML {i}/{len(OPML_SOURCES)}: {source['url']}", flush=True)
        try:
            download_opml(source["url"], dest)
            downloaded[source["filename"]] = dest
        except Exception as e:
            print(f"  Error descargando {source['url']}: {e}", flush=True)
    return downloaded


def parse_opml(data: Path | bytes) -> list[dict]:
    if isinstance(data, bytes):
        root = ET.fromstring(data)
    else:
        root = ET.parse(data).getroot()
    blogs = []
    for outline in root.iter("outline"):
        xml_url = outline.get("xmlUrl")
        if xml_url:
            blogs.append({
                "name": outline.get("text", ""),
                "html_url": outline.get("htmlUrl", ""),
                "xml_url": xml_url,
            })
    return blogs


def merge_opmls_bytes(opml_paths: list[Path]) -> bytes:
    """Mergea múltiples OPMLs deduplicando por xmlUrl.
    Devuelve el XML resultante como bytes, sin escribir a disco."""
    seen_xml_urls: set[str] = set()
    merged_blogs: list[dict] = []

    for path in opml_paths:
        blogs = parse_opml(path)
        for blog in blogs:
            if blog["xml_url"] not in seen_xml_urls:
                seen_xml_urls.add(blog["xml_url"])
                merged_blogs.append(blog)

    # Construir XML
    opml = ET.Element("opml", version="2.0")
    head = ET.SubElement(opml, "head")
    ET.SubElement(head, "title").text = "Engineering Blogs"
    body = ET.SubElement(opml, "body")
    outline = ET.SubElement(body, "outline", text="Engineering Blogs")

    for blog in merged_blogs:
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


def sha256_hex(data: bytes) -> str:
    """Devuelve el hash SHA-256 de unos bytes."""
    return hashlib.sha256(data).hexdigest()


def ensure_opml() -> Path:
    """Asegura que existe el OPML mergeado.
    Descarga las fuentes, mergea en memoria y escribe solo si hay cambios."""
    # Descargar fuentes
    downloaded = download_all_opmls()
    if not downloaded:
        print("ERROR: no se pudo descargar ningún OPML.", flush=True)
        exit(1)

    # Mergear en memoria
    print(f"Mergeando {len(downloaded)} OPMLs...", flush=True)
    merged_bytes = merge_opmls_bytes(list(downloaded.values()))
    merged_count = len(parse_opml(merged_bytes))
    print(f"  {merged_count} feeds únicos en el OPML mergeado.", flush=True)

    # Comparar hash y escribir solo si hay cambios
    new_hash = sha256_hex(merged_bytes)

    prev_hash = None
    if OPML_FILE.exists():
        prev_hash = sha256_hex(OPML_FILE.read_bytes())

    if prev_hash != new_hash:
        OPML_DIR.mkdir(parents=True, exist_ok=True)
        OPML_FILE.write_bytes(merged_bytes)
        print("  OPML mergeado actualizado.", flush=True)
    else:
        print("  Sin cambios en el OPML mergeado.", flush=True)

    return OPML_FILE


def load_cache() -> dict[str, dict]:
    """Load cache as {link: post_dict} for O(1) lookups."""
    if not CACHE_FILE.exists():
        return {}
    data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    return {p["link"]: p for p in data}


def save_cache(cache: dict[str, dict]) -> dict[str, dict]:
    """Persist cache and return the same dict."""
    posts = sorted(cache.values(), key=lambda p: p.get("published") or "", reverse=True)
    CACHE_FILE.write_text(json.dumps(posts, ensure_ascii=False, indent=1), encoding="utf-8")
    return cache


def fetch_feed(blog: dict) -> list[dict]:
    try:
        req = urllib.request.Request(
            blog["xml_url"],
            headers={"User-Agent": "EngineeringBlogsAggregator/1.0"},
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = resp.read()
        feed = feedparser.parse(data)
        if not feed.entries:
            return []
        posts = []
        for entry in feed.entries[:5]:
            published = None
            for date_attr in ("published_parsed", "updated_parsed", "created_parsed"):
                t = getattr(entry, date_attr, None)
                if t:
                    try:
                        published = datetime(*t[:6])
                    except Exception:
                        pass
                    break
            posts.append({
                "blog_name": blog["name"],
                "blog_url": blog["html_url"],
                "title": getattr(entry, "title", "Sin titulo"),
                "link": getattr(entry, "link", blog["html_url"]),
                "published": published.isoformat() if published else None,
            })
        return posts
    except Exception:
        return []


def generate_html(posts: list[dict]) -> str:
    # Agrupar posts por día
    days: dict[str, list[dict]] = {}
    for p in posts:
        date_str = p["published"][:10] if p.get("published") else "Sin fecha"
        if date_str not in days:
            days[date_str] = []
        days[date_str].append(p)

    # Generar HTML para cada día
    day_sections = []
    for date_str, day_posts in days.items():
        post_items = []
        for p in day_posts:
            title_escaped = html.escape(p["title"])
            link_escaped = html.escape(p["link"])
            blog_escaped = html.escape(p["blog_name"])
            blog_url_escaped = html.escape(p["blog_url"])
            time_str = p["published"][11:16] if p.get("published") and len(p["published"]) > 16 else ""
            post_items.append(f'''
            <div class="post-card">
              <div class="post-time">{time_str}</div>
              <div class="post-info">
                <a href="{link_escaped}" target="_blank" class="post-title">{title_escaped}</a>
                <a href="{blog_url_escaped}" target="_blank" class="post-blog">{blog_escaped}</a>
              </div>
            </div>''')
        
        post_count = len(day_posts)
        day_sections.append(f'''
        <div class="day-section" data-date="{date_str}">
          <button class="day-button" onclick="toggleDay(this)">
            <span class="day-date">{date_str}</span>
            <span class="day-count">{post_count} posts</span>
            <span class="day-arrow">&#9660;</span>
          </button>
          <div class="day-content">
            {"".join(post_items)}
          </div>
        </div>''')

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    total_posts = len(posts)
    total_days = len(days)
    
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Engineering Blogs</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ 
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; 
    background: linear-gradient(135deg, #0d1117 0%, #161b22 100%); 
    color: #c9d1d9; 
    min-height: 100vh;
    padding: 2rem;
  }}
  .container {{ max-width: 900px; margin: 0 auto; }}
  
  header {{
    text-align: center;
    margin-bottom: 2rem;
  }}
  h1 {{ 
    color: #58a6ff; 
    font-size: 2.2rem;
    margin-bottom: 0.5rem;
    text-shadow: 0 0 20px rgba(88, 166, 255, 0.3);
  }}
  .meta {{ 
    color: #8b949e; 
    font-size: 0.9rem;
  }}
  .stats {{
    display: flex;
    justify-content: center;
    gap: 2rem;
    margin-top: 1rem;
    flex-wrap: wrap;
  }}
  .stat {{
    background: #21262d;
    padding: 0.8rem 1.5rem;
    border-radius: 8px;
    border: 1px solid #30363d;
  }}
  .stat-value {{
    font-size: 1.5rem;
    font-weight: bold;
    color: #58a6ff;
  }}
  .stat-label {{
    font-size: 0.75rem;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }}

  .search-box {{ 
    display: block; 
    margin: 0 auto 2rem; 
    max-width: 400px; 
    padding: 0.8rem 1.2rem; 
    border: 1px solid #30363d; 
    border-radius: 8px; 
    background: #21262d; 
    color: #c9d1d9; 
    font-size: 1rem;
    transition: all 0.3s ease;
  }}
  .search-box:focus {{ 
    outline: none; 
    border-color: #58a6ff;
    box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.2);
  }}

  .day-section {{
    margin-bottom: 1rem;
    border-radius: 10px;
    overflow: hidden;
    background: #21262d;
    border: 1px solid #30363d;
    transition: all 0.3s ease;
  }}
  .day-section:hover {{
    border-color: #58a6ff;
    box-shadow: 0 4px 20px rgba(88, 166, 255, 0.1);
  }}
  .day-section.hidden {{
    display: none;
  }}

  .day-button {{
    width: 100%;
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem 1.5rem;
    background: transparent;
    border: none;
    color: #c9d1d9;
    cursor: pointer;
    transition: background 0.2s ease;
  }}
  .day-button:hover {{
    background: rgba(88, 166, 255, 0.1);
  }}

  .day-date {{
    font-size: 1.1rem;
    font-weight: 600;
    color: #58a6ff;
  }}
  .day-count {{
    font-size: 0.85rem;
    color: #8b949e;
    background: #30363d;
    padding: 0.2rem 0.6rem;
    border-radius: 12px;
  }}
  .day-arrow {{
    margin-left: auto;
    font-size: 0.8rem;
    color: #8b949e;
    transition: transform 0.3s ease;
  }}
  .day-button.active .day-arrow {{
    transform: rotate(180deg);
  }}

  .day-content {{
    max-height: 0;
    overflow: hidden;
    transition: max-height 0.4s ease;
    padding: 0 1.5rem;
  }}
  .day-content.open {{
    max-height: 5000px;
    padding: 0 1.5rem 1rem;
  }}

  .post-card {{
    display: flex;
    gap: 1rem;
    padding: 0.8rem;
    border-bottom: 1px solid #30363d;
    transition: background 0.2s ease;
  }}
  .post-card:last-child {{
    border-bottom: none;
  }}
  .post-card:hover {{
    background: rgba(88, 166, 255, 0.05);
    border-radius: 6px;
  }}

  .post-time {{
    min-width: 50px;
    color: #8b949e;
    font-size: 0.85rem;
    font-family: monospace;
  }}

  .post-info {{
    flex: 1;
    min-width: 0;
  }}
  .post-title {{
    display: block;
    color: #c9d1d9;
    font-weight: 500;
    text-decoration: none;
    margin-bottom: 0.3rem;
    line-height: 1.4;
  }}
  .post-title:hover {{
    color: #58a6ff;
    text-decoration: underline;
  }}
  .post-blog {{
    font-size: 0.8rem;
    color: #8b949e;
    text-decoration: none;
  }}
  .post-blog:hover {{
    color: #58a6ff;
    text-decoration: underline;
  }}

  .count {{ 
    text-align: center; 
    color: #8b949e; 
    margin-top: 2rem; 
    font-size: 0.85rem;
  }}

  @media (max-width: 640px) {{
    body {{ padding: 1rem; }}
    h1 {{ font-size: 1.6rem; }}
    .day-button {{ padding: 0.8rem 1rem; }}
    .day-date {{ font-size: 1rem; }}
    .post-card {{ flex-direction: column; gap: 0.3rem; }}
    .post-time {{ min-width: auto; }}
  }}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>&#128187; Engineering Blogs</h1>
    <p class="meta">Actualizado: {now}</p>
    <div class="stats">
      <div class="stat">
        <div class="stat-value">{total_posts}</div>
        <div class="stat-label">Posts</div>
      </div>
      <div class="stat">
        <div class="stat-value">{total_days}</div>
        <div class="stat-label">Días</div>
      </div>
    </div>
  </header>

  <input type="text" class="search-box" id="search" placeholder="&#128269; Buscar posts..." oninput="filter()">

  <div id="days-container">
    {"".join(day_sections)}
  </div>

  <p class="count" id="count">{total_posts} posts en {total_days} días</p>
</div>

<script>
function toggleDay(btn) {{
  const content = btn.nextElementSibling;
  const isOpen = content.classList.contains('open');
  
  content.classList.toggle('open');
  btn.classList.toggle('active');
}}

function filter() {{
  const q = document.getElementById("search").value.toLowerCase();
  let visiblePosts = 0;
  let visibleDays = 0;
  
  document.querySelectorAll(".day-section").forEach(section => {{
    const posts = section.querySelectorAll(".post-card");
    let dayVisiblePosts = 0;
    
    posts.forEach(card => {{
      const text = card.textContent.toLowerCase();
      const match = text.includes(q);
      card.style.display = match ? "" : "none";
      if (match) dayVisiblePosts++;
    }});
    
    if (dayVisiblePosts > 0) {{
      section.classList.remove("hidden");
      visibleDays++;
      visiblePosts += dayVisiblePosts;
      
      if (q.length > 0) {{
        const content = section.querySelector(".day-content");
        const btn = section.querySelector(".day-button");
        content.classList.add("open");
        btn.classList.add("active");
      }}
    }} else {{
      section.classList.add("hidden");
    }}
  }});
  
  document.getElementById("count").textContent = visiblePosts + " posts en " + visibleDays + " días";
}}

// Abrir el primer día por defecto
document.addEventListener("DOMContentLoaded", function() {{
  const firstButton = document.querySelector(".day-button");
  if (firstButton) {{
    toggleDay(firstButton);
  }}
}});
</script>
</body>
</html>"""


def main():
    opml_path = ensure_opml()
    blogs = parse_opml(opml_path)
    cache = load_cache()
    prev_count = len(cache)
    print(f"Cache previo: {prev_count} posts. Obteniendo {len(blogs)} feeds...", flush=True)

    fetched_posts: list[dict] = []
    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(fetch_feed, b): b for b in blogs}
        for future in concurrent.futures.as_completed(futures):
            done += 1
            if done % 50 == 0:
                print(f"  {done}/{len(blogs)}...", flush=True)
            fetched_posts.extend(future.result())

    new_count = 0
    for p in fetched_posts:
        if p["link"] not in cache:
            cache[p["link"]] = p
            new_count += 1

    cache = save_cache(cache)
    final_count = len(cache)

    all_posts = sorted(cache.values(), key=lambda p: p.get("published") or "", reverse=True)
    OUTPUT_FILE.write_text(generate_html(all_posts), encoding="utf-8")

    print(f"\nFetched: {len(fetched_posts)} | Nuevos: {new_count} | Cache total: {final_count} (was {prev_count})", flush=True)
    print(f"HTML generado: {OUTPUT_FILE}", flush=True)


if __name__ == "__main__":
    main()
