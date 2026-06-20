from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class BotConfig:
    alpaca_api_key: str
    alpaca_secret_key: str
    alpaca_paper: bool
    newsapi_key: str
    symbols: list[str]
    max_position_usd: float
    stop_loss_pct: float
    poll_interval_minutes: int



def _as_bool(raw: str, default: bool = True) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}



def load_config() -> BotConfig:
    load_dotenv()

    symbols_raw = os.getenv("SYMBOLS", "AAPL,MSFT")
    symbols = [s.strip().upper() for s in symbols_raw.split(",") if s.strip()]

    return BotConfig(
        alpaca_api_key=os.getenv("ALPACA_API_KEY", ""),
        alpaca_secret_key=os.getenv("ALPACA_SECRET_KEY", ""),
        alpaca_paper=_as_bool(os.getenv("ALPACA_PAPER", "true")),
        newsapi_key=os.getenv("NEWSAPI_KEY", ""),
        symbols=symbols,
        max_position_usd=float(os.getenv("MAX_POSITION_USD", "1000")),
        stop_loss_pct=float(os.getenv("STOP_LOSS_PCT", "0.03")),
        poll_interval_minutes=int(os.getenv("POLL_INTERVAL_MINUTES", "15")),
    )
