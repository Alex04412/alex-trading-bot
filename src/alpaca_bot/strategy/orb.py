"""Opening Range Breakout strategy — integrates with sentiment signals."""
from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

EST = ZoneInfo("America/New_York")


class ORBStrategy:
    """
    Opening Range Breakout strategy.
    Combines price action with sentiment signal as confluence filter.
    """

    def __init__(
        self,
        orb_minutes: int = 30,
        rr_ratio: float = 2.0,
        vol_multiplier: float = 1.5,
        cutoff_time: time = time(13, 30),
        close_time: time = time(15, 55),
    ) -> None:
        self.orb_minutes = orb_minutes
        self.rr_ratio = rr_ratio
        self.vol_multiplier = vol_multiplier
        self.cutoff_time = cutoff_time
        self.close_time = close_time

        # State — resets each day
        self.orb_high: float | None = None
        self.orb_low: float | None = None
        self.orb_mid: float | None = None
        self.orb_avg_vol: float | None = None
        self.orb_locked: bool = False
        self._last_date: str | None = None

    # ─────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────

    def update(self, candle: dict) -> None:
        """
        Feed a new 5-minute candle into the strategy.

        Args:
            candle: {timestamp, open, high, low, close, volume}
        """
        ts = self._to_est(candle["timestamp"])
        date_str = ts.strftime("%Y-%m-%d")

        # Reset state on new trading day
        if date_str != self._last_date:
            self._reset()
            self._last_date = date_str

        market_open = datetime(ts.year, ts.month, ts.day, 9, 30, tzinfo=EST)
        orb_end = market_open + timedelta(minutes=self.orb_minutes)

        # Build opening range
        if market_open <= ts < orb_end and not self.orb_locked:
            self._update_orb(candle)

        # Lock range once ORB window closes
        elif ts >= orb_end and not self.orb_locked:
            self._lock_orb()

    def should_enter(self, candle: dict, sentiment_score: float) -> bool:
        """
        Check if all conditions align for a long entry.

        Args:
            candle: Current 5-min candle
            sentiment_score: FinBERT score [-1, 1]

        Returns:
            True if entry conditions are met
        """
        if not self.orb_locked:
            return False

        ts = self._to_est(candle["timestamp"])

        # Time filter — no entries after cutoff
        if ts.time() >= self.cutoff_time:
            return False

        close = candle["close"]
        volume = candle["volume"]
        vwap = candle.get("vwap")

        # Core ORB conditions
        breaks_high = close > self.orb_high
        above_vwap = vwap is None or close > vwap
        vol_spike = (
            self.orb_avg_vol is None
            or volume >= self.orb_avg_vol * self.vol_multiplier
        )

        # Sentiment confluence — only trade with positive news backing
        positive_sentiment = sentiment_score >= 0.3 if sentiment_score != 0.0 else True

        return all([breaks_high, above_vwap, vol_spike, positive_sentiment])

    def get_levels(self, entry_price: float) -> dict:
        """
        Calculate stop loss and take profit levels.

        Args:
            entry_price: Price at entry

        Returns:
            {stop_loss, take_profit, risk}
        """
        if self.orb_mid is None:
            raise ValueError("ORB not yet established")

        risk = entry_price - self.orb_mid
        return {
            "stop_loss": self.orb_mid,
            "take_profit": entry_price + (risk * self.rr_ratio),
            "risk": risk,
        }

    def should_force_close(self, candle: dict) -> bool:
        """Return True if position should be force-closed (end of day)."""
        ts = self._to_est(candle["timestamp"])
        return ts.time() >= self.close_time

    # ─────────────────────────────────────────
    # INTERNAL
    # ─────────────────────────────────────────

    def _reset(self) -> None:
        self.orb_high = None
        self.orb_low = None
        self.orb_mid = None
        self.orb_avg_vol = None
        self.orb_locked = False
        self._candle_count = 0
        self._vol_total = 0.0

    def _update_orb(self, candle: dict) -> None:
        h = candle["high"]
        l = candle["low"]
        v = candle["volume"]

        self.orb_high = max(self.orb_high, h) if self.orb_high else h
        self.orb_low = min(self.orb_low, l) if self.orb_low else l
        self._vol_total = getattr(self, "_vol_total", 0.0) + v
        self._candle_count = getattr(self, "_candle_count", 0) + 1

    def _lock_orb(self) -> None:
        if self.orb_high and self.orb_low:
            self.orb_mid = (self.orb_high + self.orb_low) / 2
            count = getattr(self, "_candle_count", 1)
            self.orb_avg_vol = getattr(self, "_vol_total", 0.0) / max(count, 1)
            self.orb_locked = True

    @staticmethod
    def _to_est(ts) -> datetime:
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=EST)
        return ts.astimezone(EST)