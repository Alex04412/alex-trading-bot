from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from transformers import pipeline
from httpcore import request
import yfinance as yf
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.historical.news import NewsClient
from alpaca.data.requests import NewsRequest


class BacktestDataCollector:
    """Fetch historical prices + news for backtesting."""

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        data_dir: str = "backtest_data",
    ) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.price_client = StockHistoricalDataClient(api_key, secret_key)
        self.news_client = NewsClient(api_key, secret_key)
        print("  Loading FinBERT model...")
        self.sentiment_pipe = pipeline(
        "text-classification",
        model="ProsusAI/finbert",
        top_k=None,  # return all 3 scores
    )
    def _score_sentiment(self, headline: str) -> float:
        try:
            results = self.sentiment_pipe(headline[:512])[0]
            scores = {r["label"]: r["score"] for r in results}
            return scores.get("positive", 0) - scores.get("negative", 0)
        except Exception:
            return 0.0
    def fetch_and_save(
        self,
        symbol: str,
        start: str = "2024-01-01",
        end: str = "2024-06-01",
    ) -> None:
        print(f"  Fetching price data for {symbol}...")
        
        # Fix 1: Use recent dates — yfinance only supports 1h data for last 730 days
        price_df = yf.download(symbol, start=start, end=end, interval="1d", auto_adjust=True)

        print(f"  Fetching news for {symbol}...")
        request = NewsRequest(
            symbols=symbol,  # Fix 2: pass string not list
            start=datetime.fromisoformat(start),
            end=datetime.fromisoformat(end),
            limit=200,
        )
        news_response = self.news_client.get_news(request)
        news = news_response.data.get("news", [])

        if not news:
            print(f"  ⚠️  No news found for {symbol}")
            return

        file_path = self.data_dir / f"{symbol}_backtest.csv"
        saved = 0

        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "price", "sentiment_score", "headline"])

            for article in news:
                ts = article.created_at
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))

                try:
                    price = float(
                    price_df["Close"].asof(ts.replace(tzinfo=None)).iloc[0]
                    )
                except Exception:
                    continue

                if price and price > 0:
                    # Placeholder sentiment — will be scored by FinBERT in engine
                    sentiment_score = self._score_sentiment(article.headline)
                    writer.writerow([ts.isoformat(), price, sentiment_score, article.headline])
                    saved += 1

        print(f"  ✅ Saved {saved} records to {file_path}")

    def get_backtest_data(self, symbol: str) -> list[dict]:
        """Load saved historical data for a symbol."""
        file_path = self.data_dir / f"{symbol}_backtest.csv"
        if not file_path.exists():
            return []

        data = []
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                row["price"] = float(row["price"])
                row["sentiment_score"] = float(row["sentiment_score"])
                data.append(row)
        return data