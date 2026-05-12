import type { ReactNode } from "react";
import { BrowserRouter, NavLink, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth";
import { WatchlistProvider } from "./watchlist";
import { LoginPage } from "./pages/LoginPage";
import { MarketPage } from "./pages/MarketPage";
import { MoversPage } from "./pages/MoversPage";
import { ComparePage } from "./pages/ComparePage";
import { StockDetailPage } from "./pages/StockDetailPage";
import { PortfolioPage } from "./pages/PortfolioPage";
import { ValidationPage } from "./pages/ValidationPage";

function Shell({ children }: { children: ReactNode }) {
  const { me, logout } = useAuth();
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <h1>STOCKY</h1>
        <nav className="nav" style={{ flex: 1 }}>
          <NavLink to="/market" className={({ isActive }) => (isActive ? "active" : "")}>Market</NavLink>
          <NavLink to="/movers" className={({ isActive }) => (isActive ? "active" : "")}>Movers</NavLink>
          <NavLink to="/compare" className={({ isActive }) => (isActive ? "active" : "")}>Compare</NavLink>
          <NavLink to="/portfolio" className={({ isActive }) => (isActive ? "active" : "")}>Portfolio</NavLink>
          <NavLink to="/validation" className={({ isActive }) => (isActive ? "active" : "")}>Model check</NavLink>
        </nav>
        <div style={{ fontSize: 12, color: "var(--muted)" }}>
          <div>{me?.display_name}</div>
          <div style={{ marginTop: 4 }}>{me?.email}</div>
          <button className="secondary" style={{ marginTop: 12, width: "100%" }} onClick={logout}>
            Log out
          </button>
        </div>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}

function RequireAuth({ children }: { children: ReactNode }) {
  const { me, loading } = useAuth();
  if (loading) return <div className="notice" style={{ padding: 32 }}>Loading…</div>;
  if (!me) return <Navigate to="/login" replace />;
  return <Shell>{children}</Shell>;
}

function RouterRoot() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/market" element={<RequireAuth><MarketPage /></RequireAuth>} />
      <Route path="/movers" element={<RequireAuth><MoversPage /></RequireAuth>} />
      <Route path="/compare" element={<RequireAuth><ComparePage /></RequireAuth>} />
      <Route path="/stocks/:ticker" element={<RequireAuth><StockDetailPage /></RequireAuth>} />
      <Route path="/portfolio" element={<RequireAuth><PortfolioPage /></RequireAuth>} />
      <Route path="/validation" element={<RequireAuth><ValidationPage /></RequireAuth>} />
      <Route path="*" element={<Navigate to="/market" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <WatchlistProvider>
        <BrowserRouter>
          <RouterRoot />
        </BrowserRouter>
      </WatchlistProvider>
    </AuthProvider>
  );
}
