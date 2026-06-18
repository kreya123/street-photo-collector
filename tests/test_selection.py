from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from street_photo_collector.models import Article, SelectionStats
from street_photo_collector.renderer import render_all_outputs
from street_photo_collector.scoring import ArticleScorer, is_low_quality_page
from street_photo_collector.selector import select_articles


def article(
    index: int,
    source: str = "VOID",
    article_type: str = "Photobook",
    score: float = 20.0,
    photographer: str | None = None,
    project: str | None = None,
) -> Article:
    item = Article(
        title=f"Jane Smith {index} - Project {index}",
        url=f"https://example.com/article-{index}",
        source=source,
        published_at="2026-06-18",
        summary="photobook documentary street photography public space memory",
    )
    item.article_type = article_type
    item.genre = "Silent Stories"
    item.photographer_name = photographer or f"Jane Smith {index}"
    item.project_name = project or f"Project {index}"
    item.matched_keywords = ["photobook", "memory"]
    item.relevance_score = score
    item.why = "選んだ理由"
    item.photography_use = "撮影に役立つ点"
    return item


class SelectionTests(unittest.TestCase):
    def test_void_articles_are_limited_to_two(self) -> None:
        articles = [article(i, source="VOID", article_type="Photobook", score=30 - i) for i in range(8)]
        articles += [article(100 + i, source=f"Source {i}", article_type="Interview", score=20 - i) for i in range(6)]

        result = select_articles(articles, 60, 10, 12, 2, 4)

        self.assertLessEqual(sum(item.source == "VOID" for item in result.final_articles), 2)

    def test_store_catalogue_and_home_pages_fail_quality(self) -> None:
        bad_articles = [
            article(1, project="Our Whole Catalogue"),
            article(2, project="Photography Books"),
            article(3),
        ]
        bad_articles[0].title = "Our Whole Catalogue"
        bad_articles[0].url = "https://void.photo/catalogue"
        bad_articles[1].title = "Photography Books"
        bad_articles[1].url = "https://void.photo/store"
        bad_articles[2].title = "VOID"
        bad_articles[2].url = "https://void.photo/"

        result = select_articles(bad_articles, 60, 10, 12, 2, 4)

        self.assertEqual(result.quality_articles, [])

    def test_invalid_photographer_name_is_penalized(self) -> None:
        scorer = ArticleScorer({"score_rules": {}, "negative_keywords": {}, "street_visual_keywords": []})
        item = article(1, photographer="Photography Books")
        before = item.relevance_score
        scorer.score(item)

        self.assertLess(item.relevance_score, before)

    def test_photobook_does_not_fill_all_final_slots(self) -> None:
        articles = [article(i, source=f"PhotoBook Source {i}", article_type="Photobook", score=30 - i) for i in range(10)]
        articles += [
            article(20, source="Interview Source", article_type="Interview", score=19),
            article(21, source="Exhibition Source", article_type="Exhibition", score=18),
            article(22, source="Award Source", article_type="Award or Contest Result", score=17),
        ]

        result = select_articles(articles, 60, 10, 12, 2, 4)

        self.assertLessEqual(sum(item.article_type == "Photobook" for item in result.final_articles), 4)
        self.assertTrue(any(item.article_type == "Interview" for item in result.final_articles))
        self.assertTrue(any(item.article_type == "Exhibition" for item in result.final_articles))
        self.assertTrue(any(item.article_type == "Award or Contest Result" for item in result.final_articles))

    def test_limit_ten_keeps_outputs_within_ten_rows(self) -> None:
        articles = [article(i, source=f"Source {i}", article_type="Interview", score=30 - i) for i in range(12)]
        result = select_articles(articles, 60, 10, 12, 2, 4)

        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "output.md"
            notebook = Path(tmpdir) / "notebooklm_import.md"
            csv_path = Path(tmpdir) / "articles.csv"
            render_all_outputs(
                result.final_articles,
                output,
                notebook,
                csv_path,
                SelectionStats(
                    candidate_count=12,
                    quality_pass_count=len(result.quality_articles),
                    final_count=len(result.final_articles),
                    min_score=12,
                    max_per_source_final=2,
                    max_per_article_type_final=4,
                ),
            )

            with csv_path.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertLessEqual(len(rows), 10)
            self.assertLessEqual(output.read_text(encoding="utf-8").count("\n## "), 11)
            self.assertLessEqual(notebook.read_text(encoding="utf-8").count("\n## "), 10)

    def test_low_quality_page_helper(self) -> None:
        item = article(1)
        item.title = "Photography Books"
        item.url = "https://void.photo/store"

        self.assertTrue(is_low_quality_page(item))


if __name__ == "__main__":
    unittest.main()
