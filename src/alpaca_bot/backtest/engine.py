from __future__ import annotations

import pandas as pd
import numpy as np
import vectorbt as vbt


class BacktestEngine:
    """Run backtests using vectorbt on collected sentiment + price data."""

    def __init__(self, initial_cash: float = 10000.0, fees: float = 0.001) -> None:
        """
        Initialize backtest engine.

        Args:
            initial_cash: Starting portfolio value
            fees: Trading fee per transaction (0.1% default)
        """
        self.initial_cash = initial_cash
        self.fees = fees

    def run_backtest(
        self,
        symbol: str,
        data: list[dict],
        sentiment_threshold_buy: float = 0.3,
        sentiment_threshold_sell: float = -0.3,
    ) -> dict:
        """
        Run backtest on collected data.

        Args:
            symbol: Stock ticker
            data: List of {timestamp, price, sentiment_score, signal}
            sentiment_threshold_buy: Sentiment score to trigger BUY
            sentiment_threshold_sell: Sentiment score to trigger SELL

        Returns:
            Dict with backtest results (returns, sharpe, max_drawdown, etc.)
        """
        if not data:
            return {"error": "No data provided"}

        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame(data)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)

        # Generate trade signals based on sentiment thresholds
        entries = np.zeros(len(df), dtype=bool)
        exits = np.zeros(len(df), dtype=bool)

        for i, row in df.iterrows():
            sentiment = row["sentiment_score"]
            if sentiment >= sentiment_threshold_buy:
                entries[i] = True
            elif sentiment <= sentiment_threshold_sell:
                exits[i] = True

        # Extract price series
        prices = df["price"].values

        # Run vectorbt backtest
        pf = vbt.Portfolio.from_signals(
            close=prices,
            entries=entries,
            exits=exits,
            init_cash=self.initial_cash,
            fees=self.fees,
        )

        # Collect metrics (with fallbacks for vectorbt edge cases)
        total_return = float(pf.total_return())
        num_trades = int(pf.trades.count())
        
        # Estimate annualized return if frequency unknown
        try:
            annual_return = float(pf.annualized_return())
        except (ValueError, Exception):
            # Fallback: rough estimate based on number of observations
            days_of_data = len(df)
            annual_return = total_return * (365.0 / max(days_of_data, 1))
        
        # Get other metrics with safe defaults
        try:
            sharpe_ratio = float(pf.sharpe_ratio())
        except (ValueError, Exception):
            sharpe_ratio = 0.0
        
        try:
            max_drawdown = float(pf.max_drawdown())
        except (ValueError, Exception):
            max_drawdown = 0.0
        
        try:
            win_rate = float(pf.win_rate()) if num_trades > 0 else 0.0
        except (ValueError, Exception):
            win_rate = 0.0

        results = {
            "symbol": symbol,
            "total_return": total_return,
            "annual_return": annual_return,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "win_rate": win_rate,
            "num_trades": num_trades,
            "total_profit": float(pf.final_value() - self.initial_cash),
        }

        return results

    @staticmethod
    def backtest_summary(all_results: list[dict]) -> None:
        """Print formatted backtest summary."""
        print("\n" + "=" * 80)
        print("BACKTEST SUMMARY")
        print("=" * 80)

        for result in all_results:
            if "error" in result:
                print(f"\n{result['symbol']}: ERROR - {result['error']}")
                continue

            print(f"\n{result['symbol']}:")
            print(f"  Total Return: {result['total_return']*100:.2f}%")
            print(f"  Annual Return: {result['annual_return']*100:.2f}%")
            print(f"  Sharpe Ratio: {result['sharpe_ratio']:.2f}")
            print(f"  Max Drawdown: {result['max_drawdown']*100:.2f}%")
            print(f"  Win Rate: {result['win_rate']*100:.2f}%")
            print(f"  Trades: {result['num_trades']}")
            print(f"  Profit: ${result['total_profit']:.2f}")

        print("=" * 80 + "\n")
