from __future__ import annotations

import html
import re
import time
from datetime import datetime, timezone
from functools import lru_cache
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

import feedparser
import pandas as pd
import trafilatura

from .data import normalize_articles

USER_AGENT = "FinancialNewsConstellation/0.1 (local research tool)"


@lru_cache(maxsize=32)
def _robots_parser(robots_url: str) -> RobotFileParser | None:
    parser = RobotFileParser()
    parser.set_url(robots_url)
    try:
        request = Request(robots_url, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=5) as response:
            body = response.read(256_000).decode("utf-8", errors="replace")
        parser.parse(body.splitlines())
        return parser
    except HTTPError as exc:
        if exc.code == 404:
            parser.parse([])
            return parser
        return None
    except (URLError, TimeoutError, ValueError):
        return None


def _robots_allow(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    parser = _robots_parser(robots_url)
    return parser.can_fetch(USER_AGENT, url) if parser is not None else False


def _clean_html(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", html.unescape(without_tags)).strip()


def _extract_page(url: str) -> str:
    if not _robots_allow(url):
        return ""
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=15) as response:
            payload = response.read(4_000_000)
        return trafilatura.extract(payload, include_comments=False, include_tables=False, favor_precision=True) or ""
    except (URLError, TimeoutError, ValueError):
        return ""


def fetch_rss(feed_url: str, max_items: int = 30, fetch_full_text: bool = False) -> tuple[pd.DataFrame, list[str]]:
    """Read a user-supplied RSS/Atom feed; page extraction is opt-in and robots-aware."""
    parsed = urlparse(feed_url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Enter a complete http:// or https:// feed URL.")
    request = Request(feed_url.strip(), headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=12) as response:
            feed_bytes = response.read(3_000_000)
        feed = feedparser.parse(feed_bytes)
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise ValueError(f"Could not read this feed: {exc}") from exc
    entries = list(feed.entries[:max(1, min(int(max_items), 100))])
    if not entries:
        detail = getattr(feed, "bozo_exception", None)
        raise ValueError(f"No RSS/Atom items were found. {detail or 'Check the feed URL and try again.'}")
    feed_title = getattr(feed.feed, "title", "").strip() or parsed.netloc
    articles: list[dict[str, object]] = []
    notes: list[str] = []
    extracted = 0
    for entry in entries:
        title = _clean_html(entry.get("title", ""))
        link = str(entry.get("link", "")).strip()
        content = entry.get("content") or []
        fallback_content = content[0].get("value", "") if content else ""
        summary = _clean_html(entry.get("summary", "") or fallback_content)
        body = summary
        if fetch_full_text and link and extracted < 20:
            page_text = _extract_page(link)
            extracted += 1
            if page_text:
                body = page_text
            else:
                notes.append(f"Skipped page text for {link}: extraction was blocked, unavailable, or disallowed by robots.txt; using the feed summary.")
            time.sleep(0.3)
        published = entry.get("published_parsed") or entry.get("updated_parsed")
        published_at = datetime(*published[:6], tzinfo=timezone.utc).isoformat() if published else ""
        articles.append({
            "published_at": published_at,
            "source": feed_title,
            "title": title,
            "text": body,
            "url": link,
            "record_type": "rss",
        })
    if fetch_full_text and len(entries) > 20:
        notes.append("Full-text extraction is limited to the first 20 items per feed load.")
    return normalize_articles(pd.DataFrame(articles), source_name=feed_title), notes

