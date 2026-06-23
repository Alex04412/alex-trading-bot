from __future__ import annotations

import csv
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

EST = ZoneInfo("America/New_York")


class ORBUniverseScanner:
    """Dynamically screens a candidate pool of stocks day-by-day to eliminate bias."""

    def __init__(self, api_key: str, secret_key: str) -> None:
        self.stock_client = StockHistoricalDataClient(api_key, secret_key)

    def scan_for_day(self, symbols: list[str], target_date: str) -> list[str]:
        """
        Scans a list of target symbols for a specific date using ONLY data
        available right at market open. Returns tickers matching high ATR & Vol.
        """
        print(f" Scanning universe for date: {target_date}...")
        
        # Parse dates to get target day and lookback day
        date_obj = datetime.fromisoformat(target_date).replace(tzinfo=EST)
        start_lookback = date_obj - timedelta(days=20) # to calculate 14d ATR safely
        
        # 1. Fetch Daily Bars to analyze past ATR and volume characteristics
        try:
            daily_request = StockBarsRequest(
                symbol_or_symbols=symbols,
                timeframe=TimeFrame.Day,
                start=start_lookback,
                end=date_obj,
            )
            daily_data = self.stock_client.get_stock_bars(daily_request)
        except Exception as e:
            print(f"  ⚠️ Error fetching daily screening data: {e}")
            return []

        scored_universe = []

        for symbol in symbols:
            if symbol not in daily_data or len(daily_data[symbol]) < 15:
                continue
                
            bars = daily_data[symbol]
            
            # Sort chronologically to isolate historicals vs today
            bars_sorted = sorted(bars, key=lambda b: b.timestamp)
            
            # Identify today's session vs history
            historical_bars = [b for b in bars_sorted if b.timestamp.astimezone(EST).date() < date_obj.date()]
            today_bars = [b for b in bars_sorted if b.timestamp.astimezone(EST).date() == date_obj.date()]
            
            if not historical_bars or not today_bars:
                continue
                
            # Target Today's opening session baseline
            target_today = today_bars[0]
            prev_close = historical_bars[-1].close
            
            # --- 2. THE CHUNKY MATHEMATICAL FILTERS ---
            
            # A. Calculate Average Daily Volume over last 14 days
            avg_vol_14d = sum(b.volume for b in historical_bars[-14:]) / 14
            if avg_vol_14d < 500_000: # Liquid assets only to mitigate slippage penalty
                continue
                
            # B. Price Boundary Filter
            if not (5.0 <= prev_close <= 600.0):
                continue

            # C. True ATR % Calculation (High Price-Action Swings)
            ranges = [max(b.high - b.low, abs(b.high - historical_bars[i-1].close), abs(b.low - historical_bars[i-1].close)) 
                      for i, b in enumerate(historical_bars) if i > 0]
            avg_atr = sum(ranges[-14:]) / 14 if ranges else 0
            atr_pct = avg_atr / prev_close
            
            if atr_pct < 0.025: # Requires a natural historical variance of 2.5%+ daily
                continue

            # D. The Gap Momentum Percentage Trigger (Opening Print vs Prev Close)
            gap_pct = abs(target_today.open - prev_close) / prev_close
            
            # Score items primarily on gap sizes & baseline liquidity
            scored_universe.append({
                "symbol": symbol,
                "gap": gap_pct,
                "atr": atr_pct
            })

        # Sort the filtered results by the absolute morning gap value
        sorted_pool = sorted(scored_universe, key=lambda x: x["gap"], reverse=True)
        top_picks = [item["symbol"] for item in sorted_pool[:15]] # Top 15 assets for the day
        
        print(f"  🎯 Scanner selection for {target_date}: {top_picks}")
        return top_picks