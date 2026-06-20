from __future__ import annotations

from alpaca_bot.clients.alpaca_client import AlpacaGateway
from alpaca_bot.clients.news_client import NewsClient
from alpaca_bot.config import load_config
from alpaca_bot.execution.trader import Trader
from alpaca_bot.nlp.classifier import HeadlineClassifier
from alpaca_bot.risk.stop_loss import RiskManager
from alpaca_bot.strategy.signal_engine import SignalEngine



def run_once() -> None:
    cfg = load_config()
    if not cfg.alpaca_api_key or not cfg.alpaca_secret_key:
        raise RuntimeError("Missing Alpaca API credentials in .env")

    alpaca = AlpacaGateway(
        api_key=cfg.alpaca_api_key,
        secret_key=cfg.alpaca_secret_key,
        paper=cfg.alpaca_paper,
    )
    news = NewsClient(api_key=cfg.newsapi_key)
    classifier = HeadlineClassifier()
    signal_engine = SignalEngine()
    risk = RiskManager(cfg.max_position_usd, cfg.stop_loss_pct)
    trader = Trader(alpaca=alpaca, risk=risk)

    for symbol in cfg.symbols:
        headlines = news.fetch_market_headlines(symbol=symbol, limit=10)
        sentiment_score = classifier.score(headlines)
        signal = signal_engine.from_sentiment(sentiment_score)
        result = trader.execute_signal(symbol=symbol, signal=signal)
        print(
            f"symbol={symbol} sentiment={sentiment_score:.3f} signal={signal.value} result={result}"
        )
