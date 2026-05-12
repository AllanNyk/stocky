# Stocky — Claude development notes

This file is read by Claude Code at the start of every session in this repo, so put
durable project knowledge here (not in chat). Update when conventions change.
For your local-only preferences (style, tooling tics, things that aren't project
truth), edit `~/.claude/CLAUDE.md` instead — that one isn't checked in.

---

## What Stocky is

A paper-trading web app for US + Nordic stocks with a transparent 7-signal
prediction score. Base currency is **DKK**. No real money is involved at any
point, by design — there is no broker integration and there never will be.

**Three feature pillars** (per the original spec):
1. Live(ish) market view (15-min-delayed prices via yfinance is fine).
2. Composite prediction score (0–100) per stock, with a per-signal breakdown.
3. Paper-trading game with mock cash, persistent portfolio, P&L.

Plus a continuous **forward-test loop**: every daily snapshot freezes scores +
prices, and the validation dashboard computes 1d / 7d / 30d / 90d realized
returns of virtual portfolios that buy the top-5 / threshold-70 picks each day.

---

## Stack at a glance

- **Backend**: Python 3.13 · FastAPI · SQLAlchemy 2 · SQLite (dev) · APScheduler
- **Frontend**: React 19 + TypeScript · Vite · React Router · Recharts
- **Data sources** (all free): yfinance (prices, fundamentals, news) · Reddit API
  via praw (creds optional) · GDELT 2.0 DOC API · VADER for headline sentiment
- **Auth**: JWT, bcrypt direct (passlib is unmaintained — do not reintroduce)

---

## Run it

```powershell
# Backend (Terminal 1)
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload

# Frontend (Terminal 2)
cd frontend
npm run dev
```

Backend: <http://localhost:8000> (Swagger at `/docs`) · Frontend: <http://localhost:5173>

First-time setup is in the project [README.md](README.md). After deps are
installed, restarting the backend re-seeds the universe + creates new tables
automatically via the lifespan hook + `apply_additive_migrations()`.

---

## The 7 signals (in `backend/app/services/signals/`)

Each signal implements `compute(db, stock, as_of=None) -> SignalResult` and
returns a 0-100 score + confidence in [0, 1] + evidence dict. Composite is a
confidence-weighted average; signals with confidence 0 simply drop out and the
remaining weights renormalize.

| Signal | Source | Backtest? | Weight |
|---|---|---|---|
| `pe_percentile` | yfinance fundamentals (sector-relative) | No (no historical PE) | 0.15 |
| `momentum_50d` | PriceHistory | Yes | 0.20 |
| `percentile_52w` | PriceHistory (1y window) | Yes | 0.15 |
| `volume_momentum` | PriceHistory (5d vs 50d) | Yes | 0.10 |
| `wsb_mention_delta` | Reddit API (r/wallstreetbets, r/stocks, r/investing) | No (no historical scrape) | 0.10 |
| `news_sentiment` | yfinance.Ticker.news + VADER | No (yf.news isn't backdated) | 0.15 |
| `geopolitical_tone` | GDELT 2.0 country tone | Yes once we've been scraping a few days | 0.15 |

Weights live in `app/services/scoring.py::SIGNAL_WEIGHTS`. Sum must equal 1.0.

---

## Core conventions / invariants — don't break these

- **Never recompute historical scores from current data.** `DailyScoreSnapshot`
  freezes `composite_score` + `component_scores` + `price_at_snapshot_dkk` at
  compute time. Backtest passes `as_of=date` through the entire chain
  (`score_stock` → `compute_signals` → each signal). Signals that don't have
  historical backdata (P/E, WSB, news) MUST return `confidence=0` when `as_of`
  is in the past — never fabricate from current state. This honesty is the
  whole point of the validation dashboard.
- **DKK is the portfolio base currency.** `PriceHistory` stores both `close`
  (native) and `close_dkk` (converted at ingest time). All trade prices,
  positions, and P&L are in DKK. FX rates live in `FxRate` per currency per day.
- **Trades are append-only.** `Trade` is the source of truth; `Position` is a
  derived current-state cache (`quantity`, `avg_cost_dkk`). If they ever
  disagree, rebuild positions from the trade log.
- **Pluto tiers** drive trade fees in `services/trading.py::FEE_BY_TIER`.
  Verified against pluto.markets 2026-05-12: Pluto charges *no commission* on
  any stock or ETF — fees apply only to crypto (1%), extended-hours (0.1%),
  FX (0.15%). So every tradeable name in our universe is `commission_free`.
  Indices are `not_listed` (you can't buy an index directly anyway).
  `standard_fee` is kept as a schema option in case the broker model changes
  or a second broker is added; currently unused.
- **Schema changes** — Alembic is authoritative going forward
  (`backend/alembic/versions/`). On dev SQLite we *also* run
  `Base.metadata.create_all` + the legacy `apply_additive_migrations` helper
  in `app/db.py::_ADDITIVE_COLUMNS` on startup, so devs don't need to remember
  to run `alembic upgrade head` after every model edit. On Postgres / prod,
  Alembic is the only mechanism — run `alembic upgrade head` as a deploy step
  (see `DEPLOY.md`). Workflow for a new schema change:
  1. Edit ORM model.
  2. `cd backend && python -m alembic revision --autogenerate -m "describe change"`
  3. Inspect the generated file in `alembic/versions/`; tweak if needed.
  4. Commit it. Local SQLite picks up the change via `create_all` /
     `apply_additive_migrations`; prod picks it up via `alembic upgrade head`.

---

## Known gotchas

- **yfinance >= 1.3.0 is mandatory.** Versions 0.2.x silently return empty data
  against current Yahoo endpoints (the `curl_cffi` dep in 1.x bypasses Yahoo's
  Cloudflare-style blocking). If every ticker suddenly returns 0 rows, upgrade
  yfinance first — don't assume tickers are wrong.
- **GDELT rate-limits at "1 request per 5 seconds".** `services/gdelt.py` uses
  6s spacing + retry-on-429 with backoff. A burst will fail; the daily
  scheduled run handles it because it has all night.
- **Yahoo's per-ticker `.news` is loose** — sometimes returns headlines that
  only tangentially mention the ticker (we saw an "AAPL scammer" headline that
  was about a Chicago scam victim). Tightening the filter is a TODO.
- **`^OMXS30` (Stockholm 30 index) does not exist on Yahoo** — use `^OMXSPI`
  (Stockholm All-Share) instead. Already in the seed.
- **`/api/admin/*` and `/api/validation/run-*` are unauthenticated** for
  local-dev convenience. Lock them before deploying anywhere reachable.
- **Vite dev server occasionally dies silently.** Restart with `npm run dev`.
  Frontend production build is healthy — verify with `npm run build`.
- **PowerShell quirks**: stderr-to-stdout from native cmds shows as
  `NativeCommandError` (harmless). `Invoke-WebRequest` for DELETE in
  non-interactive mode fails; use `Invoke-RestMethod` instead.

---

## File map (the parts that matter)

```
backend/app/
  main.py                  # FastAPI app, lifespan (create_all + migrations + seed + scheduler)
  config.py                # Settings (.env-driven, pydantic-settings)
  db.py                    # Engine, SessionLocal, apply_additive_migrations
  security.py              # bcrypt + JWT (NOT passlib — see Conventions)
  scheduler.py             # APScheduler jobs (price 23:00, reddit 23:05, news 23:07, gdelt 23:08, snapshot 23:10 CET)
  models/                  # SQLAlchemy ORM, one file per concept
  routers/                 # FastAPI endpoint groups (admin, auth, stocks, portfolio, validation, watchlist)
  services/
    ingestion.py           # yfinance prices + fundamentals
    fx.py                  # daily DKK FX rates
    news_sentiment.py      # yfinance news + VADER
    reddit.py              # praw mention scraper
    gdelt.py               # GDELT 2.0 country tone
    scoring.py             # composite + SIGNAL_WEIGHTS (the heart of the model)
    snapshots.py           # daily snapshot + backtest replay + forward-return queries
    trading.py             # paper-trading engine (fees by Pluto tier)
    signals/               # one file per signal
  seeds/universe.py        # the 30 stocks + 3 benchmarks (hand-curated)

frontend/src/
  api.ts                   # Typed fetch client + endpoint surface
  auth.tsx                 # AuthProvider context, JWT in localStorage
  watchlist.tsx            # WatchlistProvider context, optimistic toggle
  format.ts                # fmtDkk, fmtPct, scoreColor, tierColor helpers
  App.tsx                  # Routes + shell (sidebar nav)
  pages/                   # LoginPage, MarketPage, StockDetailPage, PortfolioPage, ValidationPage
  components/              # RangeSelector, StarButton, TradePanel
```

---

## What CLAUDE.md files are for, broadly

Claude Code automatically reads any `CLAUDE.md` files in the current working
directory tree (and `~/.claude/CLAUDE.md` for user-wide settings) at the start
of every session, and treats their contents as persistent context.

Use the **project-level CLAUDE.md** (this file) for things every contributor —
human or Claude — needs to know to be productive in this repo:
- What the project is, in one paragraph
- Stack + run commands
- Conventions and invariants ("never do X", "always do Y")
- Known gotchas / footguns ("dep version Z is required because…")
- File map of where things live
- Anything that would otherwise need to be re-discovered each session

Don't put in CLAUDE.md:
- Things that change every day (use git/issues for transient state)
- Personal preferences (those go in `~/.claude/CLAUDE.md`)
- Anything secret (this file is committed)
- A blow-by-blow changelog (`git log` exists)

This particular file is checked in so it travels with the repo — pulling the
repo on another machine, or another contributor opening it, gets the same
context Claude does.
