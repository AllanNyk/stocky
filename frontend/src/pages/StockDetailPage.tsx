import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, type PriceBar, type ScoreHistoryPoint, type ScoreResponse, type StockRow } from "../api";
import { fmtDkk, fmtNum, fmtPct, scoreColor, tierColor, tierLabel } from "../format";
import { TradePanel } from "../components/TradePanel";
import { RangeSelector, type RangeKey, rangeToDays } from "../components/RangeSelector";

const RANGE_LABELS: Record<RangeKey, string> = {
  "5D": "5 days",
  "1M": "1 month",
  "3M": "3 months",
  "6M": "6 months",
  YTD: "year to date",
  "1Y": "1 year",
  "5Y": "5 years",
  MAX: "all available",
};

export function StockDetailPage() {
  const { ticker = "" } = useParams<{ ticker: string }>();
  const [stock, setStock] = useState<StockRow | null>(null);
  const [history, setHistory] = useState<PriceBar[]>([]);
  const [score, setScore] = useState<ScoreResponse | null>(null);
  const [scoreHistory, setScoreHistory] = useState<ScoreHistoryPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [chartLoading, setChartLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [range, setRange] = useState<RangeKey>("6M");

  // Load static stuff (stock metadata + current composite) once per ticker.
  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [s, sc] = await Promise.all([
          api.stockDetail(ticker),
          api.stockScore(ticker),
        ]);
        if (cancelled) return;
        setStock(s);
        setScore(sc);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setLoading(false);
      }
    }
    void load();
    return () => { cancelled = true; };
  }, [ticker, refreshKey]);

  // Reload chart data whenever the ticker or range changes.
  useEffect(() => {
    let cancelled = false;
    async function loadCharts() {
      setChartLoading(true);
      const days = rangeToDays(range);
      try {
        const [h, sh] = await Promise.all([
          api.stockHistory(ticker, days),
          api.stockScoreHistory(ticker, days),
        ]);
        if (cancelled) return;
        setHistory(h);
        setScoreHistory(sh);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelled) setChartLoading(false);
      }
    }
    void loadCharts();
    return () => { cancelled = true; };
  }, [ticker, range, refreshKey]);

  if (loading) return <div className="notice">Loading {ticker}…</div>;
  if (error || !stock || !score) return <div className="error">Error: {error}</div>;

  return (
    <div>
      <div style={{ marginBottom: 12 }}>
        <Link to="/market" className="muted">← Market</Link>
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 16, marginBottom: 4 }}>
        <h1 className="page-title" style={{ margin: 0 }}>{stock.ticker}</h1>
        <div className="muted">{stock.name}</div>
      </div>
      <div className="muted" style={{ marginBottom: 24, fontSize: 13 }}>
        {stock.exchange} · {stock.currency} ·{" "}
        <span className="badge" style={{ background: tierColor(stock.pluto_tier), color: "white" }}>
          {tierLabel(stock.pluto_tier)}
        </span>
      </div>

      <div className="grid-2">
        <div>
          <div className="panel">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12, gap: 12, flexWrap: "wrap" }}>
              <h2 className="h2" style={{ margin: 0 }}>
                Price (DKK){" "}
                <span className="muted" style={{ fontSize: 12, fontWeight: 400 }}>
                  · {RANGE_LABELS[range]}{chartLoading ? " · loading…" : ""}
                </span>
              </h2>
              <RangeSelector value={range} onChange={setRange} />
            </div>
            {history.length === 0 ? (
              <div className="notice">No price history for this range.</div>
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={history} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
                  <CartesianGrid stroke="#2a313c" strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#8b949e" }} minTickGap={40} />
                  <YAxis tick={{ fontSize: 11, fill: "#8b949e" }} domain={["dataMin", "dataMax"]} />
                  <Tooltip contentStyle={{ background: "#161b22", border: "1px solid #2a313c" }} />
                  <Line dataKey="close_dkk" stroke="#4f8eff" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="panel">
            <h2 className="h2">Score history</h2>
            {scoreHistory.length === 0 ? (
              <div className="notice">
                No score snapshots in this range — try a longer window, or run a backtest from the{" "}
                <Link to="/validation">Model check</Link> page to populate this.
              </div>
            ) : (
              <>
                <ResponsiveContainer width="100%" height={180}>
                  <LineChart data={scoreHistory} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
                    <CartesianGrid stroke="#2a313c" strokeDasharray="3 3" />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#8b949e" }} minTickGap={40} />
                    <YAxis domain={[0, 100]} ticks={[0, 30, 50, 70, 100]} tick={{ fontSize: 11, fill: "#8b949e" }} width={32} />
                    <Tooltip contentStyle={{ background: "#161b22", border: "1px solid #2a313c" }} />
                    <ReferenceLine y={50} stroke="#5b6370" strokeDasharray="3 3" />
                    <ReferenceLine y={70} stroke="#2e8b57" strokeDasharray="3 3" label={{ value: "70 pick threshold", fill: "#2e8b57", fontSize: 10, position: "right" }} />
                    <Line dataKey="composite_score" stroke="#c084fc" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
                <div className="muted" style={{ fontSize: 12, marginTop: 8 }}>
                  Composite score per snapshot date. Pre-news/WSB/GDELT dates use
                  momentum-only (see backtest caveat).
                </div>
              </>
            )}
          </div>

          <div className="panel">
            <h2 className="h2">Prediction score</h2>
            <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 16 }}>
              <span className="score-pill" style={{ background: scoreColor(score.composite_score), fontSize: 22, padding: "10px 18px" }}>
                {score.composite_score.toFixed(0)}
              </span>
              <div className="muted">
                Composite of {Object.keys(score.components).length} signals, confidence-weighted.
              </div>
            </div>
            {Object.entries(score.components).map(([name, sig]) => (
              <div key={name} style={{ borderTop: "1px solid var(--border)", paddingTop: 12, marginTop: 12 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <span className="score-pill" style={{ background: scoreColor(sig.score) }}>{sig.score.toFixed(0)}</span>
                  <div style={{ fontWeight: 600 }}>{name}</div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    weight {(score.weights[name] ?? 0) * 100}% · confidence {Math.round(sig.confidence * 100)}%
                  </div>
                </div>
                {sig.error ? (
                  <div className="muted" style={{ fontSize: 13, marginTop: 6 }}>{sig.error}</div>
                ) : (
                  <div style={{ fontSize: 13, marginTop: 6 }}>
                    {typeof sig.evidence.narrative === "string" ? sig.evidence.narrative : null}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="panel">
            <h2 className="h2">Snapshot</h2>
            <div className="kv">
              <div className="k">Last close</div>
              <div>{fmtNum(stock.last_close)} {stock.currency} → {fmtDkk(stock.last_close_dkk)}</div>
              <div className="k">Day change</div>
              <div className={stock.day_change_pct == null ? "muted" : stock.day_change_pct >= 0 ? "green" : "red"}>
                {fmtPct(stock.day_change_pct)}
              </div>
              <div className="k">P/E</div>
              <div>{fmtNum(stock.pe_ratio)}</div>
              <div className="k">Sector</div>
              <div>{stock.sector ?? "—"}</div>
              <div className="k">Pluto tier</div>
              <div>
                <span className="badge" style={{ background: tierColor(stock.pluto_tier), color: "white" }}>
                  {tierLabel(stock.pluto_tier)}
                </span>
              </div>
            </div>
          </div>

          <TradePanel stock={stock} onTrade={() => setRefreshKey((k) => k + 1)} />
        </div>
      </div>
    </div>
  );
}
