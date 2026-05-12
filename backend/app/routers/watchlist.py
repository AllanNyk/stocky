from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Stock, User, WatchlistEntry
from app.security import current_user

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


@router.get("")
def list_watchlist(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[str]:
    """Return the list of tickers the current user has starred."""
    entries = (
        db.query(WatchlistEntry, Stock)
        .join(Stock, Stock.id == WatchlistEntry.stock_id)
        .filter(WatchlistEntry.user_id == user.id)
        .order_by(WatchlistEntry.added_at)
        .all()
    )
    return [s.ticker for _w, s in entries]


@router.post("/{ticker}", status_code=status.HTTP_201_CREATED)
def add_to_watchlist(
    ticker: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    stock = db.query(Stock).filter(Stock.ticker == ticker).one_or_none()
    if stock is None:
        raise HTTPException(404, f"unknown ticker {ticker!r}")
    existing = (
        db.query(WatchlistEntry)
        .filter(WatchlistEntry.user_id == user.id, WatchlistEntry.stock_id == stock.id)
        .one_or_none()
    )
    if existing is not None:
        return {"ticker": ticker, "already_watched": True}
    db.add(WatchlistEntry(user_id=user.id, stock_id=stock.id))
    db.commit()
    return {"ticker": ticker, "already_watched": False}


@router.delete("/{ticker}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_watchlist(
    ticker: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> None:
    stock = db.query(Stock).filter(Stock.ticker == ticker).one_or_none()
    if stock is None:
        raise HTTPException(404, f"unknown ticker {ticker!r}")
    deleted = (
        db.query(WatchlistEntry)
        .filter(WatchlistEntry.user_id == user.id, WatchlistEntry.stock_id == stock.id)
        .delete()
    )
    db.commit()
    if deleted == 0:
        raise HTTPException(404, "not in watchlist")
    return None
