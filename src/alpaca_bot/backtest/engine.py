from __future__ import annotations

import pandas as pd
import numpy as np
import vectorbt as vbt


class BacktestEngine:
    """Run backtests using vectorbt on collected sentiment + price data."""

    def __init__(self, initial_cash: float = 10000.0, fees: float = 0.001, stop_loss_pct: float = 0.03) -> None:
        """
        Initialize backtest engine.

        Args:
            initial_cash: Starting portfolio value
            fees: Trading fee per transaction (0.1% default)
            stop_loss_pct: Stop loss percentage (0.03 = 3%)
        """
        self.initial_cash = initial_cash
        self.fees = fees
        self.stop_loss_pct = stop_loss_pct

    def run_backtest(
        self,
        symbol: str,
        data: list[dict],
        sentiment_threshold_buy: float = 0.3,
        sentiment_threshold_sell: float = -0.3,
    ) -> dict:
        if not data:
            return {"error": "No data provided"}

        # Convert to DataFrame with proper datetime index
        df = pd.DataFrame(data)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.sort_values("timestamp")
        df = df.drop_duplicates(subset="timestamp")
        df = df.set_index("timestamp")

        # Generate trade signals
        entries = df["sentiment_score"] >= sentiment_threshold_buy
        exits = df["sentiment_score"] <= sentiment_threshold_sell

        # Price series with datetime index
        prices = df["price"]

        # Run vectorbt backtest with stop loss
        pf = vbt.Portfolio.from_signals(
            close=prices,
            entries=entries,
            exits=exits,
            init_cash=self.initial_cash,
            fees=self.fees,
            sl_stop=self.stop_loss_pct,   # stop loss
            tp_stop=self.stop_loss_pct * 2,  # take profit at 2x stop loss
        )

        # Metrics
        total_return = float(pf.total_return())
        num_trades = int(pf.trades.count())

        try:
            annual_return = float(pf.annualized_return())
        except Exception:
            days = (df.index[-1] - df.index[0]).days or 1
            annual_return = total_return * (365.0 / days)

        try:
            sharpe_ratio = float(pf.sharpe_ratio())
        except Exception:
            sharpe_ratio = 0.0

        try:
            max_drawdown = float(pf.max_drawdown())
        except Exception:
            max_drawdown = 0.0

        try:
            win_rate = float(pf.trades.win_rate()) if num_trades > 0 else 0.0
        except Exception:
            win_rate = 0.0

        return {
            "symbol": symbol,
            "total_return": total_return,
            "annual_return": annual_return,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "win_rate": win_rate,
            "num_trades": num_trades,
            "total_profit": float(pf.final_value() - self.initial_cash),
        }

    @staticmethod
    def backtest_summary(all_results: list[dict]) -> None:
        """Print formatted backtest summary."""
        print("\n" + "=" * 80)
        print("BACKTEST SUMMARY")
        print("=" * 80)

        total_profit = 0.0
        valid_results = []

        for result in all_results:
            if "error" in result:
                print(f"\n{result['symbol']}: ERROR - {result['error']}")
                continue

            valid_results.append(result)
            total_profit += result["total_profit"]

            # Color-code profit/loss
            profit_str = f"${result['total_profit']:.2f}"
            profit_label = "✅" if result["total_profit"] >= 0 else "❌"

            print(f"\n{result['symbol']}:")
            print(f"  {profit_label} Profit:        {profit_str}")
            print(f"  Total Return:   {result['total_return']*100:.2f}%")
            print(f"  Annual Return:  {result['annual_return']*100:.2f}%")
            print(f"  Sharpe Ratio:   {result['sharpe_ratio']:.2f}")
            print(f"  Max Drawdown:   {result['max_drawdown']*100:.2f}%")
            print(f"  Win Rate:       {result['win_rate']*100:.2f}%")
            print(f"  Trades:         {result['num_trades']}")

        if valid_results:
            print(f"\n{'─'*80}")
            overall = "✅" if total_profit >= 0 else "❌"
            print(f"  {overall} TOTAL PORTFOLIO PROFIT: ${total_profit:.2f}")
            avg_return = sum(r["total_return"] for r in valid_results) / len(valid_results)
            print(f"  AVG RETURN ACROSS SYMBOLS: {avg_return*100:.2f}%")

        print("=" * 80 + "\n")