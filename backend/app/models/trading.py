from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class TradeSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class Position(Base):
    """A user's holdings of a single stock. Quantity can be fractional."""

    __tablename__ = "positions"
    __table_args__ = (UniqueConstraint("user_id", "stock_id", name="uq_position_user_stock"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), index=True)
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    avg_cost_dkk: Mapped[float] = mapped_column(Float, default=0.0)

    user = relationship("User", back_populates="positions")
    stock = relationship("Stock")


class Trade(Base):
    """Append-only ledger of paper trades. Re-derivable history of every position move."""

    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), index=True)
    side: Mapped[str] = mapped_column(String(4))
    quantity: Mapped[float] = mapped_column(Float)
    price_dkk: Mapped[float] = mapped_column(Float)
    fee_dkk: Mapped[float] = mapped_column(Float, default=0.0)
    executed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="trades")
    stock = relationship("Stock")
