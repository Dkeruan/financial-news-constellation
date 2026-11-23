from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Iterable

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
ARTICLE_COLUMNS = ["article_id", "published_at", "source", "title", "text", "url", "companies", "record_type"]
PROBABILITY_COLUMNS = ["negative", "neutral", "positive"]


def read_company_registry(path: Path | None = None) -> pd.DataFrame:
    """Read the editable company and alias registry shipped with the app."""
    registry_path = path or DATA_DIR / "companies.csv"
    frame = pd.read_csv(registry_path, dtype=str).fillna("")
    for column in ("ticker", "company", "aliases"):
        if column not in frame:
            frame[column] = ""
        frame[column] = frame[column].astype(str).str.strip()
    return frame[frame["ticker"].ne("") & frame["company"].ne("")].reset_index(drop=True)


def split_companies(value: object) -> list[str]:
    if value is None or pd.isna(value):
        return []
    return list(dict.fromkeys(part.strip() for part in re.split(r"[|;,]", str(value)) if part.strip()))


def normalize_articles(frame: pd.DataFrame, source_name: str = "CSV upload") -> pd.DataFrame:
    """Normalize user rows and discard exact URL/title duplicates."""
    normalized = frame.copy()
    normalized.columns = [str(name).strip().lower() for name in normalized.columns]
    aliases = {"published": "published_at", "date": "published_at", "datetime": "published_at", "body": "text", "content": "text", "headline": "title"}
    normalized = normalized.rename(columns={name: aliases[name] for name in normalized.columns if name in aliases})
    if "companies" not in normalized:
        company_columns = [name for name in ("company", "ticker") if name in normalized]
        normalized["companies"] = normalized[company_columns].fillna("").astype(str).agg("|".join, axis=1) if company_columns else ""
    for column in ("title", "text", "url", "source", "published_at", "companies"):
        if column not in normalized:
            normalized[column] = ""
        normalized[column] = normalized[column].fillna("").astype(str).str.strip()
    normalized["source"] = normalized["source"].replace("", source_name)
    normalized["published_at"] = pd.to_datetime(normalized["published_at"], utc=True, errors="coerce")
    normalized = normalized[normalized["title"].ne("") | normalized["text"].ne("")].copy()

    def stable_id(row: pd.Series) -> str:
        basis = row["url"] or re.sub(r"\W+", " ", row["title"].lower()).strip()
        return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:14]

    if "article_id" not in normalized:
        normalized["article_id"] = normalized.apply(stable_id, axis=1)
    else:
        empty_ids = normalized["article_id"].isna() | normalized["article_id"].astype(str).str.strip().eq("")
        normalized.loc[empty_ids, "article_id"] = normalized.loc[empty_ids].apply(stable_id, axis=1)
    if "record_type" not in normalized:
        normalized["record_type"] = "article"
    normalized["record_type"] = normalized["record_type"].fillna("article").astype(str)
    normalized["_dedupe_key"] = normalized["url"].str.lower().replace("", pd.NA)
    normalized["_dedupe_key"] = normalized["_dedupe_key"].fillna(
        normalized["title"].str.lower().str.replace(r"\W+", " ", regex=True).str.strip()
    )
    normalized = normalized.drop_duplicates("_dedupe_key", keep="first").drop(columns="_dedupe_key")
    return normalized[ARTICLE_COLUMNS].reset_index(drop=True)


def load_demo() -> tuple[pd.DataFrame, pd.DataFrame]:
    articles = pd.read_csv(DATA_DIR / "demo_articles.csv", dtype=str).fillna("")
    articles["published_at"] = pd.to_datetime(articles["published_at"], utc=True, errors="coerce")
    predictions = pd.read_csv(DATA_DIR / "demo_predictions.csv")
    return articles, predictions


def aliases_for_row(row: pd.Series) -> list[str]:
    company_aliases = [part.strip() for part in str(row.get("aliases", "")).split("|") if part.strip()]
    names = [str(row.get("company", "")).strip(), str(row.get("ticker", "")).strip()]
    return list(dict.fromkeys(alias for alias in [*company_aliases, *names] if alias))


def find_companies(text: str, registry: pd.DataFrame) -> list[dict[str, str]]:
    """Match curated aliases using word boundaries, avoiding opaque NER guesses."""
    found: list[dict[str, str]] = []
    for _, company in registry.iterrows():
        matched = False
        for alias in aliases_for_row(company):
            pattern = rf"(?<!\w){re.escape(alias)}(?!\w)"
            if re.search(pattern, text or "", flags=re.IGNORECASE):
                matched = True
                break
        if matched:
            found.append({"ticker": company["ticker"], "company": company["company"]})
    return found


def relevant_contexts(article: pd.Series, company: pd.Series, registry: pd.DataFrame, max_contexts: int = 8) -> list[str]:
    """Return short target-bearing text spans for long-article inference."""
    title = str(article.get("title", "")).strip()
    body = str(article.get("text", "")).strip()
    company_row = registry[registry["ticker"].str.casefold() == str(company["ticker"]).casefold()]
    aliases = aliases_for_row(company_row.iloc[0]) if not company_row.empty else [company["company"], company["ticker"]]
    pattern = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(alias) for alias in sorted(aliases, key=len, reverse=True)) + r")(?!\w)", re.IGNORECASE)
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", body) if part.strip()]
    selected: list[str] = []
    for index, sentence in enumerate(sentences):
        if pattern.search(sentence):
            context = " ".join(sentences[max(0, index - 1): min(len(sentences), index + 2)])
            if context not in selected:
                selected.append(context)
    if title and pattern.search(title):
        selected.insert(0, title)
    return selected[:max_contexts]


def expand_company_targets(articles: pd.DataFrame, registry: pd.DataFrame) -> pd.DataFrame:
    """Create one (article, company) row per supplied or alias-matched target."""
    rows: list[dict[str, object]] = []
    by_ticker = {row["ticker"].casefold(): row for _, row in registry.iterrows()}
    by_name = {row["company"].casefold(): row for _, row in registry.iterrows()}
    for _, article in articles.iterrows():
        explicit = split_companies(article.get("companies", ""))
        targets: list[dict[str, str]] = []
        for label in explicit:
            match = by_ticker.get(label.casefold())
            if match is None:
                match = by_name.get(label.casefold())
            if match is None:
                match = next((row for _, row in registry.iterrows() if label.casefold() in {alias.casefold() for alias in aliases_for_row(row)}), None)
            targets.append({"ticker": match["ticker"], "company": match["company"]} if match is not None else {"ticker": label, "company": label})
        if not targets:
            targets = find_companies(f"{article.get('title', '')} {article.get('text', '')}", registry)
        unique_targets: dict[str, dict[str, str]] = {}
        for target in targets:
            unique_targets.setdefault(target["ticker"].casefold(), target)
        for target in unique_targets.values():
            rows.append({**article.to_dict(), **target})
    return pd.DataFrame(rows)


def score_article_targets(articles: pd.DataFrame, registry: pd.DataFrame, predictor) -> pd.DataFrame:
    """Run a target-aware predictor over each target's relevant context."""
    targets = expand_company_targets(articles, registry)
    if targets.empty:
        return pd.DataFrame(columns=["article_id", "ticker", "company", *PROBABILITY_COLUMNS])
    scored: list[dict[str, object]] = []
    for _, row in targets.iterrows():
        contexts = relevant_contexts(row, row, registry)
        if not contexts:
            continue
        probabilities = predictor.predict_many(contexts, row["company"])
        mean = {label: float(sum(result[label] for result in probabilities) / len(probabilities)) for label in PROBABILITY_COLUMNS}
        scored.append({
            "article_id": row["article_id"],
            "ticker": row["ticker"],
            "company": row["company"],
            **mean,
            "context_count": len(contexts),
            "evidence_text": "\n\n".join(contexts[:4])[:2400],
            "label": max(PROBABILITY_COLUMNS, key=mean.get),
            "confidence": max(mean.values()),
            "sentiment_score": mean["positive"] - mean["negative"],
        })
    return pd.DataFrame(scored)


def merge_article_predictions(articles: pd.DataFrame, predictions: pd.DataFrame) -> pd.DataFrame:
    merged = predictions.merge(articles, on="article_id", how="left", suffixes=("", "_article"))
    if "company_article" in merged:
        merged["company"] = merged["company"].fillna(merged["company_article"])
    if "published_at" in merged:
        merged["published_at"] = pd.to_datetime(merged["published_at"], utc=True, errors="coerce")
    return merged


def company_summary(scored_articles: pd.DataFrame) -> pd.DataFrame:
    if scored_articles.empty:
        return pd.DataFrame(columns=["ticker", "company", "article_count", "sentiment_score", "confidence", *PROBABILITY_COLUMNS])
    summary = scored_articles.groupby(["ticker", "company"], as_index=False).agg(
        article_count=("article_id", "nunique"),
        sentiment_score=("sentiment_score", "mean"),
        confidence=("confidence", "mean"),
        negative=("negative", "mean"),
        neutral=("neutral", "mean"),
        positive=("positive", "mean"),
    )
    return summary.sort_values(["article_count", "company"], ascending=[False, True]).reset_index(drop=True)


def co_mention_edges(articles: pd.DataFrame, predictions: pd.DataFrame) -> pd.DataFrame:
    if predictions.empty:
        return pd.DataFrame(columns=["source", "target", "weight"])
    article_companies = predictions[["article_id", "ticker"]].drop_duplicates()
    edges: dict[tuple[str, str], set[str]] = {}
    for article_id, group in article_companies.groupby("article_id"):
        tickers = sorted(group["ticker"].unique())
        for index, first in enumerate(tickers):
            for second in tickers[index + 1:]:
                edges.setdefault((first, second), set()).add(article_id)
    return pd.DataFrame([{"source": a, "target": b, "weight": len(ids)} for (a, b), ids in edges.items()])


def sentiment_timeline(scored_articles: pd.DataFrame) -> pd.DataFrame:
    if scored_articles.empty or "published_at" not in scored_articles:
        return pd.DataFrame(columns=["date", "ticker", "company", "sentiment_score", "article_count"])
    frame = scored_articles.copy()
    frame["date"] = pd.to_datetime(frame["published_at"], utc=True, errors="coerce").dt.date
    frame = frame.dropna(subset=["date"])
    return frame.groupby(["date", "ticker", "company"], as_index=False).agg(
        sentiment_score=("sentiment_score", "mean"),
        article_count=("article_id", "nunique"),
    )

