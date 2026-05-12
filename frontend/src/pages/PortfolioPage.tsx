import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type PortfolioSummary, type TradeRecord } from "../api";
import { fmtDkk, fmtNum, fmtPct } from "../format";

export function PortfolioPage() {
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [trades, setTrades] = useState<TradeRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [p, t] = await Promise.all([api.portfolio(), api.trades()]);
        if (cancelled) return;
        setSummary(p);
        setTrades(t);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setLoading(false);
      }
    }
    void load();
    return () => { cancelled = true; };
  }, []);

  if (loading) return <div className="notice">Loading portfolio…</div>;
  if (error || !summary) return <div className="error">Error: {error}</div>;

  const totalPnlClass = summary.total_unrealized_pnl_dkk >= 0 ? "green" : "red";

  return (
    <div>
      <h1 className="page-title">Portfolio</h1>

      <div className="panel">
        <div className="kv" style={{ gridTemplateColumns: "max-content 1fr max-content 1fr" }}>
          <div className="k">Total value</div>
          <div style={{ fontWeight: 700, fontSize: 18 }}>{fmtDkk(summary.total_value_dkk)}</div>
          <div className="k">Unrealized P&L</div>
          <div className={totalPnlClass} style={{ fontWeight: 700 }}>
            {fmtDkk(summary.total_unrealized_pnl_dkk)}{" "}
            ({fmtPct(summary.cost_basis_dkk > 0 ? (summary.total_unrealized_pnl_dkk / summary.cost_basis_dkk) * 100 : 0)})
          </div>
          <div className="k">Cash</div>
          <div>{fmtDkk(summary.cash_dkk)}</div>
          <div className="k">Holdings</div>
          <div>{fmtDkk(summary.holdings_value_dkk)}</div>
        </div>
      </div>

      <div className="panel" style={{ padding: 0 }}>
        <div style={{ padding: "16px 20px 0 20px" }}>
          <h2 className="h2">Positions</h2>
        </div>
        {summary.positions.length === 0 ? (
          <div className="notice" style={{ padding: 20 }}>
            No positions yet. Visit the <Link to="/market">Market</Link> to place a trade.
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Quantity</th>
                <th style={{ textAlign: "right" }}>Avg cost</th>
                <th style={{ textAlign: "right" }}>Last</th>
                <th style={{ textAlign: "right" }}>Value</th>
                <th style={{ textAlign: "right" }}>P&L</th>
              </tr>
            </thead>
            <tbody>
              {summary.positions.map((p) => (
                <tr key={p.ticker}>
                  <td>
                    <Link to={`/stocks/${encodeURIComponent(p.ticker)}`}>{p.ticker}</Link>
                    <div className="muted" style={{ fontSize: 12 }}>{p.name}</div>
                  </td>
                  <td>{fmtNum(p.quantity, 4)}</td>
                  <td style={{ textAlign: "right" }}>{fmtDkk(p.avg_cost_dkk)}</td>
                  <td style={{ textAlign: "right" }}>{fmtDkk(p.current_price_dkk)}</td>
                  <td style={{ textAlign: "right" }}>{fmtDkk(p.market_value_dkk)}</td>
                  <td style={{ textAlign: "right" }} className={p.unrealized_pnl_dkk >= 0 ? "green" : "red"}>
                    {fmtDkk(p.unrealized_pnl_dkk)} ({fmtPct(p.unrealized_pnl_pct)})
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="panel" style={{ padding: 0 }}>
        <div style={{ padding: "16px 20px 0 20px" }}>
          <h2 className="h2">Trade history</h2>
        </div>
        {trades.length === 0 ? (
          <div className="notice" style={{ padding: 20 }}>No trades yet.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>When</th>
                <th>Side</th>
                <th>Ticker</th>
                <th style={{ textAlign: "right" }}>Quantity</th>
                <th style={{ textAlign: "right" }}>Price</th>
                <th style={{ textAlign: "right" }}>Fee</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((t) => (
                <tr key={t.id}>
                  <td className="muted">{new Date(t.executed_at).toLocaleString("da-DK")}</td>
                  <td className={t.side === "buy" ? "green" : "red"} style={{ fontWeight: 600 }}>
                    {t.side.toUpperCase()}
                  </td>
                  <td>{t.ticker}</td>
                  <td style={{ textAlign: "right" }}>{fmtNum(t.quantity, 4)}</td>
                  <td style={{ textAlign: "right" }}>{fmtDkk(t.price_dkk)}</td>
                  <td style={{ textAlign: "right" }} className="muted">{fmtDkk(t.fee_dkk)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
