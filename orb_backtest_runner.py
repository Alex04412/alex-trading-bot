"""ORB backtest runner — fetch data then simulate strategy."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from alpaca_bot.config import load_config
from alpaca_bot.backtest.orb_data_collector import ORBDataCollector
from alpaca_bot.backtest.orb_engine import ORBBacktestEngine

SYMBOLS = ["AAPL", "NVDA", "TSLA", "META", "AMD"]
START = "2024-01-01"
END   = "2025-01-01"
cfg = load_config()

SYMBOLS = cfg.symbols if cfg.symbols else SYMBOLS
# ── Step 1: Fetch data (skip if CSVs already exist) ──────────────────────────
collector = ORBDataCollector(
    api_key=cfg.alpaca_api_key,
    secret_key=cfg.alpaca_secret_key,
)
import yfinance as yf
import pandas as pd

def get_spy_direction(start: str, end: str) -> dict[str, float]:
    """Returns {date: daily_return} for SPY."""
    spy = yf.download("SPY", start=start, end=end, interval="1d", auto_adjust=True, progress=False)
    result = {}
    for ts, row in spy.iterrows():
        date_str = ts.strftime("%Y-%m-%d")
        result[date_str] = float(row["Close"]) - float(row["Open"])
    return result

spy_direction = get_spy_direction(START, END)
for symbol in SYMBOLS:
    csv_path = Path(f"backtest_data/orb/{symbol}_orb.csv")
    if csv_path.exists():
        print(f"  ⏭️  {symbol} — data already exists, skipping fetch")
        continue
    print(f"\nFetching {symbol}...")
    collector.fetch_and_save(symbol=symbol, start=START, end=END)



# ── Step 2: Run backtest ──────────────────────────────────────────────────────
engine = ORBBacktestEngine(
    initial_cash=10000.0,
    fees=0.001,
    orb_minutes=30,
    rr_ratio=1.5,        # lower from 2.0 — easier to hit TP
    vol_multiplier=1.0,  # remove volume filter effectively
    sentiment_threshold=0.3,
    max_risk_pct=0.05,
    spy_data=spy_direction,  # loosen from 0.02 — allows volatile stocks
)

all_results = []
for symbol in SYMBOLS:
    print(f"Running ORB backtest for {symbol}...")
    data = collector.get_data(symbol)
    if not data:
        print(f"  ⚠️  No data for {symbol}")
        all_results.append({"symbol": symbol, "error": "No data"})
        continue
    result = engine.run(symbol=symbol, data=data)
    all_results.append(result)

engine.summary(all_results)