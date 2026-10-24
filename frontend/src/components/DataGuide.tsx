import { useEffect, useState } from "react";
import { api, downloadFile, errorMessage } from "../api";

export interface GuideColumn {
  code: string;
  label: string;
  type: "date" | "number" | "text";
  format: string;
  example: string;
  kpis: string[];
  essential: boolean;
}

export interface Guide {
  domain: string;
  label: string;
  description: string;
  columns: GuideColumn[];
  examples: Record<string, string>[];
}

const cache = new Map<string, Promise<Guide>>();

/** Description des colonnes attendues pour un type de données (mise en cache). */
export function loadGuide(domain: string): Promise<Guide> {
  if (!cache.has(domain)) cache.set(domain, api<Guide>(`/templates/${domain}`));
  return cache.get(domain)!;
}

interface Props {
  domain: string;
  /** Propose la saisie directe dans l'application. */
  onManualEntry?: () => void;
}

/** « Quelle forme doit avoir mon fichier ? » : colonnes, formats, exemple et modèles à télécharger. */
export default function DataGuide({ domain, onManualEntry }: Props) {
  const [guide, setGuide] = useState<Guide | null>(null);
  const [view, setView] = useState<"columns" | "example">("columns");
  const [error, setError] = useState("");

  useEffect(() => {
    setGuide(null);
    loadGuide(domain).then(setGuide).catch((err) => setError(errorMessage(err)));
  }, [domain]);

  const download = (format: "xlsx" | "csv") =>
    downloadFile(`/templates/${domain}/download?format=${format}`, `modele_${domain}.${format}`).catch((err) =>
      setError(errorMessage(err)),
    );

  if (error) return <p className="error">{error}</p>;
  if (!guide) return <div className="sk sk-chart" />;

  const essential = guide.columns.filter((c) => c.essential).length;
  return (
    <div className="data-guide">
      <p>
        <strong>Forme attendue — {guide.label}.</strong> {guide.description} Les noms de colonnes peuvent être
        différents : ils sont reconnus automatiquement. {essential} colonnes sont essentielles, les autres permettent
        des indicateurs supplémentaires.
      </p>

      <div className="guide-actions">
        <button className="btn small primary" onClick={() => download("xlsx")}>
          Télécharger le modèle Excel
        </button>
        <button className="btn small" onClick={() => download("csv")}>
          Modèle CSV
        </button>
        {onManualEntry && (
          <button className="btn small" onClick={onManualEntry}>
            Saisir les données dans l'application
          </button>
        )}
        <span className="segmented" role="tablist">
          <button role="tab" aria-selected={view === "columns"} className={view === "columns" ? "on" : ""}
            onClick={() => setView("columns")}>
            Colonnes
          </button>
          <button role="tab" aria-selected={view === "example"} className={view === "example" ? "on" : ""}
            onClick={() => setView("example")}>
            Exemple de fichier
          </button>
        </span>
      </div>

      {view === "columns" ? (
        <div className="table-wrap">
          <table className="guide-table">
            <thead>
              <tr>
                <th>Colonne</th>
                <th>Format</th>
                <th>Exemple</th>
                <th>Sert à calculer</th>
              </tr>
            </thead>
            <tbody>
              {guide.columns.map((c) => (
                <tr key={c.code}>
                  <td>
                    <strong>{c.label}</strong>
                    <div>
                      <span className={`tag ${c.essential ? "p1" : ""}`}>{c.essential ? "Essentielle" : "Facultative"}</span>
                    </div>
                  </td>
                  <td className="small">{c.format}</td>
                  <td className="mono small">{c.example || "—"}</td>
                  <td className="small muted">{c.kpis.length ? c.kpis.join(" · ") : "Informations complémentaires"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="table-wrap preview">
          <table>
            <thead>
              <tr>
                {Object.keys(guide.examples[0] ?? {}).map((label) => (
                  <th key={label}>{label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {guide.examples.map((row, i) => (
                <tr key={i}>
                  {Object.values(row).map((value, j) => (
                    <td key={j}>{value}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
