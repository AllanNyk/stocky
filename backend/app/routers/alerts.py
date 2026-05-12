from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AlertCondition, AlertRule, Notification, Stock, User
from app.security import current_user

router = APIRouter(prefix="/api", tags=["alerts"])


class AlertRuleIn(BaseModel):
    ticker: str
    condition: str = Field(pattern="^(score_crosses_above|score_crosses_below)$")
    threshold: float = Field(ge=0, le=100)


class AlertRuleOut(BaseModel):
    id: int
    ticker: str
    name: str
    condition: str
    threshold: float
    active: bool
    last_observed_score: float | None
    created_at: str


class NotificationOut(BaseModel):
    id: int
    title: str
    body: str
    ticker: str | None
    is_read: bool
    created_at: str


@router.get("/alerts", response_model=list[AlertRuleOut])
def list_alerts(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[AlertRuleOut]:
    rules = (
        db.query(AlertRule)
        .filter(AlertRule.user_id == user.id)
        .order_by(desc(AlertRule.created_at))
        .all()
    )
    out: list[AlertRuleOut] = []
    for r in rules:
        stock = db.query(Stock).get(r.stock_id)
        out.append(AlertRuleOut(
            id=r.id,
            ticker=stock.ticker,
            name=stock.name,
            condition=r.condition,
            threshold=r.threshold,
            active=r.active,
            last_observed_score=r.last_observed_score,
            created_at=r.created_at.isoformat(),
        ))
    return out


@router.post("/alerts", response_model=AlertRuleOut, status_code=status.HTTP_201_CREATED)
def create_alert(
    body: AlertRuleIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> AlertRuleOut:
    stock = db.query(Stock).filter(Stock.ticker == body.ticker).one_or_none()
    if stock is None:
        raise HTTPException(404, f"unknown ticker {body.ticker!r}")
    rule = AlertRule(
        user_id=user.id,
        stock_id=stock.id,
        condition=body.condition,
        threshold=body.threshold,
        active=True,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return AlertRuleOut(
        id=rule.id,
        ticker=stock.ticker,
        name=stock.name,
        condition=rule.condition,
        threshold=rule.threshold,
        active=rule.active,
        last_observed_score=rule.last_observed_score,
        created_at=rule.created_at.isoformat(),
    )


@router.delete("/alerts/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert(
    rule_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> None:
    deleted = (
        db.query(AlertRule)
        .filter(AlertRule.id == rule_id, AlertRule.user_id == user.id)
        .delete()
    )
    db.commit()
    if deleted == 0:
        raise HTTPException(404, "alert not found")
    return None


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(
    unread_only: bool = False,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[NotificationOut]:
    q = db.query(Notification).filter(Notification.user_id == user.id)
    if unread_only:
        q = q.filter(Notification.is_read.is_(False))
    rows = q.order_by(desc(Notification.created_at)).limit(100).all()
    out: list[NotificationOut] = []
    for n in rows:
        ticker: str | None = None
        if n.stock_id:
            s = db.query(Stock).get(n.stock_id)
            ticker = s.ticker if s else None
        out.append(NotificationOut(
            id=n.id,
            title=n.title,
            body=n.body,
            ticker=ticker,
            is_read=n.is_read,
            created_at=n.created_at.isoformat(),
        ))
    return out


@router.post("/notifications/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_read(
    notification_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> None:
    n = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user.id)
        .one_or_none()
    )
    if n is None:
        raise HTTPException(404, "notification not found")
    n.is_read = True
    db.commit()
    return None


@router.post("/notifications/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_read(user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    db.query(Notification).filter(
        Notification.user_id == user.id, Notification.is_read.is_(False)
    ).update({Notification.is_read: True})
    db.commit()
    return None
