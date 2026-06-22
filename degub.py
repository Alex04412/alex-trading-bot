"""Debug ORB backtest — check why no trades trigger."""
from pathlib import Path
import sys
import csv
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent / "src"))

from alpaca_bot.strategy.orb import ORBStrategy

EST = ZoneInfo("America/New_York")

# Load one symbol
symbol = "AAPL"
file_path = Path(f"backtest_data/orb/{symbol}_orb.csv")

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

print(f"Total candles loaded: {len(data)}")
print(f"First candle: {data[0]}")
print(f"Last candle:  {data[-1]}")

# Check sentiment distribution
scores = [r["sentiment_score"] for r in data]
above_threshold = sum(1 for s in scores if s >= 0.3)
print(f"\nSentiment scores above 0.3: {above_threshold}/{len(scores)}")
print(f"Unique sentiment values: {len(set(scores))}")
print(f"Sample scores: {scores[:5]}")

# Replay and log ORB state per day
orb = ORBStrategy(orb_minutes=30, rr_ratio=2.0, vol_multiplier=1.5)
days_seen = set()
orb_locked_days = 0
entry_checks = 0
entry_hits = 0

for row in data:
    candle = {
        "timestamp": row["timestamp"],
        "open":   row["open"],
        "high":   row["high"],
        "low":    row["low"],
        "close":  row["close"],
        "volume": row["volume"],
    }
    sentiment = row["sentiment_score"]
    ts = datetime.fromisoformat(row["timestamp"]).astimezone(EST)
    date_str = ts.strftime("%Y-%m-%d")

    orb.update(candle)

    if orb.orb_locked and date_str not in days_seen:
        days_seen.add(date_str)
        orb_locked_days += 1
        print(f"\n  [{date_str}] ORB locked — high={orb.orb_high:.2f} low={orb.orb_low:.2f} mid={orb.orb_mid:.2f} avg_vol={orb.orb_avg_vol:.0f}")

    if orb.orb_locked:
        entry_checks += 1
        # Check each condition individually
        breaks_high = candle["close"] > orb.orb_high
        vol_spike   = candle["volume"] >= (orb.orb_avg_vol or 0) * 1.5
        pos_sent    = sentiment >= 0.3

        if breaks_high:
            print(f"    ✅ [{ts.strftime('%H:%M')}] Price breaks ORB high! close={candle['close']:.2f} > {orb.orb_high:.2f} | vol_spike={vol_spike} | sentiment={sentiment:.3f}({pos_sent})")

        if orb.should_enter(candle, sentiment):
            entry_hits += 1
            print(f"    🚀 ENTRY SIGNAL at {ts.strftime('%H:%M')}")

print(f"\n{'='*50}")
print(f"Days with ORB locked: {orb_locked_days}")
print(f"Candles checked for entry: {entry_checks}")
print(f"Entry signals fired: {entry_hits}")