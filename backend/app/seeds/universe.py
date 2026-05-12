"""Curated Phase 1 stock universe: 15 US large-caps + 15 Nordic blue chips + 3 benchmarks.

NOTE on `pluto_tier`: these are PLACEHOLDER classifications based on the general pattern
of Nordic commission-free brokers (curated list of major US + Nordic names is fee-free,
everything else is `standard_fee`). The real Pluto Markets list should be hand-verified
against pluto.markets and edited here before treating tier as authoritative.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import Stock


@dataclass(frozen=True)
class SeedStock:
    ticker: str
    name: str
    exchange: str
    currency: str
    sector: str
    pluto_tier: str
    is_benchmark: bool = False


UNIVERSE: list[SeedStock] = [
    # ---- US large caps (yfinance: no suffix) ----
    SeedStock("AAPL",  "Apple Inc.",                     "NASDAQ", "USD", "Technology",          "commission_free"),
    SeedStock("MSFT",  "Microsoft Corporation",          "NASDAQ", "USD", "Technology",          "commission_free"),
    SeedStock("GOOGL", "Alphabet Inc. Class A",          "NASDAQ", "USD", "Communication",       "commission_free"),
    SeedStock("AMZN",  "Amazon.com Inc.",                "NASDAQ", "USD", "Consumer Cyclical",   "commission_free"),
    SeedStock("NVDA",  "NVIDIA Corporation",             "NASDAQ", "USD", "Technology",          "commission_free"),
    SeedStock("META",  "Meta Platforms Inc.",            "NASDAQ", "USD", "Communication",       "commission_free"),
    SeedStock("TSLA",  "Tesla Inc.",                     "NASDAQ", "USD", "Consumer Cyclical",   "commission_free"),
    SeedStock("BRK-B", "Berkshire Hathaway Inc. Class B","NYSE",   "USD", "Financial Services",  "standard_fee"),
    SeedStock("JPM",   "JPMorgan Chase & Co.",           "NYSE",   "USD", "Financial Services",  "commission_free"),
    SeedStock("V",     "Visa Inc.",                      "NYSE",   "USD", "Financial Services",  "commission_free"),
    SeedStock("WMT",   "Walmart Inc.",                   "NYSE",   "USD", "Consumer Defensive",  "commission_free"),
    SeedStock("JNJ",   "Johnson & Johnson",              "NYSE",   "USD", "Healthcare",          "commission_free"),
    SeedStock("PG",    "Procter & Gamble Company",       "NYSE",   "USD", "Consumer Defensive",  "commission_free"),
    SeedStock("KO",    "Coca-Cola Company",              "NYSE",   "USD", "Consumer Defensive",  "commission_free"),
    SeedStock("INTC",  "Intel Corporation",              "NASDAQ", "USD", "Technology",          "commission_free"),

    # ---- Denmark (Copenhagen / .CO) ----
    SeedStock("NOVO-B.CO",   "Novo Nordisk A/S B",       "CPH", "DKK", "Healthcare",            "commission_free"),
    SeedStock("MAERSK-B.CO", "A.P. Moller-Maersk B",     "CPH", "DKK", "Industrials",           "commission_free"),
    SeedStock("DSV.CO",      "DSV A/S",                  "CPH", "DKK", "Industrials",           "commission_free"),
    SeedStock("ORSTED.CO",   "Orsted A/S",               "CPH", "DKK", "Utilities",             "commission_free"),
    SeedStock("CARL-B.CO",   "Carlsberg B",              "CPH", "DKK", "Consumer Defensive",    "commission_free"),
    SeedStock("DANSKE.CO",   "Danske Bank A/S",          "CPH", "DKK", "Financial Services",    "commission_free"),

    # ---- Sweden (Stockholm / .ST) ----
    SeedStock("VOLV-B.ST",   "Volvo AB B",               "STO", "SEK", "Industrials",           "commission_free"),
    SeedStock("ATCO-A.ST",   "Atlas Copco A",            "STO", "SEK", "Industrials",           "commission_free"),
    SeedStock("ERIC-B.ST",   "Telefonaktiebolaget LM Ericsson B", "STO", "SEK", "Technology",   "commission_free"),
    SeedStock("HM-B.ST",     "H & M Hennes & Mauritz B", "STO", "SEK", "Consumer Cyclical",     "commission_free"),
    SeedStock("INVE-B.ST",   "Investor AB B",            "STO", "SEK", "Financial Services",    "standard_fee"),

    # ---- Norway (Oslo / .OL) ----
    SeedStock("EQNR.OL",     "Equinor ASA",              "OSL", "NOK", "Energy",                "commission_free"),
    SeedStock("DNB.OL",      "DNB Bank ASA",             "OSL", "NOK", "Financial Services",    "commission_free"),
    SeedStock("TEL.OL",      "Telenor ASA",              "OSL", "NOK", "Communication",         "commission_free"),

    # ---- Finland (Helsinki / .HE) ----
    SeedStock("NOKIA.HE",    "Nokia Oyj",                "HEL", "EUR", "Technology",            "commission_free"),

    # ---- Benchmarks (not tradeable in paper-trading; for validation comparison) ----
    SeedStock("SPY",          "SPDR S&P 500 ETF Trust",  "NYSE", "USD", "ETF",                  "not_listed", is_benchmark=True),
    SeedStock("^OMXC25",      "OMX Copenhagen 25",       "CPH",  "DKK", "Index",                "not_listed", is_benchmark=True),
    SeedStock("^OMXSPI",      "OMX Stockholm All-Share", "STO",  "SEK", "Index",                "not_listed", is_benchmark=True),
]


def seed_universe(db: Session) -> dict[str, int]:
    """Upsert every entry in UNIVERSE. Idempotent — safe to run on every startup."""
    inserted = 0
    updated = 0
    for s in UNIVERSE:
        existing = db.query(Stock).filter(Stock.ticker == s.ticker).one_or_none()
        if existing is None:
            db.add(Stock(
                ticker=s.ticker,
                name=s.name,
                exchange=s.exchange,
                currency=s.currency,
                sector=s.sector,
                pluto_tier=s.pluto_tier,
                is_benchmark=s.is_benchmark,
            ))
            inserted += 1
        else:
            existing.name = s.name
            existing.exchange = s.exchange
            existing.currency = s.currency
            existing.sector = s.sector
            existing.pluto_tier = s.pluto_tier
            existing.is_benchmark = s.is_benchmark
            updated += 1
    db.commit()
    return {"inserted": inserted, "updated": updated, "total": len(UNIVERSE)}
