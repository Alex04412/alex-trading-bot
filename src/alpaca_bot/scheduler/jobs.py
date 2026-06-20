from __future__ import annotations

import schedule
import time

from alpaca_bot.main import run_once



def start(interval_minutes: int) -> None:
    schedule.every(interval_minutes).minutes.do(run_once)

    while True:
        schedule.run_pending()
        time.sleep(1)
