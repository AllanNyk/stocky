export const fmtDkk = (v: number | null | undefined, digits = 2): string =>
  v == null ? "—" : new Intl.NumberFormat("da-DK", { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(v) + " DKK";

export const fmtNum = (v: number | null | undefined, digits = 2): string =>
  v == null ? "—" : v.toFixed(digits);

export const fmtPct = (v: number | null | undefined, digits = 2): string =>
  v == null ? "—" : `${v >= 0 ? "+" : ""}${v.toFixed(digits)}%`;

export const scoreColor = (score: number): string => {
  if (score >= 70) return "#2e8b57";
  if (score >= 55) return "#7cb342";
  if (score >= 45) return "#9e9e9e";
  if (score >= 30) return "#fb8c00";
  return "#c62828";
};

export const tierLabel = (tier: string): string => {
  switch (tier) {
    case "commission_free":
      return "Free";
    case "standard_fee":
      return "Fee";
    case "not_listed":
      return "—";
    default:
      return tier;
  }
};

export const tierColor = (tier: string): string => {
  switch (tier) {
    case "commission_free":
      return "#2e7d32";
    case "standard_fee":
      return "#ef6c00";
    default:
      return "#757575";
  }
};
