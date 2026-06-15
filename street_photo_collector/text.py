from __future__ import annotations

import html
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


def clean_text(value: str | None, max_length: int = 500) -> str:
    if not value:
        return ""
    text = html.unescape(TAG_RE.sub(" ", value))
    text = SPACE_RE.sub(" ", text).strip()
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "..."


def clean_title(value: str | None, max_length: int = 180) -> str:
    title = clean_text(value, max_length=1000)
    if " By " in title and " published " in title:
        title = title.split(" By ", 1)[0].strip()
    title = re.sub(r"\s+\d+\s+Comments?$", "", title, flags=re.IGNORECASE)
    if len(title) <= max_length:
        return title
    return title[: max_length - 1].rstrip() + "..."


def normalize_url(url: str) -> str:
    parsed = urlsplit(url.strip())
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in {"fbclid", "gclid"}
    ]
    path = parsed.path or "/"
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, urlencode(query), ""))


def contains_any(value: str, patterns: list[str]) -> bool:
    lowered = value.lower()
    return any(pattern.lower() in lowered for pattern in patterns)
