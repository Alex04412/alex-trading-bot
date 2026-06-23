from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

EST = ZoneInfo("America/New_York")


class ORBUniverseScanner:
    """Dynamically screens a candidate pool of stocks day-by-day without lookahead bias."""

    def __init__(self, api_key: str, secret_key: str) -> None:
        self.stock_client = StockHistoricalDataClient(api_key, secret_key)

    def scan_for_day(self, symbols: list[str], target_date: str) -> list[str]:
        """
        Scans a list of target symbols for a specific date using ONLY data
        available right at market open.
        """
        # Parse target string into an explicit, clean date string
        target_date_str = datetime.fromisoformat(target_date).strftime("%Y-%m-%d")
        
        # Pull a wide 35-day window to guarantee 14 actual historical trading days
        end_dt = datetime.fromisoformat(target_date).replace(tzinfo=EST) + timedelta(days=1)
        start_dt = end_dt - timedelta(days=35)
        
        try:
            daily_request = StockBarsRequest(
                symbol_or_symbols=symbols,
                timeframe=TimeFrame.Day,
                start=start_dt,
                end=end_dt,
            )
            # Handle alpaca SDK vs .data dict return formats cleanly
            daily_response = self.stock_client.get_stock_bars(daily_request)
            daily_data = daily_response.data if hasattr(daily_response, "data") else daily_response
        except Exception as e:
            print(f"  ⚠️ Error fetching daily screening data: {e}")
            return []

        scored_universe = []

        for symbol in symbols:
            if symbol not in daily_data or not daily_data[symbol]:
                continue
                
            # Parse and align timezones cleanly to raw ISO date strings
            all_bars = sorted(daily_data[symbol], key=lambda b: b.timestamp)
            
            historical_bars = []
            today_bar = None
            
            for b in all_bars:
                bar_date_str = b.timestamp.astimezone(EST).strftime("%Y-%m-%d")
                if bar_date_str == target_date_str:
                    today_bar = b
                elif bar_date_str < target_date_str:
                    historical_bars.append(b)

            # If we don't have today's opening session or at least 14 days of history, skip safely
            if not today_bar or len(historical_bars) < 14:
                continue
                
            prev_close = float(historical_bars[-1].close)
            today_open = float(today_bar.open)
            
            # --- MATHEMATICAL FILTERS ---
            
            # A. Liquidity Filter (Ensure it trades at least 300k shares daily average)
            avg_vol_14d = sum(int(b.volume) for b in historical_bars[-14:]) / 14
            if avg_vol_14d < 300_000:
                continue
                
            # B. Price Boundaries Filter
            if not (5.0 <= prev_close <= 1500.0):
                continue

            # C. Calculate actual trailing 14-day True Range
            ranges = []
            for i in range(1, len(historical_bars)):
                h = float(historical_bars[i].high)
                l = float(historical_bars[i].low)
                pc = float(historical_bars[i-1].close)
                true_range = max(h - l, abs(h - pc), abs(l - pc))
                ranges.append(true_range)
                
            avg_atr = sum(ranges[-14:]) / 14 if ranges else 0
            atr_pct = avg_atr / prev_close
            
            # Loosen historical volatility slightly down to 1.5% to allow smoother setups
            if atr_pct < 0.015: 
                continue

            # D. The Gap Sorter (Sort by absolute opening displacement)
            gap_pct = abs(today_open - prev_close) / prev_close
            
            scored_universe.append({
                "symbol": symbol,
                "gap": gap_pct
            })

        # Return the top picks based on absolute volatility displacement
        sorted_pool = sorted(scored_universe, key=lambda x: x["gap"], reverse=True)
        
        # If the market is moving smoothly, return everything found, up to a maximum of 15 assets
        top_picks = [item["symbol"] for item in sorted_pool[:15]]
        return top_picks