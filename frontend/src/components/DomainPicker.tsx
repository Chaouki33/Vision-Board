import type { Meta } from "../types";

const DESCRIPTIONS: Record<string, string> = {
  commercial: "Chiffre d'affaires, clients, marges, impayés, commerciaux",
  production: "Volumes, rebuts, TRS, arrêts machines, coût de revient",
  stock: "Valeur du stock, ruptures, rotation, péremption",
  rh: "Effectif, contrats, stagiaires, salaires, absences, congés",
  tresorerie: "Soldes bancaires, encaissements, décaissements, autonomie",
  comptabilite: "Balance, CPC, bilan, ratios financiers",
};

interface Props {
  meta: Meta;
  sector: string;
  selected: string[];
  onChange: (domains: string[]) => void;
  /** Domaines qui ont déjà un tableau de bord (affichés, non sélectionnables). */
  existing?: string[];
  disabled?: boolean;
}

/** Choix de plusieurs types de tableau de bord, avec les types recommandés pour le secteur. */
export default function DomainPicker({ meta, sector, selected, onChange, existing = [], disabled }: Props) {
  const suggested = meta.sector_domains[sector] ?? Object.keys(meta.domains);
  const toggle = (code: string) =>
    onChange(selected.includes(code) ? selected.filter((d) => d !== code) : [...selected, code]);

  return (
    <div className="grid domains">
      {Object.entries(meta.domains).map(([code, label]) => {
        const done = existing.includes(code);
        const checked = done || selected.includes(code);
        return (
          <label key={code} className={`domain-card selectable ${checked ? "on" : ""} ${done ? "done" : ""}`}>
            <input type="checkbox" checked={checked} disabled={disabled || done} onChange={() => toggle(code)} />
            <span className="domain-title">{label}</span>
            <span className="muted small">{DESCRIPTIONS[code]}</span>
            <span className="small domain-flag">
              {done ? "✓ Déjà créé" : suggested.includes(code) ? "Recommandé pour ce secteur" : "Peu courant pour ce secteur"}
            </span>
          </label>
        );
      })}
    </div>
  );
}

export function suggestedDomains(meta: Meta, sector: string): string[] {
  return sector ? meta.sector_domains[sector] ?? [] : [];
}
