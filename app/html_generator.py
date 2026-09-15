"""Static HTML generation from a template."""

from __future__ import annotations

import html
import string
from datetime import datetime
from pathlib import Path

TEMPLATE_FILENAME = "page.html"
SOURCES_TEMPLATE_FILENAME = "sources.html"
CSS_FILENAME = "styles.css"
FAVORITES_JS_FILENAME = "favorites.js"


def load_template(template_dir: Path, filename: str = TEMPLATE_FILENAME) -> str:
    """Read an HTML template from *template_dir*."""
    return (template_dir / filename).read_text(encoding="utf-8")


def load_asset(template_dir: Path, filename: str) -> str:
    """Read a shared CSS/JS asset from *template_dir*."""
    return (template_dir / filename).read_text(encoding="utf-8")


def group_by_day(posts: list[dict]) -> dict[str, list[dict]]:
    """Group posts by their published date (YYYY-MM-DD)."""
    days: dict[str, list[dict]] = {}
    for p in posts:
        date_str = p["published"][:10] if p.get("published") else "Sin fecha"
        days.setdefault(date_str, []).append(p)
    return days


def render_post_card(post: dict) -> str:
    """Render a single post card as HTML."""
    title = html.escape(post["title"])
    link = html.escape(post["link"])
    blog_name = html.escape(post["blog_name"])
    blog_url = html.escape(post["blog_url"])
    published = post.get("published") or ""
    time_str = published[11:16] if len(published) > 16 else ""

    return f'''
            <div class="post-card" data-blog="{html.escape(post["blog_name"], quote=True)}">
              <div class="post-time">{time_str}</div>
              <div class="post-info">
                <a href="{link}" target="_blank" class="post-title">{title}</a>
                <a href="{blog_url}" target="_blank" class="post-blog">{blog_name}</a>
              </div>
            </div>'''


def get_unique_sources(posts: list[dict]) -> list[dict]:
    """Return deduplicated blog sources (name, url) preserving first-seen order."""
    seen: set[str] = set()
    sources: list[dict[str, str]] = []
    for p in posts:
        name = p.get("blog_name") or ""
        if not name or name in seen:
            continue
        seen.add(name)
        sources.append({"name": name, "url": p.get("blog_url") or ""})
    return sources


def render_sources_section(sources: list[dict]) -> str:
    """Render the interactive sources section with favorite stars."""
    if not sources:
        return ""

    items = "".join(
        f'''
            <div class="source-chip">
              <button type="button" class="source-star" data-name="{html.escape(s['name'], quote=True)}" onclick="toggleFavorite(this)" title="Marcar como favorito" aria-label="Marcar {html.escape(s['name'])} como favorito">&#9734;</button>
              <a href="{html.escape(s['url'])}" target="_blank" rel="noopener" class="source-name" title="{html.escape(s['name'])}">{html.escape(s['name'])}</a>
            </div>'''
        for s in sources
    )

    return f'''
    <section class="sources-section" id="sources">
      <div class="sources-header">
        <h2>&#128203; Orígenes de recursos</h2>
        <span class="sources-count">{len(sources)}</span>
      </div>
      <div class="sources-grid">
        {items}
      </div>
    </section>'''


def render_day_section(date_str: str, day_posts: list[dict]) -> str:
    """Render a collapsible day section with its post cards."""
    post_items = "".join(render_post_card(p) for p in day_posts)
    post_count = len(day_posts)

    return f'''
        <div class="day-section" data-date="{date_str}">
          <button class="day-button" onclick="toggleDay(this)">
            <span class="day-date">{date_str}</span>
            <span class="day-count">{post_count} posts</span>
            <span class="day-arrow">&#9660;</span>
          </button>
          <div class="day-content">
            {post_items}
          </div>
        </div>'''


def generate_html(
    posts: list[dict],
    template_dir: Path,
    updated_at: str | None = None,
) -> str:
    """Render the main page (posts grouped by day) from a sorted list of posts."""
    days = group_by_day(posts)

    day_sections = "".join(
        render_day_section(date_str, day_posts)
        for date_str, day_posts in days.items()
    )

    now = updated_at or datetime.now().strftime("%Y-%m-%d %H:%M")
    total_posts = len(posts)
    total_days = len(days)
    footer_count = f"{total_posts} posts en {total_days} días"
    base_css = load_asset(template_dir, CSS_FILENAME)
    favorites_js = load_asset(template_dir, FAVORITES_JS_FILENAME)

    template = load_template(template_dir)
    return string.Template(template).substitute(
        page_title="Engineering Blogs",
        updated_at=now,
        total_posts=str(total_posts),
        total_days=str(total_days),
        day_sections=day_sections,
        base_css=base_css,
        favorites_js=favorites_js,
        footer_count=footer_count,
    )


def generate_sources_html(
    sources: list[dict],
    template_dir: Path,
    updated_at: str | None = None,
) -> str:
    """Render the dedicated sources page with favorite stars."""
    now = updated_at or datetime.now().strftime("%Y-%m-%d %H:%M")
    base_css = load_asset(template_dir, CSS_FILENAME)
    favorites_js = load_asset(template_dir, FAVORITES_JS_FILENAME)

    template = load_template(template_dir, SOURCES_TEMPLATE_FILENAME)
    return string.Template(template).substitute(
        page_title="Orígenes de recursos",
        updated_at=now,
        total_sources=str(len(sources)),
        sources_section=render_sources_section(sources),
        base_css=base_css,
        favorites_js=favorites_js,
    )