from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from alpaca_bot.clients.alpaca_client import AlpacaGateway
from alpaca_bot.clients.news_client import NewsClient
from alpaca_bot.config import load_config
from alpaca_bot.execution.trader import Trader
from alpaca_bot.nlp.finbert_classifier import FinBERTClassifier
from alpaca_bot.risk.stop_loss import RiskManager
from alpaca_bot.strategy.signal_engine import SignalEngine
from alpaca_bot.data.collector import BacktestDataCollector
from alpaca_bot.strategy.orb import ORBStrategy

EST = ZoneInfo("America/New_York")


def run_once(
    collect_backtest_data: bool = True,
    orb_strategies: dict[str, ORBStrategy] | None = None,
) -> dict[str, ORBStrategy]:
    """
    Run one trading cycle.

    Args:
        collect_backtest_data: If True, collect prices and signals for backtesting.
        orb_strategies: Persistent ORB state per symbol (pass in from scheduler).

    Returns:
        Updated orb_strategies dict (persist this between calls).
    """
    cfg = load_config()
    if not cfg.alpaca_api_key or not cfg.alpaca_secret_key:
        raise RuntimeError("Missing Alpaca API credentials in .env")

    now_est = datetime.now(tz=EST)

    alpaca = AlpacaGateway(
        api_key=cfg.alpaca_api_key,
        secret_key=cfg.alpaca_secret_key,
        paper=cfg.alpaca_paper,
    )
    news = NewsClient(api_key=cfg.newsapi_key)
    classifier = FinBERTClassifier()
    signal_engine = SignalEngine()
    risk = RiskManager(cfg.max_position_usd, cfg.stop_loss_pct)
    trader = Trader(alpaca=alpaca, risk=risk)
    collector = BacktestDataCollector(
        api_key=cfg.alpaca_api_key,
        secret_key=cfg.alpaca_secret_key,
    )

    # Initialise ORB strategy per symbol if not already created
    if orb_strategies is None:
        orb_strategies = {}
    for symbol in cfg.symbols:
        if symbol not in orb_strategies:
            orb_strategies[symbol] = ORBStrategy(
                orb_minutes=30,
                rr_ratio=cfg.stop_loss_pct * 2 / cfg.stop_loss_pct,  # uses your config
                vol_multiplier=1.5,
            )

    for symbol in cfg.symbols:
        print(f"\n[{now_est.strftime('%H:%M')} EST] Processing {symbol}...")

        # ── 1. Get current candle + price ──────────────────────────────
        try:
            candle = alpaca.get_latest_candle(symbol)   # must return {timestamp, open, high, low, close, volume, vwap}
            price = candle["close"]
        except Exception as e:
            print(f"  ⚠️  Could not fetch candle for {symbol}: {e}")
            continue

        # ── 2. Sentiment signal ────────────────────────────────────────
        headlines = news.fetch_market_headlines(symbol=symbol, limit=10)
        sentiment_score = classifier.score(headlines)
        signal = signal_engine.from_sentiment(sentiment_score)

        # ── 3. Update ORB state with latest candle ─────────────────────
        orb = orb_strategies[symbol]
        orb.update(candle)

        # ── 4. Force close check (end of day 3:55 PM) ──────────────────
        if orb.should_force_close(candle):
            print(f"  🔔 Force closing {symbol} — end of day")
            try:
                alpaca.close_position(symbol)
            except Exception as e:
                print(f"  ⚠️  Could not close {symbol}: {e}")
            continue

        # ── 5. ORB entry — only if sentiment agrees ────────────────────
        orb_signal_fired = False
        if orb.should_enter(candle, sentiment_score=sentiment_score):
            try:
                levels = orb.get_levels(entry_price=price)
                print(
                    f"  🚀 ORB entry {symbol} | "
                    f"stop={levels['stop_loss']:.2f} | "
                    f"tp={levels['take_profit']:.2f} | "
                    f"sentiment={sentiment_score:.3f}"
                )
                trader.execute_orb_entry(
                    symbol=symbol,
                    entry_price=price,
                    stop_loss=levels["stop_loss"],
                    take_profit=levels["take_profit"],
                )
                orb_signal_fired = True
            except Exception as e:
                print(f"  ⚠️  ORB entry failed for {symbol}: {e}")

        # ── 6. Fallback — pure sentiment signal if no ORB entry ────────
        if not orb_signal_fired:
            result = trader.execute_signal(symbol=symbol, signal=signal)
            print(
                f"  sentiment={sentiment_score:.3f} "
                f"signal={signal.value} "
                f"result={result}"
            )

        # ── 7. Collect backtest data ───────────────────────────────────
        if collect_backtest_data:
            try:
                collector.append_record(
                    symbol=symbol,
                    price=price,
                    sentiment_score=sentiment_score,
                    signal=signal.value,
                )
            except Exception as e:
                print(f"  ⚠️  Backtest collection failed for {symbol}: {e}")

    return orb_strategies