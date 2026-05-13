import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";

export function LoginPage() {
  const { me, login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [inviteCode, setInviteCode] = useState("");
  const [inviteRequired, setInviteRequired] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    void api.gateStatus().then((g) => setInviteRequired(g.invite_required)).catch(() => undefined);
  }, []);

  if (me) return <Navigate to="/market" replace />;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, password, displayName || email.split("@")[0], inviteCode || undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh", padding: 24 }}>
      <div className="panel" style={{ width: 380 }}>
        <h1 style={{ fontSize: 22, margin: "0 0 4px 0", letterSpacing: 2 }}>STOCKY</h1>
        <p className="muted" style={{ marginTop: 0, marginBottom: 24, fontSize: 13 }}>
          Paper-trade Nordic + US stocks against a transparent prediction model.
        </p>
        <div className="tabs">
          <button className={`tab ${mode === "login" ? "active" : ""}`} onClick={() => setMode("login")}>Log in</button>
          <button className={`tab ${mode === "register" ? "active" : ""}`} onClick={() => setMode("register")}>Register</button>
        </div>
        <form onSubmit={submit} className="form">
          {mode === "register" && (
            <input
              placeholder="Display name"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
          )}
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
          />
          {mode === "register" && inviteRequired && (
            <input
              placeholder="Invite code"
              value={inviteCode}
              onChange={(e) => setInviteCode(e.target.value)}
              required
              autoComplete="off"
            />
          )}
          {error && <div className="error">{error}</div>}
          <button type="submit" disabled={submitting}>
            {submitting ? "…" : mode === "login" ? "Log in" : "Create account"}
          </button>
          {mode === "register" && (
            <div className="muted" style={{ fontSize: 12 }}>
              {inviteRequired
                ? "Registration is invite-only. Ask Allan for a code."
                : "New accounts start with 100,000 DKK in mock cash."}
            </div>
          )}
        </form>
      </div>
    </div>
  );
}
