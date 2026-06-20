from __future__ import annotations

from alpaca_bot.models import Signal


class SignalEngine:
    def __init__(self, buy_threshold: float = 0.5, sell_threshold: float = -0.5) -> None:
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold

    def from_sentiment(self, score: float) -> Signal:
        if score >= self.buy_threshold:
            return Signal.BUY
        if score <= self.sell_threshold:
            return Signal.SELL
        return Signal.HOLD
