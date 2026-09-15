"""Tests for app.html_generator."""

from __future__ import annotations

from app.html_generator import generate_html, group_by_day, render_day_section, render_post_card

POSTS = [
    {
        "blog_name": "Blog A",
        "blog_url": "https://a.example",
        "title": "Post 1",
        "link": "https://a.example/1",
        "published": "2025-09-15T10:00:00",
    },
    {
        "blog_name": "Blog B",
        "blog_url": "https://b.example",
        "title": "Post 2",
        "link": "https://b.example/2",
        "published": "2025-09-15T12:30:00",
    },
    {
        "blog_name": "Blog C",
        "blog_url": "https://c.example",
        "title": "Post 3",
        "link": "https://c.example/3",
        "published": "2025-09-16T08:00:00",
    },
]

UNPUBLISHED = {
    "blog_name": "Blog D",
    "blog_url": "https://d.example",
    "title": "Sin fecha",
    "link": "https://d.example/4",
    "published": None,
}


def test_group_by_day_splits_dates():
    days = group_by_day(POSTS + [UNPUBLISHED])
    assert set(days.keys()) == {"2025-09-15", "2025-09-16", "Sin fecha"}
    assert len(days["2025-09-15"]) == 2


def test_render_post_card_escapes_html():
    malicious = {
        "blog_name": "<script>alert(1)</script>",
        "blog_url": "https://x.example",
        "title": "A & B",
        "link": "https://x.example/1",
        "published": "2025-09-15T10:00:00",
    }
    html = render_post_card(malicious)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "A &amp; B" in html
    assert "10:00" in html


def test_render_post_card_no_time_for_unpublished():
    html = render_post_card(UNPUBLISHED)
    assert 'post-time"></div>' in html or 'class="post-time"' in html


def test_render_day_section_contains_count():
    html = render_day_section("2025-09-15", [POSTS[0], POSTS[1]])
    assert 'data-date="2025-09-15"' in html
    assert "2 posts" in html
    assert 'href="https://a.example/1"' in html


def test_generate_html_substitutes_all_vars(tmp_config):
    html = generate_html(POSTS, tmp_config.template_dir, updated_at="2025-09-16 20:05")
    assert "<title>Engineering Blogs</title>" in html
    assert "Actualizado: 2025-09-16 20:05" in html
    assert "3 posts en 2 días" in html
    assert "data-date=\"2025-09-15\"" in html
    assert "stat-value\">3<" in html


def test_generate_html_handles_empty_posts(tmp_config):
    html = generate_html([], tmp_config.template_dir, updated_at="2025-09-16 20:05")
    assert "0 posts en 0 días" in html
    assert 'id="days-container">' in html


def test_template_has_no_remaining_placeholders(tmp_config):
    html = generate_html(POSTS, tmp_config.template_dir, updated_at="2025-09-16 20:05")
    assert "${" not in html