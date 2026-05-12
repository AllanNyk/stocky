"""Composite prediction score: weighted sum of individual signals.

Each signal returns a SignalResult; the composite weights the *score* by the signal's
declared weight, scaled by the signal's confidence. Signals that error get weight 0 and
the remaining weights re-normalize so the composite stays in [0, 100].
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Stock
from app.services.signals.base import SignalResult
from app.services.signals.momentum import Momentum50dSignal
from app.services.signals.pe_percentile import PEPercentileSignal

SIGNAL_WEIGHTS: dict[str, float] = {
    "pe_percentile": 0.5,
    "momentum_50d": 0.5,
}

SIGNALS = [
    PEPercentileSignal(),
    Momentum50dSignal(),
]


def compute_signals(db: Session, stock: Stock) -> dict[str, SignalResult]:
    out: dict[str, SignalResult] = {}
    for sig in SIGNALS:
        try:
            out[sig.name] = sig.compute(db, stock)
        except Exception as e:
            out[sig.name] = SignalResult(score=50.0, confidence=0.0, evidence={}, error=str(e))
    return out


def composite_score(signals: dict[str, SignalResult]) -> float:
    """Confidence-weighted average. Signals with 0 confidence (errored / no data) are skipped."""
    total_weight = 0.0
    weighted = 0.0
    for name, result in signals.items():
        w = SIGNAL_WEIGHTS.get(name, 0.0) * result.confidence
        if w <= 0:
            continue
        total_weight += w
        weighted += w * result.score
    if total_weight <= 0:
        return 50.0
    return weighted / total_weight


def score_stock(db: Session, stock: Stock) -> dict:
    signals = compute_signals(db, stock)
    composite = composite_score(signals)
    return {
        "ticker": stock.ticker,
        "composite_score": round(composite, 2),
        "components": {name: r.to_dict() for name, r in signals.items()},
        "weights": SIGNAL_WEIGHTS,
    }
