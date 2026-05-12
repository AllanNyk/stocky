"""Composite prediction score: weighted sum of individual signals.

Each signal returns a SignalResult; the composite weights the *score* by the signal's
declared weight, scaled by the signal's confidence. Signals that error get weight 0 and
the remaining weights re-normalize so the composite stays in [0, 100].
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models import Stock
from app.services.signals.base import SignalResult
from app.services.signals.geopolitical_tone import GeopoliticalToneSignal
from app.services.signals.insider_activity import InsiderActivitySignal
from app.services.signals.momentum import Momentum50dSignal
from app.services.signals.news_sentiment import NewsSentimentSignal
from app.services.signals.pe_percentile import PEPercentileSignal
from app.services.signals.percentile_52w import Percentile52wSignal
from app.services.signals.volume_momentum import VolumeMomentumSignal
from app.services.signals.wsb_mentions import WsbMentionDeltaSignal

# Weights sum to 1.0. Tuning rationale:
# - Pure-price signals (momentum_50d, percentile_52w) carry most weight because they
#   have full historical backdata AND high confidence on every stock in the universe.
# - Alt-data signals (WSB, news, geopolitical, insider) add breadth but are noisier.
# - Volume momentum is direction-agnostic so it gets the lowest weight.
SIGNAL_WEIGHTS: dict[str, float] = {
    "pe_percentile": 0.15,
    "momentum_50d": 0.18,
    "percentile_52w": 0.12,
    "volume_momentum": 0.08,
    "wsb_mention_delta": 0.10,
    "news_sentiment": 0.13,
    "geopolitical_tone": 0.12,
    "insider_activity": 0.12,
}

SIGNALS = [
    PEPercentileSignal(),
    Momentum50dSignal(),
    Percentile52wSignal(),
    VolumeMomentumSignal(),
    WsbMentionDeltaSignal(),
    NewsSentimentSignal(),
    GeopoliticalToneSignal(),
    InsiderActivitySignal(),
]


def compute_signals(db: Session, stock: Stock, as_of: date | None = None) -> dict[str, SignalResult]:
    out: dict[str, SignalResult] = {}
    for sig in SIGNALS:
        try:
            out[sig.name] = sig.compute(db, stock, as_of=as_of)
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


def score_stock(db: Session, stock: Stock, as_of: date | None = None) -> dict:
    signals = compute_signals(db, stock, as_of=as_of)
    composite = composite_score(signals)
    return {
        "ticker": stock.ticker,
        "composite_score": round(composite, 2),
        "components": {name: r.to_dict() for name, r in signals.items()},
        "weights": SIGNAL_WEIGHTS,
    }
