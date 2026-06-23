from __future__ import annotations

from collections import defaultdict
from datetime import datetime, time
from zoneinfo import ZoneInfo

from alpaca_bot.strategy.orb import ORBStrategy

EST = ZoneInfo("America/New_York")


class ORBBacktestEngine:
    """
    Replay historical 5-min candles through ORBStrategy day by day.
    Simulates exact same logic as live bot.
    """

    def __init__(
        self,
        initial_cash: float = 10000.0,
        fees: float = 0.001,
        orb_minutes: int = 30,
        rr_ratio: float = 2.0,
        vol_multiplier: float = 1.1,
        sentiment_threshold: float = 0.3,
        max_risk_pct: float = 0.02,
        spy_data: dict[str, float] = None,
    ) -> None:
        self.initial_cash = initial_cash
        self.fees = fees
        self.orb_minutes = orb_minutes
        self.rr_ratio = rr_ratio
        self.vol_multiplier = vol_multiplier
        self.sentiment_threshold = sentiment_threshold
        self.max_risk_pct = max_risk_pct  # skip trade if stop > 2% away
        self.spy_data = spy_data  # date_str → daily_return for SPY, used to gauge market direction

    def _is_market_bullish(self, date_str: str, spy_data: dict[str, float]) -> bool:
        """Return True if SPY closed above its open on this date."""
        return spy_data.get(date_str, 1.0) > 0  # positive = bullish day
    

    def run(self, symbol: str, data: list[dict]) -> dict:
        if not data:
            return {"symbol": symbol, "error": "No data"}

        orb = ORBStrategy(
            orb_minutes=self.orb_minutes,
            rr_ratio=self.rr_ratio,
            vol_multiplier=self.vol_multiplier,
        )

        cash = self.initial_cash
        trades = []

        in_position = False
        position_side = "LONG"
        
        entry_price = 0.0
        stop_loss = 0.0
        take_profit = 0.0
        qty = 0.0
        
        SLIPPAGE = 0.001  # 0.1% slippage on entry and exit

        for row in data:
            candle = {
                "timestamp": row["timestamp"],
                "open":      row["open"],
                "high":      row["high"],
                "low":       row["low"],
                "close":     row["close"],
                "volume":    row["volume"],
            }
            
            sentiment = row["sentiment_score"]
            ts_est = self._to_est(candle["timestamp"])
            date_str = ts_est.strftime("%Y-%m-%d")
            
            orb.update(candle)

            # ── Exit logic ────────────────────────────────────────────────
            if in_position:
                if position_side == "LONG":
                    if candle["low"] <= stop_loss:
                        # Selling to exit: Slippage lowers your sell price
                        real_exit_price = stop_loss * (1 - SLIPPAGE)
                        pnl = (real_exit_price - entry_price) * qty * (1 - self.fees)
                        cash += entry_price * qty + pnl
                        trades.append({
                            "exit": row["timestamp"],
                            "pnl": pnl,
                            "exit_type": "STOP_LOSS",
                            "side": "LONG",
                            "entry": entry_price,
                            "exit_price": real_exit_price,
                        })
                        in_position = False

                    elif candle["high"] >= take_profit:
                        # Selling to exit: Slippage lowers your sell price
                        real_exit_price = take_profit * (1 - SLIPPAGE)
                        pnl = (real_exit_price - entry_price) * qty * (1 - self.fees)
                        cash += entry_price * qty + pnl
                        trades.append({
                            "exit": row["timestamp"],
                            "pnl": pnl,
                            "exit_type": "TAKE_PROFIT",
                            "side": "LONG",
                            "entry": entry_price,
                            "exit_price": real_exit_price,
                        })
                        in_position = False

                    elif orb.should_force_close(candle):
                        real_exit_price = candle["close"] * (1 - SLIPPAGE)
                        pnl = (real_exit_price - entry_price) * qty * (1 - self.fees)
                        cash += entry_price * qty + pnl
                        trades.append({
                            "exit": row["timestamp"],
                            "pnl": pnl,
                            "exit_type": "EOD_CLOSE",
                            "side": "LONG",
                            "entry": entry_price,
                            "exit_price": real_exit_price,
                        })
                        in_position = False

                elif position_side == "SHORT":
                    if candle["high"] >= stop_loss:
                        # Buying to cover: Slippage raises your buy price
                        real_exit_price = stop_loss * (1 + SLIPPAGE)
                        pnl = (entry_price - real_exit_price) * qty * (1 - self.fees)
                        cash += entry_price * qty + pnl
                        trades.append({
                            "exit": row["timestamp"],
                            "pnl": pnl,
                            "exit_type": "STOP_LOSS",
                            "side": "SHORT",
                            "entry": entry_price,
                            "exit_price": real_exit_price,
                        })
                        in_position = False

                    elif candle["low"] <= take_profit:
                        # Buying to cover: Slippage raises your buy price
                        real_exit_price = take_profit * (1 + SLIPPAGE)
                        pnl = (entry_price - real_exit_price) * qty * (1 - self.fees)
                        cash += entry_price * qty + pnl
                        trades.append({
                            "exit": row["timestamp"],
                            "pnl": pnl,
                            "exit_type": "TAKE_PROFIT",
                            "side": "SHORT",
                            "entry": entry_price,
                            "exit_price": real_exit_price,
                        })
                        in_position = False

                    elif orb.should_force_close(candle):
                        # Buying to cover: Slippage raises your buy price
                        real_exit_price = candle["close"] * (1 + SLIPPAGE)
                        pnl = (entry_price - real_exit_price) * qty * (1 - self.fees)
                        cash += entry_price * qty + pnl
                        trades.append({
                            "exit": row["timestamp"],
                            "pnl": pnl,
                            "exit_type": "EOD_CLOSE",
                            "side": "SHORT",
                            "entry": entry_price,
                            "exit_price": real_exit_price,
                        })
                        in_position = False

            # ── Entry logic ───────────────────────────────────────────────
            if not in_position and orb.orb_locked:
                ts_est = self._to_est(candle["timestamp"])
                past_cutoff = ts_est.time() >= orb.cutoff_time
                force_close = orb.should_force_close(candle)
                vol_spike = candle["volume"] >= (orb.orb_avg_vol or 0) * self.vol_multiplier
                
                market_bullish = self.spy_data.get(date_str, 1.0) > 0 if self.spy_data else True
                
                # LONG — price breaks above ORB high
                if orb.should_enter(candle, sentiment) and not past_cutoff and market_bullish:
                    levels = orb.get_levels(candle["close"])
                    
                    # Buying to enter: Slippage raises your entry price
                    real_entry_price = candle["close"] * (1 + SLIPPAGE)
                    risk_pct = (real_entry_price - levels["stop_loss"]) / real_entry_price

                    if risk_pct > self.max_risk_pct:
                        pass  # stop too wide, skip
                    else:
                        entry_price   = real_entry_price
                        stop_loss     = levels["stop_loss"]
                        take_profit   = levels["take_profit"]
                        qty           = (cash * 0.95) / entry_price
                        cash         -= entry_price * qty * (1 + self.fees)
                        in_position   = True
                        position_side = "LONG"

                # SHORT — price breaks below ORB low with negative sentiment
                elif (
                    candle["close"] < orb.orb_low
                    and vol_spike
                    and sentiment <= -0.3
                    and not past_cutoff
                    and not force_close
                ):
                    risk         = orb.orb_mid - candle["close"]
                    
                    # Selling to enter short: Slippage lowers your execution price
                    real_entry_price = candle["close"] * (1 - SLIPPAGE)
                    stop_loss    = orb.orb_mid
                    take_profit  = real_entry_price - (risk * self.rr_ratio)
                    risk_pct     = (stop_loss - real_entry_price) / real_entry_price

                    if risk_pct > self.max_risk_pct:
                        pass  # stop too wide, skip
                    else:
                        entry_price   = real_entry_price
                        qty           = (cash * 0.95) / entry_price
                        cash         -= entry_price * qty * (1 + self.fees)
                        in_position   = True
                        position_side = "SHORT"

        # Force close anything still open at end of data
        if in_position and data:
            if position_side == "LONG":
                real_exit_price = data[-1]["close"] * (1 - SLIPPAGE)
                pnl = (real_exit_price - entry_price) * qty * (1 - self.fees)
            else:
                real_exit_price = data[-1]["close"] * (1 + SLIPPAGE)
                pnl = (entry_price - real_exit_price) * qty * (1 - self.fees)
                
            cash += entry_price * qty + pnl
            trades.append({
                "exit": data[-1]["timestamp"],
                "pnl": pnl,
                "exit_type": "EOD_CLOSE",
                "side": position_side,
                "entry": entry_price,
                "exit_price": real_exit_price,
            })

        # ── Metrics ──────────────────────────────────────────────────────
        final_value  = cash
        total_return = (final_value - self.initial_cash) / self.initial_cash
        num_trades   = len(trades)
        wins         = [t for t in trades if t["pnl"] > 0]
        losses       = [t for t in trades if t["pnl"] <= 0]
        win_rate     = len(wins) / num_trades if num_trades > 0 else 0.0
        avg_win      = sum(t["pnl"] for t in wins)   / len(wins)   if wins   else 0.0
        avg_loss     = sum(t["pnl"] for t in losses)  / len(losses) if losses else 0.0

        exit_counts = defaultdict(int)
        side_counts = defaultdict(int)
        for t in trades:
            exit_counts[t["exit_type"]] += 1
            side_counts[t["side"]] += 1

        return {
            "symbol":       symbol,
            "total_return": total_return,
            "total_profit": final_value - self.initial_cash,
            "final_value":  final_value,
            "num_trades":   num_trades,
            "win_rate":     win_rate,
            "avg_win":      avg_win,
            "avg_loss":     avg_loss,
            "stop_losses":  exit_counts["STOP_LOSS"],
            "take_profits": exit_counts["TAKE_PROFIT"],
            "eod_closes":   exit_counts["EOD_CLOSE"],
            "long_trades":  side_counts["LONG"],
            "short_trades": side_counts["SHORT"],
            "trades":       trades,
        }

    @staticmethod
    def _to_est(ts) -> datetime:
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=EST)
        return ts.astimezone(EST)

    @staticmethod
    def summary(all_results: list[dict]) -> None:
        """Print formatted ORB backtest summary."""
        print("\n" + "=" * 80)
        print("ORB BACKTEST SUMMARY")
        print("=" * 80)

        total_profit = 0.0
        valid = []

        for r in all_results:
            if "error" in r:
                print(f"\n{r['symbol']}: ERROR — {r['error']}")
                continue

            valid.append(r)
            total_profit += r["total_profit"]
            label = "✅" if r["total_profit"] >= 0 else "❌"

            print(f"\n{r['symbol']}:")
            print(f"  {label} Profit:        ${r['total_profit']:.2f}")
            print(f"  Total Return:   {r['total_return']*100:.2f}%")
            print(f"  Trades:         {r['num_trades']} (Long: {r.get('long_trades', 0)} Short: {r.get('short_trades', 0)})")
            print(f"  Win Rate:       {r['win_rate']*100:.1f}%")
            print(f"  Avg Win:        ${r['avg_win']:.2f}")
            print(f"  Avg Loss:       ${r['avg_loss']:.2f}")
            print(f"  Stop Losses:    {r['stop_losses']}")
            print(f"  Take Profits:   {r['take_profits']}")
            print(f"  EOD Closes:     {r['eod_closes']}")

        if valid:
            print(f"\n{'─'*80}")
            label = "✅" if total_profit >= 0 else "❌"
            print(f"  {label} TOTAL PROFIT: ${total_profit:.2f}")
            avg = sum(r["total_return"] for r in valid) / len(valid)
            print(f"  AVG RETURN:     {avg*100:.2f}%")

        print("=" * 80 + "\n")
    