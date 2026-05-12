"""Paper-trading engine: execute mock buys/sells at latest close in DKK.

Pluto-tier business rules (placeholder, refine per real Pluto fee schedule):
- commission_free: 0 DKK fee
- standard_fee: 29 DKK per trade (rough Nordnet/Saxo retail fee)
- not_listed: cannot be traded (benchmarks)
"""

from __future__ import annotations

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import PlutoTier, Position, PriceHistory, Stock, Trade, TradeSide, User

FEE_BY_TIER = {
    PlutoTier.COMMISSION_FREE.value: 0.0,
    PlutoTier.STANDARD_FEE.value: 29.0,
    PlutoTier.NOT_LISTED.value: None,  # None = not tradeable
}


class TradingError(Exception):
    """Raised for any paper-trading business-rule violation."""


def fee_for(stock: Stock) -> float:
    fee = FEE_BY_TIER.get(stock.pluto_tier)
    if fee is None:
        raise TradingError(f"{stock.ticker} is not tradeable (tier={stock.pluto_tier})")
    return fee


def latest_close_dkk(db: Session, stock: Stock) -> float:
    last = (
        db.query(PriceHistory)
        .filter(PriceHistory.stock_id == stock.id)
        .order_by(desc(PriceHistory.trade_date))
        .first()
    )
    if last is None:
        raise TradingError(f"no price history for {stock.ticker}")
    return last.close_dkk


def get_or_create_position(db: Session, user: User, stock: Stock) -> Position:
    pos = (
        db.query(Position)
        .filter(Position.user_id == user.id, Position.stock_id == stock.id)
        .one_or_none()
    )
    if pos is None:
        pos = Position(user_id=user.id, stock_id=stock.id, quantity=0.0, avg_cost_dkk=0.0)
        db.add(pos)
        db.flush()
    return pos


def execute_buy(db: Session, user: User, stock: Stock, quantity: float) -> Trade:
    if quantity <= 0:
        raise TradingError("buy quantity must be > 0")
    price = latest_close_dkk(db, stock)
    fee = fee_for(stock)
    gross = price * quantity
    total_cost = gross + fee
    if total_cost > user.cash_balance_dkk + 1e-6:
        raise TradingError(
            f"insufficient cash: need {total_cost:.2f} DKK, have {user.cash_balance_dkk:.2f}"
        )

    pos = get_or_create_position(db, user, stock)
    new_qty = pos.quantity + quantity
    pos.avg_cost_dkk = (pos.avg_cost_dkk * pos.quantity + gross) / new_qty if new_qty > 0 else 0.0
    pos.quantity = new_qty
    user.cash_balance_dkk -= total_cost

    trade = Trade(
        user_id=user.id,
        stock_id=stock.id,
        side=TradeSide.BUY.value,
        quantity=quantity,
        price_dkk=price,
        fee_dkk=fee,
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade


def execute_sell(db: Session, user: User, stock: Stock, quantity: float) -> Trade:
    if quantity <= 0:
        raise TradingError("sell quantity must be > 0")
    pos = (
        db.query(Position)
        .filter(Position.user_id == user.id, Position.stock_id == stock.id)
        .one_or_none()
    )
    if pos is None or pos.quantity < quantity - 1e-6:
        held = pos.quantity if pos else 0
        raise TradingError(f"cannot sell {quantity} {stock.ticker} — holding {held}")

    price = latest_close_dkk(db, stock)
    fee = fee_for(stock)
    proceeds = price * quantity - fee
    pos.quantity -= quantity
    if pos.quantity < 1e-9:
        pos.quantity = 0.0
        pos.avg_cost_dkk = 0.0
    user.cash_balance_dkk += proceeds

    trade = Trade(
        user_id=user.id,
        stock_id=stock.id,
        side=TradeSide.SELL.value,
        quantity=quantity,
        price_dkk=price,
        fee_dkk=fee,
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade


def portfolio_summary(db: Session, user: User) -> dict:
    positions = db.query(Position).filter(Position.user_id == user.id, Position.quantity > 0).all()
    rows: list[dict] = []
    holdings_value = 0.0
    cost_basis = 0.0
    for pos in positions:
        stock = db.query(Stock).get(pos.stock_id)
        current_price = latest_close_dkk(db, stock)
        market_value = current_price * pos.quantity
        position_cost = pos.avg_cost_dkk * pos.quantity
        unrealized = market_value - position_cost
        holdings_value += market_value
        cost_basis += position_cost
        rows.append({
            "ticker": stock.ticker,
            "name": stock.name,
            "currency": stock.currency,
            "pluto_tier": stock.pluto_tier,
            "quantity": pos.quantity,
            "avg_cost_dkk": pos.avg_cost_dkk,
            "current_price_dkk": current_price,
            "market_value_dkk": market_value,
            "unrealized_pnl_dkk": unrealized,
            "unrealized_pnl_pct": (unrealized / position_cost * 100.0) if position_cost else 0.0,
        })
    return {
        "cash_dkk": user.cash_balance_dkk,
        "holdings_value_dkk": holdings_value,
        "total_value_dkk": user.cash_balance_dkk + holdings_value,
        "cost_basis_dkk": cost_basis,
        "total_unrealized_pnl_dkk": holdings_value - cost_basis,
        "positions": rows,
    }
