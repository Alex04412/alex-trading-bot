from __future__ import annotations


class RiskManager:
    def __init__(self, max_position_usd: float, stop_loss_pct: float) -> None:
        self.max_position_usd = max_position_usd
        self.stop_loss_pct = stop_loss_pct

    def calculate_quantity(self, price: float) -> float:
        if price <= 0:
            return 0.0
        return round(self.max_position_usd / price, 4)

    def stop_price(self, entry_price: float) -> float:
        return round(entry_price * (1.0 - self.stop_loss_pct), 2)
