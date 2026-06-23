"""ORB backtest runner — fetch data then simulate strategy with dynamic screening."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from alpaca_bot.config import load_config
from alpaca_bot.backtest.orb_data_collector import ORBDataCollector
from alpaca_bot.backtest.orb_engine import ORBBacktestEngine
# Import your Universe Scanner class (assuming it's in your src path or local)
from alpaca_bot.backtest.orb_universe_scanner import ORBUniverseScanner 

import yfinance as yf
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

EST = ZoneInfo("America/New_York")

SYMBOLS = ["AAPL", "NVDA", "TSLA", "META", "AMD"]
START = "2023-01-01"
END   = "2023-03-31"
cfg = load_config()

SYMBOLS = cfg.symbols if cfg.symbols else SYMBOLS

# ── Step 1: Fetch data (skip if CSVs already exist) ──────────────────────────
collector = ORBDataCollector(
    api_key=cfg.alpaca_api_key,
    secret_key=cfg.alpaca_secret_key,
)

def get_spy_direction(start: str, end: str) -> dict[str, float]:
    """Returns {date: daily_return} for SPY."""
    spy = yf.download("SPY", start=start, end=end, interval="1d", auto_adjust=True, progress=False)
    result = {}
    for ts, row in spy.iterrows():
        date_str = ts.strftime("%Y-%m-%d")
        result[date_str] = float(row["Close"]) - float(row["Open"])
    return result

spy_direction = get_spy_direction(START, END)
trading_days = sorted(list(spy_direction.keys()))

for symbol in SYMBOLS:
    csv_path = Path(f"backtest_data/orb/{symbol}_orb.csv")
    if csv_path.exists():
        print(f"  ⏭️  {symbol} — data already exists, skipping fetch")
        continue
    print(f"\nFetching {symbol}...")
    collector.fetch_and_save(symbol=symbol, start=START, end=END)


# ── Step 2: Dynamic Universe Screening ───────────────────────────────────────
print("\n🔍 Executing dynamic day-by-day market scanning...")
# Initialize scanner instance using properties from your provided snippet
scanner = ORBUniverseScanner(api_key=cfg.alpaca_api_key, secret_key=cfg.alpaca_secret_key)

# Map tracking format: { symbol: set(allowed_date_strings) }
allowed_days_per_symbol = {symbol: set() for symbol in SYMBOLS}

for day_str in trading_days:
    # Scan standard candidate list on this day specifically
    selected_for_day = scanner.scan_for_day(symbols=SYMBOLS, target_date=day_str)
    for symbol in selected_for_day:
        if symbol in allowed_days_per_symbol:
            allowed_days_per_symbol[symbol].add(day_str)


# ── Step 3: Run backtest ──────────────────────────────────────────────────────
engine = ORBBacktestEngine(
    initial_cash=10000.0,
    fees=0.001,
    orb_minutes=15,        # Shorter ORB to catch more early-morning breakouts.
    
    # 1. AIM FOR CHUNKY WINS
    rr_ratio=2.5,        # Force the strategy to hunt for larger moves
                         # that make a 0.1% slippage fee negligible.
                         
    # 2. DEMAND INSTITUTIONAL MOMENTUM
    vol_multiplier=1.3,  # Volume must be 30% higher than the morning average.
                         
    sentiment_threshold=0.3,
    
    # 3. KEEP RISK TIGHT
    max_risk_pct=0.02,   # Skip highly erratic asset days to protect capital.
                         
    spy_data=spy_direction,
)

all_results = []
for symbol in SYMBOLS:
    print(f"Running ORB backtest for {symbol}...")
    full_data = collector.get_data(symbol)
    
    if not full_data:
        print(f"  ⚠️  No data for {symbol}")
        all_results.append({"symbol": symbol, "error": "No data"})
        continue
        
    # Extract matching trading dates allowed by our memory-safe scanner matrix
    allowed_dates = allowed_days_per_symbol.get(symbol, set())
    
    # Filter intraday rows cleanly checking both string formats and objects
    filtered_data = []
    for candle in full_data:
        ts = candle.get("timestamp")
        if ts is None:
            continue
        ts_str = ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts)[:10]
        
        if ts_str in allowed_dates:
            filtered_data.append(candle)
            
    if not filtered_data:
        print(f"  ℹ️  {symbol} was never selected by the daily gap scanner metrics. Skipping simulation.")
        continue
        
    result = engine.run(symbol=symbol, data=filtered_data)
    all_results.append(result)

engine.summary(all_results)