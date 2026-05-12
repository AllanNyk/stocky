import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, type Notification } from "./api";
import { useAuth } from "./auth";

interface NotificationsValue {
  notifications: Notification[];
  unreadCount: number;
  refresh: () => Promise<void>;
  markRead: (id: number) => Promise<void>;
  markAllRead: () => Promise<void>;
}

const NotificationsContext = createContext<NotificationsValue | null>(null);

export function NotificationsProvider({ children }: { children: ReactNode }) {
  const { me } = useAuth();
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const refresh = useCallback(async () => {
    if (!me) {
      setNotifications([]);
      return;
    }
    try {
      const rows = await api.notifications(false);
      setNotifications(rows);
    } catch {
      // Non-fatal — leave previous state.
    }
  }, [me]);

  useEffect(() => {
    void refresh();
    if (!me) return;
    // Light polling every 60s so newly-fired notifications appear without a refresh.
    const handle = setInterval(refresh, 60_000);
    return () => clearInterval(handle);
  }, [me, refresh]);

  const markRead = useCallback(async (id: number) => {
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
    try { await api.markNotificationRead(id); } catch { void refresh(); }
  }, [refresh]);

  const markAllRead = useCallback(async () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    try { await api.markAllNotificationsRead(); } catch { void refresh(); }
  }, [refresh]);

  const value: NotificationsValue = {
    notifications,
    unreadCount: notifications.filter((n) => !n.is_read).length,
    refresh,
    markRead,
    markAllRead,
  };
  return <NotificationsContext.Provider value={value}>{children}</NotificationsContext.Provider>;
}

export function useNotifications(): NotificationsValue {
  const ctx = useContext(NotificationsContext);
  if (!ctx) throw new Error("useNotifications must be used inside NotificationsProvider");
  return ctx;
}
