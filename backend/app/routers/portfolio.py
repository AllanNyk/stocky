from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Stock, Trade, User
from app.security import current_user
from app.services.trading import TradingError, execute_buy, execute_sell, portfolio_summary

router = APIRouter(prefix="/api", tags=["portfolio"])


class TradeIn(BaseModel):
    ticker: str
    side: str = Field(pattern="^(buy|sell)$")
    quantity: float = Field(gt=0)


class TradeOut(BaseModel):
    id: int
    ticker: str
    side: str
    quantity: float
    price_dkk: float
    fee_dkk: float
    executed_at: str


@router.get("/portfolio")
def get_portfolio(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    return portfolio_summary(db, user)


@router.post("/trade", response_model=TradeOut)
def trade(
    body: TradeIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> TradeOut:
    stock = db.query(Stock).filter(Stock.ticker == body.ticker).one_or_none()
    if stock is None:
        raise HTTPException(404, f"unknown ticker {body.ticker!r}")
    try:
        if body.side == "buy":
            t = execute_buy(db, user, stock, body.quantity)
        else:
            t = execute_sell(db, user, stock, body.quantity)
    except TradingError as e:
        raise HTTPException(400, str(e))
    return TradeOut(
        id=t.id,
        ticker=stock.ticker,
        side=t.side,
        quantity=t.quantity,
        price_dkk=t.price_dkk,
        fee_dkk=t.fee_dkk,
        executed_at=t.executed_at.isoformat(),
    )


@router.get("/trades", response_model=list[TradeOut])
def trade_history(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[TradeOut]:
    trades = (
        db.query(Trade)
        .filter(Trade.user_id == user.id)
        .order_by(desc(Trade.executed_at))
        .all()
    )
    out: list[TradeOut] = []
    for t in trades:
        stock = db.query(Stock).get(t.stock_id)
        out.append(TradeOut(
            id=t.id,
            ticker=stock.ticker,
            side=t.side,
            quantity=t.quantity,
            price_dkk=t.price_dkk,
            fee_dkk=t.fee_dkk,
            executed_at=t.executed_at.isoformat(),
        ))
    return out
