from __future__ import annotations

from alpaca_bot.clients.alpaca_client import AlpacaGateway
from alpaca_bot.models import Signal
from alpaca_bot.risk.stop_loss import RiskManager


class Trader:
    def __init__(self, alpaca: AlpacaGateway, risk: RiskManager) -> None:
        self.alpaca = alpaca
        self.risk = risk

    def execute_signal(self, symbol: str, signal: Signal) -> dict[str, str]:
        if signal is Signal.HOLD:
            return {"symbol": symbol, "action": "HOLD", "order_id": ""}

        side = "BUY" if signal is Signal.BUY else "SELL"
        last_price = self.alpaca.get_last_price(symbol)
        qty = self.risk.calculate_quantity(last_price)

        if qty <= 0:
            return {"symbol": symbol, "action": "SKIP", "order_id": ""}

        order_id = self.alpaca.submit_market_order(symbol=symbol, qty=qty, side=side)
        result = {"symbol": symbol, "action": side, "order_id": order_id}

        if signal is Signal.BUY:
            stop_price = self.risk.stop_price(last_price)
            stop_order_id = self.alpaca.submit_stop_order(
                symbol=symbol,
                qty=qty,
                stop_price=stop_price,
                side="SELL",
            )
            result["stop_order_id"] = stop_order_id

        return result
