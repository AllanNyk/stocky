# Stocky

A paper-trading web app with a transparent prediction score and continuous forward-testing of the model. No real money involved.

## What's in Phase 1

- 30 curated stocks (15 US large-caps + 15 Nordic blue chips) plus 3 benchmark indices, with Pluto Markets-style brokerage-tier badges (commission-free / standard fee).
- Daily price + fundamentals ingestion via yfinance (1y history backfill).
- Base currency is **DKK** — every price/portfolio number normalizes through daily FX rates (USD, EUR, SEK, NOK → DKK).
- Composite prediction score (0–100) from rule-based signals:
  - P/E percentile vs sector peers (cheap = bullish).
  - 50-day price momentum vs SMA.
- **Continuous forward-testing**: each day's snapshot freezes scores + entry prices; realized 1d / 7d / 30d / 90d returns are computed on read. Two virtual portfolios run side-by-side:
  - Top-5 by composite score, equal weight.
  - Every stock with score ≥ 70, equal weight.
- Paper trading: register, get 100,000 DKK in mock cash, buy/sell at last close, see positions/P&L/trade history.
- JWT auth ready for multi-user.

## Stack

- **Backend** – Python 3.13 · FastAPI · SQLAlchemy 2 · SQLite (dev; swap `DATABASE_URL` to Postgres later) · APScheduler · yfinance ≥ 1.3 (with `curl-cffi` for Yahoo Cloudflare bypass).
- **Frontend** – React 19 · TypeScript · Vite · React Router · Recharts.

## Quick start (Windows / PowerShell)

```powershell
# --- Backend (Terminal 1) ---
cd C:\myapps\stocky\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload

# --- Frontend (Terminal 2) ---
cd C:\myapps\stocky\frontend
copy .env.example .env
npm install
npm run dev
```

If `Activate.ps1` is blocked, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first.

- Backend: <http://localhost:8000> (Swagger UI at `/docs`)
- Frontend: <http://localhost:5173>

On first boot the backend seeds 33 stocks/benchmarks into SQLite. **Prices are not auto-fetched on startup** — trigger them manually once via Swagger or curl, then the daily scheduler keeps them fresh:

```powershell
# Pull 1y of OHLCV for everything (~30s)
Invoke-RestMethod -Method POST http://localhost:8000/api/admin/refresh-prices

# Take today's score snapshot so the validation page has data
Invoke-RestMethod -Method POST http://localhost:8000/api/validation/run-snapshot
```

Then open <http://localhost:5173>, register an account, and you're ready.

## Daily jobs (APScheduler, in-process)

- `23:00` Europe/Copenhagen — refresh prices + FX.
- `23:10` Europe/Copenhagen — run score snapshot (locks today's composites and updates the virtual portfolios).

## Endpoint map

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/api/health` | – | Liveness. |
| POST | `/api/auth/register` | – | Create account, returns JWT. |
| POST | `/api/auth/login` | – | Returns JWT. |
| GET | `/api/auth/me` | ✓ | Current user + cash balance. |
| GET | `/api/stocks` | – | Market list. |
| GET | `/api/stocks/{ticker}` | – | Single stock + last close. |
| GET | `/api/stocks/{ticker}/history?days=180` | – | OHLCV series. |
| GET | `/api/stocks/{ticker}/score` | – | Composite + component scores. |
| GET | `/api/scores` | – | Composite for every stock. |
| POST | `/api/trade` | ✓ | Paper buy/sell at last close. |
| GET | `/api/portfolio` | ✓ | Positions, P&L, cash. |
| GET | `/api/trades` | ✓ | Trade history. |
| GET | `/api/validation/latest-picks` | – | Most-recent picks + realized return per strategy. |
| GET | `/api/validation/performance` | – | Aggregate hit rate + avg return per horizon, per strategy. |
| POST | `/api/validation/run-snapshot` | – | Manually run today's snapshot. |
| POST | `/api/admin/refresh-fx` | – | Pull DKK FX rates. |
| POST | `/api/admin/refresh-prices?period=1y` | – | Pull OHLCV for every ticker. |

> `/api/admin/*` and `/api/validation/run-snapshot` are unauthenticated in Phase 1 for local-dev convenience. Lock them down before deploying anywhere public.

## Project layout

```
backend/
  app/
    main.py               FastAPI app + lifespan (seeds DB, starts scheduler)
    config.py             Settings via pydantic-settings
    db.py                 SQLAlchemy engine + session
    security.py           JWT + password hashing
    scheduler.py          APScheduler jobs
    models/               User, Stock, PriceHistory, FxRate, DailyScoreSnapshot, ModelPortfolioPick, Position, Trade
    routers/              admin, auth, stocks, portfolio, validation
    services/
      fx.py               DKK FX rate refresh
      ingestion.py        yfinance price + fundamentals pull
      scoring.py          Composite from individual signals
      signals/
        base.py
        pe_percentile.py
        momentum.py
      snapshots.py        Daily snapshot + forward-return queries
      trading.py          Paper-trading engine (Pluto-tier fees)
    seeds/universe.py     30 stocks + 3 benchmarks, with Pluto tier
frontend/
  src/
    api.ts                Typed fetch wrapper + endpoint client
    auth.tsx              Auth context (JWT in localStorage)
    format.ts             DKK / pct / score-color helpers
    App.tsx               Routes + shell
    pages/                LoginPage, MarketPage, StockDetailPage, PortfolioPage, ValidationPage
    components/TradePanel.tsx
```

## Roadmap beyond Phase 1

Designed-for-but-deferred work, in rough priority order:

1. **More signals**: news sentiment (NewsAPI free tier + FinBERT), Reddit/WSB mention delta, GDELT geopolitical exposure, insider trades (Finnhub free tier), Truth Social political signal.
2. **Postgres + Alembic** when the SQLite single-writer ceiling is hit.
3. **Hand-verify Pluto tier** against the actual pluto.markets list and add a refresh job.
4. **Backtest UI**: "if you'd traded the signal 90 days ago, your portfolio would look like…"
5. **ML upgrade**: train on the `daily_score_snapshots` history (which is the entire point of building snapshot persistence on day one).
6. **Watchlists, alerts, leaderboard** once multi-user has real users.

## Known limitations

- yfinance is unofficial and Yahoo regularly changes endpoints. `yfinance>=1.3` plus `curl-cffi` is required (0.2.x is silently broken). If ingestion suddenly returns 0 rows, upgrade yfinance first.
- Prices are end-of-day, not intraday. Fine for a paper-trading game, not for any real-money use (good — there is none).
- All Pluto-tier classifications in `app/seeds/universe.py` are placeholders. Edit them once you've verified the real Pluto Markets list.
