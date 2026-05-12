from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import Base, SessionLocal, apply_additive_migrations, engine
from app import models  # noqa: F401  ensures model classes register with Base.metadata
from app.routers import admin, auth, portfolio, stocks, validation
from app.scheduler import build_scheduler
from app.seeds.universe import seed_universe


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    apply_additive_migrations()
    with SessionLocal() as db:
        seed_universe(db)
    sched = build_scheduler()
    sched.start()
    try:
        yield
    finally:
        sched.shutdown(wait=False)


app = FastAPI(title="Stocky", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(stocks.router)
app.include_router(validation.router)
app.include_router(portfolio.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
