import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { useNotifications } from "../notifications";

export function NotificationBell() {
  const { notifications, unreadCount, markRead, markAllRead } = useNotifications();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close on outside click.
  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    }
    if (open) {
      document.addEventListener("click", onClick);
      return () => document.removeEventListener("click", onClick);
    }
  }, [open]);

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="secondary"
        title={unreadCount > 0 ? `${unreadCount} unread` : "Notifications"}
        style={{ width: "100%", textAlign: "left", display: "flex", alignItems: "center", justifyContent: "space-between" }}
      >
        <span>🔔 Alerts</span>
        {unreadCount > 0 && (
          <span style={{ background: "var(--accent)", color: "white", borderRadius: 10, padding: "1px 7px", fontSize: 11, fontWeight: 700 }}>
            {unreadCount}
          </span>
        )}
      </button>
      {open && (
        <div style={{
          position: "absolute", left: 0, bottom: "calc(100% + 6px)",
          width: 320, maxHeight: 420, overflow: "auto",
          background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 6,
          padding: 8, zIndex: 10, boxShadow: "0 12px 32px rgba(0,0,0,0.5)",
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", padding: "4px 6px 8px", borderBottom: "1px solid var(--border)" }}>
            <span style={{ fontWeight: 600, fontSize: 13 }}>Notifications</span>
            {unreadCount > 0 && (
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); void markAllRead(); }}
                style={{ fontSize: 11, background: "transparent", color: "var(--muted)", border: "none", padding: 0, cursor: "pointer" }}
              >
                Mark all read
              </button>
            )}
          </div>
          {notifications.length === 0 ? (
            <div className="notice" style={{ padding: 10, fontSize: 12 }}>
              No notifications yet. Create alerts on a stock detail page.
            </div>
          ) : (
            notifications.map((n) => (
              <Link
                key={n.id}
                to={n.ticker ? `/stocks/${encodeURIComponent(n.ticker)}` : "/market"}
                onClick={() => { setOpen(false); if (!n.is_read) void markRead(n.id); }}
                style={{
                  display: "block", padding: 8, textDecoration: "none",
                  borderRadius: 4,
                  background: n.is_read ? "transparent" : "var(--panel-2)",
                  borderLeft: n.is_read ? "3px solid transparent" : "3px solid var(--accent)",
                  marginBottom: 4, color: "var(--text)",
                }}
              >
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 2 }}>{n.title}</div>
                <div className="muted" style={{ fontSize: 11, marginBottom: 2 }}>{n.body}</div>
                <div className="muted" style={{ fontSize: 10 }}>
                  {new Date(n.created_at).toLocaleString("da-DK")}
                </div>
              </Link>
            ))
          )}
        </div>
      )}
    </div>
  );
}
