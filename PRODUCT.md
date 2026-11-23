# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Streamlit for a local app on the user's Apple Silicon Mac; Python, Hugging Face Transformers, and PyTorch MPS for the NLP pipeline. The app opens to an empty research workspace, with bundled or user-added RSS, CSV upload, and fictional demo available as explicit actions. When a local checkpoint is available, the app automatically scores the fictional demo text; fine-tuning remains an explicit local command.

## Users

The primary user is a solo analyst or project reviewer who wants to scan financial news for sentiment toward selected companies and inspect the evidence behind each result. 

## Product Purpose

Financial News Constellation collects selected financial news, identifies companies, estimates positive, neutral, or negative sentiment toward each company, and presents the results in an interactive co-mention graph and time-based view. Success means a reviewer can understand which companies are discussed, see the model's estimated sentiment and article volume, and inspect source text supporting the predictions.

## Positioning

The product connects company-targeted sentiment predictions to their article sources and supporting text, rather than presenting an unexplained sentiment score. Co-mentions describe shared coverage only; the product does not infer company relationships, market correlation, future returns, or investment recommendations.

## Operating Context

The app runs locally and opens to a research setup. Users can select companies, choose from the bundled RSS catalog or add their own RSS/Atom URL in Source status, and fetch headlines for a lookback window; CSV upload and fictional sample data remain available as separate actions. The company names and aliases are editable in the web interface and saved to `data/companies.csv`. Results and feed records are saved locally in SQLite. Users can select a company in the graph and review article evidence and model probabilities.

## Capabilities and Constraints

- The implemented training script fine-tunes `distilbert/distilbert-base-uncased` as a three-class model conditioned on a company target. It pairs each text span with its target; long articles are scored using target-bearing sentences and adjacent context.
- The benchmark is SEntFiN 1.0. Data is downloaded separately, and the upstream dataset and model terms must be reviewed before redistributing data or checkpoints. Full-article performance requires separate validation on reviewed article text.
- Demo article text is fictional. With a local checkpoint, displayed scores are the model's predictions on that fictional text and are labeled as such; without a checkpoint, hand-authored illustrative scores are labeled as illustrative.
- RSS headlines come from a locally stored curated catalog seeded from `data/rss_sources.csv`; users can also add a custom RSS/Atom URL in Source status. Feed records are saved in SQLite. The app checks selected feeds only when Research is run and saves results locally. It does not poll in the background or fetch full article pages from RSS. CSV remains a separate input. Catalog inclusion is not a guarantee of accuracy or complete coverage, and feeds may provide only a limited recent slice.
- The training script selects Apple MPS when available and otherwise uses CPU. Actual speed and memory use depend on unified memory and other running applications.
- This is a news analysis and research-triage tool, not a financial forecasting or trading system.

## Brand Commitments

The project name is **Financial News Constellation**. Its interface uses a screenshot-inspired analytics layout: a warm gray shell, charcoal data panels, a compact research setup, and a prominent company network. A recent-articles analytics table and sentiment timeline sit together below the company network. Coral highlights interaction; green, salmon, and silver identify positive, negative, and near-neutral sentiment. Network edges mean that companies were co-mentioned in the same article.

## Evidence on Hand

- `sentiment-analysis-for-financial-news.ipynb` is the existing baseline: an AWD-LSTM/ULMFiT classifier trained on financial sentence labels. Its saved outputs report 76% accuracy and 0.72 macro F1 on a random held-out split. It does not ingest articles, identify tickers, or build the constellation.
- `app.py`, `src/finnews/`, and `scripts/train_model.py` implement the local dashboard, ingestion/inference pipeline, and target-aware DistilBERT fine-tuning workflow.
- `Financial News Constellation.md` and `README.md` explain the data, methodology, outputs, limitations, setup, and interview summary.
- This workspace contains an ignored local SEntFiN CSV, trained checkpoint, and evaluation report; a fresh Git checkout does not include them and must download the dataset and train locally. The recorded MPS run reached 0.8522 held-out macro F1 on 2,887 target-labeled headline examples. This does not establish performance on full articles or new publishers. The bundled RSS list is a convenience catalog, not a reliability certification or a production scraping permission.

## Product Principles

- Show the article and text evidence behind each prediction.
- Keep sentiment tied to a named company target.
- Preserve source, publication time, and deduplication provenance.
- Make uncertainty and article volume visible alongside aggregate sentiment.
- Keep descriptive sentiment analysis separate from return prediction.

## Accessibility & Inclusion

Use readable labels, standard keyboard-operable filters, visible focus states, and text alternatives for graph relationships so the key information is available without relying on color alone.
