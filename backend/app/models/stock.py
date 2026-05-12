from datetime import date, datetime
from enum import Enum

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class PlutoTier(str, Enum):
    COMMISSION_FREE = "commission_free"
    STANDARD_FEE = "standard_fee"
    NOT_LISTED = "not_listed"


class Stock(Base):
    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    exchange: Mapped[str] = mapped_column(String(20))
    currency: Mapped[str] = mapped_column(String(3))
    sector: Mapped[str | None] = mapped_column(String(80), nullable=True)
    pluto_tier: Mapped[str] = mapped_column(String(20), default=PlutoTier.NOT_LISTED.value)
    is_benchmark: Mapped[bool] = mapped_column(default=False)

    pe_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_cap: Mapped[float | None] = mapped_column(Float, nullable=True)
    fundamentals_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Pipe-separated list of how WSB / r/stocks users refer to this stock,
    # e.g. "NOVO|NVO|NovoNordisk" for NOVO-B.CO. Used for mention counting.
    wsb_aliases: Mapped[str | None] = mapped_column(String(200), nullable=True)

    prices: Mapped[list["PriceHistory"]] = relationship(back_populates="stock", cascade="all, delete-orphan")
    snapshots: Mapped[list["DailyScoreSnapshot"]] = relationship(back_populates="stock", cascade="all, delete-orphan")


class PriceHistory(Base):
    __tablename__ = "price_history"
    __table_args__ = (UniqueConstraint("stock_id", "trade_date", name="uq_price_stock_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), index=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    open: Mapped[float | None] = mapped_column(Float, nullable=True)
    high: Mapped[float | None] = mapped_column(Float, nullable=True)
    low: Mapped[float | None] = mapped_column(Float, nullable=True)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    close_dkk: Mapped[float] = mapped_column(Float)

    stock: Mapped[Stock] = relationship(back_populates="prices")


class FxRate(Base):
    __tablename__ = "fx_rates"
    __table_args__ = (UniqueConstraint("currency", "rate_date", name="uq_fx_currency_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    currency: Mapped[str] = mapped_column(String(3), index=True)
    rate_date: Mapped[date] = mapped_column(Date, index=True)
    to_dkk: Mapped[float] = mapped_column(Float)


class RedditMentionCount(Base):
    """Daily mention counts per stock across watched subreddits.

    `count` is the total number of posts (title or selftext) on `mention_date`
    that contained any of the stock's WSB aliases. `subreddits_seen` is a
    pipe-separated list of subreddits that contributed at least one mention.
    """

    __tablename__ = "reddit_mention_counts"
    __table_args__ = (UniqueConstraint("stock_id", "mention_date", name="uq_reddit_stock_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), index=True)
    mention_date: Mapped[date] = mapped_column(Date, index=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
    subreddits_seen: Mapped[str | None] = mapped_column(String(200), nullable=True)
