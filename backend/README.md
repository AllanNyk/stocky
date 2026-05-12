# Stocky backend

FastAPI service. Phase 1 uses SQLite for zero-friction dev; swap `DATABASE_URL` to Postgres later.

## Dev setup (Windows / PowerShell)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

Health check: http://localhost:8000/api/health
API docs: http://localhost:8000/docs
