# avanza-bot

Trading bot för Avanza.

## Kom igång

1. Använd den redan skapade virtuella miljön:

```powershell
.venv\Scripts\Activate.ps1
```

Om PowerShell blockerar skript kan du i stället köra:

```bat
.venv\Scripts\activate.bat
```

2. Installera beroenden:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

3. Kopiera `.env.example` till `.env` och fyll i:

```text
USERNAME=
PASSWORD=
TOTP_SECRET=
```

4. Kör startskriptet:

```powershell
.venv\Scripts\python.exe avanza_bot.py
```

## Nästa steg

`avanza_bot.py` loggar in och skriver ut kontoöversikten. Därifrån kan du bygga vidare med strategi, riskhantering och orderläggning.
