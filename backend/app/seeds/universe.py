"""Curated stock universe: US large-caps + heavy Nordic coverage + benchmarks.

NOTE on `pluto_tier`: per pluto.markets (verified 2026-05-12) Pluto operates a flat
commission-free model on all stocks + ETFs in their offering — ~4,000 products across
US (~3,700 names), the 26 largest Danish stocks, "largest European stocks" (Swedish /
Norwegian / Finnish / German etc.), and 60 of the largest European ETFs. They charge
ONLY on:
  - crypto (1%)
  - extended trading hours (0.1%)
  - currency exchange (0.15%)
So in this universe everything tradeable is `commission_free`. The `standard_fee`
tier is kept as a schema option for future brokers / changes but isn't used today.
Indices (`^OMX*`) remain `not_listed` because you can't trade an index directly.

NOTE on `wsb_aliases`: pipe-separated tokens that WSB / r/stocks posters typically use
to refer to each stock, AND used by the news-sentiment ticker-mention filter. Use the
ticker plus 1-2 unambiguous longer forms. Avoid single common-English letters as aliases
(F, T, C alone) — they cause false positives in word-boundary matching. Bare tickers of
length >= 3 are usually safe.

NOTE on `country_code`: FIPS code (NOT ISO) so it joins directly with GDELT data.
FIPS: US (United States), DA (Denmark), SW (Sweden), NO (Norway), FI (Finland).

NOTE on yfinance suffixes by exchange:
- Copenhagen: .CO    - Stockholm: .ST    - Oslo: .OL    - Helsinki: .HE
- US: no suffix
- Some tickers may move/delist; the ingestion logger flags those.
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
    wsb_aliases: str
    country_code: str
    is_benchmark: bool = False


UNIVERSE: list[SeedStock] = [
    # ===================================================================
    # US large + mega caps
    # ===================================================================
    SeedStock("AAPL",  "Apple Inc.",                       "NASDAQ", "USD", "Technology",          "commission_free", "AAPL|Apple",                       "US"),
    SeedStock("MSFT",  "Microsoft Corporation",            "NASDAQ", "USD", "Technology",          "commission_free", "MSFT|Microsoft",                   "US"),
    SeedStock("GOOGL", "Alphabet Inc. Class A",            "NASDAQ", "USD", "Communication",       "commission_free", "GOOGL|GOOG|Alphabet|Google",       "US"),
    SeedStock("AMZN",  "Amazon.com Inc.",                  "NASDAQ", "USD", "Consumer Cyclical",   "commission_free", "AMZN|Amazon",                      "US"),
    SeedStock("NVDA",  "NVIDIA Corporation",               "NASDAQ", "USD", "Technology",          "commission_free", "NVDA|Nvidia",                      "US"),
    SeedStock("META",  "Meta Platforms Inc.",              "NASDAQ", "USD", "Communication",       "commission_free", "META|Meta|Facebook",               "US"),
    SeedStock("TSLA",  "Tesla Inc.",                       "NASDAQ", "USD", "Consumer Cyclical",   "commission_free", "TSLA|Tesla",                       "US"),
    SeedStock("BRK-B", "Berkshire Hathaway Inc. Class B",  "NYSE",   "USD", "Financial Services",  "commission_free",    "BRK|BRK.B|Berkshire|Buffett",      "US"),
    SeedStock("JPM",   "JPMorgan Chase & Co.",             "NYSE",   "USD", "Financial Services",  "commission_free", "JPM|JPMorgan",                     "US"),
    SeedStock("V",     "Visa Inc.",                        "NYSE",   "USD", "Financial Services",  "commission_free", "Visa",                             "US"),
    SeedStock("MA",    "Mastercard Incorporated",          "NYSE",   "USD", "Financial Services",  "commission_free", "Mastercard",                       "US"),
    SeedStock("WMT",   "Walmart Inc.",                     "NYSE",   "USD", "Consumer Defensive",  "commission_free", "WMT|Walmart",                      "US"),
    SeedStock("JNJ",   "Johnson & Johnson",                "NYSE",   "USD", "Healthcare",          "commission_free", "JNJ|Johnson",                      "US"),
    SeedStock("PG",    "Procter & Gamble Company",         "NYSE",   "USD", "Consumer Defensive",  "commission_free", "Procter",                          "US"),
    SeedStock("KO",    "Coca-Cola Company",                "NYSE",   "USD", "Consumer Defensive",  "commission_free", "Coca-Cola|CocaCola",               "US"),
    SeedStock("PEP",   "PepsiCo Inc.",                     "NASDAQ", "USD", "Consumer Defensive",  "commission_free", "PEP|PepsiCo",                      "US"),
    SeedStock("INTC",  "Intel Corporation",                "NASDAQ", "USD", "Technology",          "commission_free", "INTC|Intel",                       "US"),
    SeedStock("AMD",   "Advanced Micro Devices Inc.",      "NASDAQ", "USD", "Technology",          "commission_free", "AMD",                              "US"),
    SeedStock("ORCL",  "Oracle Corporation",               "NYSE",   "USD", "Technology",          "commission_free", "ORCL|Oracle",                      "US"),
    SeedStock("CRM",   "Salesforce Inc.",                  "NYSE",   "USD", "Technology",          "commission_free", "CRM|Salesforce",                   "US"),
    SeedStock("ADBE",  "Adobe Inc.",                       "NASDAQ", "USD", "Technology",          "commission_free", "ADBE|Adobe",                       "US"),
    SeedStock("AVGO",  "Broadcom Inc.",                    "NASDAQ", "USD", "Technology",          "commission_free", "AVGO|Broadcom",                    "US"),
    SeedStock("CSCO",  "Cisco Systems Inc.",               "NASDAQ", "USD", "Technology",          "commission_free", "CSCO|Cisco",                       "US"),
    SeedStock("QCOM",  "QUALCOMM Incorporated",            "NASDAQ", "USD", "Technology",          "commission_free", "QCOM|Qualcomm",                    "US"),
    SeedStock("TXN",   "Texas Instruments Incorporated",   "NASDAQ", "USD", "Technology",          "commission_free", "TXN|Texas Instruments",            "US"),
    SeedStock("IBM",   "International Business Machines",  "NYSE",   "USD", "Technology",          "commission_free", "IBM",                              "US"),
    SeedStock("NFLX",  "Netflix Inc.",                     "NASDAQ", "USD", "Communication",       "commission_free", "NFLX|Netflix",                     "US"),
    SeedStock("DIS",   "Walt Disney Company",              "NYSE",   "USD", "Communication",       "commission_free", "DIS|Disney",                       "US"),
    SeedStock("COST",  "Costco Wholesale Corporation",     "NASDAQ", "USD", "Consumer Defensive",  "commission_free", "COST|Costco",                      "US"),
    SeedStock("HD",    "Home Depot Inc.",                  "NYSE",   "USD", "Consumer Cyclical",   "commission_free", "Home Depot",                       "US"),
    SeedStock("MCD",   "McDonald's Corporation",           "NYSE",   "USD", "Consumer Cyclical",   "commission_free", "MCD|McDonald",                     "US"),
    SeedStock("SBUX",  "Starbucks Corporation",            "NASDAQ", "USD", "Consumer Cyclical",   "commission_free", "SBUX|Starbucks",                   "US"),
    SeedStock("NKE",   "NIKE Inc.",                        "NYSE",   "USD", "Consumer Cyclical",   "commission_free", "NKE|Nike",                         "US"),
    SeedStock("TGT",   "Target Corporation",               "NYSE",   "USD", "Consumer Defensive",  "commission_free", "TGT|Target Corp",                  "US"),
    SeedStock("BAC",   "Bank of America Corporation",      "NYSE",   "USD", "Financial Services",  "commission_free", "BAC|Bank of America",              "US"),
    SeedStock("WFC",   "Wells Fargo & Company",            "NYSE",   "USD", "Financial Services",  "commission_free", "WFC|Wells Fargo",                  "US"),
    SeedStock("GS",    "Goldman Sachs Group Inc.",         "NYSE",   "USD", "Financial Services",  "commission_free", "Goldman Sachs|Goldman",            "US"),
    SeedStock("MS",    "Morgan Stanley",                   "NYSE",   "USD", "Financial Services",  "commission_free", "Morgan Stanley",                   "US"),
    SeedStock("PFE",   "Pfizer Inc.",                      "NYSE",   "USD", "Healthcare",          "commission_free", "PFE|Pfizer",                       "US"),
    SeedStock("MRK",   "Merck & Co. Inc.",                 "NYSE",   "USD", "Healthcare",          "commission_free", "MRK|Merck",                        "US"),
    SeedStock("ABBV",  "AbbVie Inc.",                      "NYSE",   "USD", "Healthcare",          "commission_free", "ABBV|AbbVie",                      "US"),
    SeedStock("LLY",   "Eli Lilly and Company",            "NYSE",   "USD", "Healthcare",          "commission_free", "LLY|Eli Lilly",                    "US"),
    SeedStock("UNH",   "UnitedHealth Group Incorporated",  "NYSE",   "USD", "Healthcare",          "commission_free", "UNH|UnitedHealth",                 "US"),
    SeedStock("XOM",   "Exxon Mobil Corporation",          "NYSE",   "USD", "Energy",              "commission_free", "XOM|Exxon",                        "US"),
    SeedStock("CVX",   "Chevron Corporation",              "NYSE",   "USD", "Energy",              "commission_free", "CVX|Chevron",                      "US"),
    SeedStock("BA",    "Boeing Company",                   "NYSE",   "USD", "Industrials",         "commission_free", "Boeing",                           "US"),
    SeedStock("CAT",   "Caterpillar Inc.",                 "NYSE",   "USD", "Industrials",         "commission_free", "Caterpillar",                      "US"),
    SeedStock("DE",    "Deere & Company",                  "NYSE",   "USD", "Industrials",         "commission_free", "Deere",                            "US"),
    SeedStock("LMT",   "Lockheed Martin Corporation",      "NYSE",   "USD", "Industrials",         "commission_free", "LMT|Lockheed",                     "US"),
    SeedStock("RTX",   "RTX Corporation",                  "NYSE",   "USD", "Industrials",         "commission_free", "RTX|Raytheon",                     "US"),
    SeedStock("COIN",  "Coinbase Global Inc.",             "NASDAQ", "USD", "Financial Services",  "commission_free", "COIN|Coinbase",                    "US"),
    SeedStock("PYPL",  "PayPal Holdings Inc.",             "NASDAQ", "USD", "Financial Services",  "commission_free", "PYPL|PayPal",                      "US"),
    SeedStock("SHOP",  "Shopify Inc.",                     "NYSE",   "USD", "Technology",          "commission_free", "SHOP|Shopify",                     "US"),
    SeedStock("UBER",  "Uber Technologies Inc.",           "NYSE",   "USD", "Technology",          "commission_free", "UBER|Uber",                        "US"),
    SeedStock("ABNB",  "Airbnb Inc.",                      "NASDAQ", "USD", "Consumer Cyclical",   "commission_free", "ABNB|Airbnb",                      "US"),
    SeedStock("SNOW",  "Snowflake Inc.",                   "NYSE",   "USD", "Technology",          "commission_free", "SNOW|Snowflake",                   "US"),
    SeedStock("PLTR",  "Palantir Technologies Inc.",       "NYSE",   "USD", "Technology",          "commission_free", "PLTR|Palantir",                    "US"),
    SeedStock("CRWD",  "CrowdStrike Holdings Inc.",        "NASDAQ", "USD", "Technology",          "commission_free", "CRWD|CrowdStrike",                 "US"),
    SeedStock("PANW",  "Palo Alto Networks Inc.",          "NASDAQ", "USD", "Technology",          "commission_free", "PANW|Palo Alto",                   "US"),
    SeedStock("VZ",    "Verizon Communications Inc.",      "NYSE",   "USD", "Communication",       "commission_free", "Verizon",                          "US"),
    SeedStock("CMCSA", "Comcast Corporation",              "NASDAQ", "USD", "Communication",       "commission_free", "CMCSA|Comcast",                    "US"),

    # ===================================================================
    # Denmark (FIPS: DA) — 25 names
    # ===================================================================
    SeedStock("NOVO-B.CO",   "Novo Nordisk A/S B",         "CPH", "DKK", "Healthcare",          "commission_free", "NOVO|NVO|Novo Nordisk",        "DA"),
    SeedStock("MAERSK-B.CO", "A.P. Moller-Maersk B",       "CPH", "DKK", "Industrials",         "commission_free", "MAERSK|Maersk",                "DA"),
    SeedStock("DSV.CO",      "DSV A/S",                    "CPH", "DKK", "Industrials",         "commission_free", "DSV",                          "DA"),
    SeedStock("ORSTED.CO",   "Orsted A/S",                 "CPH", "DKK", "Utilities",           "commission_free", "ORSTED|Orsted",                "DA"),
    SeedStock("CARL-B.CO",   "Carlsberg B",                "CPH", "DKK", "Consumer Defensive",  "commission_free", "Carlsberg",                    "DA"),
    SeedStock("DANSKE.CO",   "Danske Bank A/S",            "CPH", "DKK", "Financial Services",  "commission_free", "Danske Bank",                  "DA"),
    SeedStock("VWS.CO",      "Vestas Wind Systems A/S",    "CPH", "DKK", "Industrials",         "commission_free", "VWS|Vestas",                   "DA"),
    SeedStock("PNDORA.CO",   "Pandora A/S",                "CPH", "DKK", "Consumer Cyclical",   "commission_free", "Pandora",                      "DA"),
    SeedStock("GMAB.CO",     "Genmab A/S",                 "CPH", "DKK", "Healthcare",          "commission_free", "GMAB|Genmab",                  "DA"),
    SeedStock("COLO-B.CO",   "Coloplast B",                "CPH", "DKK", "Healthcare",          "commission_free", "Coloplast",                    "DA"),
    SeedStock("DEMANT.CO",   "Demant A/S",                 "CPH", "DKK", "Healthcare",          "commission_free", "Demant|William Demant",        "DA"),
    SeedStock("GN.CO",       "GN Store Nord A/S",          "CPH", "DKK", "Healthcare",          "commission_free", "GN Store Nord",                "DA"),
    SeedStock("JYSK.CO",     "Jyske Bank A/S",             "CPH", "DKK", "Financial Services",  "commission_free", "Jyske Bank",                   "DA"),
    SeedStock("NETC.CO",     "Netcompany Group A/S",       "CPH", "DKK", "Technology",          "commission_free", "Netcompany",                   "DA"),
    SeedStock("ROCK-B.CO",   "Rockwool A/S B",             "CPH", "DKK", "Industrials",         "commission_free", "Rockwool",                     "DA"),
    SeedStock("SIM.CO",      "SimCorp A/S",                "CPH", "DKK", "Technology",          "commission_free", "SimCorp",                      "DA"),
    SeedStock("TRYG.CO",     "Tryg A/S",                   "CPH", "DKK", "Financial Services",  "commission_free", "Tryg",                         "DA"),
    SeedStock("AMBU-B.CO",   "Ambu A/S B",                 "CPH", "DKK", "Healthcare",          "commission_free", "AMBU|Ambu",                    "DA"),
    SeedStock("ISS.CO",      "ISS A/S",                    "CPH", "DKK", "Industrials",         "commission_free", "ISS A/S",                      "DA"),
    SeedStock("HLUN-B.CO",   "H. Lundbeck A/S B",          "CPH", "DKK", "Healthcare",          "commission_free", "Lundbeck",                     "DA"),
    SeedStock("RBREW.CO",    "Royal Unibrew A/S",          "CPH", "DKK", "Consumer Defensive",  "commission_free", "Royal Unibrew|Unibrew",        "DA"),
    SeedStock("TOP.CO",      "Topdanmark A/S",             "CPH", "DKK", "Financial Services",  "commission_free", "Topdanmark",                   "DA"),
    SeedStock("ZEAL.CO",     "Zealand Pharma A/S",         "CPH", "DKK", "Healthcare",          "commission_free",    "Zealand Pharma",               "DA"),
    SeedStock("SYDB.CO",     "Sydbank A/S",                "CPH", "DKK", "Financial Services",  "commission_free", "Sydbank",                      "DA"),
    SeedStock("BAVA.CO",     "Bavarian Nordic A/S",        "CPH", "DKK", "Healthcare",          "commission_free",    "Bavarian Nordic",              "DA"),

    # ===================================================================
    # Sweden (FIPS: SW) — 12 names
    # ===================================================================
    SeedStock("VOLV-B.ST",   "Volvo AB B",                 "STO", "SEK", "Industrials",         "commission_free", "Volvo",                        "SW"),
    SeedStock("ATCO-A.ST",   "Atlas Copco A",              "STO", "SEK", "Industrials",         "commission_free", "Atlas Copco",                  "SW"),
    SeedStock("ERIC-B.ST",   "Ericsson B",                 "STO", "SEK", "Technology",          "commission_free", "ERIC|Ericsson",                "SW"),
    SeedStock("HM-B.ST",     "H & M Hennes & Mauritz B",   "STO", "SEK", "Consumer Cyclical",   "commission_free", "H&M",                          "SW"),
    SeedStock("INVE-B.ST",   "Investor AB B",              "STO", "SEK", "Financial Services",  "commission_free",    "Investor AB",                  "SW"),
    SeedStock("SAND.ST",     "Sandvik AB",                 "STO", "SEK", "Industrials",         "commission_free", "Sandvik",                      "SW"),
    SeedStock("SKF-B.ST",    "SKF B",                      "STO", "SEK", "Industrials",         "commission_free", "SKF",                          "SW"),
    SeedStock("ALFA.ST",     "Alfa Laval AB",              "STO", "SEK", "Industrials",         "commission_free", "Alfa Laval",                   "SW"),
    SeedStock("AZN.ST",      "AstraZeneca PLC (SE)",       "STO", "SEK", "Healthcare",          "commission_free", "AZN|AstraZeneca",              "SW"),
    SeedStock("TELIA.ST",    "Telia Company AB",           "STO", "SEK", "Communication",       "commission_free", "Telia",                        "SW"),
    SeedStock("SEB-A.ST",    "Skandinaviska Enskilda Banken A","STO","SEK","Financial Services","commission_free", "SEB|Skandinaviska",            "SW"),
    SeedStock("SWED-A.ST",   "Swedbank AB A",              "STO", "SEK", "Financial Services",  "commission_free", "Swedbank",                     "SW"),

    # ===================================================================
    # Norway (FIPS: NO) — 8 names
    # ===================================================================
    SeedStock("EQNR.OL",     "Equinor ASA",                "OSL", "NOK", "Energy",              "commission_free", "EQNR|Equinor",                 "NO"),
    SeedStock("DNB.OL",      "DNB Bank ASA",               "OSL", "NOK", "Financial Services",  "commission_free", "DNB",                          "NO"),
    SeedStock("TEL.OL",      "Telenor ASA",                "OSL", "NOK", "Communication",       "commission_free", "Telenor",                      "NO"),
    SeedStock("YAR.OL",      "Yara International ASA",     "OSL", "NOK", "Industrials",         "commission_free", "YAR|Yara",                     "NO"),
    SeedStock("NHY.OL",      "Norsk Hydro ASA",            "OSL", "NOK", "Industrials",         "commission_free", "NHY|Norsk Hydro",              "NO"),
    SeedStock("MOWI.OL",     "Mowi ASA",                   "OSL", "NOK", "Consumer Defensive",  "commission_free", "MOWI|Mowi",                    "NO"),
    SeedStock("SUBC.OL",     "Subsea 7 S.A.",              "OSL", "NOK", "Energy",              "commission_free", "Subsea 7|Subsea7",             "NO"),
    SeedStock("AKERBP.OL",   "Aker BP ASA",                "OSL", "NOK", "Energy",              "commission_free", "Aker BP",                      "NO"),

    # ===================================================================
    # Finland (FIPS: FI) — 5 names
    # ===================================================================
    SeedStock("NOKIA.HE",    "Nokia Oyj",                  "HEL", "EUR", "Technology",          "commission_free", "NOK|Nokia",                    "FI"),
    SeedStock("KNEBV.HE",    "KONE Oyj B",                 "HEL", "EUR", "Industrials",         "commission_free", "KONE",                         "FI"),
    SeedStock("UPM.HE",      "UPM-Kymmene Oyj",            "HEL", "EUR", "Industrials",         "commission_free", "UPM|UPM-Kymmene",              "FI"),
    SeedStock("NESTE.HE",    "Neste Oyj",                  "HEL", "EUR", "Energy",              "commission_free", "Neste",                        "FI"),
    SeedStock("FORTUM.HE",   "Fortum Oyj",                 "HEL", "EUR", "Utilities",           "commission_free", "Fortum",                       "FI"),

    # ===================================================================
    # Benchmarks (not tradeable; for validation comparison)
    # ===================================================================
    SeedStock("SPY",     "SPDR S&P 500 ETF Trust",      "NYSE", "USD", "ETF",   "not_listed", "SPY|S&P 500",     "US", is_benchmark=True),
    SeedStock("QQQ",     "Invesco QQQ Trust",           "NASDAQ","USD","ETF",   "not_listed", "QQQ|Nasdaq 100",  "US", is_benchmark=True),
    SeedStock("^OMXC25", "OMX Copenhagen 25",           "CPH",  "DKK", "Index", "not_listed", "OMXC25",          "DA", is_benchmark=True),
    SeedStock("^OMXSPI", "OMX Stockholm All-Share",     "STO",  "SEK", "Index", "not_listed", "OMXSPI|OMXS",     "SW", is_benchmark=True),
    SeedStock("^OMXH25", "OMX Helsinki 25",             "HEL",  "EUR", "Index", "not_listed", "OMXH25",          "FI", is_benchmark=True),
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
                wsb_aliases=s.wsb_aliases,
                country_code=s.country_code,
                is_benchmark=s.is_benchmark,
            ))
            inserted += 1
        else:
            existing.name = s.name
            existing.exchange = s.exchange
            existing.currency = s.currency
            existing.sector = s.sector
            existing.pluto_tier = s.pluto_tier
            existing.wsb_aliases = s.wsb_aliases
            existing.country_code = s.country_code
            existing.is_benchmark = s.is_benchmark
            updated += 1
    db.commit()
    return {"inserted": inserted, "updated": updated, "total": len(UNIVERSE)}
