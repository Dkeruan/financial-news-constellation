from __future__ import annotations

import hashlib
import html
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from finnews.data import (  # noqa: E402
    ARTICLE_COLUMNS,
    PROBABILITY_COLUMNS,
    company_summary,
    co_mention_edges,
    load_demo,
    merge_article_predictions,
    normalize_articles,
    read_company_registry,
    score_article_targets,
    sentiment_timeline,
)
from finnews.graph import make_constellation  # noqa: E402
from finnews.ingest import fetch_rss  # noqa: E402
from finnews.storage import (  # noqa: E402
    add_source,
    initialize_store,
    list_sources,
    load_latest_research,
    save_research_run,
    update_source_check,
)

MODEL_DIR = ROOT / "models" / "financial-target-distilbert"
DATA_DIR = ROOT / "data"
SOURCE_DB = DATA_DIR / "financial_news.sqlite3"
SOURCE_SEED = DATA_DIR / "rss_sources.csv"


st.set_page_config(
    page_title="Financial News Constellation",
    page_icon="F",
    layout="wide",
    initial_sidebar_state="auto",
)


def _style() -> None:
    st.markdown(
        """
        <style>
        :root {
          --canvas: #e7e5e2;
          --surface: #f4f2ef;
          --surface-soft: #ebe9e6;
          --ink: #181818;
          --muted: #5e5d5a;
          --quiet: #777572;
          --line: #cfccc8;
          --panel: #242424;
          --panel-raised: #30302f;
          --panel-ink: #f5f4f2;
          --panel-muted: #b9b7b4;
          --panel-line: #4a4947;
          --accent: #c43a50;
          --accent-bright: #fa7182;
          --positive: #82dc98;
          --negative: #ff7887;
          --neutral: #c1c4c9;
          --warning: #f0c16b;
        }
        .stApp, [data-testid="stAppViewContainer"] { background:var(--canvas); color:var(--ink); }
        [data-testid="stHeader"], [data-testid="stFooter"] { display:none; }
        .block-container { max-width:1540px; padding-top:1.35rem; padding-bottom:2.2rem; }
        section[data-testid="stSidebar"] { background:var(--surface); border-right:1px solid var(--line); }
        h1, h2, h3 { color:var(--ink); letter-spacing:-.035em; }
        h1 { font-size:clamp(1.8rem, 3vw, 2.45rem); font-weight:620; line-height:1.08; }
        h2 { font-size:1.42rem; font-weight:620; }
        h3 { font-size:1.02rem; font-weight:620; }
        div[data-testid="stMarkdownContainer"] h2 { font-size:1.42rem !important; font-weight:620 !important; }
        div[data-testid="stMarkdownContainer"] h3 { font-size:1.02rem !important; font-weight:620 !important; }
        p, label, [data-testid="stCaptionContainer"] { color:var(--muted); }
        [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color:var(--muted) !important; opacity:1 !important; }
        .fnc-head { display:flex; align-items:center; justify-content:space-between; gap:1.25rem; padding:0 0 .7rem; margin-bottom:.45rem; }
        .fnc-name { color:var(--ink); font-size:1.88rem; font-weight:620; letter-spacing:-.045em; }
        .fnc-description { max-width:65ch; color:var(--muted); font-size:.88rem; margin-top:.22rem; }
        .bento-card { background:var(--surface); border:1px solid var(--line); border-radius:18px; padding:1rem 1.15rem; }
        .st-key-research-panel { background:var(--surface); border:1px solid var(--line); border-radius:18px; padding:.8rem 1rem; margin-bottom:.75rem; }
        .st-key-constellation-card, .st-key-company-summary, .st-key-trend-card, .st-key-article-card { background:var(--panel); border:1px solid var(--panel-line); border-radius:18px; padding:1rem 1.1rem; color:var(--panel-ink); }
        .st-key-company-workspace { background:var(--panel); border:1px solid var(--panel-line); border-radius:18px; padding:.65rem .85rem; color:var(--panel-ink); margin-top:.45rem; }
        .st-key-trend-evidence { margin-top:.45rem; }
        .st-key-company-workspace .st-key-constellation-card, .st-key-company-workspace .st-key-company-summary { background:transparent; border:0; border-radius:0; padding:.55rem .6rem; }
        .st-key-company-workspace [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) { border-left:1px solid var(--panel-line); padding-left:1rem; }
        .st-key-company-summary .score-number { font-size:2.45rem; }
        .st-key-company-workspace [data-testid="stHorizontalBlock"], .st-key-trend-evidence [data-testid="stHorizontalBlock"] { gap:1rem; }
        .st-key-research-panel div[data-testid="stPopover"] > button { min-height:2.7rem; white-space:nowrap; }
        .st-key-constellation-card h1, .st-key-constellation-card h2, .st-key-constellation-card h3,
        .st-key-company-summary h1, .st-key-company-summary h2, .st-key-company-summary h3,
        .st-key-trend-card h1, .st-key-trend-card h2, .st-key-trend-card h3,
        .st-key-article-card h1, .st-key-article-card h2, .st-key-article-card h3 { color:var(--panel-ink); }
        .st-key-constellation-card p, .st-key-constellation-card [data-testid="stCaptionContainer"], .st-key-constellation-card [data-testid="stCaptionContainer"] p,
        .st-key-company-summary p, .st-key-company-summary [data-testid="stCaptionContainer"], .st-key-company-summary [data-testid="stCaptionContainer"] p,
        .st-key-trend-card p, .st-key-trend-card [data-testid="stCaptionContainer"], .st-key-trend-card [data-testid="stCaptionContainer"] p,
        .st-key-article-card p, .st-key-article-card [data-testid="stCaptionContainer"], .st-key-article-card [data-testid="stCaptionContainer"] p { color:var(--panel-muted) !important; }
        .st-key-company-summary label, .st-key-company-summary [data-testid="stWidgetLabel"] p { color:var(--panel-muted) !important; }
        .st-key-company-summary [data-baseweb="select"] > div { background:var(--panel-raised) !important; border-color:var(--panel-line) !important; color:var(--panel-ink) !important; }
        .st-key-company-summary [data-baseweb="select"] input, .st-key-company-summary [data-baseweb="select"] span { color:var(--panel-ink) !important; }
        .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"], button[data-testid="stBaseButton-primary"] { background:#111 !important; border-color:#111 !important; color:#fff !important; }
        .stButton > button[kind="primary"] *, .stFormSubmitButton > button[kind="primary"] *, button[data-testid="stBaseButton-primary"] * { color:#fff !important; -webkit-text-fill-color:#fff !important; }
        .stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover { background:#353535 !important; border-color:#353535 !important; }
        .stButton > button[kind="primary"]:disabled, .stFormSubmitButton > button[kind="primary"]:disabled, button[data-testid="stBaseButton-primary"]:disabled { background:#626262 !important; border-color:#626262 !important; color:#fff !important; }
        .stButton > button, .stFormSubmitButton > button { border-radius:999px !important; }
        .board-label { color:var(--muted); font-size:.75rem; line-height:1.35; font-weight:650; }
        .section-note { max-width:72ch; color:var(--panel-muted); font-size:.8rem; line-height:1.45; margin:-.2rem 0 .45rem; }
        .fnc-state { display:inline-flex; width:fit-content; align-items:center; color:var(--panel-ink); background:rgba(255,255,255,.07); border:1px solid var(--panel-line); border-radius:999px; padding:.3rem .58rem; font-size:.7rem; line-height:1.3; white-space:nowrap; }
        .fnc-state .state-dot { display:inline-block; width:7px; height:7px; border-radius:50%; background:var(--positive); margin:0 .38rem .02rem 0; }
        .fnc-state-warning .state-dot { background:var(--warning); }
        .coverage-summary-line { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:.55rem 1rem; margin-top:.9rem; padding-top:.7rem; border-top:1px solid var(--panel-line); }
        .coverage-summary-facts { display:flex; flex-wrap:wrap; gap:.25rem .7rem; color:var(--panel-muted); font-size:.7rem; line-height:1.4; font-variant-numeric:tabular-nums; }
        .coverage-summary-facts strong { color:var(--panel-ink); font-weight:600; }
        .coverage-unmatched { color:var(--warning); }
        .coverage-summary-state { display:flex; align-items:center; flex-wrap:wrap; gap:.3rem .55rem; color:var(--panel-muted); font-size:.68rem; line-height:1.4; }
        .coverage-empty-facts { margin-top:.55rem; color:var(--muted); font-size:.76rem; font-variant-numeric:tabular-nums; }
        .coverage-empty-facts strong { color:var(--ink); }
        .snapshot-signal-row { display:flex; align-items:flex-end; justify-content:space-between; gap:.8rem; margin:.12rem 0 .2rem; }
        .snapshot-score-block { min-width:0; }
        .snapshot-volume { flex:0 0 auto; text-align:right; padding-bottom:.1rem; }
        .snapshot-volume-value { color:var(--panel-ink); font-size:1.45rem; font-weight:620; line-height:1; letter-spacing:-.03em; font-variant-numeric:tabular-nums; }
        .snapshot-volume-label { color:var(--panel-muted); font-size:.68rem; margin-top:.28rem; }
        .constellation-legend { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:.55rem 1rem; margin:.05rem 0 .4rem; padding-bottom:.65rem; border-bottom:1px solid var(--panel-line); }
        .legend-sentiment { display:flex; align-items:center; gap:.55rem; min-width:0; }
        .legend-title { flex:0 0 auto; color:var(--panel-muted); font-size:.68rem; font-weight:600; }
        .sentiment-ramp-wrap { width:154px; max-width:36vw; }
        .sentiment-ramp { display:grid; grid-template-columns:repeat(3,1fr); height:7px; overflow:hidden; border-radius:999px; gap:2px; }
        .sentiment-ramp .ramp-negative { background:var(--negative); border-radius:999px 0 0 999px; }
        .sentiment-ramp .ramp-neutral { background:var(--neutral); }
        .sentiment-ramp .ramp-positive { background:var(--positive); border-radius:0 999px 999px 0; }
        .sentiment-ramp-labels { display:flex; justify-content:space-between; gap:.15rem; margin-top:.2rem; color:var(--panel-muted); font-size:.56rem; line-height:1.2; white-space:nowrap; }
        .legend-encodings { display:flex; align-items:center; flex-wrap:wrap; gap:.35rem .75rem; color:var(--panel-muted); font-size:.65rem; }
        .legend-encoding { display:inline-flex; align-items:center; gap:.35rem; white-space:nowrap; }
        .legend-node-mark { width:9px; height:9px; border:1.5px solid var(--panel-ink); border-radius:50%; opacity:.85; }
        .legend-link-mark { width:15px; height:1px; background:#858b91; }
        .empty-state { border:1px dashed var(--line); border-radius:16px; padding:1rem 1.1rem; color:var(--muted); background:var(--surface); line-height:1.55; }
        .score-number { color:var(--positive); font-size:2rem; font-weight:650; font-variant-numeric:tabular-nums; line-height:1.05; letter-spacing:-.04em; }
        .score-negative { color:var(--negative); }
        .score-neutral { color:var(--neutral); }
        .score-positive { color:var(--positive); }
        .st-key-company-summary .board-label { color:var(--panel-muted); }
        .sentiment-mix { display:flex; height:9px; overflow:hidden; border:1px solid var(--panel-line); background:var(--panel-raised); border-radius:999px; margin:.55rem 0 .35rem; }
        .sentiment-mix span { display:block; height:100%; }
        .mix-negative { background:var(--negative); }
        .mix-neutral { background:var(--neutral); }
        .mix-positive { background:var(--positive); }
        .mix-labels { display:flex; justify-content:space-between; gap:.4rem; color:var(--panel-muted); font-size:.68rem; font-variant-numeric:tabular-nums; }
        .article-list { width:100%; margin-top:.35rem; color:var(--panel-ink); font-variant-numeric:tabular-nums; }
        .article-list-head, .article-row { display:grid; grid-template-columns:minmax(0,68fr) minmax(0,32fr); gap:.5rem; align-items:center; }
        .article-list-head { color:var(--panel-muted); font-size:.62rem; font-weight:550; letter-spacing:.02em; text-transform:uppercase; padding:.45rem 0 .6rem; border-bottom:1px solid var(--panel-line); }
        .article-list-head > :last-child { text-align:right; }
        .article-row { padding:.68rem 0; border-bottom:1px solid var(--panel-line); font-size:.78rem; }
        .article-row:last-child { border-bottom:0; }
        .article-cell-story { min-width:0; }
        .article-title { display:-webkit-box; overflow:hidden; -webkit-box-orient:vertical; -webkit-line-clamp:2; color:var(--panel-ink) !important; text-decoration:none; font-size:.78rem; font-weight:560; line-height:1.35; }
        .article-title:hover { color:#fff !important; text-decoration:underline; text-decoration-color:var(--accent-bright); text-underline-offset:3px; }
        .article-meta { color:var(--panel-muted); font-size:.67rem; line-height:1.35; margin-top:.18rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
        .signal-chip { display:inline-flex; align-items:center; border-radius:999px; padding:.22rem .48rem; font-size:.67rem; white-space:nowrap; }
        .signal-positive { color:var(--positive); background:rgba(130,220,152,.13); }
        .signal-negative { color:var(--negative); background:rgba(255,120,135,.13); }
        .signal-neutral { color:var(--neutral); background:rgba(193,196,201,.13); }
        .signal-unscored { color:#dedbd6; background:rgba(255,255,255,.1); }
        .article-number { color:var(--panel-ink); white-space:nowrap; }
        .article-outcome { display:flex; min-width:0; flex-direction:column; align-items:flex-end; gap:.24rem; }
        .article-scores { display:flex; flex-wrap:wrap; justify-content:flex-end; gap:.1rem .42rem; font-size:.66rem; }
        .article-empty { color:var(--panel-muted); font-size:.84rem; padding:.8rem 0 .25rem; line-height:1.5; }
        .st-key-company-summary .score-positive, .st-key-company-summary .score-negative, .st-key-company-summary .score-neutral { color:inherit; }
        .st-key-company-summary .score-positive { color:var(--positive); }
        .st-key-company-summary .score-negative { color:var(--negative); }
        .st-key-company-summary .score-neutral { color:var(--neutral); }
        @media (prefers-reduced-motion:reduce) { *, *::before, *::after { scroll-behavior:auto !important; animation-duration:.01ms !important; animation-iteration-count:1 !important; transition-duration:.01ms !important; } }
        button:focus-visible, a:focus-visible, [tabindex]:focus-visible, input:focus-visible { outline:2px solid var(--accent) !important; outline-offset:3px !important; }
        .stButton button, .stFormSubmitButton button { transition:transform 120ms cubic-bezier(.16,1,.3,1), background-color 120ms ease, border-color 120ms ease; }
        .stButton button:active { transform:scale(.985); }
        .stFormSubmitButton button:active { transform:scale(.985); }
        ::selection { background:#f5b8c0; color:var(--ink); }
        input, textarea { caret-color:var(--accent) !important; }
        a { text-underline-offset:3px; }
        [data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:12px; overflow:hidden; }
        [data-testid="stAlert"] { border-radius:14px; }
        [data-testid="stExpander"] { border:1px solid var(--line); border-radius:12px; background:var(--surface); }
        @media (max-width:600px) {
          .block-container { padding-top:1rem !important; padding-bottom:1.35rem !important; padding-left:.85rem !important; padding-right:.85rem !important; }
          .fnc-head { align-items:flex-start; flex-direction:column; gap:.55rem; }
          .fnc-state { white-space:normal; }
          .fnc-description { font-size:.82rem; }
          .st-key-company-workspace [data-testid="stHorizontalBlock"], .st-key-trend-evidence [data-testid="stHorizontalBlock"] { gap:.7rem; }
          .st-key-company-summary .score-number { font-size:2.1rem; }
          .st-key-research-panel, .st-key-constellation-card, .st-key-company-summary, .st-key-trend-card, .st-key-article-card { padding:.75rem .8rem; border-radius:15px; }
          .st-key-company-workspace { padding:.45rem .55rem; border-radius:15px; }
          .st-key-company-workspace .st-key-constellation-card, .st-key-company-workspace .st-key-company-summary { padding:.55rem .35rem; }
          .st-key-company-workspace [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) { border-left:0; border-top:1px solid var(--panel-line); padding:1rem .35rem .45rem; }
          .constellation-legend { align-items:flex-start; flex-direction:column; gap:.5rem; }
          .sentiment-ramp-wrap { width:150px; max-width:48vw; }
          .coverage-summary-line { align-items:flex-start; flex-direction:column; }
          .st-key-company-summary .score-number { font-size:2.1rem; }
          .article-list-head { font-size:.57rem; }
          .article-title { font-size:.73rem; }
          .article-scores { gap:.28rem; font-size:.62rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_resource(show_spinner=False)
def _load_predictor(model_dir: str):
    from finnews.model import TargetSentimentModel

    return TargetSentimentModel(Path(model_dir))


def _empty_articles() -> pd.DataFrame:
    return pd.DataFrame(columns=ARTICLE_COLUMNS)


def _empty_predictions() -> pd.DataFrame:
    return pd.DataFrame(columns=["article_id", "ticker", "company", *PROBABILITY_COLUMNS, "label", "confidence", "sentiment_score", "evidence_text"])


def _constellation_alt(summary: pd.DataFrame, edges: pd.DataFrame) -> str:
    labels = []
    for _, row in summary.sort_values("ticker").iterrows():
        score = float(row["sentiment_score"])
        sentiment = "positive" if score >= 0.12 else "negative" if score <= -0.12 else "near neutral"
        labels.append(f"{row['ticker']}: {sentiment}, index {score:+.2f}, {int(row['article_count'])} articles")
    relationships = []
    if not edges.empty:
        ordered_edges = edges.sort_values("weight", ascending=False)
        relationships = [
            f"{row['source']} and {row['target']} shared {int(row['weight'])} articles"
            for _, row in ordered_edges.head(10).iterrows()
        ]
        if len(ordered_edges) > 10:
            relationships.append(f"and {len(ordered_edges) - 10} additional co-mention pairs")
    edge_text = "; ".join(relationships) if relationships else "no shared-article co-mention edges"
    return "Company sentiment network. Nodes: " + "; ".join(labels) + ". Co-mentions: " + edge_text + ". Position is a layout of shared article coverage, not a financial relationship."


def _constellation_legend_html() -> str:
    return (
        '<div class="constellation-legend" role="group" aria-label="Constellation legend">'
        '<div class="legend-sentiment"><span class="legend-title">Sentiment</span>'
        '<div class="sentiment-ramp-wrap" role="img" aria-label="Negative, near neutral, and positive sentiment bands">'
        '<div class="sentiment-ramp" aria-hidden="true"><span class="ramp-negative"></span>'
        '<span class="ramp-neutral"></span><span class="ramp-positive"></span></div>'
        '<div class="sentiment-ramp-labels"><span>Negative</span><span>Near neutral</span><span>Positive</span></div>'
        '</div></div><div class="legend-encodings">'
        '<span class="legend-encoding"><i class="legend-node-mark" aria-hidden="true"></i>Node size · articles</span>'
        '<span class="legend-encoding"><i class="legend-link-mark" aria-hidden="true"></i>Link width · shared articles</span>'
        '</div></div>'
    )


def _model_ready() -> bool:
    return (MODEL_DIR / "config.json").exists() and any(
        path.exists() for path in (MODEL_DIR / "model.safetensors", MODEL_DIR / "pytorch_model.bin")
    )


def _model_stamp() -> str:
    weights = [path for path in (MODEL_DIR / "model.safetensors", MODEL_DIR / "pytorch_model.bin") if path.exists()]
    return str(max(path.stat().st_mtime_ns for path in weights)) if weights else "missing"


def _demo_predictions(registry: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    articles, predictions = load_demo()
    company_names = registry.set_index("ticker")["company"].to_dict()
    predictions["company"] = predictions["ticker"].map(company_names).fillna(predictions["ticker"])
    predictions["label"] = predictions[PROBABILITY_COLUMNS].idxmax(axis=1)
    predictions["confidence"] = predictions[PROBABILITY_COLUMNS].max(axis=1)
    predictions["sentiment_score"] = predictions["positive"] - predictions["negative"]
    predictions["evidence_text"] = ""
    return articles, predictions


def _safe_source_url(value: object) -> str | None:
    url = str(value or "").strip()
    parsed = urlsplit(url)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return url
    return None


def _format_date(value: object) -> str:
    timestamp = pd.to_datetime(value, utc=True, errors="coerce")
    return timestamp.strftime("%d %b · %H:%M UTC") if not pd.isna(timestamp) else "Time unavailable"


def _timeline_figure(timeline: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    if not timeline.empty:
        dated = timeline.copy()
        dated["date"] = pd.to_datetime(dated["date"], errors="coerce")
        dated["sentiment_score"] = pd.to_numeric(dated["sentiment_score"], errors="coerce")
        dated["article_count"] = pd.to_numeric(dated["article_count"], errors="coerce").fillna(0)
        dated = dated.dropna(subset=["date", "sentiment_score"]).sort_values("date")
    else:
        dated = pd.DataFrame()
    if not dated.empty:
        figure.add_trace(go.Scatter(
            x=dated["date"],
            y=dated["sentiment_score"],
            customdata=dated["article_count"],
            mode="lines+markers",
            line={"color": "#fa7182", "width": 2.7},
            marker={"color": "#fa7182", "size": 7, "line": {"color": "#242424", "width": 1.5}},
            hovertemplate="%{x|%b %d}<br>Sentiment index: %{y:+.2f}<br>Articles: %{customdata}<extra></extra>",
            showlegend=False,
        ))
        figure.add_hline(y=0, line_color="#aaa7a3", line_width=1, line_dash="dot")
    else:
        figure.add_annotation(
            text="No dated sentiment records",
            x=0.5, y=0.5, xref="paper", yref="paper",
            showarrow=False, font={"size": 12, "color": "#b9b7b4"},
        )
    figure.update_layout(
        height=342,
        margin={"l": 56, "r": 18, "t": 14, "b": 54},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#c4c2bf", "family": "system-ui, -apple-system, BlinkMacSystemFont, sans-serif", "size": 11},
        hoverlabel={"bgcolor": "#f4f2ef", "bordercolor": "#c43a50", "font": {"color": "#181818"}},
        xaxis={
            "showgrid": False,
            "showline": False,
            "tickformat": "%b %d",
            "tickfont": {"color": "#c4c2bf", "size": 10},
            "ticks": "outside",
            "ticklen": 4,
            "tickcolor": "#777572",
            "automargin": True,
            "nticks": 6,
            "fixedrange": False,
        },
        yaxis={
            "range": [-1, 1],
            "tickvals": [-1, 0, 1],
            "ticktext": ["−1", "0", "+1"],
            "title": {"text": "Sentiment index", "font": {"size": 10, "color": "#c4c2bf"}, "standoff": 8},
            "tickfont": {"color": "#c4c2bf", "size": 10},
            "gridcolor": "rgba(214,211,207,.16)",
            "griddash": "dot",
            "zeroline": False,
            "fixedrange": False,
        },
        dragmode="zoom",
        uirevision="sentiment-timeline",
    )
    return figure


def _save_company_registry(registry: pd.DataFrame) -> None:
    """Validate and atomically persist the editable local company CSV."""
    columns = ["ticker", "company", "aliases"]
    cleaned = registry.copy()
    for column in columns:
        if column not in cleaned:
            cleaned[column] = ""
        cleaned[column] = cleaned[column].fillna("").astype(str).str.strip()
    cleaned["ticker"] = cleaned["ticker"].str.upper()
    cleaned = cleaned[cleaned["ticker"].ne("") | cleaned["company"].ne("")].copy()
    if cleaned["ticker"].eq("").any() or cleaned["company"].eq("").any():
        raise ValueError("Each company needs both a ticker and a company name.")
    duplicate_tickers = cleaned[cleaned["ticker"].duplicated(keep=False)]["ticker"].unique().tolist()
    if duplicate_tickers:
        raise ValueError(f"Ticker(s) must be unique: {', '.join(duplicate_tickers)}.")
    cleaned["aliases"] = cleaned["aliases"].str.replace(r"\s*[;,]\s*", "|", regex=True).str.strip("|")
    temporary_path = DATA_DIR / "companies.csv.tmp"
    cleaned[columns].to_csv(temporary_path, index=False)
    temporary_path.replace(DATA_DIR / "companies.csv")


def _story_table(merged: pd.DataFrame) -> pd.DataFrame:
    if merged.empty:
        return pd.DataFrame()
    table = merged.copy()
    table["Published (UTC)"] = pd.to_datetime(table["published_at"], utc=True, errors="coerce").dt.strftime("%Y-%m-%d %H:%M")
    table["Top class probability"] = 100 * pd.to_numeric(table.get("confidence", pd.Series(index=table.index, dtype=float)), errors="coerce")
    table["Sentiment index"] = pd.to_numeric(table.get("sentiment_score", pd.Series(index=table.index, dtype=float)), errors="coerce")
    for column in ("ticker", "label", "source", "title", "url"):
        if column not in table:
            table[column] = ""
    return table


def _recent_articles_html(rows: pd.DataFrame) -> str:
    if rows.empty:
        return '<div class="article-empty">No scored articles are available for this company in the selected coverage.</div>'

    table_rows: list[str] = []
    for _, story in rows.head(6).iterrows():
        title_text = str(story.get("title", "Untitled story") or "Untitled story")
        title = html.escape(title_text)
        source = html.escape(str(story.get("source", "Unknown source") or "Unknown source"))
        published = html.escape(_format_date(story.get("published_at")))
        label_value = str(story.get("label", "unscored") or "unscored").strip().lower().replace("_", " ")
        if label_value == "positive":
            sentiment_class = "positive"
        elif label_value == "negative":
            sentiment_class = "negative"
        elif label_value == "neutral":
            sentiment_class = "neutral"
        else:
            sentiment_class = "unscored"
        label = html.escape(label_value.title())
        score = pd.to_numeric(story.get("sentiment_score", None), errors="coerce")
        score_text = f"{score:+.2f}" if pd.notna(score) else "—"
        probability = pd.to_numeric(story.get("confidence", None), errors="coerce")
        probability_text = f"{probability:.0%}" if pd.notna(probability) else "—"
        url = _safe_source_url(story.get("url", ""))
        linked_title = (
            f'<a class="article-title" href="{html.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{title}</a>'
            if url else f'<span class="article-title">{title}</span>'
        )
        table_rows.append(
            f'<div class="article-row" role="row"><div class="article-cell-story" role="cell">{linked_title}'
            f'<div class="article-meta">{source} · {published}</div></div>'
            f'<div class="article-outcome" role="cell"><span class="signal-chip signal-{sentiment_class}">{label}</span>'
            f'<div class="article-scores"><span aria-label="Sentiment index">{score_text}</span>'
            f'<span aria-label="Top class model probability">{probability_text} est.</span></div></div></div>'
        )
    return (
        '<div class="article-list" role="table" aria-label="Recent company-targeted articles and sentiment estimates">'
        '<div class="article-list-head" role="row"><span role="columnheader">Article</span>'
        '<span role="columnheader">Signal · index · est.</span></div>'
        f'{"".join(table_rows)}</div>'
    )


def _load_metrics() -> dict | None:
    path = MODEL_DIR / "evaluation.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


@st.cache_data(show_spinner=False)
def _cached_infer(
    articles: pd.DataFrame,
    registry: pd.DataFrame,
    model_dir: str,
    model_stamp: str,
) -> pd.DataFrame:
    predictor = _load_predictor(model_dir)
    return score_article_targets(articles, registry, predictor)


def _infer(articles: pd.DataFrame, registry: pd.DataFrame) -> pd.DataFrame:
    return _cached_infer(articles, registry, str(MODEL_DIR), _model_stamp())


def _collect_curated_sources(sources: list[dict], lookback_days: int) -> tuple[pd.DataFrame, list[dict[str, str]]]:
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=lookback_days)
    frames: list[pd.DataFrame] = []
    outcomes: list[dict[str, str]] = []
    checked_at = datetime.now(timezone.utc).isoformat()
    for source in sources:
        source_id = str(source["source_id"])
        try:
            frame, _ = fetch_rss(str(source["feed_url"]), max_items=100, fetch_full_text=False)
            item_count = len(frame)
            published = pd.to_datetime(frame["published_at"], utc=True, errors="coerce")
            recent_mask = published.notna() & published.ge(cutoff)
            undated_count = int(published.isna().sum())
            recent = frame.loc[recent_mask].copy()
            recent["published_at"] = published.loc[recent_mask]
            recent["source"] = f"{source['publisher']} · {source['name']}"
            recent["source_id"] = source_id
            recent["record_type"] = "rss"
            message = f"{item_count} feed items checked; {len(recent)} dated within {lookback_days} days; {undated_count} undated skipped."
            update_source_check(SOURCE_DB, source_id, "OK", message, item_count, checked_at)
            outcomes.append({"source_id": source_id, "name": f"{source['publisher']} · {source['name']}", "status": "OK", "message": message})
            if not recent.empty:
                frames.append(recent)
        except Exception as exc:
            message = str(exc).strip() or "Feed request failed."
            update_source_check(SOURCE_DB, source_id, "Unavailable", message[:400], 0, checked_at)
            outcomes.append({"source_id": source_id, "name": f"{source['publisher']} · {source['name']}", "status": "Unavailable", "message": message[:400]})

    if frames:
        articles = pd.concat(frames, ignore_index=True)
        articles = articles.drop_duplicates("article_id", keep="first").sort_values("published_at", ascending=False).reset_index(drop=True)
        return articles, outcomes
    return pd.DataFrame(columns=[*ARTICLE_COLUMNS, "source_id"]), outcomes


_style()
initialize_store(SOURCE_DB, SOURCE_SEED)
registry = read_company_registry()
model_ready = _model_ready()
sources = list_sources(SOURCE_DB)
source_by_id = {source["source_id"]: source for source in sources}
pending_source_id = st.session_state.pop("pending_source_id", None)
if "selected_source_ids" not in st.session_state:
    st.session_state["selected_source_ids"] = list(source_by_id)
else:
    st.session_state["selected_source_ids"] = [
        source_id for source_id in st.session_state["selected_source_ids"] if source_id in source_by_id
    ]
if pending_source_id in source_by_id:
    selected_ids = st.session_state.get("selected_source_ids", list(source_by_id))
    st.session_state["selected_source_ids"] = list(dict.fromkeys([*selected_ids, pending_source_id]))
if "lookback_days" not in st.session_state:
    st.session_state["lookback_days"] = 7
if "workspace_view" not in st.session_state:
    st.session_state["workspace_view"] = "research"
valid_company_tickers = registry["ticker"].astype(str).tolist()
if "company_targets" not in st.session_state:
    st.session_state["company_targets"] = []
else:
    st.session_state["company_targets"] = [
        ticker for ticker in st.session_state["company_targets"] if ticker in valid_company_tickers
    ]

workspace_view = st.session_state["workspace_view"]
score_error: str | None = None
research_message = st.session_state.pop("research_message", "")
source_added_message = st.session_state.pop("source_added_message", "")

header_title, header_action = st.columns([0.84, 0.16], vertical_alignment="center")
with header_title:
    st.markdown(
        '<div class="fnc-head"><div><div class="fnc-name">Financial News Constellation</div>'
        '<div class="fnc-description">Company sentiment linked to the stories behind each signal.</div></div></div>',
        unsafe_allow_html=True,
    )
with header_action:
    action_label = "Demo" if workspace_view == "research" else "← Research"
    if st.button(action_label, key="workspace-nav", type="secondary", use_container_width=True):
        st.session_state["workspace_view"] = "demo" if workspace_view == "research" else "research"
        st.rerun()

if workspace_view == "research":
    with st.container(key="research-panel"):
        st.markdown("### Set up research")
        st.caption("Choose companies and a coverage window. RSS headlines stay on this Mac; full article pages are not fetched.")

        registry_signature = hashlib.sha256(registry.to_csv(index=False).encode("utf-8")).hexdigest()[:10]
        with st.expander("Manage company list", expanded=False):
            st.caption("Edit the local `data/companies.csv` registry. Aliases help match company mentions in headlines.")
            edited_registry = st.data_editor(
                registry,
                width="stretch",
                height=230,
                hide_index=True,
                num_rows="dynamic",
                key=f"company-registry-{registry_signature}",
                column_config={
                    "ticker": st.column_config.TextColumn("Ticker", help="Short unique identifier", max_chars=12),
                    "company": st.column_config.TextColumn("Company name", help="Name passed to the sentiment model"),
                    "aliases": st.column_config.TextColumn("Aliases", help="Separate alternate names with |"),
                },
            )
            save_company_col, registry_note_col = st.columns([0.22, 0.78], vertical_alignment="center")
            with save_company_col:
                if st.button("Save company list", key="save-company-list", type="secondary"):
                    try:
                        _save_company_registry(edited_registry)
                        st.session_state["company_targets"] = [
                            ticker for ticker in st.session_state["company_targets"]
                            if ticker in set(edited_registry.get("ticker", pd.Series(dtype=str)).astype(str).str.upper())
                        ]
                        st.rerun()
                    except (OSError, ValueError) as exc:
                        st.error(f"Company list not saved: {exc}")
            with registry_note_col:
                st.caption("Changes are saved on this Mac and used on the next analysis run.")

            with st.form(f"add-company-form-{registry_signature}", clear_on_submit=True):
                st.markdown("**Add a company**")
                add_ticker_col, add_name_col, add_alias_col = st.columns([0.18, 0.34, 0.48])
                with add_ticker_col:
                    new_ticker = st.text_input("Ticker", placeholder="ORCL", max_chars=12)
                with add_name_col:
                    new_company = st.text_input("Company name", placeholder="Oracle Corporation")
                with add_alias_col:
                    new_aliases = st.text_input("Aliases", placeholder="Oracle | Oracle Corp.")
                add_company_clicked = st.form_submit_button("Add company", type="secondary")
                if add_company_clicked:
                    ticker_value = new_ticker.strip().upper()
                    name_value = new_company.strip()
                    existing = set(registry["ticker"].astype(str).str.upper())
                    if not ticker_value or not name_value:
                        st.error("Enter both a ticker and a company name.")
                    elif ticker_value in existing:
                        st.error(f"{ticker_value} already exists. Edit that row in the company list.")
                    else:
                        try:
                            added = pd.DataFrame([{
                                "ticker": ticker_value,
                                "company": name_value,
                                "aliases": new_aliases.strip().replace(",", "|").replace(";", "|"),
                            }])
                            _save_company_registry(pd.concat([edited_registry, added], ignore_index=True))
                            st.rerun()
                        except (OSError, ValueError) as exc:
                            st.error(f"Company not added: {exc}")

        valid_company_tickers = registry["ticker"].astype(str).tolist()
        st.session_state["company_targets"] = [
            ticker for ticker in st.session_state["company_targets"] if ticker in valid_company_tickers
        ]
        current_source_ids = st.session_state.get("selected_source_ids", list(source_by_id))
        selected_source_ids = current_source_ids
        target_col, controls_col = st.columns([1.05, 1.15], vertical_alignment="bottom")
        with target_col:
            selected_company_tickers = st.multiselect(
                "Companies to analyze",
                options=valid_company_tickers,
                format_func=lambda ticker: f"{ticker} · {registry.set_index('ticker')['company'].get(ticker, ticker)}",
                placeholder="All saved companies",
                key="company_targets",
                help="Leave empty to include every saved company. Add or edit companies in Manage company list.",
            )
        with controls_col:
            feed_col, period_col, action_col = st.columns([0.9, 1.05, 1], vertical_alignment="bottom")
            with feed_col:
                with st.popover(f"Feeds · {len(current_source_ids)}", use_container_width=True):
                    selected_source_ids = st.multiselect(
                        "RSS feeds",
                        options=list(source_by_id),
                        format_func=lambda source_id: f"{source_by_id[source_id]['publisher']} · {source_by_id[source_id]['name']}",
                        key="selected_source_ids",
                        help="Selected feeds are checked when you run Research; inclusion is not a guarantee of accuracy or complete coverage.",
                    )
            with period_col:
                lookback_days = st.selectbox(
                    "Look back",
                    options=[1, 3, 7, 14, 30],
                    format_func=lambda days: f"Last {days} day{'s' if days != 1 else ''}",
                    key="lookback_days",
                )
            with action_col:
                research_clicked = st.button("Research", key="research-now", type="primary", use_container_width=True)

        research_registry = registry[
            registry["ticker"].isin(selected_company_tickers or valid_company_tickers)
        ].copy()

        st.caption("Feeds expose a limited recent slice; undated headlines are skipped.")

        if research_clicked:
            if not selected_source_ids:
                st.warning("Select at least one source to run Research.")
            else:
                selected_sources = [source_by_id[source_id] for source_id in selected_source_ids]
                started_at = datetime.now(timezone.utc).isoformat()
                run_id = uuid4().hex
                with st.spinner("Checking feeds, keeping recent headlines, and scoring company mentions…"):
                    articles, outcomes = _collect_curated_sources(selected_sources, int(lookback_days))
                    successful_sources = sum(result["status"] == "OK" for result in outcomes)
                    if articles.empty:
                        failed = sum(result["status"] != "OK" for result in outcomes)
                        st.session_state["research_message"] = (
                            "No dated headlines were found in this window. Check source status below, or widen the lookback period."
                            if failed == 0
                            else f"No recent headlines loaded; {failed} source(s) could not be read. Check source status below."
                        )
                    else:
                        predictions = _infer(articles, research_registry) if model_ready else _empty_predictions()
                        run_status = "complete" if successful_sources == len(selected_sources) else "partial"
                        if not model_ready:
                            run_status = "unscored"
                        note = f"{successful_sources}/{len(selected_sources)} sources responded."
                        save_research_run(
                            SOURCE_DB,
                            run_id=run_id,
                            started_at=started_at,
                            finished_at=datetime.now(timezone.utc).isoformat(),
                            lookback_days=int(lookback_days),
                            source_ids=selected_source_ids,
                            articles=articles,
                            predictions=predictions,
                            status=run_status,
                            note=note,
                        )
                        st.session_state["research_message"] = f"Loaded {len(articles)} recent headlines from {successful_sources} of {len(selected_sources)} selected feeds."
                st.session_state["workspace_view"] = "research"
                st.rerun()

        if research_message:
            st.info(research_message)

        with st.expander("Source status", expanded=False):
            source_status = pd.DataFrame([
                {
                    "Publisher": source["publisher"],
                    "Feed": source["name"],
                    "Status": source["last_status"],
                    "Last checked · UTC": _format_date(source["last_checked_at"]) if source["last_checked_at"] else "Not checked",
                    "Items last check": source["last_item_count"],
                    "RSS feed": source["feed_url"],
                }
                for source in sources
            ])
            st.dataframe(
                source_status,
                width="stretch",
                hide_index=True,
                column_config={
                    "Publisher": st.column_config.TextColumn("Publisher", width="small"),
                    "Feed": st.column_config.TextColumn("Feed", width="medium"),
                    "Status": st.column_config.TextColumn("Status", width="small"),
                    "Last checked · UTC": st.column_config.TextColumn("Last checked · UTC", width="medium"),
                    "Items last check": st.column_config.NumberColumn("Items", width="small"),
                    "RSS feed": st.column_config.LinkColumn("RSS URL", display_text="Open", width="small"),
                },
                alt="RSS feeds and their last live health check.",
            )
            with st.form("add-rss-source", clear_on_submit=True):
                st.markdown("**Add your own feed**")
                rss_url = st.text_input("RSS or Atom URL", placeholder="https://example.com/markets/rss")
                rss_name = st.text_input("Feed label · optional", placeholder="e.g. Markets headlines", max_chars=80)
                add_feed_clicked = st.form_submit_button("Add feed", type="secondary")
                if add_feed_clicked:
                    try:
                        new_source_id = add_source(SOURCE_DB, rss_url, rss_name)
                    except ValueError as exc:
                        st.error(str(exc))
                    else:
                        st.session_state["pending_source_id"] = new_source_id
                        st.session_state["source_added_message"] = "Feed added and selected. Press Research to check it and load headlines."
                        st.rerun()
            st.caption("Feeds are saved locally and are not contacted until you press Research. Bundled sources stay in the list when the catalog refreshes.")

        if source_added_message:
            st.success(source_added_message)

        with st.expander("Analyze a CSV instead", expanded=False):
            uploaded = st.file_uploader(
                "Choose an article CSV",
                type=["csv"],
                help="Required: title or text. Optional: published_at, source, url, companies.",
                key="csv-upload",
            )
            if uploaded is not None:
                raw_bytes = uploaded.getvalue()
                digest = hashlib.sha256(raw_bytes).hexdigest()
                if st.session_state.get("csv_digest") != digest:
                    try:
                        imported = normalize_articles(pd.read_csv(io.BytesIO(raw_bytes)), source_name=uploaded.name)
                        with st.spinner("Scoring the uploaded articles locally…"):
                                csv_predictions = _infer(imported, research_registry) if model_ready else _empty_predictions()
                        st.session_state["csv_digest"] = digest
                        st.session_state["csv_articles"] = imported
                        st.session_state["csv_predictions"] = csv_predictions
                        st.session_state["csv_name"] = uploaded.name
                        st.session_state["workspace_view"] = "csv"
                        st.rerun()
                    except Exception as exc:
                        score_error = f"Could not analyze this CSV. Check its columns and encoding. {exc}"
                        st.error(score_error)

if workspace_view == "demo":
    demo_articles, predictions = _demo_predictions(registry)
    scored_by_model = False
    if model_ready:
        try:
            with st.spinner("Scoring the fictional demo headlines with the local model…"):
                predictions = _infer(demo_articles, registry)
            scored_by_model = True
        except Exception as exc:
            score_error = f"The local model could not score the demo: {exc}"
    articles = demo_articles.copy()
elif workspace_view == "csv":
    articles = st.session_state.get("csv_articles", _empty_articles()).copy()
    predictions = st.session_state.get("csv_predictions", _empty_predictions())
    scored_by_model = model_ready and not predictions.empty
else:
    latest_run, articles, predictions = load_latest_research(SOURCE_DB)
    scored_by_model = model_ready and not predictions.empty
    if latest_run is not None:
        try:
            selected_run_sources = json.loads(latest_run["source_ids"])
        except (TypeError, json.JSONDecodeError):
            selected_run_sources = []
    else:
        selected_run_sources = []

if workspace_view != "research":
    latest_run = None
    selected_run_sources = []

if "published_at" in articles:
    articles["published_at"] = pd.to_datetime(articles["published_at"], utc=True, errors="coerce")
    articles = articles.drop_duplicates("article_id", keep="first").reset_index(drop=True)
if "published_at" in predictions and not predictions.empty:
    predictions["published_at"] = pd.to_datetime(predictions["published_at"], utc=True, errors="coerce")

all_tickers = sorted(predictions.get("ticker", pd.Series(dtype=str)).dropna().astype(str).unique().tolist())
company_names = registry.set_index("ticker")["company"].to_dict()
target_filter = st.session_state.get("company_targets", [])
selected_tickers = [ticker for ticker in all_tickers if not target_filter or ticker in target_filter]
visible_articles = articles.copy()
visible_ids = set(visible_articles.get("article_id", pd.Series(dtype=str)).astype(str))
visible_predictions = predictions[predictions.get("article_id", pd.Series(dtype=str)).astype(str).isin(visible_ids)].copy() if not predictions.empty else _empty_predictions()
visible_predictions = visible_predictions[visible_predictions["ticker"].isin(selected_tickers)].copy() if not visible_predictions.empty else _empty_predictions()

summary_all = company_summary(visible_predictions)
summary = summary_all.copy()
visible_tickers = set(summary.get("ticker", pd.Series(dtype=str)).astype(str))
graph_predictions = visible_predictions[visible_predictions["ticker"].isin(visible_tickers)].copy() if not visible_predictions.empty else _empty_predictions()
edges = co_mention_edges(visible_articles, graph_predictions)
merged_stories = merge_article_predictions(visible_articles, graph_predictions) if not graph_predictions.empty else pd.DataFrame()
unmatched_count = len(visible_articles) - visible_articles[visible_articles["article_id"].isin(graph_predictions.get("article_id", []))]["article_id"].nunique() if not visible_articles.empty else 0

if workspace_view == "demo":
    state_text = "MODEL SCORES · FICTIONAL TEXT" if scored_by_model else "DEMO · ILLUSTRATIVE SCORES"
elif workspace_view == "csv":
    state_text = "CSV · LOCAL MODEL SCORES" if scored_by_model else "CSV · NOT SCORED"
elif scored_by_model:
    state_text = "SAVED RESEARCH · LOCAL MODEL"
else:
    state_text = "SAVED RESEARCH · MODEL NOT TRAINED" if not visible_articles.empty else "READY TO RESEARCH"

total_articles = int(visible_articles["article_id"].nunique()) if not visible_articles.empty else 0
total_companies = int(summary["ticker"].nunique()) if not summary.empty else 0
if not visible_articles.empty and "source_id" in visible_articles:
    feed_ids = visible_articles["source_id"].fillna("").astype(str)
    source_count = int(feed_ids[feed_ids.ne("")].nunique())
else:
    source_count = 0
if source_count == 0 and not visible_articles.empty and "source" in visible_articles:
    source_count = int(visible_articles["source"].nunique())
latest = visible_articles["published_at"].max() if not visible_articles.empty and "published_at" in visible_articles else pd.NaT
source_count_label = "feeds" if workspace_view == "research" else "sources"
if workspace_view == "demo":
    updated_text = "Demo sample"
elif workspace_view == "csv":
    updated_text = "CSV import"
else:
    updated_at = pd.to_datetime(latest_run.get("finished_at") if latest_run else latest, utc=True, errors="coerce")
    updated_text = updated_at.strftime("%d %b") if not pd.isna(updated_at) else "—"
coverage_note = str(latest_run.get("note", "")) if workspace_view == "research" and latest_run else "Sentiment is an estimate, not a forecast."
status_class = "fnc-state-warning" if "NOT TRAINED" in state_text or "NOT SCORED" in state_text else ""
status_label = {
    "SAVED RESEARCH · LOCAL MODEL": "SAVED · LOCAL MODEL",
    "SAVED RESEARCH · MODEL NOT TRAINED": "HEADLINES ONLY",
    "READY TO RESEARCH": "READY",
    "MODEL SCORES · FICTIONAL TEXT": "DEMO · MODEL SCORES",
    "DEMO · ILLUSTRATIVE SCORES": "DEMO · ILLUSTRATIVE",
    "CSV · LOCAL MODEL SCORES": "CSV · MODEL SCORES",
}.get(state_text, state_text)

st.markdown("## Company signals")

if summary.empty:
    if visible_articles.empty:
        if workspace_view == "csv":
            empty_message = "Upload an article CSV in the Research setup to analyze it."
        elif workspace_view == "demo":
            empty_message = "The demo sample has no articles to display."
        else:
            empty_message = "Choose RSS feeds and press Research, or open Demo to see the dashboard with sample data."
    elif not model_ready and workspace_view != "demo":
        empty_message = "Headlines are ready. Train the target-aware classifier to add company sentiment."
    else:
        empty_message = "No scored company targets match the current selection. Review company names and aliases in Manage company list."
    if not visible_articles.empty:
        coverage_context = (
            f'<div class="coverage-empty-facts"><strong>{total_articles:,}</strong> headlines · '
            f'<strong>{source_count:,}</strong> {html.escape(source_count_label)} · '
            f'Updated {html.escape(updated_text)}</div>'
        )
    else:
        coverage_context = ""
    st.markdown(
        f'<div class="empty-state">{html.escape(empty_message)}{coverage_context}</div>',
        unsafe_allow_html=True,
    )
else:
    company_options = summary["ticker"].astype(str).tolist()
    old_selection = str(st.session_state.get("company_select", ""))
    if old_selection not in company_options:
        old_selection = company_options[0]
    st.session_state["company_select"] = old_selection
    with st.container(key="company-workspace"):
        graph_col, insight_col = st.columns([1.48, 1], gap="large", vertical_alignment="top")

    with graph_col, st.container(key="constellation-card"):
        st.markdown("### Co-mention network")
        st.markdown(_constellation_legend_html(), unsafe_allow_html=True)
        figure = make_constellation(summary, edges, selected=old_selection)
        graph_key = f"company-network-{workspace_view}-{'-'.join(sorted(visible_tickers))}"
        event = st.plotly_chart(
            figure,
            width="stretch",
            theme=None,
            key=graph_key,
            on_select="rerun",
            selection_mode="points",
            alt=_constellation_alt(summary, edges),
            config={
                "displayModeBar": "hover",
                "displaylogo": False,
                "modeBarButtonsToAdd": ["resetScale2d"],
                "scrollZoom": False,
            },
        )
        selection = getattr(event, "selection", {})
        points = selection.get("points", []) if hasattr(selection, "get") else []
        for point in reversed(points):
            custom = point.get("customdata")
            ticker = custom[0] if isinstance(custom, (list, tuple)) and custom else custom
            if str(ticker) in company_options:
                st.session_state["company_select"] = str(ticker)
                break

    with insight_col, st.container(key="company-summary"):
        st.markdown("### Company snapshot")
        selected_ticker = st.selectbox(
            "Company",
            company_options,
            key="company_select",
            format_func=lambda ticker: f"{ticker} · {company_names.get(ticker, ticker)}",
        )
        selected_summary = summary[summary["ticker"] == selected_ticker].iloc[0]
        score = float(selected_summary["sentiment_score"])
        score_class = "score-positive" if score >= 0.12 else "score-negative" if score <= -0.12 else "score-neutral"
        score_label = "Leaning positive" if score >= 0.12 else "Leaning negative" if score <= -0.12 else "Near neutral"
        st.markdown(
            f'<div class="snapshot-signal-row"><div class="snapshot-score-block">'
            f'<div class="score-number {score_class}">{score:+.2f}</div>'
            f'<div class="board-label {score_class}">{score_label} · sentiment index</div></div>'
            f'<div class="snapshot-volume"><div class="snapshot-volume-value">{int(selected_summary["article_count"]):,}</div>'
            '<div class="snapshot-volume-label">targeted articles</div></div></div>',
            unsafe_allow_html=True,
        )
        st.caption("Index ranges from −1 to +1.")
        st.markdown('<div class="board-label">Average model probability by class</div>', unsafe_allow_html=True)
        probabilities = {label: max(0.0, min(1.0, float(selected_summary[label]))) for label in PROBABILITY_COLUMNS}
        total_probability = sum(probabilities.values()) or 1.0
        percentages = {label: probabilities[label] / total_probability * 100 for label in PROBABILITY_COLUMNS}
        probability_description = ", ".join(f"{label.title()} {percentages[label]:.0f}%" for label in ("negative", "neutral", "positive"))
        st.markdown(
            f'<div class="sentiment-mix" role="img" aria-label="Average model probabilities: {html.escape(probability_description)}">'
            f'<span class="mix-negative" style="width:{percentages["negative"]:.2f}%"></span>'
            f'<span class="mix-neutral" style="width:{percentages["neutral"]:.2f}%"></span>'
            f'<span class="mix-positive" style="width:{percentages["positive"]:.2f}%"></span></div>'
            f'<div class="mix-labels"><span>Negative {percentages["negative"]:.0f}%</span><span>Neutral {percentages["neutral"]:.0f}%</span><span>Positive {percentages["positive"]:.0f}%</span></div>',
            unsafe_allow_html=True,
        )
        st.caption("Model probabilities are estimates, not calibrated certainty.")
        unmatched_html = (
            f'<span class="coverage-unmatched"><strong>{unmatched_count:,}</strong> unmatched</span>'
            if unmatched_count > 0 else ""
        )
        st.markdown(
            f'<div class="coverage-summary-line"><div class="coverage-summary-facts">'
            f'<span><strong>{total_articles:,}</strong> headlines</span>'
            f'<span><strong>{total_companies:,}</strong> companies</span>'
            f'<span><strong>{source_count:,}</strong> {html.escape(source_count_label)}</span>'
            f'<span>Updated <strong>{html.escape(updated_text)}</strong></span>'
            f'{unmatched_html}</div>'
            f'<div class="coverage-summary-state"><span class="fnc-state {status_class}">'
            f'<span class="state-dot"></span>{html.escape(status_label)}</span>'
            f'<span>{html.escape(coverage_note)}</span></div></div>',
            unsafe_allow_html=True,
        )

    selected_ticker = st.session_state.get("company_select", old_selection)
    selected_timeline = sentiment_timeline(merged_stories)
    selected_timeline = selected_timeline[selected_timeline["ticker"] == selected_ticker] if not selected_timeline.empty else selected_timeline
    selected_rows = merged_stories[merged_stories["ticker"] == selected_ticker].sort_values("published_at", ascending=False) if not merged_stories.empty else pd.DataFrame()

    with st.container(key="trend-evidence"):
        trend_col, article_col = st.columns([1.2, 1], gap="large", vertical_alignment="top")
    with trend_col, st.container(key="trend-card"):
        st.markdown("### Sentiment over time")
        st.markdown('<div class="section-note">Daily sentiment index from −1 (negative) to +1 (positive). Hover for article count.</div>', unsafe_allow_html=True)
        st.plotly_chart(
            _timeline_figure(selected_timeline),
            width="stretch",
            theme=None,
            config={
                "displayModeBar": "hover",
                "displaylogo": False,
                "modeBarButtonsToAdd": ["resetScale2d"],
                "scrollZoom": False,
            },
            alt="Daily target sentiment index for the selected company.",
        )

    with article_col, st.container(key="article-card"):
        ticker_label = html.escape(str(selected_ticker))
        st.markdown(f"### Recent articles · {ticker_label}")
        st.markdown('<div class="section-note">Newest first · open a headline to read its source. Model estimates are probabilities, not certainty.</div>', unsafe_allow_html=True)
        st.markdown(_recent_articles_html(selected_rows), unsafe_allow_html=True)

coverage_label = f"Browse all articles · {len(visible_articles)}"
with st.expander(coverage_label, expanded=False):
    if not visible_articles.empty:
        if not merged_stories.empty:
            coverage = _story_table(merged_stories)
            columns = ["Published (UTC)", "ticker", "title", "label", "Sentiment index", "Top class probability", "source", "url"]
            coverage = coverage[[column for column in columns if column in coverage.columns]].copy()
            event = st.dataframe(
                coverage,
                width="stretch",
                height=min(520, max(240, 38 * min(12, len(coverage)) + 42)),
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                key=f"coverage-table-{workspace_view}-{len(coverage)}",
                column_config={
                    "Published (UTC)": st.column_config.TextColumn("Published · UTC", width="small"),
                    "ticker": st.column_config.TextColumn("Company", width="small"),
                    "title": st.column_config.TextColumn("Article", width="large"),
                    "label": st.column_config.TextColumn("Sentiment", width="small"),
                    "Sentiment index": st.column_config.NumberColumn("Index", format="%+.2f", width="small"),
                    "Top class probability": st.column_config.NumberColumn("Class probability", format="%.0f%%", width="small"),
                    "source": st.column_config.TextColumn("Source", width="medium"),
                    "url": st.column_config.LinkColumn("Article link", display_text="Open", width="small"),
                },
                alt="Sortable table of company-targeted news, sentiment estimates, and sources.",
            )
            rows_selected = getattr(getattr(event, "selection", {}), "rows", [])
            if rows_selected:
                position = rows_selected[0]
                if 0 <= position < len(merged_stories):
                    story = merged_stories.iloc[position]
                    st.markdown(f"**{story.get('title', 'Untitled story')}**")
                    article_text = str(story.get("evidence_text", "") or story.get("text", "")).strip()
                    st.write(article_text or "No article body text was supplied.")
                    st.caption(f"{story.get('company', story.get('ticker', ''))} · {story.get('label', 'unscored')} · model probability {float(story.get('confidence', 0)):.0%}")
                    url = _safe_source_url(story.get("url", ""))
                    if url:
                        st.link_button("Open source article", url)
            export = merged_stories.to_csv(index=False).encode("utf-8")
            st.download_button("Download scored articles", export, file_name="financial_news_target_sentiment.csv", mime="text/csv")
        else:
            raw = visible_articles.copy()
            raw["Published (UTC)"] = raw["published_at"].dt.strftime("%Y-%m-%d %H:%M")
            raw["Article link"] = raw["url"].fillna("")
            columns = ["Published (UTC)", "source", "title", "companies", "Article link"]
            show = raw[[column for column in columns if column in raw.columns]].copy()
            st.dataframe(
                show,
                width="stretch",
                height=min(520, max(240, 38 * min(12, len(show)) + 42)),
                hide_index=True,
                column_config={"Article link": st.column_config.LinkColumn("Source", display_text="Open")},
                alt="Sortable table of imported financial news articles.",
            )
            st.caption("Train the target classifier to add company-level sentiment scores.")
            export = visible_articles.to_csv(index=False).encode("utf-8")
            st.download_button("Download articles", export, file_name="financial_news_articles.csv", mime="text/csv")
    else:
        st.markdown('<div class="empty-state">No articles match the current source and filters.</div>', unsafe_allow_html=True)

metrics = _load_metrics()
headline_f1 = metrics.get("held_out_macro_f1") if metrics else None
model_expander_label = f"Model quality & method · held-out headline macro F1 {float(headline_f1):.3f}" if headline_f1 is not None else "Model quality & method"
with st.expander(model_expander_label, expanded=False):
    st.markdown("### What the model reads")
    st.markdown("The fine-tuned DistilBERT classifier receives a company name together with a financial headline or text span. It estimates positive, neutral, and negative probabilities for that company. The dashboard averages those probabilities across unique company–article pairs; the sentiment index is average positive probability minus average negative probability.")
    if model_ready:
        st.caption("Local fine-tuned checkpoint found. RSS and CSV predictions run on this machine.")
        if metrics:
            st.markdown("### Held-out evaluation")
            st.caption("Headline-level test results, grouped by normalized headline. They do not establish accuracy on longer article bodies or new publishers.")
            st.markdown(f"Held-out macro F1: **{float(headline_f1):.3f}**")
            report = metrics.get("classification_report", {})
            rows = [
                {
                    "Class": label.title(),
                    "Precision": report.get(label, {}).get("precision"),
                    "Recall": report.get(label, {}).get("recall"),
                    "F1": report.get(label, {}).get("f1-score"),
                    "Support": report.get(label, {}).get("support"),
                }
                for label in ["negative", "neutral", "positive"]
            ]
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True, alt="Per-class precision, recall, F1, and held-out support.")
            matrix = metrics.get("confusion_matrix_true_rows_predicted_columns")
            if matrix:
                heat = go.Figure(go.Heatmap(
                    z=matrix,
                    x=["Negative", "Neutral", "Positive"],
                    y=["Negative", "Neutral", "Positive"],
                    colorscale=[[0, "#eae5d9"], [1, "#566b50"]],
                    text=matrix,
                    texttemplate="%{text}",
                    hovertemplate="Actual %{y}<br>Predicted %{x}<br>Count %{z}<extra></extra>",
                    colorbar={"title": "Rows"},
                ))
                heat.update_layout(
                    height=290,
                    margin={"l": 4, "r": 4, "t": 12, "b": 4},
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font={"color": "#615f55"},
                )
                st.plotly_chart(heat, width="stretch", theme=None, config={"displayModeBar": False}, alt="Confusion matrix for the grouped held-out headline set.")
        else:
            st.info("The checkpoint is present, but its evaluation report is missing. Re-run training to create an auditable result.")
    else:
        st.info("No fine-tuned checkpoint is present. Demo sentiment is illustrative; RSS and CSV articles remain unscored until a model is trained.")

    st.markdown("### Train locally")
    st.markdown("Download the SEntFiN dataset from the [official repository](https://github.com/pyRis/SEntFiN), then run:")
    st.code("python scripts/train_model.py --data data/SEntFiN.csv", language="bash")
    st.markdown("Training expands each headline into company-targeted examples, keeps versions of the same headline in one data split, selects a checkpoint by validation macro F1, and reports class-level test metrics. It uses Apple MPS when available and CPU otherwise.")
    st.markdown("SEntFiN labels company sentiment in headlines. Softmax probabilities are estimates, not calibrated certainty. The constellation line only means two companies appeared in one article; the tool does not predict returns or provide investment advice.")
    st.caption("The dataset is downloaded separately. Review its terms before redistributing data or checkpoints. The app reads user-selected RSS feeds or CSV files; optional page extraction is manual, capped, and checks robots.txt.")
