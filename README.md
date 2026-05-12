# stockdeal

Semiconductor stock analysis & trading system.
Peter Lynch framework + Claude (LLM) + time-series DL, executed against the KIS OpenAPI.

## Quick start

```bash
# 1. Install
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 2. Configure
cp .env.example .env
# fill in keys: KIS, Anthropic, DART, Finnhub, Naver, Telegram, Kakao, SMTP, DB

# 3. Start MySQL locally
docker compose up -d mysql

# 4. Apply schema
stockdeal db-init

# 5. Run service
stockdeal serve
# in another shell:
stockdeal worker
```

## Project layout

```
src/stockdeal/
  config.py            Pydantic Settings (.env)
  logging.py           structlog setup
  db/                  SQLAlchemy engine/session
  collectors/
    kis.py             KIS REST + WebSocket
    dart.py            Open DART
    news/              naver, finnhub, rss
    macro/             FRED, ECOS
  analysis/
    llm.py             Claude tiered client
    lynch.py           Peter Lynch checklist
    technical.py       TA indicators
    ml/timeseries.py   DL forecasting
  strategy/
    signal.py          Signal generation
    risk.py            Pre-trade risk gates
  execution/
    trader.py          Mode-aware dispatcher
    paper.py           Paper trading
    real.py            KIS order routing
    mode.py            Mode mutation + kill switch
  notify/
    telegram.py        Real-time alerts + bot commands
    kakao.py           Critical alerts (나에게 보내기)
    email.py           Daily/weekly reports (Gmail SMTP)
  reports/
    daily.py           Report builder
    templates/
  learning/
    outcome.py         D+5/20/60 labeling
    retrospective.py   Weekly Claude review -> lessons_learned
    tuning.py          Monthly param auto-tune
  scheduler.py         APScheduler jobs
  api.py               FastAPI (control plane)
  cli.py               typer CLI

sql/schema.sql         MySQL DDL
```

## Trading modes

| Mode | Behavior |
|---|---|
| OFF | Record signals only. No paper, no real. |
| SIMULATION | Paper trading runs. No real orders. (Default.) |
| CONFIRM | Paper runs. Real orders require explicit user approval via Telegram/Kakao. |
| AUTO | Paper runs. Real orders placed immediately, subject to risk limits. |

Change at runtime:
- `POST /mode` with body `{"mode":"CONFIRM"}`
- Telegram `/mode confirm`
- Kill switch: `POST /halt` or Telegram `/halt`

## Watchlist

Default: HPSP (403870), 삼성전자 (005930), SK하이닉스 (000660), 심텍 (222800), 동진쎄미켐 (005290), 씨엠티엑스 (442900). Primary analysis target: HPSP.

## Status

Scaffold only. Module bodies are `NotImplementedError` placeholders; the next
milestone is the KIS + DART PoC against HPSP.
