from __future__ import annotations

from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from typing import Iterable
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from .models import Article
from .text import clean_text, clean_title, contains_any, normalize_url


USER_AGENT = "street-photo-collector/0.1 (+https://github.com/)"
SKIP_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".mp4", ".mov", ".avi", ".pdf", ".zip")


@dataclass(slots=True)
class FetchResult:
    articles: list[Article]
    errors: list[str]


def fetch_url(url: str, timeout: int = 20) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/rss+xml,application/atom+xml"})
    with urlopen(request, timeout=timeout) as response:
        raw = response.read()
        charset = response.headers.get_content_charset()
        if charset and charset.lower() != "utf-8":
            decoded = raw.decode(charset, errors="replace")
            if "窶" not in decoded and "ﾃ" not in decoded:
                return decoded
        return raw.decode("utf-8", errors="replace")


def fetch_source(source: dict[str, object], max_items: int = 20) -> FetchResult:
    source_type = str(source.get("type", "auto")).lower()
    errors: list[str] = []
    soft_errors: list[str] = []
    articles: list[Article] = []

    if source_type in {"rss", "auto"} and source.get("rss_url"):
        try:
            articles = parse_feed(fetch_url(str(source["rss_url"])), source)
            if articles:
                return FetchResult(filter_articles(articles, source, max_items), errors)
        except Exception as exc:  # noqa: BLE001 - collection should continue across source failures.
            message = f"{source.get('name')}: RSS failed: {exc}"
            if source_type == "rss":
                errors.append(message)
            else:
                soft_errors.append(message)

    if source_type in {"html", "auto"}:
        try:
            html = fetch_url(str(source["url"]))
            if source_type == "auto":
                rss_link = discover_feed_url(html, str(source["url"]))
                if rss_link:
                    try:
                        articles = parse_feed(fetch_url(rss_link), source)
                        if articles:
                            return FetchResult(filter_articles(articles, source, max_items), errors)
                    except Exception as exc:  # noqa: BLE001
                        soft_errors.append(f"{source.get('name')}: discovered RSS failed: {exc}")

            articles = parse_html_listing(html, source)
            return FetchResult(filter_articles(articles, source, max_items), errors)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{source.get('name')}: HTML failed: {exc}")

    return FetchResult([], errors or soft_errors)


def parse_feed(xml_text: str, source: dict[str, object]) -> list[Article]:
    root = ET.fromstring(xml_text.strip())
    if _local_name(root.tag) == "rss":
        items = root.findall("./channel/item")
    else:
        items = [node for node in root.iter() if _local_name(node.tag) == "entry"]

    articles: list[Article] = []
    for item in items:
        title = _child_text(item, "title")
        url = _rss_link(item)
        if not title or not url:
            continue
        articles.append(
            Article(
                title=clean_title(title, 180),
                url=normalize_url(url),
                source=str(source["name"]),
                published_at=_date_text(_child_text(item, "pubDate") or _child_text(item, "published") or _child_text(item, "updated")),
                summary=clean_text(_child_text(item, "description") or _child_text(item, "summary") or _child_text(item, "content"), 700),
            )
        )
    return articles


class ListingParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.anchors: list[tuple[str, str]] = []
        self.feed_links: list[str] = []
        self.times: list[str] = []
        self.description = ""
        self.page_title = ""
        self._anchor_href = ""
        self._anchor_text: list[str] = []
        self._in_anchor = False
        self._in_heading = 0
        self._in_title = False
        self._title_text: list[str] = []
        self._in_time = False
        self._time_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = {key.lower(): value or "" for key, value in attrs}
        tag = tag.lower()

        if tag == "meta":
            name = attrs_map.get("name", attrs_map.get("property", "")).lower()
            if name in {"description", "og:description", "twitter:description"} and not self.description:
                self.description = attrs_map.get("content", "")

        if tag == "link":
            rel = attrs_map.get("rel", "").lower()
            link_type = attrs_map.get("type", "").lower()
            href = attrs_map.get("href", "")
            if href and "alternate" in rel and ("rss" in link_type or "atom" in link_type):
                self.feed_links.append(urljoin(self.base_url, href))

        if tag in {"h1", "h2", "h3"}:
            self._in_heading += 1

        if tag == "title":
            self._in_title = True
            self._title_text = []

        if tag == "a" and attrs_map.get("href"):
            self._in_anchor = True
            self._anchor_href = urljoin(self.base_url, attrs_map["href"])
            self._anchor_text = []

        if tag == "time":
            self._in_time = True
            self._time_text = []
            if attrs_map.get("datetime"):
                self.times.append(attrs_map["datetime"])

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"h1", "h2", "h3"} and self._in_heading:
            self._in_heading -= 1
        if tag == "title" and self._in_title:
            self.page_title = clean_text(" ".join(self._title_text), 220)
            self._in_title = False
            self._title_text = []
        if tag == "a" and self._in_anchor:
            title = clean_title(" ".join(self._anchor_text), 180)
            if len(title) >= 18 and self._anchor_href.startswith(("http://", "https://")):
                self.anchors.append((title, normalize_url(self._anchor_href)))
            self._in_anchor = False
            self._anchor_href = ""
            self._anchor_text = []
        if tag == "time" and self._in_time:
            text = clean_text(" ".join(self._time_text), 80)
            if text:
                self.times.append(text)
            self._in_time = False
            self._time_text = []

    def handle_data(self, data: str) -> None:
        if self._in_anchor:
            self._anchor_text.append(data)
        if self._in_title:
            self._title_text.append(data)
        if self._in_time:
            self._time_text.append(data)


def discover_feed_url(html: str, base_url: str) -> str:
    parser = ListingParser(base_url)
    parser.feed(html)
    return parser.feed_links[0] if parser.feed_links else ""


def parse_html_listing(html: str, source: dict[str, object]) -> list[Article]:
    parser = ListingParser(str(source["url"]))
    parser.feed(html)
    seen: set[str] = set()
    articles: list[Article] = []
    page_summary = clean_text(parser.description, 700)
    published_at = _date_text(parser.times[0]) if parser.times else ""
    page_title = parser.page_title or str(source["name"])

    articles.append(
        Article(
            title=clean_title(page_title, 180),
            url=normalize_url(str(source["url"])),
            source=str(source["name"]),
            published_at=published_at,
            summary=page_summary,
        )
    )
    seen.add(normalize_url(str(source["url"])))

    for title, url in parser.anchors:
        if url in seen:
            continue
        seen.add(url)
        articles.append(
            Article(
                title=title,
                url=url,
                source=str(source["name"]),
                published_at="",
                summary=page_summary,
            )
        )
    return articles


def filter_articles(articles: Iterable[Article], source: dict[str, object], max_items: int) -> list[Article]:
    include_patterns = [str(item) for item in source.get("include_url_patterns", [])]
    exclude_patterns = [str(item) for item in source.get("exclude_url_patterns", [])]
    filtered: list[Article] = []
    source_host = urlsplit(str(source.get("url", ""))).netloc.removeprefix("www.")
    same_domain_only = bool(source.get("same_domain_only", False))
    for article in articles:
        article_host = urlsplit(article.url).netloc.removeprefix("www.")
        article_path = urlsplit(article.url).path
        if same_domain_only and source_host and article_host != source_host:
            continue
        if article_path in {"", "/"} and normalize_url(article.url) != normalize_url(str(source.get("url", ""))):
            continue
        if article_path.lower().endswith(SKIP_EXTENSIONS):
            continue
        haystack = f"{article.title} {article.url} {article.summary}"
        if exclude_patterns and contains_any(haystack, exclude_patterns):
            continue
        if include_patterns and not contains_any(haystack, include_patterns):
            continue
        filtered.append(article)
        if len(filtered) >= max_items:
            break
    return filtered


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child_text(item: ET.Element, child_name: str) -> str:
    for child in item:
        if _local_name(child.tag) == child_name:
            return "".join(child.itertext()).strip()
    return ""


def _rss_link(item: ET.Element) -> str:
    text_link = _child_text(item, "link")
    if text_link:
        return text_link
    for child in item:
        if _local_name(child.tag) == "link" and child.attrib.get("href"):
            return child.attrib["href"]
    return ""


def _date_text(value: str) -> str:
    if not value:
        return ""
    try:
        return parsedate_to_datetime(value).date().isoformat()
    except (TypeError, ValueError, IndexError):
        return clean_text(value, 80)
