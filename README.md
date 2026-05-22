# Stocky

A paper-trading web app with a transparent prediction score and continuous forward-testing of the model. No real money involved.

## What's in Phase 1

- 116 curated names (111 US large-caps + Nordic blue chips, plus 5 benchmark indices), with Pluto Markets-style brokerage-tier badges (commission-free / standard fee).
- Daily price + fundamentals ingestion via yfinance (1y history backfill).
- Base currency is **DKK** — every price/portfolio number normalizes through daily FX rates (USD, EUR, SEK, NOK → DKK).
- Composite prediction score (0–100) from 9 rule-based signals (confidence-weighted; weights in `app/services/scoring.py`):
  - 50-day price momentum vs SMA (weight 0.17).
  - P/E percentile vs sector peers — cheap = bullish (0.13).
  - News sentiment — VADER compound score over per-ticker headlines from yfinance, pooled across the last 5 days (0.13).
  - 52-week percentile — where today sits in the 1y high-low range (0.12).
  - Geopolitical tone — GDELT 2.0 country-level mean news tone for the stock's home country, catching wars/crises/policy shocks (0.12).
  - Insider activity — 30-day net Finnhub insider buying vs selling, US-only (0.11).
  - Social sentiment — StockTwits bull/bear message tags, US-only (0.10).
  - Volume momentum — 5d avg vs 50d avg, an attention amplifier, direction-agnostic (0.08).
  - WSB mention delta — **dormant** (weight 0.04, confidence 0): Reddit's Responsible Builder Policy gates personal-use access. Re-activates without code changes if access reopens.
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

On first boot the backend seeds 116 names (111 stocks + 5 benchmarks) into SQLite. **Prices are not auto-fetched on startup** — trigger them manually once via Swagger or curl, then the daily scheduler keeps them fresh:

```powershell
# Pull 1y of OHLCV for everything (~30s)
Invoke-RestMethod -Method POST http://localhost:8000/api/admin/refresh-prices

# Take today's score snapshot so the validation page has data
Invoke-RestMethod -Method POST http://localhost:8000/api/validation/run-snapshot
```

Then open <http://localhost:5173>, register an account, and you're ready.

### Optional: insider-activity signal (Finnhub)

The `insider_activity` signal stays at confidence 0 until a free Finnhub key is set:

1. Grab a free key at <https://finnhub.io>.
2. Paste `FINNHUB_API_KEY` into `backend/.env`.
3. Restart the backend, then:
   ```powershell
   Invoke-RestMethod -Method POST http://localhost:8000/api/admin/refresh-insider
   ```

`social_sentiment` (StockTwits) needs **no key** — it uses the public stream and is
US-only. `wsb_mention_delta` (Reddit) is **dormant**: Reddit's Responsible Builder
Policy gates personal-use API access, so the signal sits at confidence 0 and the
`refresh-reddit` job is a no-op. If you have approved Reddit creds, set
`REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` / `REDDIT_USER_AGENT` and it re-activates.

### Optional: invite-only registration

Set `INVITE_CODE` in `backend/.env` to require an invite code on `/api/auth/register`.
Leave it unset for open registration (the dev default). The frontend reads
`/api/auth/gate` to decide whether to show the invite-code field.

## Daily jobs (APScheduler, in-process)

- `22:58` Europe/Copenhagen — refresh StockTwits bull/bear tags (US tickers).
- `23:00` Europe/Copenhagen — refresh prices + FX.
- `23:05` Europe/Copenhagen — scrape Reddit mentions (no-op while dormant).
- `23:07` Europe/Copenhagen — refresh news sentiment.
- `23:08` Europe/Copenhagen — refresh GDELT country tones.
- `23:09` Europe/Copenhagen — refresh Finnhub insider activity (skipped if key missing).
- `23:10` Europe/Copenhagen — run score snapshot (locks today's composites, updates the virtual portfolios, and fires any crossed alert rules).

## Endpoint map

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/api/health` | – | Liveness. |
| GET | `/api/auth/gate` | – | Whether registration needs an invite code. |
| POST | `/api/auth/register` | – | Create account (invite code required if `INVITE_CODE` set), returns JWT. |
| POST | `/api/auth/login` | – | Returns JWT. |
| GET | `/api/auth/me` | ✓ | Current user + cash balance. |
| GET | `/api/stocks` | – | Market list. |
| GET | `/api/stocks/{ticker}` | – | Single stock + last close. |
| GET | `/api/stocks/{ticker}/history?days=180` | – | OHLCV series. |
| GET | `/api/stocks/{ticker}/score` | – | Composite + component scores. |
| GET | `/api/scores` | – | Composite for every stock. |
| GET | `/api/movers` | – | Top gainers/losers by recent score/price move. |
| POST | `/api/trade` | ✓ | Paper buy/sell at last close. |
| GET | `/api/portfolio` | ✓ | Positions, P&L, cash. |
| GET | `/api/trades` | ✓ | Trade history. |
| GET/POST/DELETE | `/api/watchlist[/{ticker}]` | ✓ | List / add / remove a watched ticker. |
| GET/POST/DELETE | `/api/alerts[/{id}]` | ✓ | List / create / delete score-crossing alert rules. |
| GET | `/api/notifications` | ✓ | Fired-alert notifications (`?unread_only=`). |
| POST | `/api/notifications/{id}/read`, `/read-all` | ✓ | Mark notification(s) read. |
| GET | `/api/validation/latest-picks` | – | Most-recent picks + realized return per strategy. |
| GET | `/api/validation/performance` | – | Aggregate hit rate + avg return per horizon, per strategy. |
| POST | `/api/validation/run-snapshot` | – | Manually run today's snapshot. |
| POST | `/api/validation/run-backtest?days=90` | – | Replay last N days using only signals with backdata (momentum-only today). |
| POST | `/api/admin/refresh-fx` | †  | Pull DKK FX rates. |
| POST | `/api/admin/refresh-prices?period=1y` | † | Pull OHLCV for every ticker. |
| POST | `/api/admin/refresh-news` | † | Pull per-ticker news via yfinance, score with VADER. |
| POST | `/api/admin/refresh-stocktwits` | † | Pull StockTwits bull/bear tags per US ticker. |
| POST | `/api/admin/refresh-insider` | † | Pull Finnhub insider transactions (US-only; needs `FINNHUB_API_KEY`). |
| POST | `/api/admin/refresh-gdelt` | † | Pull daily GDELT mean tone per country (rate-limited; takes ~30-60s). |
| POST | `/api/admin/refresh-reddit` | † | Scrape Reddit mentions (dormant — no-op unless creds set). |

> † `/api/admin/*` is gated by `ADMIN_TOKEN`: when that env var is set, requests
> must send a matching `X-Admin-Token` header; when unset, the endpoints stay open
> for local-dev convenience. `/api/validation/run-*` is still open — lock it down
> the same way before deploying anywhere public. Always set `ADMIN_TOKEN` in prod.

## Project layout

```
backend/
  app/
    main.py               FastAPI app + lifespan (seeds DB, starts scheduler)
    config.py             Settings via pydantic-settings
    db.py                 SQLAlchemy engine + session
    security.py           JWT + password hashing
    scheduler.py          APScheduler jobs
    models/               User, Stock, PriceHistory, FxRate, DailyScoreSnapshot, ModelPortfolioPick, Position, Trade, Watchlist, AlertRule, Notification
    routers/              admin, auth, stocks, portfolio, validation, watchlist, alerts, movers
    services/
      fx.py               DKK FX rate refresh
      ingestion.py        yfinance price + fundamentals pull
      news_sentiment.py   yfinance news + VADER
      stocktwits.py       StockTwits bull/bear stream
      insider.py          Finnhub insider transactions
      reddit.py           praw mention scraper (dormant)
      gdelt.py            GDELT 2.0 country tone
      scoring.py          Composite from individual signals (SIGNAL_WEIGHTS)
      signals/            9 signals — one file each (base.py is the protocol)
      snapshots.py        Daily snapshot + backtest replay + forward-return queries
      alerts.py           Score-crossing alert evaluation (called from snapshot job)
      trading.py          Paper-trading engine (Pluto-tier fees)
    seeds/universe.py     116 names (111 stocks + 5 benchmarks), with Pluto tier
frontend/
  src/
    api.ts                Typed fetch wrapper + endpoint client
    auth.tsx              Auth context (JWT in localStorage)
    watchlist.tsx         Watchlist context (optimistic toggle)
    format.ts             DKK / pct / score-color helpers
    App.tsx               Routes + shell
    pages/                LoginPage, MarketPage, StockDetailPage, PortfolioPage, ValidationPage
    components/           RangeSelector, StarButton, TradePanel
```

## Deploying somewhere reachable from your phone

See [DEPLOY.md](DEPLOY.md) for step-by-step instructions for Render + Supabase
+ Vercel (all free tiers). The short version:

1. Provision a Postgres database (Supabase / Neon).
2. From your laptop, point at it and run `alembic upgrade head` once.
3. Deploy the backend to Render, frontend to Vercel. Set `ADMIN_TOKEN` to
   lock down `/api/admin/*` once anything outside localhost can reach it.

## Roadmap beyond Phase 1

Designed-for-but-deferred work, in rough priority order:

1. **More signals**: Truth Social political signal; re-activate WSB if Reddit access reopens; tighten the loose yfinance per-ticker news matching.
2. **Backtest UI**: "if you'd traded the signal 90 days ago, your portfolio would look like…"
3. **ML upgrade**: train on the `daily_score_snapshots` history (which is the entire point of building snapshot persistence on day one).
4. **Leaderboard** once multi-user has real users.

Already shipped since the original Phase 1 spec: news sentiment (VADER), StockTwits
social sentiment, GDELT geopolitical tone, Finnhub insider activity, Postgres +
Alembic, watchlists, score-crossing alerts + notifications, invite-only registration,
and a verified Pluto tier (commission-free across the universe).

## Known limitations

- yfinance is unofficial and Yahoo regularly changes endpoints. `yfinance>=1.3` plus `curl-cffi` is required (0.2.x is silently broken). If ingestion suddenly returns 0 rows, upgrade yfinance first.
- Prices are end-of-day, not intraday. Fine for a paper-trading game, not for any real-money use (good — there is none).
- Pluto-tier classifications were verified against pluto.markets (2026-05-12): Pluto charges no commission on any stock or ETF, so every tradeable name in the universe is `commission_free`; indices are `not_listed`.
- Yahoo's per-ticker `.news` is loose and occasionally returns only-tangentially-related headlines; tightening the filter is a TODO.
