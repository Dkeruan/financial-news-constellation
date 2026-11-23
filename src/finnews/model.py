from __future__ import annotations

from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

LABELS = ("negative", "neutral", "positive")


def preferred_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


class TargetSentimentModel:
    """Local classifier that scores one text span in relation to one company."""

    def __init__(self, model_dir: Path, device: torch.device | None = None):
        self.device = device or preferred_device()
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_dir, local_files_only=True)
        self.model.to(self.device)
        self.model.eval()
        configured = self.model.config.id2label or {}
        self.labels = [str(configured.get(index, configured.get(str(index), LABELS[index]))).lower() for index in range(self.model.config.num_labels)]
        if set(self.labels) != set(LABELS):
            self.labels = list(LABELS)

    @torch.inference_mode()
    def predict_many(self, texts: list[str], target: str, batch_size: int = 16) -> list[dict[str, float]]:
        if not texts:
            return []
        output: list[dict[str, float]] = []
        for start in range(0, len(texts), batch_size):
            batch = texts[start:start + batch_size]
            encoded = self.tokenizer(
                batch,
                [target] * len(batch),
                padding=True,
                truncation=True,
                max_length=128,
                return_tensors="pt",
            )
            encoded = {name: value.to(self.device) for name, value in encoded.items() if name in {"input_ids", "attention_mask", "token_type_ids"}}
            logits = self.model(**encoded).logits
            probabilities = torch.softmax(logits.float(), dim=-1).cpu().tolist()
            for row in probabilities:
                output.append({label: float(row[self.labels.index(label)]) for label in LABELS})
        return output

