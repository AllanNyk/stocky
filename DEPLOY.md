# Stocky deploy guide

Phase 1 ran on localhost with SQLite. To put Stocky somewhere your phone can reach,
you need a Postgres database, a Python host that runs the backend, and a static host
that serves the React frontend. Every part has a free tier.

## What you need before you start

- A **GitHub account** to push this repo to (the hosts pull from there)
- A **Postgres database**. Recommended: [Supabase](https://supabase.com) (500 MB free)
  or [Neon](https://neon.tech) (3 GB free). Either gives you a connection string like
  `postgresql://USER:PASS@HOST:5432/DBNAME?sslmode=require`.
- A **backend host**. Recommended: [Render](https://render.com) (free web service tier,
  spins down when idle), [Fly.io](https://fly.io), or [Railway](https://railway.app).
- A **frontend host**. Easiest: [Vercel](https://vercel.com) or [Netlify](https://netlify.com).
- (Optional) The Reddit / Finnhub API keys if you want the alt-data signals live
  in production too. They degrade gracefully if absent.

---

## 1. Push the repo to GitHub

```powershell
cd C:\myapps\stocky
gh repo create stocky --private --source=. --remote=origin --push
```
(Install GitHub CLI from <https://cli.github.com> if you don't have `gh`. Or do the
classic `git remote add origin … && git push -u origin main` flow.)

## 2. Provision the database

Create a Postgres database on Supabase or Neon. Copy the **connection pooler URL**
(both providers show one in their dashboard). It should look like:
```
postgresql+psycopg://postgres.xxx:PASSWORD@aws-0-eu-central-1.pooler.supabase.com:5432/postgres
```
Two things to verify:
- The URL uses the `+psycopg` driver prefix (psycopg 3). If your provider gives the
  bare `postgresql://`, add `+psycopg` after `postgresql`.
- `sslmode=require` is in the query string for Supabase / Neon.

## 3. Apply the schema once

From your local machine (with the venv active) point at the new database and run:
```powershell
cd C:\myapps\stocky\backend
$env:DATABASE_URL = "postgresql+psycopg://…your URL…"
.\.venv\Scripts\python.exe -m alembic upgrade head
Remove-Item Env:DATABASE_URL
```
You should see one revision applied (`1003dafc7073, initial schema`). Future schema
changes are: `alembic revision --autogenerate -m "describe change"`, commit, then on
deploy run `alembic upgrade head` again.

## 4. Deploy the backend

On **Render** (the path I recommend for first deploy):

1. New Web Service → connect your GitHub repo.
2. Root directory: `backend`.
3. Build command:
   ```
   pip install -r requirements.txt
   ```
4. Start command:
   ```
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
5. Environment variables (Render → Environment):
   ```
   DATABASE_URL = postgresql+psycopg://…
   JWT_SECRET = <generate a long random string>
   ADMIN_TOKEN = <generate another long random string>
   CORS_ORIGINS = https://your-frontend-url.vercel.app
   REDDIT_CLIENT_ID = …  (optional)
   REDDIT_CLIENT_SECRET = …  (optional)
   REDDIT_USER_AGENT = stocky-prod/0.1 by u/<your reddit username>
   FINNHUB_API_KEY = …  (optional)
   ```
6. Deploy. After it's live, hit `https://your-backend.onrender.com/api/health` to verify.

> The Render free tier spins the service down after ~15 min idle. First request after
> cold start takes ~30s. APScheduler jobs (price refresh, snapshot) won't run while
> the service is asleep — for serious use, upgrade to a paid tier or move jobs to
> Render Cron Jobs that hit the `/api/admin/refresh-*` endpoints with the
> `X-Admin-Token: $ADMIN_TOKEN` header.

## 5. Deploy the frontend

On **Vercel**:

1. New Project → import the GitHub repo.
2. Root directory: `frontend`.
3. Framework preset: Vite.
4. Build command: `npm run build`. Output directory: `dist`.
5. Environment variable:
   ```
   VITE_API_BASE = https://your-backend.onrender.com
   ```
6. Deploy. After it's live, update the backend's `CORS_ORIGINS` to match the Vercel URL.

## 6. Seed the universe + first data

Once both services are up, prime the database. From your laptop with the admin token:

```powershell
$h = @{ "X-Admin-Token" = "your-admin-token" }
Invoke-RestMethod -Method POST -Headers $h "https://your-backend.onrender.com/api/admin/refresh-fx"
Invoke-RestMethod -Method POST -Headers $h "https://your-backend.onrender.com/api/admin/refresh-prices?period=5y"
Invoke-RestMethod -Method POST -Headers $h "https://your-backend.onrender.com/api/admin/refresh-news"
Invoke-RestMethod -Method POST -Headers $h "https://your-backend.onrender.com/api/admin/refresh-gdelt"
Invoke-RestMethod -Method POST -Headers $h "https://your-backend.onrender.com/api/validation/run-backtest?days=90"
```

The universe seed runs automatically on every backend startup, so all 116 stocks will
be in the database already; the admin calls above fill them with prices, news, and
geopolitical data.

## Future schema changes

```powershell
cd backend
# 1. Edit ORM models
# 2. Generate migration:
.\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "add new column X"
# 3. Inspect the generated file in alembic/versions/
# 4. Commit it
# 5. Apply locally (dev) and in prod:
.\.venv\Scripts\python.exe -m alembic upgrade head
```

The `apply_additive_migrations()` helper in `app/db.py` remains for dev SQLite
convenience but Alembic is authoritative once you're on Postgres.

## Cost

For a personal-use app with ~1 active user, all of the above is free. Render free tier
is fine if you accept cold-start latency. If you want the daily scheduler to actually
run on time, the cheapest reliable path is Render's $7/month "starter" tier on the
backend; everything else stays free.
