from __future__ import annotations

from newsapi import NewsApiClient


class NewsClient:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = NewsApiClient(api_key=api_key) if api_key else None

    def fetch_market_headlines(self, symbol: str, limit: int = 10) -> list[str]:
        if not self._client:
            # Allow running the bot before NewsAPI is configured.
            return []

        response = self._client.get_everything(
            q=f"{symbol} stock market",
            language="en",
            sort_by="publishedAt",
            page_size=limit,
        )
        articles = response.get("articles", [])
        return [a.get("title", "").strip() for a in articles if a.get("title")]
