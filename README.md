# Financial News Constellation

A local Streamlit app for exploring sentiment toward selected companies in financial news. It turns RSS headlines or a CSV into target-specific sentiment estimates, an interactive co-mention network, a sentiment timeline, and linked article evidence.

## Screenshots

**Company signals** — network, selected-company sentiment, trend, and article evidence.

![Company signals dashboard](screenshots/company-signals.png)

**Research setup** — company and date-range controls, feed status, and custom RSS entry.

![Research setup and RSS source status](screenshots/research-setup.png)

## Run the app

Requires Python 3.10+. On Apple Silicon, PyTorch uses MPS when available and otherwise falls back to CPU.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

Use **Demo** to explore sample articles. The demo works without a trained checkpoint; fallback scores are labeled as illustrative. To analyze your own articles, choose RSS feeds and press **Research**, add a custom RSS/Atom URL under **Source status**, or upload a CSV with a `title` or `text` column. Optional CSV columns include `published_at`, `source`, `url`, and `companies`.

## Train the sentiment model

The app uses a target-conditioned DistilBERT classifier. It receives a financial text span and company name together, then estimates negative, neutral, and positive probabilities. The model is fully fine-tuned; stories with multiple companies are scored separately for each target.

Training uses [SEntFiN 1.0](https://arxiv.org/abs/2305.12257), a human-labeled financial headline dataset with entity-specific sentiment labels. The dataset and model checkpoint are not included in this repository.

1. Download `SEntFiN.csv` from the [official repository](https://github.com/pyRis/SEntFiN) into `data/`.
2. Run:

   ```bash
   python scripts/train_model.py --data data/SEntFiN.csv
   ```

The first run downloads the base DistilBERT checkpoint. Training uses Apple MPS when available and saves the fine-tuned checkpoint under `models/financial-target-distilbert/`. That directory is ignored by Git.

## How to read the outputs

The company sentiment index is the mean positive probability minus the mean negative probability across unique company–article pairs, from −1 to +1. Network edges count shared article mentions; node size represents article volume. Positions only arrange the network and do not indicate financial distance, correlation, or causation.

The held-out headline benchmark reached **0.8522 macro F1** on 2,887 target-labeled examples, using a split grouped by normalized headline to prevent labels from the same headline leaking across partitions. This does not establish accuracy on full article bodies or every publisher. Probabilities are model estimates, not calibrated certainty.

## Data and limitations

- RSS collection is manual. Selected headlines and summaries are stored locally in `data/financial_news.sqlite3`; the app does not poll in the background or fetch full article pages for Research.
- CSV uploads stay in Streamlit session memory. No remote inference service is used.
- Company matching uses the editable alias list in `data/companies.csv`, not general-purpose named-entity recognition.
- Sentiment is estimated from headlines or target-related text and is not a stock-price forecast or investment recommendation.
- Training data and model terms are described in [REFERENCES.md](REFERENCES.md); review those terms before redistributing data or derived weights.

More detail: [project overview](PRODUCT.md) · [design notes](DESIGN.md) · [references](REFERENCES.md).
