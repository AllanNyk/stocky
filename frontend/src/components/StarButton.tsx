import type { MouseEvent } from "react";
import { useWatchlist } from "../watchlist";

export function StarButton({
  ticker,
  size = 18,
  disabled = false,
}: {
  ticker: string;
  size?: number;
  disabled?: boolean;
}) {
  const { isWatched, toggle } = useWatchlist();
  const on = isWatched(ticker);

  function click(e: MouseEvent) {
    // Stop the click from also triggering parent row navigation.
    e.stopPropagation();
    e.preventDefault();
    if (disabled) return;
    void toggle(ticker);
  }

  return (
    <button
      type="button"
      onClick={click}
      disabled={disabled}
      title={on ? "Remove from watchlist" : "Add to watchlist"}
      aria-label={on ? "Remove from watchlist" : "Add to watchlist"}
      style={{
        background: "transparent",
        border: "none",
        padding: 2,
        cursor: disabled ? "not-allowed" : "pointer",
        color: on ? "#facc15" : "#5b6370",
        fontSize: size,
        lineHeight: 1,
      }}
    >
      {on ? "★" : "☆"}
    </button>
  );
}
