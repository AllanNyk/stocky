import { useState } from "react";
import { api, type StockRow } from "../api";
import { fmtDkk } from "../format";
import { useAuth } from "../auth";

export function TradePanel({ stock, onTrade }: { stock: StockRow; onTrade: () => void }) {
  const { refresh } = useAuth();
  const [side, setSide] = useState<"buy" | "sell">("buy");
  const [qty, setQty] = useState("1");
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const tradeable = stock.pluto_tier !== "not_listed";
  const price = stock.last_close_dkk;
  const quantity = Number.parseFloat(qty) || 0;
  const estimated = price != null ? price * quantity : null;
  const fee = stock.pluto_tier === "standard_fee" ? 29.0 : 0.0;
  const total = side === "buy" ? (estimated ?? 0) + fee : (estimated ?? 0) - fee;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setStatus(null);
    setSubmitting(true);
    try {
      const t = await api.trade(stock.ticker, side, quantity);
      setStatus(`Executed: ${t.side.toUpperCase()} ${t.quantity} ${t.ticker} @ ${fmtDkk(t.price_dkk)}`);
      await refresh();
      onTrade();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  }

  if (!tradeable) {
    return (
      <div className="panel">
        <h2 className="h2">Trade</h2>
        <div className="muted">This symbol is a benchmark and not tradeable.</div>
      </div>
    );
  }

  return (
    <div className="panel">
      <h2 className="h2">Paper trade</h2>
      <form onSubmit={submit} className="form">
        <div className="tabs">
          <button type="button" className={`tab ${side === "buy" ? "active" : ""}`} onClick={() => setSide("buy")}>Buy</button>
          <button type="button" className={`tab ${side === "sell" ? "active" : ""}`} onClick={() => setSide("sell")}>Sell</button>
        </div>
        <label className="kv">
          <span className="k">Quantity</span>
          <input
            type="number"
            min={0}
            step="0.0001"
            value={qty}
            onChange={(e) => setQty(e.target.value)}
            required
          />
        </label>
        <div className="kv">
          <div className="k">Price (last close)</div>
          <div>{fmtDkk(price)}</div>
          <div className="k">Fee</div>
          <div>{fmtDkk(fee)}</div>
          <div className="k">Estimated {side === "buy" ? "cost" : "proceeds"}</div>
          <div style={{ fontWeight: 600 }}>{fmtDkk(total)}</div>
        </div>
        {error && <div className="error">{error}</div>}
        {status && <div className="green" style={{ fontSize: 13 }}>{status}</div>}
        <button type="submit" disabled={submitting || !tradeable || price == null}>
          {submitting ? "…" : `${side === "buy" ? "Buy" : "Sell"} ${stock.ticker}`}
        </button>
      </form>
    </div>
  );
}
