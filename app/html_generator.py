"""Static HTML generation from a template."""

from __future__ import annotations

import html
import string
from datetime import datetime
from pathlib import Path

TEMPLATE_FILENAME = "page.html"


def load_template(template_dir: Path) -> str:
    """Read the HTML template from *template_dir*."""
    return (template_dir / TEMPLATE_FILENAME).read_text(encoding="utf-8")


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
            <div class="post-card">
              <div class="post-time">{time_str}</div>
              <div class="post-info">
                <a href="{link}" target="_blank" class="post-title">{title}</a>
                <a href="{blog_url}" target="_blank" class="post-blog">{blog_name}</a>
              </div>
            </div>'''


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
    """Render the full HTML page from a sorted list of posts."""
    days = group_by_day(posts)

    day_sections = "".join(
        render_day_section(date_str, day_posts)
        for date_str, day_posts in days.items()
    )

    now = updated_at or datetime.now().strftime("%Y-%m-%d %H:%M")
    total_posts = len(posts)
    total_days = len(days)
    footer_count = f"{total_posts} posts en {total_days} días"

    template = load_template(template_dir)
    return string.Template(template).substitute(
        page_title="Engineering Blogs",
        updated_at=now,
        total_posts=str(total_posts),
        total_days=str(total_days),
        day_sections=day_sections,
        footer_count=footer_count,
    )