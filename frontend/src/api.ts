const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

const TOKEN_KEY = "stocky_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token === null) localStorage.removeItem(TOKEN_KEY);
  else localStorage.setItem(TOKEN_KEY, token);
}

async function request<T>(
  path: string,
  options: { method?: string; body?: unknown; auth?: boolean; form?: URLSearchParams } = {},
): Promise<T> {
  const headers: Record<string, string> = {};
  let body: BodyInit | undefined;

  if (options.form) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    body = options.form;
  } else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }
  if (options.auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method: options.method ?? "GET",
    headers,
    body,
  });
  if (!res.ok) {
    let detail: string;
    try {
      const data = await res.json();
      detail = data?.detail ?? JSON.stringify(data);
    } catch {
      detail = await res.text();
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ---- types ----
export interface StockRow {
  ticker: string;
  name: string;
  exchange: string;
  currency: string;
  sector: string | null;
  pluto_tier: "commission_free" | "standard_fee" | "not_listed";
  is_benchmark: boolean;
  pe_ratio: number | null;
  market_cap: number | null;
  last_close: number | null;
  last_close_dkk: number | null;
  last_trade_date: string | null;
  day_change_pct: number | null;
}

export interface SignalResult {
  score: number;
  confidence: number;
  evidence: Record<string, unknown>;
  error: string | null;
}

export interface ScoreResponse {
  ticker: string;
  composite_score: number;
  components: Record<string, SignalResult>;
  weights: Record<string, number>;
}

export interface PriceBar {
  date: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number;
  close_dkk: number;
  volume: number | null;
}

export interface ScoreHistoryPoint {
  date: string;
  composite_score: number;
  price_at_snapshot_dkk: number;
}

export interface Position {
  ticker: string;
  name: string;
  currency: string;
  pluto_tier: string;
  quantity: number;
  avg_cost_dkk: number;
  current_price_dkk: number;
  market_value_dkk: number;
  unrealized_pnl_dkk: number;
  unrealized_pnl_pct: number;
}

export interface PortfolioSummary {
  cash_dkk: number;
  holdings_value_dkk: number;
  total_value_dkk: number;
  cost_basis_dkk: number;
  total_unrealized_pnl_dkk: number;
  positions: Position[];
}

export interface TradeRecord {
  id: number;
  ticker: string;
  side: "buy" | "sell";
  quantity: number;
  price_dkk: number;
  fee_dkk: number;
  executed_at: string;
}

export interface Me {
  id: number;
  email: string;
  display_name: string;
  cash_balance_dkk: number;
}

export interface LatestPick {
  ticker: string;
  name: string;
  snapshot_date: string;
  composite_score: number;
  weight: number;
  entry_price_dkk: number;
  current_price_dkk: number | null;
  return_pct: number | null;
}

export interface HorizonStats {
  horizon_days: number;
  sample_size: number;
  avg_return_pct: number | null;
  hit_rate: number | null;
}

export interface StrategyPerformance {
  strategy: string;
  total_picks: number;
  per_horizon: Record<string, HorizonStats>;
}

// ---- endpoints ----
export const api = {
  listStocks: () => request<StockRow[]>("/api/stocks"),
  stockDetail: (ticker: string) => request<StockRow>(`/api/stocks/${encodeURIComponent(ticker)}`),
  stockHistory: (ticker: string, days = 180) =>
    request<PriceBar[]>(`/api/stocks/${encodeURIComponent(ticker)}/history?days=${days}`),
  stockScore: (ticker: string) =>
    request<ScoreResponse>(`/api/stocks/${encodeURIComponent(ticker)}/score`),
  stockScoreHistory: (ticker: string, days = 90) =>
    request<ScoreHistoryPoint[]>(`/api/stocks/${encodeURIComponent(ticker)}/score-history?days=${days}`),
  allScores: () => request<ScoreResponse[]>("/api/scores"),

  register: (email: string, password: string, display_name: string) =>
    request<{ access_token: string }>("/api/auth/register", {
      method: "POST",
      body: { email, password, display_name },
    }),
  login: (email: string, password: string) => {
    const form = new URLSearchParams();
    form.append("username", email);
    form.append("password", password);
    return request<{ access_token: string }>("/api/auth/login", { method: "POST", form });
  },
  me: () => request<Me>("/api/auth/me", { auth: true }),

  portfolio: () => request<PortfolioSummary>("/api/portfolio", { auth: true }),
  trades: () => request<TradeRecord[]>("/api/trades", { auth: true }),
  trade: (ticker: string, side: "buy" | "sell", quantity: number) =>
    request<TradeRecord>("/api/trade", {
      method: "POST",
      body: { ticker, side, quantity },
      auth: true,
    }),

  latestPicks: () => request<Record<string, LatestPick[]>>("/api/validation/latest-picks"),
  modelPerformance: () => request<Record<string, StrategyPerformance>>("/api/validation/performance"),
  runSnapshot: () => request<{ snapshot_date: string; scored: number }>("/api/validation/run-snapshot", { method: "POST" }),
  runBacktest: (days = 90) =>
    request<{ start_date: string; end_date: string; trading_days_processed: number }>(
      `/api/validation/run-backtest?days=${days}`,
      { method: "POST" },
    ),

  refreshPrices: () =>
    request<Record<string, number>>("/api/admin/refresh-prices", { method: "POST" }),
};
