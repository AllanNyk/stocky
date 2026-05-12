from datetime import date
from enum import Enum

from sqlalchemy import JSON, Date, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class PickStrategy(str, Enum):
    TOP5_EQUAL_WEIGHT = "top5_equal_weight"
    THRESHOLD_70 = "threshold_70"


class DailyScoreSnapshot(Base):
    """Composite score + components for one stock on one day.

    Persisted at the moment of computation — never recomputed retroactively (would leak future info).
    """

    __tablename__ = "daily_score_snapshots"
    __table_args__ = (UniqueConstraint("stock_id", "snapshot_date", name="uq_score_stock_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, index=True)
    composite_score: Mapped[float] = mapped_column(Float)
    component_scores: Mapped[dict] = mapped_column(JSON, default=dict)
    price_at_snapshot_dkk: Mapped[float] = mapped_column(Float)

    stock = relationship("Stock", back_populates="snapshots")


class ModelPortfolioPick(Base):
    """One stock 'bought' by a virtual model-portfolio strategy on a given day.

    `entry_price_dkk` is locked at snapshot time. Forward returns are computed on read by
    joining with PriceHistory at the desired horizon.
    """

    __tablename__ = "model_portfolio_picks"
    __table_args__ = (
        UniqueConstraint("snapshot_date", "pick_strategy", "stock_id", name="uq_pick_date_strategy_stock"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_date: Mapped[date] = mapped_column(Date, index=True)
    pick_strategy: Mapped[str] = mapped_column(String(40), index=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), index=True)
    composite_score: Mapped[float] = mapped_column(Float)
    weight: Mapped[float] = mapped_column(Float)
    entry_price_dkk: Mapped[float] = mapped_column(Float)
