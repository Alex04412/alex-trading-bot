from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.historical.news import NewsClient
from alpaca.data.requests import StockBarsRequest, NewsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from transformers import pipeline

EST = ZoneInfo("America/New_York")

SENTIMENT_DEFAULT = 0.5  # neutral-positive when no news available


class ORBDataCollector:
    """Fetch 5-minute intraday bars + daily sentiment for ORB backtesting."""

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        data_dir: str = "backtest_data/orb",
    ) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.stock_client = StockHistoricalDataClient(api_key, secret_key)
        self.news_client = NewsClient(api_key, secret_key)

        print("  Loading FinBERT model...")
        self.sentiment_pipe = pipeline(
            "text-classification",
            model="ProsusAI/finbert",
            top_k=None,
        )

    def fetch_and_save(
        self,
        symbol: str,
        start: str = "2024-10-01",
        end: str = "2025-01-01",
    ) -> None:
        """Fetch 5-min price bars + daily sentiment and save to CSV."""
        print(f"  Fetching 5-min bars for {symbol} from Alpaca...")
        try:
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame(5, TimeFrameUnit.Minute),  # true 5-min bars
                start=datetime.fromisoformat(start),
                end=datetime.fromisoformat(end),
                # No limit — fetch entire date range
            )
            bars_response = self.stock_client.get_stock_bars(request)
            bars = bars_response[symbol]
        except Exception as e:
            print(f"  ⚠️  Could not fetch bars for {symbol}: {e}")
            return

        if not bars:
            print(f"  ⚠️  No price data for {symbol}")
            return

        print(f"  Got {len(bars)} candles")

        print(f"  Fetching news sentiment for {symbol}...")
        daily_sentiment = self._fetch_daily_sentiment(symbol, start, end)

        file_path = self.data_dir / f"{symbol}_orb.csv"
        saved = 0

        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp", "open", "high", "low", "close", "volume", "sentiment_score"
            ])

            for bar in bars:
                ts = bar.timestamp
                if hasattr(ts, "astimezone"):
                    ts_est = ts.astimezone(EST)
                else:
                    ts_est = ts

                date_str = ts_est.strftime("%Y-%m-%d")
                sentiment = daily_sentiment.get(date_str, SENTIMENT_DEFAULT)

                writer.writerow([
                    ts_est.isoformat(),
                    round(float(bar.open),  4),
                    round(float(bar.high),  4),
                    round(float(bar.low),   4),
                    round(float(bar.close), 4),
                    int(bar.volume),
                    round(sentiment, 4),
                ])
                saved += 1

        print(f"  ✅ Saved {saved} candles to {file_path}")

    def get_data(self, symbol: str) -> list[dict]:
        """Load saved ORB backtest data."""
        file_path = self.data_dir / f"{symbol}_orb.csv"
        if not file_path.exists():
            return []

        data = []
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                row["open"]            = float(row["open"])
                row["high"]            = float(row["high"])
                row["low"]             = float(row["low"])
                row["close"]           = float(row["close"])
                row["volume"]          = float(row["volume"])
                row["sentiment_score"] = float(row["sentiment_score"])
                data.append(row)
        return data

    # ─────────────────────────────────────────
    # INTERNAL
    # ─────────────────────────────────────────

    def _fetch_daily_sentiment(self, symbol: str, start: str, end: str) -> dict[str, float]:
        """Return {date_str: sentiment_score} for each trading day."""
        try:
            request = NewsRequest(
                symbols=symbol,
                start=datetime.fromisoformat(start),
                end=datetime.fromisoformat(end),
                limit=200,
            )
            news_response = self.news_client.get_news(request)
            news = news_response.data.get("news", [])

            if not news:
                print(f"  ⚠️  No news found for {symbol} — all days will use default sentiment {SENTIMENT_DEFAULT}")
                return {}

        except Exception as e:
            print(f"  ⚠️  News fetch failed: {e} — all days will use default sentiment {SENTIMENT_DEFAULT}")
            return {}

        daily: dict[str, list[float]] = {}
        for article in news:
            ts = article.created_at
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            date_str = ts.astimezone(EST).strftime("%Y-%m-%d")
            score = self._score(article.headline)
            daily.setdefault(date_str, []).append(score)

        result = {date: sum(scores) / len(scores) for date, scores in daily.items()}
        print(f"  ✅ Got real sentiment for {len(result)} trading days")
        return result

    def _score(self, headline: str) -> float:
        try:
            results = self.sentiment_pipe(headline[:512])[0]
            scores = {r["label"]: r["score"] for r in results}
            return scores.get("positive", 0.0) - scores.get("negative", 0.0)
        except Exception:
            return 0.0