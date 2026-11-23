from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import pandas as pd

from .data import ARTICLE_COLUMNS, PROBABILITY_COLUMNS

PREDICTION_COLUMNS = [
    "article_id",
    "ticker",
    "company",
    *PROBABILITY_COLUMNS,
    "label",
    "confidence",
    "sentiment_score",
    "evidence_text",
]


def _connect(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, timeout=15)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_store(database_path: Path, seed_path: Path) -> None:
    """Create the local research database and refresh its curated source records."""
    with _connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS sources (
                source_id TEXT PRIMARY KEY,
                publisher TEXT NOT NULL,
                name TEXT NOT NULL,
                topic TEXT NOT NULL,
                feed_url TEXT NOT NULL UNIQUE,
                homepage_url TEXT NOT NULL,
                description TEXT NOT NULL,
                last_checked_at TEXT,
                last_status TEXT NOT NULL DEFAULT 'Not checked',
                last_message TEXT NOT NULL DEFAULT '',
                last_item_count INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS research_runs (
                run_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL,
                lookback_days INTEGER NOT NULL,
                source_ids TEXT NOT NULL,
                source_count INTEGER NOT NULL,
                article_count INTEGER NOT NULL,
                scored_pair_count INTEGER NOT NULL,
                status TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS run_articles (
                run_id TEXT NOT NULL,
                article_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                published_at TEXT,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                text TEXT NOT NULL,
                url TEXT NOT NULL,
                companies TEXT NOT NULL,
                record_type TEXT NOT NULL,
                PRIMARY KEY (run_id, article_id)
            );
            CREATE TABLE IF NOT EXISTS target_predictions (
                run_id TEXT NOT NULL,
                article_id TEXT NOT NULL,
                ticker TEXT NOT NULL,
                company TEXT NOT NULL,
                negative REAL NOT NULL,
                neutral REAL NOT NULL,
                positive REAL NOT NULL,
                label TEXT NOT NULL,
                confidence REAL NOT NULL,
                sentiment_score REAL NOT NULL,
                evidence_text TEXT NOT NULL,
                PRIMARY KEY (run_id, article_id, ticker)
            );
            CREATE INDEX IF NOT EXISTS idx_run_articles_run ON run_articles(run_id);
            CREATE INDEX IF NOT EXISTS idx_predictions_run ON target_predictions(run_id);
            """
        )
        with seed_path.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        connection.executemany(
            """
            INSERT INTO sources (
                source_id, publisher, name, topic, feed_url, homepage_url, description
            ) VALUES (
                :source_id, :publisher, :name, :topic, :feed_url, :homepage_url, :description
            )
            ON CONFLICT(source_id) DO UPDATE SET
                publisher=excluded.publisher,
                name=excluded.name,
                topic=excluded.topic,
                feed_url=excluded.feed_url,
                homepage_url=excluded.homepage_url,
                description=excluded.description
            """,
            rows,
        )


def list_sources(database_path: Path) -> list[dict[str, Any]]:
    with _connect(database_path) as connection:
        rows = connection.execute(
            "SELECT * FROM sources ORDER BY publisher COLLATE NOCASE, name COLLATE NOCASE"
        ).fetchall()
    return [dict(row) for row in rows]


def add_source(database_path: Path, feed_url: str, name: str = "") -> str:
    """Persist a user-added RSS/Atom URL without requesting it."""
    candidate = str(feed_url or "").strip()
    if len(candidate) > 2048 or any(character.isspace() for character in candidate):
        raise ValueError("Enter a feed URL without spaces, up to 2,048 characters.")
    parsed = urlsplit(candidate)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Enter a complete http:// or https:// RSS or Atom URL.")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Remove usernames and passwords from the feed URL.")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Check the port in this feed URL.") from exc

    host = parsed.hostname.lower()
    netloc_host = f"[{host}]" if ":" in host else host
    netloc = netloc_host if port is None else f"{netloc_host}:{port}"
    normalized_url = urlunsplit((parsed.scheme.lower(), netloc, parsed.path or "/", parsed.query, ""))
    source_id = "custom-" + hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()[:24]
    label = str(name or "").strip() or "Custom RSS"
    homepage_url = f"{parsed.scheme.lower()}://{netloc}/"

    with _connect(database_path) as connection:
        existing = connection.execute(
            "SELECT source_id FROM sources WHERE feed_url=?",
            (normalized_url,),
        ).fetchone()
        if existing:
            raise ValueError("This RSS feed is already in Source status.")
        try:
            connection.execute(
                """INSERT INTO sources
                   (source_id, publisher, name, topic, feed_url, homepage_url, description)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (source_id, host.removeprefix("www."), label, "Custom", normalized_url, homepage_url,
                 "User-added RSS or Atom feed; not checked until Research is run."),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("This RSS feed is already in Source status.") from exc
    return source_id


def update_source_check(
    database_path: Path,
    source_id: str,
    status: str,
    message: str,
    item_count: int,
    checked_at: str | None = None,
) -> None:
    checked_at = checked_at or datetime.now(timezone.utc).isoformat()
    with _connect(database_path) as connection:
        connection.execute(
            """UPDATE sources SET last_checked_at=?, last_status=?, last_message=?, last_item_count=?
               WHERE source_id=?""",
            (checked_at, status, message, int(item_count), source_id),
        )


def save_research_run(
    database_path: Path,
    *,
    run_id: str,
    started_at: str,
    finished_at: str,
    lookback_days: int,
    source_ids: list[str],
    articles: pd.DataFrame,
    predictions: pd.DataFrame,
    status: str,
    note: str = "",
) -> None:
    with _connect(database_path) as connection:
        connection.execute(
            """INSERT OR REPLACE INTO research_runs
               (run_id, started_at, finished_at, lookback_days, source_ids,
                source_count, article_count, scored_pair_count, status, note)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                started_at,
                finished_at,
                int(lookback_days),
                json.dumps(source_ids),
                len(source_ids),
                len(articles),
                len(predictions),
                status,
                note,
            ),
        )
        article_rows = []
        for _, row in articles.iterrows():
            article_rows.append((
                run_id,
                str(row.get("article_id", "")),
                str(row.get("source_id", "")),
                _timestamp_text(row.get("published_at")),
                str(row.get("source", "")),
                str(row.get("title", "")),
                str(row.get("text", "")),
                str(row.get("url", "")),
                str(row.get("companies", "")),
                str(row.get("record_type", "rss")),
            ))
        connection.executemany(
            """INSERT OR REPLACE INTO run_articles
               (run_id, article_id, source_id, published_at, source, title, text, url, companies, record_type)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            article_rows,
        )
        prediction_rows = []
        for _, row in predictions.iterrows():
            prediction_rows.append((
                run_id,
                str(row.get("article_id", "")),
                str(row.get("ticker", "")),
                str(row.get("company", "")),
                *[float(row.get(label, 0.0)) for label in PROBABILITY_COLUMNS],
                str(row.get("label", "")),
                float(row.get("confidence", 0.0)),
                float(row.get("sentiment_score", 0.0)),
                str(row.get("evidence_text", "")),
            ))
        connection.executemany(
            """INSERT OR REPLACE INTO target_predictions
               (run_id, article_id, ticker, company, negative, neutral, positive,
                label, confidence, sentiment_score, evidence_text)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            prediction_rows,
        )


def load_latest_research(database_path: Path) -> tuple[dict[str, Any] | None, pd.DataFrame, pd.DataFrame]:
    with _connect(database_path) as connection:
        run = connection.execute(
            """SELECT * FROM research_runs WHERE status IN ('complete', 'partial', 'unscored')
               ORDER BY finished_at DESC LIMIT 1"""
        ).fetchone()
        if run is None:
            return None, pd.DataFrame(columns=[*ARTICLE_COLUMNS, "source_id"]), pd.DataFrame(columns=PREDICTION_COLUMNS)
        run_dict = dict(run)
        articles = pd.read_sql_query(
            "SELECT article_id, published_at, source, title, text, url, companies, record_type, source_id FROM run_articles WHERE run_id=? ORDER BY published_at DESC",
            connection,
            params=(run_dict["run_id"],),
        )
        predictions = pd.read_sql_query(
            "SELECT article_id, ticker, company, negative, neutral, positive, label, confidence, sentiment_score, evidence_text FROM target_predictions WHERE run_id=?",
            connection,
            params=(run_dict["run_id"],),
        )
    if not articles.empty:
        articles["published_at"] = pd.to_datetime(articles["published_at"], utc=True, errors="coerce")
    return run_dict, articles, predictions


def _timestamp_text(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    timestamp = pd.to_datetime(value, utc=True, errors="coerce")
    return None if pd.isna(timestamp) else timestamp.isoformat()
