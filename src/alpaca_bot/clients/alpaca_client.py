from __future__ import annotations

from dataclasses import dataclass

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, StopOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import StockLatestTradeRequest


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
