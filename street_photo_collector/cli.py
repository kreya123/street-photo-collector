from __future__ import annotations

import argparse
from pathlib import Path

from .classify import ArticleClassifier
from .config import load_article_types, load_genres, load_sources
from .db import SeenDatabase
from .fetchers import fetch_source
from .renderer import render_all_outputs, render_candidates_csv
from .scoring import ArticleScorer, explain_selection
from .selector import select_articles


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect overseas street photography links and convert them into shooting ideas.")
    parser.add_argument("--sources", default="sources.yaml", help="Path to sources.yaml")
    parser.add_argument("--genres", default="genres.yaml", help="Path to genres.yaml")
    parser.add_argument("--article-types", default="article_types.yaml", help="Path to article_types.yaml")
    parser.add_argument("--db", default="data/seen.sqlite3", help="Path to SQLite database")
    parser.add_argument("--output", default="output.md", help="Path to output markdown")
    parser.add_argument("--notebooklm-output", default="notebooklm_import.md", help="Path to NotebookLM import markdown")
    parser.add_argument("--csv-output", default="articles.csv", help="Path to CSV output")
    parser.add_argument("--candidate-limit", type=int, default=60, help="Maximum number of scored candidate articles to keep before final selection")
    parser.add_argument("--limit", type=int, default=10, help="Number of final selected articles to output")
    parser.add_argument("--per-source", type=int, default=15, help="Maximum items to fetch from each source")
    parser.add_argument("--min-score", type=float, default=12.0, help="Minimum relevance score for final quality filtering")
    parser.add_argument("--max-per-source-final", type=int, default=2, help="Maximum final articles from the same source")
    parser.add_argument("--max-per-article-type-final", type=int, default=4, help="Maximum final articles with the same article type")
    parser.add_argument("--candidates-output", default="outputs/candidates.csv", help="Path to debug CSV containing candidate articles")
    parser.add_argument("--include-seen", action="store_true", help="Include URLs already stored in SQLite")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    sources = load_sources(args.sources)
    genre_config = load_genres(args.genres)
    article_type_config = load_article_types(args.article_types)
    classifier = ArticleClassifier(genre_config, article_type_config)
    scorer = ArticleScorer(article_type_config)

    errors: list[str] = []
    collected = []

    with SeenDatabase(args.db) as db:
        for source in sources:
            result = fetch_source(source, max_items=args.per_source)
            errors.extend(result.errors)
            source_score = float(source.get("source_score", 0.0))

            for article in result.articles:
                if not args.include_seen and db.is_seen(article.url):
                    continue
                classifier.classify(article)
                scorer.score(article, source_score=source_score)
                explain_selection(article, article_type_config)
                collected.append(article)
                db.mark_seen(article)

        db.commit()

    selection = select_articles(
        collected,
        candidate_limit=args.candidate_limit,
        final_limit=args.limit,
        min_score=args.min_score,
        max_per_source_final=args.max_per_source_final,
        max_per_article_type_final=args.max_per_article_type_final,
    )
    render_all_outputs(
        selection.final_articles,
        Path(args.output),
        Path(args.notebooklm_output),
        Path(args.csv_output),
        selection.stats,
        errors,
    )
    render_candidates_csv(selection.candidates, Path(args.candidates_output))
    print(f"Wrote {len(selection.final_articles)} final articles to {args.output}, {args.notebooklm_output}, and {args.csv_output}")
    print(f"Wrote {len(selection.candidates)} candidate articles to {args.candidates_output}")
    if errors:
        print(f"Completed with {len(errors)} fetch note(s).")
    return 0
