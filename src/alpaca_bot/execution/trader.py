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

        try:
            side = "BUY" if signal is Signal.BUY else "SELL"
            last_price = self.alpaca.get_last_price(symbol)
            qty = self.risk.calculate_quantity(last_price)

            if qty <= 0:
                return {"symbol": symbol, "action": "SKIP", "order_id": "", "reason": "qty <= 0"}

            # Check position before SELL
            if side == "SELL":
                position = self.alpaca.get_position(symbol)
                if position <= 0:
                    return {
                        "symbol": symbol,
                        "action": "SKIP",
                        "order_id": "",
                        "reason": f"no position to sell (have {position})",
                    }
                qty = min(qty, position)

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

        except Exception as e:
            return {
                "symbol": symbol,
                "action": "ERROR",
                "order_id": "",
                "error": str(e),
            }

    def execute_orb_entry(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
    ) -> dict[str, str]:
        """
        Execute an ORB bracket order — entry + stop loss + take profit in one shot.

        Args:
            symbol: Stock ticker
            entry_price: Current price at entry
            stop_loss: Stop loss price (ORB midpoint)
            take_profit: Take profit price (entry + 2x risk)
        """
        try:
            # Skip if we already have a position
            existing = self.alpaca.get_position(symbol)
            if existing > 0:
                return {
                    "symbol": symbol,
                    "action": "SKIP",
                    "order_id": "",
                    "reason": f"already in position ({existing} shares)",
                }

            qty = self.risk.calculate_quantity(entry_price)
            if qty <= 0:
                return {
                    "symbol": symbol,
                    "action": "SKIP",
                    "order_id": "",
                    "reason": "qty <= 0",
                }

            # Validate levels make sense before submitting
            if stop_loss >= entry_price:
                return {
                    "symbol": symbol,
                    "action": "SKIP",
                    "order_id": "",
                    "reason": f"invalid stop loss {stop_loss:.2f} >= entry {entry_price:.2f}",
                }

            if take_profit <= entry_price:
                return {
                    "symbol": symbol,
                    "action": "SKIP",
                    "order_id": "",
                    "reason": f"invalid take profit {take_profit:.2f} <= entry {entry_price:.2f}",
                }

            order_id = self.alpaca.submit_bracket_order(
                symbol=symbol,
                qty=qty,
                stop_loss=stop_loss,
                take_profit=take_profit,
            )

            print(
                f"  ✅ ORB bracket order submitted | "
                f"{symbol} x{qty} | "
                f"SL={stop_loss:.2f} TP={take_profit:.2f} | "
                f"order_id={order_id}"
            )

            return {
                "symbol": symbol,
                "action": "ORB_BUY",
                "order_id": order_id,
                "qty": str(qty),
                "stop_loss": str(stop_loss),
                "take_profit": str(take_profit),
            }

        except Exception as e:
            return {
                "symbol": symbol,
                "action": "ERROR",
                "order_id": "",
                "error": str(e),
            }