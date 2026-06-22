from __future__ import annotations

from collections.abc import Sequence
from transformers import pipeline


class FinBERTClassifier:
    """FinBERT-based financial sentiment classifier using HuggingFace transformers."""

    def __init__(self, model_name: str = "ProsusAI/finbert") -> None:
        """
        Initialize FinBERT model.

        Args:
            model_name: HuggingFace model ID (default: ProsusAI/finbert - well-maintained)
        """
        try:
            self.pipeline = pipeline(
                "sentiment-analysis",
                model=model_name,
                framework="pt",
                device=0 if self._cuda_available() else -1,
            )
        except Exception as e:
            print(f"Warning: Failed to load FinBERT model {model_name}: {e}")
            print("Falling back to lightweight keyword classifier")
            self.pipeline = None

    @staticmethod
    def _cuda_available() -> bool:
        """Check if CUDA is available (fallback to CPU if not)."""
        try:
            import torch
            return torch.cuda.is_available()
        except (ImportError, Exception):
            return False

    def score(self, headlines: Sequence[str]) -> float:
        """
        Score headlines using FinBERT or fallback to keyword-based scoring.

        Returns sentiment score in range [-1.0, 1.0]:
        - Positive (bullish): 0.0 to 1.0
        - Negative (bearish): -1.0 to 0.0
        - Neutral: 0.0
        """
        if not headlines:
            return 0.0

        # Use FinBERT if available
        if self.pipeline:
            return self._score_finbert(headlines)
        else:
            return self._score_keywords(headlines)

    def _score_finbert(self, headlines: Sequence[str]) -> float:
        """Score using FinBERT model."""
        try:
            # Run inference on all headlines at once
            results = self.pipeline(list(headlines), truncation=True, max_length=512)

            # Aggregate scores
            total_score = 0.0
            for result in results:
                label = result["label"].lower()
                confidence = result["score"]

                if label == "positive":
                    total_score += confidence
                elif label == "negative":
                    total_score -= confidence
                # neutral adds 0

            return total_score / max(len(headlines), 1)
        except Exception as e:
            print(f"FinBERT scoring failed: {e}. Falling back to keywords.")
            return self._score_keywords(headlines)

    def _score_keywords(self, headlines: Sequence[str]) -> float:
        """Fallback: keyword-based sentiment scoring."""
        positive_words = {"beat", "growth", "upgrade", "surge", "profit", "bullish", "rally", "strong"}
        negative_words = {"miss", "downgrade", "lawsuit", "drop", "loss", "bearish", "plunge", "weak"}

        total = 0
        for headline in headlines:
            lowered = headline.lower()
            total += sum(1 for w in positive_words if w in lowered)
            total -= sum(1 for w in negative_words if w in lowered)

        return total / max(len(headlines), 1)
