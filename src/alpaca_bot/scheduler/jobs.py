from __future__ import annotations

import schedule
import time

from alpaca_bot.main import run_once


orb_strategies: dict = {}


def job() -> None:
    global orb_strategies
    orb_strategies = run_once(orb_strategies=orb_strategies)


def start(interval_minutes: int) -> None:
    schedule.every(interval_minutes).minutes.do(job)

    while True:
        schedule.run_pending()
        time.sleep(1)