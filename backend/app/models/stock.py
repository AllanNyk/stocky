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
    # FIPS country code of the primary listing exchange (US, DA, SW, NO, FI, ...).
    # Different from ISO 3166 — GDELT uses FIPS, so we store FIPS for easy joins.
    country_code: Mapped[str | None] = mapped_column(String(4), nullable=True)
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


class CountryToneScore(Base):
    """Daily GDELT mean tone per FIPS country code.

    GDELT's "tone" is roughly the average sentiment of articles mentioning a country
    in [-10, +10] (negative = bad news, positive = good). Wars, financial crises,
    and political turmoil drive tone sharply negative; routine days hover near 0.
    """

    __tablename__ = "country_tone_scores"
    __table_args__ = (UniqueConstraint("country_code", "score_date", name="uq_country_tone_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country_code: Mapped[str] = mapped_column(String(4), index=True)
    score_date: Mapped[date] = mapped_column(Date, index=True)
    mean_tone: Mapped[float] = mapped_column(Float)
    article_count: Mapped[int] = mapped_column(Integer, default=0)


class NewsHeadline(Base):
    """Individual news headline that passed our 'mentions the ticker' filter.

    Stored so the stock-detail page can surface the actual articles driving
    today's news_sentiment score, and so future analytics can correlate
    specific headlines with price moves.
    """

    __tablename__ = "news_headlines"
    __table_args__ = (UniqueConstraint("stock_id", "link", name="uq_news_headline_link"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    title: Mapped[str] = mapped_column(String(500))
    link: Mapped[str] = mapped_column(String(800))
    compound_score: Mapped[float] = mapped_column(Float)


class NewsSentimentScore(Base):
    """Daily aggregate of VADER sentiment over per-ticker news headlines.

    `mean_compound` is the average VADER compound score (in [-1, +1]) across
    `sample_size` headlines from the last 24h. `top_headline` captures the
    single most-extreme headline so the UI can show what's driving the signal.
    """

    __tablename__ = "news_sentiment_scores"
    __table_args__ = (UniqueConstraint("stock_id", "score_date", name="uq_news_stock_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), index=True)
    score_date: Mapped[date] = mapped_column(Date, index=True)
    mean_compound: Mapped[float] = mapped_column(Float, default=0.0)
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    top_headline: Mapped[str | None] = mapped_column(String(400), nullable=True)
    top_headline_score: Mapped[float | None] = mapped_column(Float, nullable=True)
