from __future__ import annotations

import argparse
import ast
import hashlib
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import transformers
import sklearn
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import GroupShuffleSplit
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "distilbert/distilbert-base-uncased"
LABELS = ["negative", "neutral", "positive"]
LABEL_TO_ID = {label: index for index, label in enumerate(LABELS)}


class PairDataset(Dataset):
    def __init__(self, frame: pd.DataFrame, tokenizer, max_length: int):
        self.texts = frame["text"].tolist()
        self.targets = frame["target"].tolist()
        self.labels = frame["label_id"].tolist()
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        encoded = self.tokenizer(
            self.texts[index], self.targets[index],
            truncation=True, padding="max_length", max_length=self.max_length,
            return_tensors="pt",
        )
        item = {name: value.squeeze(0) for name, value in encoded.items() if name in {"input_ids", "attention_mask", "token_type_ids"}}
        item["labels"] = torch.tensor(self.labels[index], dtype=torch.long)
        return item


def expand_sentfin(path: Path) -> pd.DataFrame:
    source = pd.read_csv(path)
    columns = {str(column).strip().casefold(): column for column in source.columns}
    title_col = columns.get("title") or columns.get("headline")
    decisions_col = columns.get("decisions") or columns.get("sentiment")
    if title_col is None or decisions_col is None:
        raise ValueError("Expected SEntFiN columns Title and Decisions. See the README for the source and format.")
    rows: list[dict[str, str]] = []
    for _, row in source.iterrows():
        text = str(row[title_col]).strip()
        if not text or text.casefold() == "nan":
            continue
        raw = row[decisions_col]
        try:
            decisions = ast.literal_eval(raw) if isinstance(raw, str) else raw
        except (ValueError, SyntaxError):
            continue
        if not isinstance(decisions, dict):
            continue
        for target, sentiment in decisions.items():
            label = str(sentiment).strip().casefold()
            if label in LABEL_TO_ID and str(target).strip():
                rows.append({"text": text, "target": str(target).strip(), "label": label})
    frame = pd.DataFrame(rows).drop_duplicates(["text", "target", "label"]).reset_index(drop=True)
    if frame.empty:
        raise ValueError("No usable entity sentiment labels were found in the dataset.")
    frame["label_id"] = frame["label"].map(LABEL_TO_ID).astype(int)
    frame["group"] = frame["text"].str.casefold().str.replace(r"\W+", " ", regex=True).str.strip()
    return frame


def split_by_headline(frame: pd.DataFrame, seed: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    first = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed)
    trainval_ix, test_ix = next(first.split(frame, groups=frame["group"]))
    trainval = frame.iloc[trainval_ix]
    second = GroupShuffleSplit(n_splits=1, test_size=0.125, random_state=seed + 1)
    train_ix, val_ix = next(second.split(trainval, groups=trainval["group"]))
    return trainval.iloc[train_ix].reset_index(drop=True), trainval.iloc[val_ix].reset_index(drop=True), frame.iloc[test_ix].reset_index(drop=True)


def evaluate(model, loader, device) -> tuple[float, list[int], list[int], list[list[float]]]:
    model.eval()
    predicted: list[int] = []
    expected: list[int] = []
    probabilities: list[list[float]] = []
    with torch.inference_mode():
        for batch in loader:
            batch = {name: value.to(device) for name, value in batch.items()}
            labels = batch.pop("labels")
            logits = model(**batch).logits
            predicted.extend(logits.argmax(dim=-1).cpu().tolist())
            expected.extend(labels.cpu().tolist())
            probabilities.extend(torch.softmax(logits.float(), dim=-1).cpu().tolist())
    return f1_score(expected, predicted, average="macro", labels=list(range(3)), zero_division=0), expected, predicted, probabilities


def main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune a target-aware DistilBERT sentiment model on SEntFiN.")
    parser.add_argument("--data", type=Path, required=True, help="Path to the SEntFiN.csv file downloaded from the official repository.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Hugging Face base checkpoint (default: DistilBERT uncased).")
    parser.add_argument("--output", type=Path, default=ROOT / "models" / "financial-target-distilbert")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-length", type=int, default=96)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.backends.mps.is_available():
        torch.mps.manual_seed(args.seed)
        device = torch.device("mps")
    else:
        device = torch.device("cpu")
    print(f"Device: {device}. Training examples: local; checkpoint download occurs on first run.")
    dataset_hash = hashlib.sha256(args.data.read_bytes()).hexdigest()

    data = expand_sentfin(args.data)
    train_frame, val_frame, test_frame = split_by_headline(data, args.seed)
    print(f"Rows: train={len(train_frame):,}, validation={len(val_frame):,}, test={len(test_frame):,}; split groups are unique headlines.")
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model,
        num_labels=3,
        id2label={index: label for index, label in enumerate(LABELS)},
        label2id=LABEL_TO_ID,
    ).to(device)
    base_revision = getattr(model.config, "_commit_hash", None)
    train_loader = DataLoader(PairDataset(train_frame, tokenizer, args.max_length), batch_size=args.batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(PairDataset(val_frame, tokenizer, args.max_length), batch_size=args.batch_size, shuffle=False, num_workers=0)
    test_loader = DataLoader(PairDataset(test_frame, tokenizer, args.max_length), batch_size=args.batch_size, shuffle=False, num_workers=0)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=0.01)
    total_steps = max(1, len(train_loader) * args.epochs)
    scheduler = get_linear_schedule_with_warmup(optimizer, num_warmup_steps=max(1, int(total_steps * 0.06)), num_training_steps=total_steps)
    best_macro_f1 = -1.0
    best_epoch = 0
    args.output.mkdir(parents=True, exist_ok=True)
    for epoch in range(1, args.epochs + 1):
        model.train()
        total_loss = 0.0
        for batch in train_loader:
            batch = {name: value.to(device) for name, value in batch.items()}
            optimizer.zero_grad(set_to_none=True)
            output = model(**batch)
            output.loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            total_loss += float(output.loss.detach().cpu())
        macro_f1, _, _, _ = evaluate(model, val_loader, device)
        mean_loss = total_loss / max(1, len(train_loader))
        print(f"Epoch {epoch}/{args.epochs}: train_loss={mean_loss:.4f}, validation_macro_f1={macro_f1:.4f}")
        if macro_f1 > best_macro_f1:
            best_macro_f1, best_epoch = macro_f1, epoch
            model.save_pretrained(args.output)
            tokenizer.save_pretrained(args.output)

    best_model = AutoModelForSequenceClassification.from_pretrained(args.output).to(device)
    test_macro_f1, expected, predicted, test_probabilities = evaluate(best_model, test_loader, device)
    report = classification_report(expected, predicted, labels=list(range(3)), target_names=LABELS, output_dict=True, zero_division=0)
    metrics = {
        "dataset": "SEntFiN 1.0",
        "dataset_sha256": dataset_hash,
        "base_checkpoint": args.model,
        "base_checkpoint_revision": base_revision,
        "task": "target-conditioned three-class sentiment",
        "split": "grouped by normalized headline; 70/10/20 train/validation/test approximation",
        "seed": args.seed,
        "device": str(device),
        "python_version": sys.version.split()[0],
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
        "scikit_learn_version": sklearn.__version__,
        "hyperparameters": {"epochs_requested": args.epochs, "batch_size": args.batch_size, "max_length": args.max_length, "learning_rate": args.learning_rate, "weight_decay": 0.01},
        "best_epoch": best_epoch,
        "best_validation_macro_f1": best_macro_f1,
        "held_out_macro_f1": test_macro_f1,
        "confusion_matrix_true_rows_predicted_columns": confusion_matrix(expected, predicted, labels=list(range(3))).tolist(),
        "classification_report": report,
        "class_counts": dict(Counter(data["label"])),
        "split_class_counts": {
            "train": train_frame["label"].value_counts().to_dict(),
            "validation": val_frame["label"].value_counts().to_dict(),
            "test": test_frame["label"].value_counts().to_dict(),
        },
        "sizes": {"train": len(train_frame), "validation": len(val_frame), "test": len(test_frame)},
        "limitations": [
            "SEntFiN labels headlines; they do not establish full-article performance.",
            "A held-out headline split is not an external-source evaluation.",
            "Check upstream dataset terms and model checkpoint license before redistribution or commercial use.",
        ],
    }
    (args.output / "evaluation.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    test_output = test_frame[["text", "target", "label"]].reset_index(drop=True).rename(columns={"label": "true_label"})
    test_output["predicted_label"] = [LABELS[index] for index in predicted]
    for class_index, label in enumerate(LABELS):
        test_output[f"p_{label}"] = [row[class_index] for row in test_probabilities]
    test_output.to_csv(args.output / "test_predictions.csv", index=False)
    print(f"Held-out macro F1: {test_macro_f1:.4f}. Best checkpoint from epoch {best_epoch}; saved to {args.output}.")


if __name__ == "__main__":
    main()

