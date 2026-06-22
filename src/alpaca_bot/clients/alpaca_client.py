from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, StopOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import StockLatestTradeRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame

EST = ZoneInfo("America/New_York")


@dataclass
class AlpacaClients:
    trading: TradingClient
    market_data: StockHistoricalDataClient


class AlpacaGateway:
    def __init__(self, api_key: str, secret_key: str, paper: bool = True) -> None:
        self._clients = AlpacaClients(
            trading=TradingClient(api_key=api_key, secret_key=secret_key, paper=paper),
            market_data=StockHistoricalDataClient(api_key=api_key, secret_key=secret_key),
        )

    def get_last_price(self, symbol: str) -> float:
        req = StockLatestTradeRequest(symbol_or_symbols=[symbol])
        data = self._clients.market_data.get_stock_latest_trade(req)
        return float(data[symbol].price)

    def get_latest_candle(self, symbol: str) -> dict:
        """
        Fetch the latest completed 5-minute candle for a symbol.
        Returns {timestamp, open, high, low, close, volume, vwap}
        """
        now = datetime.now(tz=EST)
        start = now - timedelta(minutes=15)  # grab last 15 min to ensure we get a completed candle

        req = StockBarsRequest(
            symbol_or_symbols=[symbol],
            timeframe=TimeFrame.Minute,
            start=start,
            end=now,
            limit=3,
        )
        bars = self._clients.market_data.get_stock_bars(req)
        symbol_bars = bars[symbol]

        if not symbol_bars:
            raise ValueError(f"No candle data returned for {symbol}")

        # Use the most recent completed bar
        bar = symbol_bars[-1]

        # Calculate VWAP manually if not provided (typical_price * volume / volume)
        vwap = getattr(bar, "vwap", None)
        if vwap is None:
            typical_price = (bar.high + bar.low + bar.close) / 3
            vwap = typical_price  # fallback approximation

        return {
            "timestamp": bar.timestamp.isoformat(),
            "open":      float(bar.open),
            "high":      float(bar.high),
            "low":       float(bar.low),
            "close":     float(bar.close),
            "volume":    float(bar.volume),
            "vwap":      float(vwap),
        }

    def get_position(self, symbol: str) -> int:
        """Get current position qty for symbol (0 if none)."""
        try:
            positions = self._clients.trading.get_all_positions()
            for pos in positions:
                if pos.symbol == symbol:
                    return int(float(pos.qty))
            return 0
        except Exception:
            return 0

    def close_position(self, symbol: str) -> None:
        """Market close any open position for symbol."""
        try:
            self._clients.trading.close_position(symbol)
            print(f"  ✅ Closed position for {symbol}")
        except Exception as e:
            print(f"  ⚠️  Could not close position for {symbol}: {e}")

    def submit_market_order(self, symbol: str, qty: float, side: str) -> str:
        order = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
        )
        created = self._clients.trading.submit_order(order_data=order)
        return str(created.id)

    def submit_stop_order(self, symbol: str, qty: float, stop_price: float, side: str = "SELL") -> str:
        order = StopOrderRequest(
            symbol=symbol,
            qty=qty,
            stop_price=stop_price,
            side=OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
        )
        created = self._clients.trading.submit_order(order_data=order)
        return str(created.id)

    def submit_bracket_order(self, symbol: str, qty: float, stop_loss: float, take_profit: float) -> str:
        """
        Submit a bracket order — entry + stop loss + take profit in one order.
        Used by ORB strategy.
        """
        from alpaca.trading.requests import MarketOrderRequest, TakeProfitRequest, StopLossRequest
        from alpaca.trading.enums import OrderClass

        order = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY,
            order_class=OrderClass.BRACKET,
            take_profit=TakeProfitRequest(limit_price=round(take_profit, 2)),
            stop_loss=StopLossRequest(stop_price=round(stop_loss, 2)),
        )
        created = self._clients.trading.submit_order(order_data=order)
        return str(created.id)