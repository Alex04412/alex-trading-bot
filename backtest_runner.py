"""Backtest runner for strategy validation."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / "src"))

from alpaca_bot.config import load_config
from alpaca_bot.data.collector import BacktestDataCollector
from alpaca_bot.backtest.engine import BacktestEngine


def run_backtest(
    symbols: list[str] | None = None,
    sentiment_buy: float = 0.3,
    sentiment_sell: float = -0.3,
    initial_cash: float = 10000.0,
) -> None:
    """
    Run backtest on collected data.

    Args:
        symbols: List of symbols to backtest (defaults to config symbols)
        sentiment_buy: Sentiment threshold for BUY signal
        sentiment_sell: Sentiment threshold for SELL signal
        initial_cash: Starting portfolio value
    """
    cfg = load_config()
    if symbols is None:
        symbols = cfg.symbols

    collector = BacktestDataCollector(
        api_key=cfg.alpaca_api_key,
        secret_key=cfg.alpaca_secret_key,
    )
    engine = BacktestEngine(
        initial_cash=initial_cash,
        stop_loss_pct=cfg.stop_loss_pct,  # uses your .env value
    )

    all_results = []
    for symbol in symbols:
        print(f"Running backtest for {symbol}...")
        data = collector.get_backtest_data(symbol)
        
        if not data:
            print(f"  ⚠️  No backtest data for {symbol} (run live trading to collect)")
            all_results.append({"symbol": symbol, "error": "No data"})
            continue
        
        result = engine.run_backtest(
            symbol=symbol,
            data=data,
            sentiment_threshold_buy=sentiment_buy,
            sentiment_threshold_sell=sentiment_sell,
        )
        all_results.append(result)

    engine.backtest_summary(all_results)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Backtest sentiment-driven trading strategy")
    parser.add_argument(
        "--buy-threshold",
        type=float,
        default=0.3,
        help="Sentiment threshold for BUY (default: 0.3)",
    )
    parser.add_argument(
        "--sell-threshold",
        type=float,
        default=-0.3,
        help="Sentiment threshold for SELL (default: -0.3)",
    )
    parser.add_argument(
        "--initial-cash",
        type=float,
        default=10000.0,
        help="Starting portfolio value (default: 10000)",
    )
    parser.add_argument(
        "symbols",
        nargs="*",
        help="Symbols to backtest (defaults to config symbols if not provided)",
    )

    args = parser.parse_args()
    run_backtest(
        symbols=args.symbols if args.symbols else None,
        sentiment_buy=args.buy_threshold,
        sentiment_sell=args.sell_threshold,
        initial_cash=args.initial_cash,
    )
