"""Signal protocol + helpers.

Every signal returns a SignalResult: a 0-100 score, a confidence in [0,1], and
human-readable evidence the UI can render in the breakdown view. Signals are
pure functions of (db, stock) so they're easy to compose into a composite.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
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

    def compute(self, db: Session, stock: Stock) -> SignalResult: ...


def clip(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def empty_result(reason: str) -> SignalResult:
    return SignalResult(score=50.0, confidence=0.0, evidence={}, error=reason)
