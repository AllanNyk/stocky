import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "./api";
import { useAuth } from "./auth";

interface WatchlistValue {
  watched: Set<string>;
  isWatched: (ticker: string) => boolean;
  toggle: (ticker: string) => Promise<void>;
}

const WatchlistContext = createContext<WatchlistValue | null>(null);

export function WatchlistProvider({ children }: { children: ReactNode }) {
  const { me } = useAuth();
  const [watched, setWatched] = useState<Set<string>>(new Set());

  // Reset and refetch when the user changes (login/logout).
  useEffect(() => {
    if (!me) {
      setWatched(new Set());
      return;
    }
    let cancelled = false;
    void api.watchlist().then((list) => {
      if (!cancelled) setWatched(new Set(list));
    }).catch(() => {
      // Non-fatal: leave empty.
    });
    return () => { cancelled = true; };
  }, [me?.id]);

  const toggle = useCallback(async (ticker: string) => {
    if (!me) return;
    const isOn = watched.has(ticker);
    // Optimistic update; rollback on failure.
    setWatched((prev) => {
      const next = new Set(prev);
      if (isOn) next.delete(ticker); else next.add(ticker);
      return next;
    });
    try {
      if (isOn) await api.watchRemove(ticker);
      else await api.watchAdd(ticker);
    } catch {
      setWatched((prev) => {
        const next = new Set(prev);
        if (isOn) next.add(ticker); else next.delete(ticker);
        return next;
      });
    }
  }, [me, watched]);

  const value: WatchlistValue = {
    watched,
    isWatched: (t) => watched.has(t),
    toggle,
  };
  return <WatchlistContext.Provider value={value}>{children}</WatchlistContext.Provider>;
}

export function useWatchlist(): WatchlistValue {
  const ctx = useContext(WatchlistContext);
  if (!ctx) throw new Error("useWatchlist must be used inside WatchlistProvider");
  return ctx;
}
