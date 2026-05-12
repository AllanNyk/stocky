import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type MoverRow, type MoversResponse } from "../api";
import { fmtDkk, scoreColor, tierColor, tierLabel } from "../format";
import { StarButton } from "../components/StarButton";

const LOOKBACK_OPTIONS: { days: number; label: string }[] = [
  { days: 1, label: "1 day" },
  { days: 7, label: "1 week" },
  { days: 30, label: "1 month" },
  { days: 90, label: "3 months" },
];

function MoverTable({ rows, kind }: { rows: MoverRow[]; kind: "top" | "risers" | "fallers" }) {
  if (rows.length === 0) {
    return <div className="notice" style={{ padding: 16 }}>No data yet.</div>;
  }
  return (
    <table>
      <thead>
        <tr>
          <th style={{ width: 32 }}></th>
          <th>Ticker</th>
          <th>Name</th>
          <th style={{ textAlign: "center" }}>Score now</th>
          {kind !== "top" && (
            <>
              <th style={{ textAlign: "center" }}>Score then</th>
              <th style={{ textAlign: "right" }}>Change</th>
            </>
          )}
          <th style={{ textAlign: "right" }}>Last</th>
          <th>Tier</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => {
          const change = r.change;
          return (
            <tr key={r.ticker}>
              <td onClick={(e) => e.stopPropagation()} style={{ textAlign: "center", padding: "0 4px" }}>
                <StarButton ticker={r.ticker} />
              </td>
              <td>
                <Link to={`/stocks/${encodeURIComponent(r.ticker)}`} style={{ fontWeight: 600 }}>
                  {r.ticker}
                </Link>
              </td>
              <td>
                {r.name}
                {r.sector && <div className="muted" style={{ fontSize: 11 }}>{r.sector}</div>}
              </td>
              <td style={{ textAlign: "center" }}>
                <span className="score-pill" style={{ background: scoreColor(r.score_now) }}>
                  {r.score_now.toFixed(0)}
                </span>
              </td>
              {kind !== "top" && (
                <>
                  <td style={{ textAlign: "center" }} className="muted">
                    {r.score_then == null ? "—" : r.score_then.toFixed(0)}
                  </td>
                  <td
                    style={{ textAlign: "right", fontWeight: 600 }}
                    className={change == null ? "muted" : change >= 0 ? "green" : "red"}
                  >
                    {change == null ? "—" : `${change >= 0 ? "+" : ""}${change.toFixed(1)}`}
                  </td>
                </>
              )}
              <td style={{ textAlign: "right" }}>{fmtDkk(r.last_close_dkk)}</td>
              <td>
                <span className="badge" style={{ background: tierColor(r.pluto_tier), color: "white" }}>
                  {tierLabel(r.pluto_tier)}
                </span>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

export function MoversPage() {
  const [lookback, setLookback] = useState(1);
  const [data, setData] = useState<MoversResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const r = await api.movers(lookback, 10);
        if (cancelled) return;
        setData(r);
        setError(null);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => { cancelled = true; };
  }, [lookback]);

  if (loading) return <div className="notice">Loading movers…</div>;
  if (error) return <div className="error">Error: {error}</div>;
  if (!data) return null;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, flexWrap: "wrap", gap: 12 }}>
        <h1 className="page-title" style={{ margin: 0 }}>What the model is saying</h1>
        <div className="row" style={{ gap: 4 }}>
          <span className="muted" style={{ fontSize: 12, marginRight: 8 }}>Compare to:</span>
          {LOOKBACK_OPTIONS.map((opt) => (
            <button
              key={opt.days}
              type="button"
              onClick={() => setLookback(opt.days)}
              className={lookback === opt.days ? "" : "secondary"}
              style={{ fontSize: 12, padding: "4px 10px" }}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      <div className="panel" style={{ borderLeft: "3px solid var(--accent)", background: "var(--panel-2)" }}>
        <div className="muted" style={{ fontSize: 13 }}>
          Comparing scores on <b style={{ color: "var(--text)" }}>{data.to_date}</b> to those on or before{" "}
          <b style={{ color: "var(--text)" }}>{data.from_date}</b>.
          {" "}
          {data.comparable_count} of {data.total_count} stocks have data on both dates. While most historical
          snapshots are still backtest-generated (momentum-only composite), changes will partly reflect new
          signals coming online — give it a few weeks of real daily snapshots before treating moves as pure
          market dynamics.
        </div>
      </div>

      <div className="panel">
        <h2 className="h2">Top picks today (highest composite score)</h2>
        <MoverTable rows={data.top_picks} kind="top" />
      </div>

      <div className="panel">
        <h2 className="h2">Biggest risers</h2>
        <MoverTable rows={data.risers} kind="risers" />
      </div>

      <div className="panel">
        <h2 className="h2">Biggest fallers</h2>
        <MoverTable rows={data.fallers} kind="fallers" />
      </div>
    </div>
  );
}
