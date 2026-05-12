"""Alert rule evaluation: check active rules against the latest composite score.

`check_and_fire_alerts` is called from the daily snapshot job after fresh scores
have been persisted. For each active rule we compare:
  - new score (just computed)
  - last_observed_score (what we saw on the previous evaluation)
to detect a *crossing*. We never fire on the first observation (when
last_observed_score is None) — that prevents a burst of bogus alerts the day
a user creates a bunch of rules.
"""

from __future__ import annotations

from datetime import date
from logging import getLogger

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import AlertCondition, AlertRule, DailyScoreSnapshot, Notification, Stock

log = getLogger(__name__)


def _crossed_above(prev: float | None, now: float, threshold: float) -> bool:
    if prev is None:
        return False
    return prev < threshold <= now


def _crossed_below(prev: float | None, now: float, threshold: float) -> bool:
    if prev is None:
        return False
    return prev > threshold >= now


def check_and_fire_alerts(db: Session, on_date: date | None = None) -> dict:
    """Evaluate every active AlertRule against today's snapshot. Create Notifications
    for triggered rules. Idempotent within a day — last_observed_score acts as state."""
    target = on_date or date.today()
    rules = db.query(AlertRule).filter(AlertRule.active.is_(True)).all()

    fired = 0
    evaluated = 0
    for rule in rules:
        snap = (
            db.query(DailyScoreSnapshot)
            .filter(
                DailyScoreSnapshot.stock_id == rule.stock_id,
                DailyScoreSnapshot.snapshot_date <= target,
            )
            .order_by(desc(DailyScoreSnapshot.snapshot_date))
            .first()
        )
        if snap is None:
            continue
        evaluated += 1
        prev = rule.last_observed_score
        now = snap.composite_score

        triggered = False
        if rule.condition == AlertCondition.SCORE_CROSSES_ABOVE.value:
            triggered = _crossed_above(prev, now, rule.threshold)
        elif rule.condition == AlertCondition.SCORE_CROSSES_BELOW.value:
            triggered = _crossed_below(prev, now, rule.threshold)

        if triggered:
            stock = db.query(Stock).get(rule.stock_id)
            direction = "above" if "above" in rule.condition else "below"
            db.add(Notification(
                user_id=rule.user_id,
                rule_id=rule.id,
                stock_id=rule.stock_id,
                title=f"{stock.ticker} crossed {direction} {rule.threshold:.0f}",
                body=(
                    f"{stock.name}'s composite score moved from "
                    f"{prev:.1f} to {now:.1f} on {snap.snapshot_date.isoformat()}."
                ),
            ))
            fired += 1

        rule.last_observed_score = now

    db.commit()
    return {"rules_evaluated": evaluated, "notifications_fired": fired}
