import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type LatestPick, type StrategyPerformance } from "../api";
import { fmtDkk, fmtPct } from "../format";

const STRATEGY_LABELS: Record<string, string> = {
  top5_equal_weight: "Top 5, equal weight",
  threshold_70: "All scores ≥ 70",
};

const HORIZON_LABELS: Record<string, string> = {
  "1": "1 day",
  "7": "1 week",
  "30": "1 month",
  "90": "3 months",
};

export function ValidationPage() {
  const [picks, setPicks] = useState<Record<string, LatestPick[]>>({});
  const [perf, setPerf] = useState<Record<string, StrategyPerformance>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const [p, q] = await Promise.all([api.latestPicks(), api.modelPerformance()]);
      setPicks(p);
      setPerf(q);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  async function runSnapshot() {
    setRunning(true);
    try {
      await api.runSnapshot();
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  }

  if (loading) return <div className="notice">Loading validation data…</div>;

  const strategyKeys = Object.keys(STRATEGY_LABELS).filter((k) => picks[k] || perf[k]);
  const hasAnyPicks = strategyKeys.some((k) => (picks[k] ?? []).length > 0);

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h1 className="page-title" style={{ margin: 0 }}>Does the model work?</h1>
        <button onClick={runSnapshot} disabled={running}>
          {running ? "Running…" : "Run snapshot now"}
        </button>
      </div>

      {error && <div className="error" style={{ marginBottom: 12 }}>Error: {error}</div>}

      {!hasAnyPicks && (
        <div className="panel">
          <div className="notice">
            No score snapshots have been taken yet. Click <b>Run snapshot now</b> above to take
            today's snapshot. Forward returns will accumulate over the coming days as new prices come in.
          </div>
        </div>
      )}

      {strategyKeys.map((strat) => {
        const pickList = picks[strat] ?? [];
        const perfData = perf[strat];
        return (
          <div className="panel" key={strat}>
            <h2 className="h2">{STRATEGY_LABELS[strat] ?? strat}</h2>

            <h3 className="h3">If you had bought these on the most recent snapshot:</h3>
            {pickList.length === 0 ? (
              <div className="notice">No picks for this strategy yet.</div>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Ticker</th>
                    <th>Snapshot date</th>
                    <th style={{ textAlign: "right" }}>Score</th>
                    <th style={{ textAlign: "right" }}>Entry</th>
                    <th style={{ textAlign: "right" }}>Now</th>
                    <th style={{ textAlign: "right" }}>Return</th>
                  </tr>
                </thead>
                <tbody>
                  {pickList.map((p) => (
                    <tr key={p.ticker}>
                      <td>
                        <Link to={`/stocks/${encodeURIComponent(p.ticker)}`}>{p.ticker}</Link>
                        <div className="muted" style={{ fontSize: 12 }}>{p.name}</div>
                      </td>
                      <td className="muted">{p.snapshot_date}</td>
                      <td style={{ textAlign: "right" }}>{p.composite_score.toFixed(0)}</td>
                      <td style={{ textAlign: "right" }}>{fmtDkk(p.entry_price_dkk)}</td>
                      <td style={{ textAlign: "right" }}>{fmtDkk(p.current_price_dkk)}</td>
                      <td style={{ textAlign: "right" }} className={(p.return_pct ?? 0) >= 0 ? "green" : "red"}>
                        {fmtPct(p.return_pct)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            <h3 className="h3" style={{ marginTop: 16 }}>
              Aggregate performance across all historical snapshots ({perfData?.total_picks ?? 0} picks total):
            </h3>
            {perfData && Object.keys(perfData.per_horizon).length > 0 ? (
              <table>
                <thead>
                  <tr>
                    <th>Horizon</th>
                    <th style={{ textAlign: "right" }}>Sample size</th>
                    <th style={{ textAlign: "right" }}>Avg return</th>
                    <th style={{ textAlign: "right" }}>Hit rate</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(perfData.per_horizon).map(([h, stats]) => (
                    <tr key={h}>
                      <td>{HORIZON_LABELS[h] ?? `${h}d`}</td>
                      <td style={{ textAlign: "right" }}>{stats.sample_size}</td>
                      <td style={{ textAlign: "right" }} className={(stats.avg_return_pct ?? 0) >= 0 ? "green" : "red"}>
                        {stats.avg_return_pct == null ? "—" : fmtPct(stats.avg_return_pct)}
                      </td>
                      <td style={{ textAlign: "right" }}>
                        {stats.hit_rate == null ? "—" : `${Math.round(stats.hit_rate * 100)}%`}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="notice">Not enough history yet. Hit rate and average return appear once snapshots are several days old.</div>
            )}
          </div>
        );
      })}

      <div className="panel">
        <div className="muted" style={{ fontSize: 13 }}>
          <b>How this works:</b> Every snapshot records each stock's composite score and the price at that moment.
          We never recompute past scores from current data (that would leak future information). Forward returns are
          computed by comparing each historical pick's entry price to the actual price 1 day, 1 week, 1 month, and 3
          months later. Hit rate = the share of picks that ended higher than entry; positive avg return + hit rate
          above 50% suggest the model is picking up real signal.
        </div>
      </div>
    </div>
  );
}
