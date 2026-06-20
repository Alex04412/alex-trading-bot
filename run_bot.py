from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / "src"))

from alpaca_bot.main import run_once


if __name__ == "__main__":
    run_once()
