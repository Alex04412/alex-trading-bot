from __future__ import annotations

# This file is deprecated. Use engine.py instead.
# Example:
#   from alpaca_bot.backtest.engine import BacktestEngine
#   from alpaca_bot.data.collector import BacktestDataCollector
#
#   collector = BacktestDataCollector()
#   engine = BacktestEngine()
#   data = collector.get_backtest_data("AAPL")
#   results = engine.run_backtest("AAPL", data)

from alpaca_bot.backtest.engine import BacktestEngine


def run_backtest_placeholder() -> None:
    """Deprecated: use BacktestEngine directly."""
    print("See backtest/engine.py for vectorbt backtesting.")

