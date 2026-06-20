from __future__ import annotations

from collections.abc import Sequence


class HeadlineClassifier:
    """Lightweight sentiment scorer with clear upgrade path to FinBERT."""

    def score(self, headlines: Sequence[str]) -> float:
        if not headlines:
            return 0.0

        positive_words = {"beat", "growth", "upgrade", "surge", "profit", "bullish"}
        negative_words = {"miss", "downgrade", "lawsuit", "drop", "loss", "bearish"}

        total = 0
        for headline in headlines:
            lowered = headline.lower()
            total += sum(1 for w in positive_words if w in lowered)
            total -= sum(1 for w in negative_words if w in lowered)

        return total / max(len(headlines), 1)
