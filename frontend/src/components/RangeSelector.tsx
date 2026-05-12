/** Range options matching common stock-viewer convention.
 *  YTD is computed at click time since "year to date" is calendar-relative.
 */

export type RangeKey = "5D" | "1M" | "3M" | "6M" | "YTD" | "1Y" | "5Y" | "MAX";

export const RANGES: { key: RangeKey; label: string; days: () => number }[] = [
  { key: "5D",  label: "5D",  days: () => 5 },
  { key: "1M",  label: "1M",  days: () => 30 },
  { key: "3M",  label: "3M",  days: () => 90 },
  { key: "6M",  label: "6M",  days: () => 180 },
  { key: "YTD", label: "YTD", days: () => ytdDays() },
  { key: "1Y",  label: "1Y",  days: () => 365 },
  { key: "5Y",  label: "5Y",  days: () => 1825 },
  { key: "MAX", label: "Max", days: () => 9999 },
];

function ytdDays(): number {
  const now = new Date();
  const jan1 = new Date(now.getFullYear(), 0, 1);
  return Math.max(1, Math.floor((now.getTime() - jan1.getTime()) / 86_400_000));
}

export function rangeToDays(key: RangeKey): number {
  return RANGES.find((r) => r.key === key)?.days() ?? 180;
}

export function RangeSelector({
  value,
  onChange,
}: {
  value: RangeKey;
  onChange: (next: RangeKey) => void;
}) {
  return (
    <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
      {RANGES.map((r) => (
        <button
          key={r.key}
          type="button"
          onClick={() => onChange(r.key)}
          className={value === r.key ? "" : "secondary"}
          style={{
            padding: "4px 10px",
            fontSize: 12,
            minWidth: 38,
          }}
        >
          {r.label}
        </button>
      ))}
    </div>
  );
}
