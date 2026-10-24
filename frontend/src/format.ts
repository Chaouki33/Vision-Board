const compact = new Intl.NumberFormat("fr-FR", { notation: "compact", maximumFractionDigits: 1 });
const integer = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 });
const decimal = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 });
const full = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 2 });

/** Valeur principale d'un KPI, compacte au-delà de 10 000 (12,9 k, 4,2 M). */
export function formatValue(value: number | null, unit: string): string {
  if (value === null) return "—";
  switch (unit) {
    case "MAD":
      return `${Math.abs(value) >= 10_000 ? compact.format(value) : integer.format(value)} MAD`;
    case "%":
      return `${decimal.format(value)} %`;
    case "ratio":
      return full.format(value);
    case "jours":
    case "mois":
    case "heures":
    case "ans":
      return `${decimal.format(value)} ${unit}`;
    default:
      return Math.abs(value) >= 10_000 ? compact.format(value) : integer.format(value);
  }
}

/** Valeur exacte, pour les infobulles et les tableaux. */
export function formatExact(value: number, unit: string): string {
  const text = unit === "%" ? decimal.format(value) : full.format(value);
  if (unit === "MAD") return `${text} MAD`;
  if (unit === "%") return `${text} %`;
  return text;
}

/** Graduations d'axe : 0 / 1 k / 2 k. */
export function formatAxis(value: number, unit: string): string {
  if (unit === "%") return `${integer.format(value)} %`;
  return Math.abs(value) >= 1000 ? compact.format(value) : integer.format(value);
}

export function formatDelta(delta: number): string {
  return `${delta > 0 ? "+" : ""}${decimal.format(delta)} %`;
}
