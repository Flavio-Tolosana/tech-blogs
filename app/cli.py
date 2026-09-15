"""Command-line entry point and orchestration."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app import cache, feed, html_generator, opml
from app.config import Config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tech-blogs",
        description="Genera index.html a partir de OPMLs descargados y mergeados.",
        epilog=(
            "Modo contenedor (por defecto): usa la variable de entorno OUTPUT_DIR. "
            "Modo local: usa --local."
        ),
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Ejecutar en local: la salida se escribe en dist/.",
    )
    return parser


def resolve_config(args: argparse.Namespace) -> Config:
    """Resolve the runtime Config from parsed CLI args."""
    if args.local:
        return Config.from_local()
    return Config.from_env()


def main(argv: list[str] | None = None) -> int:
    """Run the full fetch pipeline. Returns the exit status."""
    try:
        args = build_parser().parse_args(argv)
        config = resolve_config(args)
        _run_pipeline(config)
        return 0
    except RuntimeError as e:
        print(f"ERROR: {e}", flush=True)
        return 1


def _run_pipeline(config: Config) -> None:
    """Download OPMLs, fetch feeds, update cache and generate index.html."""
    opml_path = opml.ensure_opml(config)
    blogs = opml.parse_opml(opml_path)
    cache_data = cache.load_cache(config.cache_file)
    prev_count = len(cache_data)

    print(f"Cache previo: {prev_count} posts. Obteniendo {len(blogs)} feeds...", flush=True)

    fetched_posts = feed.fetch_all_feeds(blogs)
    new_count = cache.merge_new_posts(cache_data, fetched_posts)
    cache.save_cache(cache_data, config.cache_file)
    final_count = len(cache_data)

    all_posts = cache.sort_posts(cache_data)
    config.output_dir.mkdir(parents=True, exist_ok=True)

    config.output_file.write_text(
        html_generator.generate_html(all_posts, config.template_dir),
        encoding="utf-8",
    )

    sources = html_generator.get_unique_sources(all_posts)
    config.sources_file.write_text(
        html_generator.generate_sources_html(sources, config.template_dir),
        encoding="utf-8",
    )

    print(
        f"\nFetched: {len(fetched_posts)} | Nuevos: {new_count} | "
        f"Cache total: {final_count} (was {prev_count})",
        flush=True,
    )
    print(f"HTML generado: {config.output_file}", flush=True)
    print(f"Fuentes generadas: {config.sources_file}", flush=True)


if __name__ == "__main__":
    sys.exit(main())