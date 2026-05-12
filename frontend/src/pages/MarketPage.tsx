import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, type ScoreResponse, type StockRow } from "../api";
import { fmtNum, fmtPct, scoreColor, tierColor, tierLabel } from "../format";

type SortKey = "ticker" | "score" | "last" | "change" | "tier";

export function MarketPage() {
  const [stocks, setStocks] = useState<StockRow[]>([]);
  const [scores, setScores] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("score");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

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

  const sorted = useMemo(() => {
    const rows = [...stocks];
    const dir = sortDir === "asc" ? 1 : -1;
    rows.sort((a, b) => {
      switch (sortKey) {
        case "ticker": return a.ticker.localeCompare(b.ticker) * dir;
        case "score": return ((scores[a.ticker] ?? 0) - (scores[b.ticker] ?? 0)) * dir;
        case "last": return ((a.last_close_dkk ?? 0) - (b.last_close_dkk ?? 0)) * dir;
        case "change": return ((a.day_change_pct ?? 0) - (b.day_change_pct ?? 0)) * dir;
        case "tier": return a.pluto_tier.localeCompare(b.pluto_tier) * dir;
      }
    });
    return rows;
  }, [stocks, scores, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(key); setSortDir(key === "ticker" ? "asc" : "desc"); }
  }

  function sortIndicator(key: SortKey) {
    if (key !== sortKey) return "";
    return sortDir === "asc" ? " ▲" : " ▼";
  }

  if (loading) return <div className="notice">Loading market…</div>;
  if (error) return <div className="error">Error: {error}</div>;

  return (
    <div>
      <h1 className="page-title">Market</h1>
      <div className="panel" style={{ padding: 0 }}>
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
            {sorted.map((s) => {
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
      </div>
    </div>
  );
}
