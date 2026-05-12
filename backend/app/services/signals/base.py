"""Signal protocol + helpers.

Every signal returns a SignalResult: a 0-100 score, a confidence in [0,1], and
human-readable evidence the UI can render in the breakdown view. Signals are
pure functions of (db, stock, as_of_date) so they're easy to compose into a
composite — and so the same code path drives both live scoring and historical
backtests.

`as_of` is None for live scoring (= "use latest available data") and a concrete
date for backtests. Signals that don't have meaningful historical inputs
(currently P/E percentile and WSB mention-delta) return confidence=0 for past
dates rather than fabricating numbers from current state.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date as _date
from typing import Protocol

from sqlalchemy.orm import Session

from app.models import Stock


@dataclass
class SignalResult:
    score: float  # 0-100, where 100 = strongest bullish reading
    confidence: float  # 0-1, how much we trust this signal for this stock right now
    evidence: dict = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class Signal(Protocol):
    name: str

    def compute(self, db: Session, stock: Stock, as_of: _date | None = None) -> SignalResult: ...


def clip(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def empty_result(reason: str) -> SignalResult:
    return SignalResult(score=50.0, confidence=0.0, evidence={}, error=reason)
