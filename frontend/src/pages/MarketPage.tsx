import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, type ScoreResponse, type StockRow } from "../api";
import { fmtNum, fmtPct, scoreColor, tierColor, tierLabel } from "../format";

type SortKey = "ticker" | "score" | "last" | "change" | "tier";
type TierFilter = "all" | "commission_free" | "standard_fee";
type CountryFilter = "all" | "US" | "DA" | "SW" | "NO" | "FI";

const COUNTRY_LABEL: Record<CountryFilter, string> = {
  all: "All",
  US: "United States",
  DA: "Denmark",
  SW: "Sweden",
  NO: "Norway",
  FI: "Finland",
};

export function MarketPage() {
  const [stocks, setStocks] = useState<StockRow[]>([]);
  const [scores, setScores] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [sortKey, setSortKey] = useState<SortKey>("score");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const [search, setSearch] = useState("");
  const [tierFilter, setTierFilter] = useState<TierFilter>("all");
  const [countryFilter, setCountryFilter] = useState<CountryFilter>("all");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [list, scoreList] = await Promise.all([api.listStocks(), api.allScores()]);
        if (cancelled) return;
        setStocks(list);
        const m: Record<string, number> = {};
        scoreList.forEach((s: ScoreResponse) => { m[s.ticker] = s.composite_score; });
        setScores(m);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setLoading(false);
      }
    }
    void load();
    return () => { cancelled = true; };
  }, []);

  const filteredAndSorted = useMemo(() => {
    const needle = search.trim().toLowerCase();
    let rows = stocks.filter((s) => {
      if (tierFilter !== "all" && s.pluto_tier !== tierFilter) return false;
      if (countryFilter !== "all" && s.country_code !== countryFilter) return false;
      if (needle && !s.ticker.toLowerCase().includes(needle) && !s.name.toLowerCase().includes(needle)) {
        return false;
      }
      return true;
    });
    const dir = sortDir === "asc" ? 1 : -1;
    rows = [...rows].sort((a, b) => {
      switch (sortKey) {
        case "ticker": return a.ticker.localeCompare(b.ticker) * dir;
        case "score": return ((scores[a.ticker] ?? 0) - (scores[b.ticker] ?? 0)) * dir;
        case "last": return ((a.last_close_dkk ?? 0) - (b.last_close_dkk ?? 0)) * dir;
        case "change": return ((a.day_change_pct ?? 0) - (b.day_change_pct ?? 0)) * dir;
        case "tier": return a.pluto_tier.localeCompare(b.pluto_tier) * dir;
      }
    });
    return rows;
  }, [stocks, scores, sortKey, sortDir, search, tierFilter, countryFilter]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(key); setSortDir(key === "ticker" ? "asc" : "desc"); }
  }

  function sortIndicator(key: SortKey) {
    if (key !== sortKey) return "";
    return sortDir === "asc" ? " ▲" : " ▼";
  }

  function clearFilters() {
    setSearch("");
    setTierFilter("all");
    setCountryFilter("all");
  }

  const hasFilters = search !== "" || tierFilter !== "all" || countryFilter !== "all";

  if (loading) return <div className="notice">Loading market…</div>;
  if (error) return <div className="error">Error: {error}</div>;

  return (
    <div>
      <h1 className="page-title">Market</h1>

      <div className="panel" style={{ padding: 16, marginBottom: 12 }}>
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <input
            placeholder="Search ticker or name…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ flex: "1 1 220px", minWidth: 180 }}
          />
          <label className="row" style={{ gap: 6, fontSize: 13 }}>
            <span className="muted">Pluto:</span>
            <select value={tierFilter} onChange={(e) => setTierFilter(e.target.value as TierFilter)}>
              <option value="all">All</option>
              <option value="commission_free">Commission-free</option>
              <option value="standard_fee">Standard fee</option>
            </select>
          </label>
          <label className="row" style={{ gap: 6, fontSize: 13 }}>
            <span className="muted">Country:</span>
            <select value={countryFilter} onChange={(e) => setCountryFilter(e.target.value as CountryFilter)}>
              {(Object.keys(COUNTRY_LABEL) as CountryFilter[]).map((k) => (
                <option key={k} value={k}>{COUNTRY_LABEL[k]}</option>
              ))}
            </select>
          </label>
          {hasFilters && (
            <button className="secondary" onClick={clearFilters} style={{ fontSize: 12, padding: "4px 10px" }}>
              Clear
            </button>
          )}
          <div className="muted" style={{ fontSize: 12, marginLeft: "auto" }}>
            Showing {filteredAndSorted.length} of {stocks.length} stocks
          </div>
        </div>
      </div>

      <div className="panel" style={{ padding: 0 }}>
        {filteredAndSorted.length === 0 ? (
          <div className="notice" style={{ padding: 20 }}>
            No stocks match these filters. {hasFilters && (
              <button className="secondary" onClick={clearFilters} style={{ fontSize: 12, padding: "2px 8px", marginLeft: 8 }}>
                Clear filters
              </button>
            )}
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th onClick={() => toggleSort("ticker")} style={{ cursor: "pointer" }}>Ticker{sortIndicator("ticker")}</th>
                <th>Name</th>
                <th onClick={() => toggleSort("tier")} style={{ cursor: "pointer" }}>Pluto{sortIndicator("tier")}</th>
                <th onClick={() => toggleSort("score")} style={{ cursor: "pointer", textAlign: "center" }}>Score{sortIndicator("score")}</th>
                <th onClick={() => toggleSort("last")} style={{ cursor: "pointer", textAlign: "right" }}>Last (DKK){sortIndicator("last")}</th>
                <th onClick={() => toggleSort("change")} style={{ cursor: "pointer", textAlign: "right" }}>Day %{sortIndicator("change")}</th>
                <th>Sector</th>
              </tr>
            </thead>
            <tbody>
              {filteredAndSorted.map((s) => {
                const score = scores[s.ticker];
                return (
                  <tr key={s.ticker}>
                    <td>
                      <Link to={`/stocks/${encodeURIComponent(s.ticker)}`} style={{ fontWeight: 600 }}>
                        {s.ticker}
                      </Link>
                    </td>
                    <td>{s.name}</td>
                    <td>
                      <span className="badge" style={{ background: tierColor(s.pluto_tier), color: "white" }}>
                        {tierLabel(s.pluto_tier)}
                      </span>
                    </td>
                    <td style={{ textAlign: "center" }}>
                      {score !== undefined && (
                        <span className="score-pill" style={{ background: scoreColor(score) }}>
                          {score.toFixed(0)}
                        </span>
                      )}
                    </td>
                    <td style={{ textAlign: "right" }}>{fmtNum(s.last_close_dkk)}</td>
                    <td style={{ textAlign: "right" }}
                        className={s.day_change_pct == null ? "muted" : s.day_change_pct >= 0 ? "green" : "red"}>
                      {fmtPct(s.day_change_pct)}
                    </td>
                    <td className="muted">{s.sector ?? "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
