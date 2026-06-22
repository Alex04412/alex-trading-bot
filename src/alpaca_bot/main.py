from __future__ import annotations

from alpaca_bot.clients.alpaca_client import AlpacaGateway
from alpaca_bot.clients.news_client import NewsClient
from alpaca_bot.config import load_config
from alpaca_bot.execution.trader import Trader
from alpaca_bot.nlp.finbert_classifier import FinBERTClassifier
from alpaca_bot.risk.stop_loss import RiskManager
from alpaca_bot.strategy.signal_engine import SignalEngine
from alpaca_bot.data.collector import BacktestDataCollector


def run_once(collect_backtest_data: bool = True) -> None:
    """
    Run one trading cycle.

    Args:
        collect_backtest_data: If True, collect prices and signals for backtesting.
    """
    cfg = load_config()
    if not cfg.alpaca_api_key or not cfg.alpaca_secret_key:
        raise RuntimeError("Missing Alpaca API credentials in .env")

    alpaca = AlpacaGateway(
        api_key=cfg.alpaca_api_key,
        secret_key=cfg.alpaca_secret_key,
        paper=cfg.alpaca_paper,
    )
    news = NewsClient(api_key=cfg.newsapi_key)
    classifier = FinBERTClassifier()  # FinBERT-based sentiment analysis
    signal_engine = SignalEngine()
    risk = RiskManager(cfg.max_position_usd, cfg.stop_loss_pct)
    trader = Trader(alpaca=alpaca, risk=risk)
    
   
    collector = BacktestDataCollector(
        api_key=cfg.alpaca_api_key,
        secret_key=cfg.alpaca_secret_key,
    )

    for symbol in cfg.symbols:
        headlines = news.fetch_market_headlines(symbol=symbol, limit=10)
        sentiment_score = classifier.score(headlines)
        signal = signal_engine.from_sentiment(sentiment_score)
        result = trader.execute_signal(symbol=symbol, signal=signal)
        
        # Collect data for backtesting if enabled
        if collector:
            try:
                price = alpaca.get_last_price(symbol)
                collector.append_record(
                    symbol=symbol,
                    price=price,
                    sentiment_score=sentiment_score,
                    signal=signal.value,
                )
            except Exception as e:
                print(f"Failed to collect backtest data for {symbol}: {e}")
        
        print(
            f"symbol={symbol} sentiment={sentiment_score:.3f} signal={signal.value} result={result}"
        )
