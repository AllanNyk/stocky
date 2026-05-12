import { useEffect, useState } from "react";
import { api, type AlertCondition, type AlertRule } from "../api";

export function AlertsPanel({ ticker }: { ticker: string }) {
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [condition, setCondition] = useState<AlertCondition>("score_crosses_above");
  const [threshold, setThreshold] = useState<string>("70");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      const all = await api.listAlerts();
      setRules(all.filter((r) => r.ticker === ticker));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { void load(); }, [ticker]);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const t = Number.parseFloat(threshold);
      if (!Number.isFinite(t) || t < 0 || t > 100) throw new Error("threshold must be 0-100");
      await api.createAlert(ticker, condition, t);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: number) {
    setBusy(true);
    try { await api.deleteAlert(id); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }

  return (
    <div className="panel">
      <h2 className="h2">Alerts for {ticker}</h2>
      {loading ? (
        <div className="notice">Loading…</div>
      ) : rules.length === 0 ? (
        <div className="muted" style={{ fontSize: 12, marginBottom: 12 }}>
          No alerts yet for this stock.
        </div>
      ) : (
        <div style={{ marginBottom: 12 }}>
          {rules.map((r) => (
            <div key={r.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 0", borderBottom: "1px solid var(--border)", fontSize: 13 }}>
              <div>
                Composite{" "}
                <b>{r.condition === "score_crosses_above" ? "crosses above" : "crosses below"}</b>{" "}
                {r.threshold.toFixed(0)}
                <div className="muted" style={{ fontSize: 11 }}>
                  Last observed: {r.last_observed_score == null ? "—" : r.last_observed_score.toFixed(1)}
                </div>
              </div>
              <button
                type="button"
                className="secondary"
                onClick={() => remove(r.id)}
                disabled={busy}
                style={{ fontSize: 11, padding: "2px 8px" }}
              >Remove</button>
            </div>
          ))}
        </div>
      )}
      <form onSubmit={add} style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
        <select value={condition} onChange={(e) => setCondition(e.target.value as AlertCondition)} style={{ fontSize: 12 }}>
          <option value="score_crosses_above">Crosses above</option>
          <option value="score_crosses_below">Crosses below</option>
        </select>
        <input
          type="number"
          value={threshold}
          min={0}
          max={100}
          onChange={(e) => setThreshold(e.target.value)}
          style={{ width: 64, fontSize: 12 }}
        />
        <button type="submit" disabled={busy} style={{ fontSize: 12, padding: "4px 10px" }}>
          Add alert
        </button>
      </form>
      {error && <div className="error" style={{ marginTop: 8 }}>{error}</div>}
    </div>
  );
}
