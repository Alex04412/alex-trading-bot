# avanza-bot

Alpaca paper trading-bot med nyhetsdriven signalering.

## Arkitektur

Nyhetsartiklar -> Text classifier -> Signal (BUY/SELL/HOLD) -> Alpaca Trade API

- `BUY` placerar marknadsorder och stop loss-order.
- `SELL` placerar marknadsorder.
- `HOLD` gör ingen order.

## Stack

- Broker/API: Alpaca Markets
- Nyhetsdata: NewsAPI
- NLP/Classifier: FinBERT (planerad) + scikit-learn (placeholder)
- Backtesting: vectorbt (stub)
- Schemalaggning: schedule

## Kom igang (Windows PowerShell)

1. Ta bort gammal miljo och skapa en ny:

```powershell
Remove-Item -Recurse -Force .venv
py -3 -m venv .venv
```

2. Aktivera miljo:

```powershell
.venv\Scripts\Activate.ps1
```

3. Installera beroenden:

```powershell
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

4. Skapa `.env` fran `.env.example` och fyll i:

```text
ALPACA_API_KEY=
ALPACA_SECRET_KEY=
ALPACA_PAPER=true
NEWSAPI_KEY=
SYMBOLS=AAPL,MSFT,NVDA
MAX_POSITION_USD=1000
STOP_LOSS_PCT=0.03
POLL_INTERVAL_MINUTES=15
```

`NEWSAPI_KEY` kan vara tom tills du skapat konto/nyckel pa newsapi.org.

5. Kor en trading-cykel:

```powershell
.venv\Scripts\python.exe run_bot.py
```

## Projektstruktur

```text
.
|-- .env.example
|-- requirements.txt
|-- run_bot.py
`-- src/alpaca_bot/
	|-- clients/
	|   |-- alpaca_client.py
	|   `-- news_client.py
	|-- nlp/
	|   `-- classifier.py
	|-- strategy/
	|   `-- signal_engine.py
	|-- risk/
	|   `-- stop_loss.py
	|-- execution/
	|   `-- trader.py
	|-- scheduler/
	|   `-- jobs.py
	|-- backtest/
	|   `-- vectorbt_stub.py
	|-- config.py
	`-- main.py
```

## Nasta steg

- Byt ut `HeadlineClassifier` mot riktig FinBERT-pipeline.
- Lagg till en riktig stop order/oco-strategi per symbol och position.
- Koppla in vectorbt med historiska priser + nyhetssignaler.
