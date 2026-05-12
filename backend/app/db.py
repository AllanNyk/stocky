from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Minimal additive migrations for Phase 1/2 hand-off. Replace with Alembic once Postgres lands. ---

_ADDITIVE_COLUMNS: list[tuple[str, str, str]] = [
    # (table, column_name, ALTER ADD COLUMN body — types/defaults compatible with SQLite + Postgres)
    ("stocks", "wsb_aliases", "VARCHAR(200)"),
    ("stocks", "country_code", "VARCHAR(4)"),
]


def apply_additive_migrations() -> None:
    """Add any new columns the ORM declares that aren't yet in the live table.

    Only handles additive changes (`ALTER TABLE ... ADD COLUMN`); destructive or
    type-altering migrations must go through Alembic. Idempotent — safe on every boot.
    """
    insp = inspect(engine)
    with engine.begin() as conn:
        for table, column, body in _ADDITIVE_COLUMNS:
            if not insp.has_table(table):
                continue  # create_all will handle a brand-new table
            existing = {c["name"] for c in insp.get_columns(table)}
            if column in existing:
                continue
            conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {body}'))
