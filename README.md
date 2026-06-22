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
- NLP/Classifier: **FinBERT** (yiyanghkust/finbert-tone) - financial sentiment analysis
- Backtesting: **vectorbt** - historical strategy simulation
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
	|   |-- classifier.py (legacy keyword-based)
	|   `-- finbert_classifier.py (FinBERT-based)
	|-- data/
	|   `-- collector.py (backtest data storage)
	|-- strategy/
	|   `-- signal_engine.py
	|-- risk/
	|   `-- stop_loss.py
	|-- execution/
	|   `-- trader.py
	|-- scheduler/
	|   `-- jobs.py
	|-- backtest/
	|   `-- engine.py (vectorbt backtesting)
	|-- config.py
	`-- main.py
|-- backtest_runner.py (CLI for strategy backtesting)
```

## FinBERT Sentiment Analysis

Bot använder **FinBERT** för finansiell sentimentanalys.

Sentiment-skala: **-1.0 till 1.0**
- Positiv (bullish): 0.0 - 1.0
- Negativ (bearish): -1.0 - 0.0
- Neutral: 0.0

FinBERT laddas ned automatiskt från HuggingFace (~250MB) vid forsta koring.

## Backtesting med Vectorbt

Live-trading samlar automatiskt in:
- **Timestamp**: Signal-tid
- **Pris**: Aktiepris vid tillfallet
- **Sentiment Score**: FinBERT-klassificering
- **Signal**: BUY/SELL/HOLD resultat

Data lagras i: `backtest_data/{SYMBOL}_backtest.csv`

### Kor backtest

Efter insamling av data genom live-trading:

```powershell
.venv\Scripts\python.exe backtest_runner.py AAPL MSFT NVDA
```

Med egna sentiment-troskelvarден:

```powershell
.venv\Scripts\python.exe backtest_runner.py --buy-threshold 0.4 --sell-threshold -0.4 AAPL
```

Resultat visar:
- Total avkastning %
- Annualiserad avkastning %
- Sharpe-kvot
- Max drawdown %
- Vinstfrekvens %
- Antal trades
- Total profit/loss

## Nasta steg

- Justera sentiment-troskelvardern baserat pa backtest-resultat.
- Implementera riktig stop order/OCO (One-Cancels-Other) strategi.
- Fine-tune FinBERT-modellen pa finansiell nyhetsdataset.
