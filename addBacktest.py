"""Fetch historical data for backtesting — run this first."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from alpaca_bot.data.collector import BacktestDataCollector
from alpaca_bot.config import load_config  # adjust if your function is named differently


cfg = load_config()

collector = BacktestDataCollector(
    api_key=cfg.alpaca_api_key,
    secret_key=cfg.alpaca_secret_key,
)

SYMBOLS = ["AAPL", "NVDA", "TSLA", "META", "AMD"]

for symbol in SYMBOLS:
    print(f"\nFetching {symbol}...")
    collector.fetch_and_save(
    symbol=symbol,
    start="2024-06-01",
    end="2025-01-01",
)

print("\nDone! Now run backtest.py")