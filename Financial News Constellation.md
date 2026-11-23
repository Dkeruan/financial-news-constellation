# Financial News Constellation

_A local NLP tool for company-targeted sentiment analysis of financial news._

## Purpose

Financial News Constellation fetches headlines from a curated RSS catalog or accepts CSV articles, identifies companies through an editable alias registry, and estimates positive, neutral, or negative sentiment toward each company. It presents the results as an interactive company co-mention graph, a sentiment timeline, and source-linked evidence.

The tool supports news analysis and research triage. It does not predict returns, infer company relationships, or make investment recommendations.

## Data

The fine-tuning benchmark is **SEntFiN 1.0**, a human-annotated financial news headline dataset with 10,753 headlines and 14,404 entity-sentiment annotations. Some headlines contain multiple companies with different labels, making the data relevant to target-conditioned sentiment classification. The dataset is downloaded separately and is not bundled with this project. See the [SEntFiN paper](https://arxiv.org/abs/2305.12257) and its [official repository](https://github.com/pyRis/SEntFiN); check upstream terms before redistributing the CSV or derived model files.

Research runs are manual: the user selects companies, a lookback window, and feeds from the local curated catalog. The catalog is seeded from `data/rss_sources.csv`, and feed status and analyzed headline records are saved in `data/financial_news.sqlite3`. The app stores RSS headlines, summaries, source links, and predictions; it does not fetch full article pages or poll in the background. CSV input can include publication time, source, URL, title, text, and optional company targets. The web interface can edit the local alias registry at `data/companies.csv` or add a company through ticker, name, and alias fields.

The bundled demo article text is fictional and lives behind an explicit `Demo` button. When a local checkpoint is available, the app runs the model on that fictional text and labels the result `MODEL SCORES · FICTIONAL TEXT`. If no checkpoint is available, it uses hand-authored illustrative probabilities and labels them as illustrative.

## Method

The training script fine-tunes **DistilBERT uncased** as a three-class sequence classifier. The model receives `(text span, company target)` as a pair. For long articles, the app selects sentences that mention a company, includes adjacent context, and averages sentence-level probabilities into one article/company prediction. The code uses PyTorch on Apple MPS when available, with CPU fallback. [PyTorch MPS docs](https://docs.pytorch.org/docs/main/notes/mps.html) · [DistilBERT model card](https://huggingface.co/distilbert/distilbert-base-uncased).

SEntFiN labels are expanded to one example per company. Normalized headlines are kept together when making approximately 70/10/20 training, validation, and test partitions, so multiple company labels from the same headline cannot cross partitions. The script selects the best epoch on validation macro F1 and saves macro F1, per-class precision/recall/F1, class counts, a confusion matrix, and test predictions. The current workspace has an ignored local checkpoint and evaluation report; a fresh Git checkout must download the dataset and run the training command before it can score user-provided coverage.

The recorded three-epoch Apple MPS run selected epoch 2 and reached 0.8522 held-out macro F1 on 2,887 target-labeled headline examples. That benchmark measures held-out SEntFiN headlines, not long article bodies or unseen publishers.

For each article/company pair, the sentiment index is:

```text
P(positive) − P(negative)
```

The app averages this value across unique articles for company summaries. Softmax probabilities are not calibrated certainty; headline benchmark performance does not establish performance on full article bodies or on publishers absent from the benchmark.

## Interactive output

- A company node’s size represents unique article volume; its color represents average target sentiment.
- An undirected edge connects companies that appeared in the same article. Edge width counts co-mentions.
- Selecting a node synchronizes its probability summary, supporting article text, and sentiment timeline.
- The time-ordered coverage board keeps publication time, target, sentiment, and source link together.

Graph position is a layout aid and carries no financial meaning. Edges describe shared article coverage only.

## Local use

Install the packages in `requirements.txt`, then run `streamlit run app.py`. To enable live scoring, place `SEntFiN.csv` in `data/` and run:

```bash
python scripts/train_model.py --data data/SEntFiN.csv
```

The first training run downloads the DistilBERT base weights. User articles and model inference stay on the local machine. See [README.md](README.md) for setup, input columns, evaluation details, and an interview-ready project summary.

