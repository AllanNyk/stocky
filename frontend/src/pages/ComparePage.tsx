import { useEffect, useMemo, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, type PriceBar, type ScoreResponse, type StockRow } from "../api";
import { fmtPct, scoreColor } from "../format";
import { RangeSelector, type RangeKey, rangeToDays } from "../components/RangeSelector";

const MAX_TICKERS = 4;
const LINE_COLORS = ["#4f8eff", "#facc15", "#34d399", "#f472b6", "#a78bfa"];

interface CompareDatum {
  date: string;
  [tickerKey: string]: string | number | null;
}

function normalize(history: PriceBar[]): { date: string; pct: number }[] {
  if (history.length === 0) return [];
  const base = history[0].close_dkk;
  if (!base || base === 0) return [];
  return history.map((b) => ({ date: b.date, pct: (b.close_dkk / base) * 100 - 100 }));
}

export function ComparePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [universe, setUniverse] = useState<StockRow[]>([]);
  const [scores, setScores] = useState<Record<string, ScoreResponse>>({});
  const [series, setSeries] = useState<Record<string, PriceBar[]>>({});
  const [range, setRange] = useState<RangeKey>("1Y");
  const [loading, setLoading] = useState(false);
  const [pickerValue, setPickerValue] = useState<string>("");

  const tickers = useMemo(() => {
    const raw = (searchParams.get("tickers") ?? "").split(",").map((s) => s.trim()).filter(Boolean);
    // Dedup, cap at MAX_TICKERS.
    const out: string[] = [];
    for (const t of raw) if (!out.includes(t)) out.push(t);
    return out.slice(0, MAX_TICKERS);
  }, [searchParams]);

  function setTickers(next: string[]) {
    const params = new URLSearchParams(searchParams);
    if (next.length === 0) params.delete("tickers");
    else params.set("tickers", next.join(","));
    setSearchParams(params, { replace: true });
  }

  function addTicker(t: string) {
    if (!t || tickers.includes(t) || tickers.length >= MAX_TICKERS) return;
    setTickers([...tickers, t]);
    setPickerValue("");
  }

  function removeTicker(t: string) {
    setTickers(tickers.filter((x) => x !== t));
  }

  // Load the full stock list once so the picker has something to render.
  useEffect(() => {
    void api.listStocks().then(setUniverse).catch(() => undefined);
  }, []);

  // Refetch scores + price history whenever tickers or range changes.
  useEffect(() => {
    let cancelled = false;
    if (tickers.length === 0) {
      setScores({});
      setSeries({});
      return;
    }
    setLoading(true);
    const days = rangeToDays(range);
    Promise.all(
      tickers.map(async (t) => {
        const [score, history] = await Promise.all([
          api.stockScore(t).catch(() => null),
          api.stockHistory(t, days).catch(() => [] as PriceBar[]),
        ]);
        return { t, score, history };
      }),
    ).then((results) => {
      if (cancelled) return;
      const nextScores: Record<string, ScoreResponse> = {};
      const nextSeries: Record<string, PriceBar[]> = {};
      for (const { t, score, history } of results) {
        if (score) nextScores[t] = score;
        nextSeries[t] = history;
      }
      setScores(nextScores);
      setSeries(nextSeries);
    }).finally(() => {
      if (!cancelled) setLoading(false);
    });
    return () => { cancelled = true; };
  }, [tickers.join(","), range]);

  // Merge normalized series into a single chart data array keyed by date.
  const chartData: CompareDatum[] = useMemo(() => {
    if (tickers.length === 0) return [];
    const byDate = new Map<string, CompareDatum>();
    for (const t of tickers) {
      const norm = normalize(series[t] ?? []);
      for (const p of norm) {
        const existing = byDate.get(p.date) ?? { date: p.date };
        existing[t] = p.pct;
        byDate.set(p.date, existing);
      }
    }
    return [...byDate.values()].sort((a, b) => (a.date as string).localeCompare(b.date as string));
  }, [tickers, series]);

  // The signal-row keys we want to render side-by-side; derived from whichever
  // ticker has the most signals (all should have the same set).
  const signalKeys = useMemo(() => {
    for (const t of tickers) {
      const s = scores[t];
      if (s?.components) return Object.keys(s.components);
    }
    return [];
  }, [tickers, scores]);

  // Available stocks for the picker: full universe minus already-selected, minus benchmarks.
  const pickerOptions = useMemo(() => {
    return universe
      .filter((s) => !s.is_benchmark && !tickers.includes(s.ticker))
      .sort((a, b) => a.ticker.localeCompare(b.ticker));
  }, [universe, tickers]);

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, gap: 12, flexWrap: "wrap" }}>
        <h1 className="page-title" style={{ margin: 0 }}>Compare</h1>
        <RangeSelector value={range} onChange={setRange} />
      </div>

      <div className="panel" style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
        {tickers.map((t, i) => (
          <span
            key={t}
            style={{
              display: "inline-flex", alignItems: "center", gap: 6,
              padding: "4px 10px", borderRadius: 14,
              background: LINE_COLORS[i] + "22",
              border: `1px solid ${LINE_COLORS[i]}55`,
              fontSize: 13,
            }}
          >
            <span style={{ width: 8, height: 8, borderRadius: "50%", background: LINE_COLORS[i] }} />
            <Link to={`/stocks/${encodeURIComponent(t)}`} style={{ fontWeight: 600 }}>{t}</Link>
            <button
              type="button"
              onClick={() => removeTicker(t)}
              title="Remove"
              style={{ background: "transparent", color: "var(--muted)", border: "none", padding: 0, fontSize: 14, cursor: "pointer" }}
            >×</button>
          </span>
        ))}
        {tickers.length < MAX_TICKERS && (
          <select
            value={pickerValue}
            onChange={(e) => addTicker(e.target.value)}
            style={{ minWidth: 200 }}
          >
            <option value="">+ Add ticker…</option>
            {pickerOptions.map((s) => (
              <option key={s.ticker} value={s.ticker}>
                {s.ticker} — {s.name}
              </option>
            ))}
          </select>
        )}
        {tickers.length > 0 && (
          <button className="secondary" onClick={() => setTickers([])} style={{ fontSize: 12, padding: "4px 10px" }}>
            Clear all
          </button>
        )}
      </div>

      {tickers.length === 0 ? (
        <div className="panel">
          <div className="notice">
            Pick up to {MAX_TICKERS} tickers above to compare their normalized price performance
            and 7-signal scores side-by-side.
          </div>
        </div>
      ) : (
        <>
          <div className="panel">
            <h2 className="h2">
              Normalized price <span className="muted" style={{ fontSize: 12, fontWeight: 400 }}>· % change from start of range</span>
              {loading && <span className="muted" style={{ fontSize: 12 }}> · loading…</span>}
            </h2>
            <ResponsiveContainer width="100%" height={320}>
              <LineChart data={chartData} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
                <CartesianGrid stroke="#2a313c" strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#8b949e" }} minTickGap={40} />
                <YAxis
                  tick={{ fontSize: 11, fill: "#8b949e" }}
                  tickFormatter={(v) => `${v >= 0 ? "+" : ""}${(v as number).toFixed(0)}%`}
                />
                <Tooltip
                  contentStyle={{ background: "#161b22", border: "1px solid #2a313c" }}
                  formatter={(v) => {
                    if (typeof v !== "number") return "—";
                    return `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
                  }}
                />
                <Legend />
                {tickers.map((t, i) => (
                  <Line
                    key={t}
                    type="monotone"
                    dataKey={t}
                    stroke={LINE_COLORS[i]}
                    strokeWidth={2}
                    dot={false}
                    connectNulls={false}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="panel" style={{ padding: 0 }}>
            <div style={{ padding: "16px 20px 0 20px" }}>
              <h2 className="h2">Signal breakdown</h2>
            </div>
            <table>
              <thead>
                <tr>
                  <th>Signal</th>
                  {tickers.map((t, i) => (
                    <th key={t} style={{ textAlign: "center" }}>
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                        <span style={{ width: 8, height: 8, borderRadius: "50%", background: LINE_COLORS[i] }} />
                        {t}
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td style={{ fontWeight: 700 }}>Composite</td>
                  {tickers.map((t) => {
                    const s = scores[t];
                    if (!s) return <td key={t} className="muted" style={{ textAlign: "center" }}>—</td>;
                    return (
                      <td key={t} style={{ textAlign: "center" }}>
                        <span className="score-pill" style={{ background: scoreColor(s.composite_score), fontSize: 14, padding: "4px 12px" }}>
                          {s.composite_score.toFixed(0)}
                        </span>
                      </td>
                    );
                  })}
                </tr>
                {signalKeys.map((sigName) => (
                  <tr key={sigName}>
                    <td>{sigName}</td>
                    {tickers.map((t) => {
                      const sig = scores[t]?.components[sigName];
                      if (!sig) return <td key={t} className="muted" style={{ textAlign: "center" }}>—</td>;
                      return (
                        <td key={t} style={{ textAlign: "center" }}>
                          <span className="score-pill" style={{ background: scoreColor(sig.score), opacity: 0.3 + 0.7 * sig.confidence }}>
                            {sig.score.toFixed(0)}
                          </span>
                          <div className="muted" style={{ fontSize: 10, marginTop: 2 }}>
                            conf {Math.round(sig.confidence * 100)}%
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="muted" style={{ fontSize: 12, padding: "12px 20px" }}>
              Pill opacity reflects each signal's confidence — faded pills are essentially neutral votes in the composite.
              Total return over the selected range:{" "}
              {tickers.map((t, i) => {
                const norm = normalize(series[t] ?? []);
                if (norm.length === 0) return null;
                const ret = norm[norm.length - 1].pct;
                return (
                  <span key={t} style={{ marginLeft: 12 }}>
                    <span style={{ color: LINE_COLORS[i], fontWeight: 600 }}>{t}</span>: {fmtPct(ret)}
                  </span>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
