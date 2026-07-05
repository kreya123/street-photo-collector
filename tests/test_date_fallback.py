from __future__ import annotations

import unittest

from street_photo_collector.classify import ArticleClassifier
from street_photo_collector.fetchers import parse_html_listing
from street_photo_collector.models import Article


class DateFallbackTests(unittest.TestCase):
    def test_html_published_time_meta_is_used(self) -> None:
        html = """
        <html>
          <head>
            <title>Jane Smith - City Memory</title>
            <meta property="article:published_time" content="2026-06-18T12:30:00+00:00">
          </head>
          <body></body>
        </html>
        """
        source = {"name": "Example", "url": "https://example.com/features"}

        articles = parse_html_listing(html, source)

        self.assertEqual(articles[0].published_at, "2026-06-18")

    def test_url_date_is_used_when_article_date_is_missing(self) -> None:
        classifier = ArticleClassifier(
            {"genres": {"Silent Stories": {"keywords": {"memory": 1}}}, "priority_order": ["Silent Stories"]},
            {"types": {"Other": {"keywords": []}}, "priority_order": ["Other"], "street_visual_keywords": [], "negative_keywords": {}},
        )
        article = Article(
            title="Jane Smith - City Memory",
            url="https://example.com/2026/06/city-memory",
            source="Example",
            summary="memory in public space",
        )

        classifier.classify(article)

        self.assertEqual(article.published_at, "2026-06")


if __name__ == "__main__":
    unittest.main()
