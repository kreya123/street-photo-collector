from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from .models import Article


HEADER = [
    "Title",
    "Source",
    "URL",
    "Date",
    "Article Type",
    "Photographer Name",
    "Project / Series / Book / Exhibition Name",
    "Detected Street Genre",
    "Matched Keywords",
    "Relevance Score",
    "Why this was selected",
    "Why this may be useful for my photography",
]


def render_all_outputs(
    articles: list[Article],
    output_path: str | Path,
    notebooklm_path: str | Path,
    csv_path: str | Path,
    errors: list[str] | None = None,
) -> None:
    render_markdown(articles, output_path, errors)
    render_notebooklm_import(articles, notebooklm_path, errors)
    render_csv(articles, csv_path)


def render_markdown(articles: list[Article], output_path: str | Path, errors: list[str] | None = None) -> None:
    path = Path(output_path)
    _ensure_parent(path)

    lines = [
        "# Overseas Street Photography Watchlist",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "Focus: photographers, projects, exhibitions, photobooks, and award results.",
        "Street genre priority: Silent Stories > Fine Art Street > Urban Landscape > Humor or Decisive Moment > Candid > Street Portrait > Street Fashion",
        "",
    ]

    if not articles:
        lines.extend(["No new high-relevance articles were collected.", ""])
    else:
        for index, article in enumerate(articles, start=1):
            lines.extend(
                [
                    f"## {index}. {article.title}",
                    "",
                    f"- Title: {article.title}",
                    f"- Source: {article.source}",
                    f"- URL: {article.url}",
                    f"- Date: {article.published_at or 'Unknown'}",
                    f"- Article Type: {article.article_type}",
                    f"- Photographer Name: {article.photographer_name}",
                    f"- Project / Series / Book / Exhibition Name: {article.project_name}",
                    f"- Detected Street Genre: {article.genre}",
                    f"- Matched Keywords: {_format_keywords(article)}",
                    f"- Relevance Score: {article.relevance_score:.2f}",
                    f"- Why this was selected: {article.why}",
                    f"- Why this may be useful for my photography: {article.photography_use}",
                    "",
                ]
            )

    if errors:
        lines.extend(["---", "", "## Fetch Notes", ""])
        lines.extend(f"- {error}" for error in errors)
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def render_notebooklm_import(articles: list[Article], output_path: str | Path, errors: list[str] | None = None) -> None:
    path = Path(output_path)
    _ensure_parent(path)

    lines = [
        "# NotebookLM Import: Overseas Street Photography Research",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "This file is optimized for research import. It prioritizes articles connected to photographers, bodies of work, exhibitions, photobooks, and contest results.",
        "",
    ]

    for article in articles:
        lines.extend(
            [
                f"## {article.title}",
                "",
                f"Source: {article.source}",
                f"URL: {article.url}",
                f"Date: {article.published_at or 'Unknown'}",
                f"Article Type: {article.article_type}",
                f"Photographer Name: {article.photographer_name}",
                f"Project / Series / Book / Exhibition Name: {article.project_name}",
                f"Detected Street Genre: {article.genre}",
                f"Matched Keywords: {_format_keywords(article)}",
                f"Relevance Score: {article.relevance_score:.2f}",
                "",
                f"Why this was selected: {article.why}",
                "",
                f"Why this may be useful for my photography: {article.photography_use}",
                "",
            ]
        )

    if errors:
        lines.extend(["## Fetch Notes", ""])
        lines.extend(f"- {error}" for error in errors)
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def render_csv(articles: list[Article], output_path: str | Path) -> None:
    path = Path(output_path)
    _ensure_parent(path)

    with path.open("w", encoding="utf-8", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(HEADER)
        for article in articles:
            writer.writerow(
                [
                    article.title,
                    article.source,
                    article.url,
                    article.published_at or "Unknown",
                    article.article_type,
                    article.photographer_name,
                    article.project_name,
                    article.genre,
                    _format_keywords(article),
                    f"{article.relevance_score:.2f}",
                    article.why,
                    article.photography_use,
                ]
            )


def _format_keywords(article: Article) -> str:
    return ", ".join(article.matched_keywords) if article.matched_keywords else "None"


def _ensure_parent(path: Path) -> None:
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
