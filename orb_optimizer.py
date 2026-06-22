"""Find optimal ORB parameters by grid search."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from alpaca_bot.backtest.orb_data_collector import ORBDataCollector
from alpaca_bot.backtest.orb_engine import ORBBacktestEngine
from alpaca_bot.config import load_config

SYMBOLS = ["AAPL", "NVDA", "TSLA", "META", "AMD"]

cfg = load_config()
collector = ORBDataCollector(
    api_key=cfg.alpaca_api_key,
    secret_key=cfg.alpaca_secret_key,
)

# Load data once
all_data = {s: collector.get_data(s) for s in SYMBOLS}

# Parameter grid
rr_ratios       = [1.5, 2.0, 2.5]
vol_multipliers = [1.0, 1.2, 1.5]
max_risks       = [0.03, 0.05, 0.08]
orb_minutes     = [15, 30]

best_result = None
best_profit = float("-inf")
best_params = {}

print("Running grid search...\n")
total = len(rr_ratios) * len(vol_multipliers) * len(max_risks) * len(orb_minutes)
run = 0

for rr in rr_ratios:
    for vol in vol_multipliers:
        for risk in max_risks:
            for orb_min in orb_minutes:
                run += 1
                engine = ORBBacktestEngine(
                    initial_cash=10000.0,
                    fees=0.001,
                    orb_minutes=orb_min,
                    rr_ratio=rr,
                    vol_multiplier=vol,
                    max_risk_pct=risk,
                )

                results = []
                for symbol in SYMBOLS:
                    data = all_data[symbol]
                    if data:
                        results.append(engine.run(symbol=symbol, data=data))

                total_profit = sum(r["total_profit"] for r in results if "error" not in r)
                total_trades = sum(r["num_trades"]   for r in results if "error" not in r)
                avg_wr       = sum(r["win_rate"]     for r in results if "error" not in r) / len(results)

                print(f"[{run}/{total}] rr={rr} vol={vol} risk={risk} orb={orb_min}min → profit=${total_profit:.2f} trades={total_trades} wr={avg_wr*100:.1f}%")

                if total_profit > best_profit and total_trades >= 10:
                    best_profit = total_profit
                    best_params = {
                        "rr_ratio":       rr,
                        "vol_multiplier": vol,
                        "max_risk_pct":   risk,
                        "orb_minutes":    orb_min,
                    }

print(f"\n{'='*60}")
print(f"BEST PARAMS (profit=${best_profit:.2f}):")
for k, v in best_params.items():
    print(f"  {k}: {v}")
print(f"{'='*60}")