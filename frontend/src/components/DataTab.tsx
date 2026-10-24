import { useEffect, useState, type FormEvent } from "react";
import { api, errorMessage } from "../api";
import type { Company, Dataset, DatasetDetail, Meta } from "../types";
import DataEntry from "./DataEntry";
import DataGuide from "./DataGuide";

interface Props {
  meta: Meta;
  company: Company;
  canEdit: boolean;
}

export default function DataTab({ meta, company, canEdit }: Props) {
  const base = `/companies/${company.id}/datasets`;
  const [datasets, setDatasets] = useState<Dataset[] | null>(null);
  const [open, setOpen] = useState<DatasetDetail | null>(null);
  const [entry, setEntry] = useState<{ domain: string; datasetId?: number } | null>(null);
  const [error, setError] = useState("");

  const refresh = () => api<Dataset[]>(base).then(setDatasets).catch((err) => setError(errorMessage(err)));
  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company.id]);

  const show = async (id: number) => {
    setError("");
    try {
      setOpen(await api<DatasetDetail>(`${base}/${id}`));
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const remove = async (d: Dataset) => {
    if (!window.confirm(`Supprimer le fichier « ${d.name} » et ses données ?`)) return;
    await api(`${base}/${d.id}`, { method: "DELETE" });
    if (open?.id === d.id) setOpen(null);
    refresh();
  };

  return (
    <>
      {canEdit && !entry && (
        <UploadForm
          meta={meta}
          url={base}
          onUploaded={(d) => {
            setOpen(d);
            refresh();
          }}
          onManualEntry={(domain) => {
            setOpen(null);
            setEntry({ domain });
          }}
        />
      )}

      {entry && (
        <section className="card highlight">
          <h2>
            {entry.datasetId ? "Modifier les données saisies" : "Saisir des données"} — {meta.domains[entry.domain]}
          </h2>
          <DataEntry
            companyId={company.id}
            domain={entry.domain}
            domainLabel={meta.domains[entry.domain]}
            datasetId={entry.datasetId}
            onSaved={() => {
              setEntry(null);
              refresh();
            }}
            onCancel={() => setEntry(null)}
          />
        </section>
      )}

      {open && (
        <MappingEditor
          key={open.id}
          meta={meta}
          dataset={open}
          url={`${base}/${open.id}`}
          canEdit={canEdit}
          onSaved={(d) => {
            setOpen(d);
            refresh();
          }}
          onClose={() => setOpen(null)}
        />
      )}

      <section className="card">
        <h2>Données importées et saisies</h2>
        {error && <p className="error">{error}</p>}
        {datasets?.length === 0 && <p className="muted">Aucune donnée pour l'instant.</p>}
        {datasets && datasets.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Nom</th>
                  <th>Domaine</th>
                  <th>Lignes</th>
                  <th>Champs reconnus</th>
                  <th>Importé le</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {datasets.map((d) => (
                  <tr key={d.id}>
                    <td>
                      <strong>{d.name}</strong>
                      <div className="muted small">{d.source_filename}</div>
                    </td>
                    <td>{meta.domains[d.domain]}</td>
                    <td>{d.row_count.toLocaleString("fr-FR")}</td>
                    <td>
                      {Object.keys(d.mapping).length} / {meta.fields[d.domain].length}
                    </td>
                    <td>{new Date(d.created_at).toLocaleDateString("fr-FR")}</td>
                    <td className="row-actions">
                      {canEdit && d.file_type === "saisie" ? (
                        <button className="btn small" onClick={() => { setOpen(null); setEntry({ domain: d.domain, datasetId: d.id }); }}>
                          Modifier
                        </button>
                      ) : (
                        <button className="btn small" onClick={() => show(d.id)}>
                          {canEdit ? "Colonnes" : "Aperçu"}
                        </button>
                      )}
                      {canEdit && (
                        <button className="btn small danger" onClick={() => remove(d)}>
                          Supprimer
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}

interface UploadProps {
  meta: Meta;
  url: string;
  onUploaded: (d: DatasetDetail) => void;
  /** Type de données imposé (import depuis un tableau de bord) : le choix n'est pas proposé. */
  fixedDomain?: string;
  title?: string;
  /** Propose la saisie directe pour le type choisi. */
  onManualEntry?: (domain: string) => void;
}

export function UploadForm({ meta, url, onUploaded, fixedDomain, title = "Importer un fichier", onManualEntry }: UploadProps) {
  const [domain, setDomain] = useState(fixedDomain ?? "");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [inputKey, setInputKey] = useState(0);
  const [showGuide, setShowGuide] = useState(true);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setError("");
    setBusy(true);
    const form = new FormData();
    form.append("file", file);
    form.append("domain", domain);
    try {
      onUploaded(await api<DatasetDetail>(url, { form }));
      setFile(null);
      setInputKey((k) => k + 1);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card">
      <h2>{title}</h2>
      <p className="muted">
        Formats acceptés : CSV, Excel (XLSX, XLS). Les colonnes sont reconnues automatiquement, puis vous pouvez
        corriger la correspondance.{!fixedDomain && " Choisissez le type de données pour voir la forme attendue du fichier."}
      </p>
      <form className="upload-row" onSubmit={submit}>
        {!fixedDomain && (
          <label>
            Type de données
            <select value={domain} onChange={(e) => setDomain(e.target.value)} required>
              <option value="">— Choisir —</option>
              {Object.entries(meta.domains).map(([code, label]) => (
                <option key={code} value={code}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        )}
        <label className="grow">
          Fichier
          <input
            key={inputKey}
            type="file"
            accept=".csv,.txt,.xlsx,.xlsm,.xls"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            required
          />
        </label>
        <button className="btn primary" disabled={busy || !file}>
          {busy ? "Import…" : "Importer"}
        </button>
      </form>
      {error && <p className="error">{error}</p>}
      {!fixedDomain && domain && (
        <>
          <button className="btn link guide-toggle" onClick={() => setShowGuide(!showGuide)} aria-expanded={showGuide}>
            {showGuide ? "▾" : "▸"} Quelle forme doit avoir mon fichier « {meta.domains[domain]} » ?
          </button>
          {showGuide && (
            <DataGuide domain={domain} onManualEntry={onManualEntry ? () => onManualEntry(domain) : undefined} />
          )}
        </>
      )}
    </section>
  );
}

interface MappingProps {
  meta: Meta;
  dataset: DatasetDetail;
  url: string;
  canEdit: boolean;
  onSaved: (d: DatasetDetail) => void;
  onClose: () => void;
}

function MappingEditor({ meta, dataset, url, canEdit, onSaved, onClose }: MappingProps) {
  const [mapping, setMapping] = useState<Record<string, string>>(dataset.mapping);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const used = new Set(Object.values(mapping));

  const save = async () => {
    setError("");
    try {
      onSaved(await api<DatasetDetail>(url, { method: "PATCH", body: { mapping } }));
      setSaved(true);
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const set = (code: string, column: string) => {
    setSaved(false);
    setMapping((m) => {
      const next = { ...m };
      if (column) next[code] = column;
      else delete next[code];
      return next;
    });
  };

  return (
    <section className="card highlight">
      <div className="card-head">
        <div>
          <h2>Correspondance des colonnes — {dataset.name}</h2>
          <p className="muted">
            {meta.domains[dataset.domain]} · {dataset.row_count.toLocaleString("fr-FR")} lignes. Associez chaque
            information attendue à une colonne de votre fichier.
          </p>
        </div>
        <button className="btn ghost" onClick={onClose}>
          Fermer
        </button>
      </div>

      <div className="mapping-grid">
        {meta.fields[dataset.domain].map((field) => (
          <label key={field.code} className={mapping[field.code] ? "mapped" : ""}>
            <span>
              {field.label} <span className="muted small">({field.type === "number" ? "nombre" : field.type === "date" ? "date" : "texte"})</span>
            </span>
            <select value={mapping[field.code] ?? ""} onChange={(e) => set(field.code, e.target.value)} disabled={!canEdit}>
              <option value="">— Non disponible —</option>
              {dataset.columns.map((col) => (
                <option key={col} value={col} disabled={used.has(col) && mapping[field.code] !== col}>
                  {col}
                </option>
              ))}
            </select>
          </label>
        ))}
      </div>

      {canEdit && (
        <div className="actions">
          {saved && <span className="ok">Correspondance enregistrée ✓</span>}
          <button className="btn primary" onClick={save}>
            Enregistrer la correspondance
          </button>
        </div>
      )}
      {error && <p className="error">{error}</p>}

      <h3>Aperçu des données</h3>
      <div className="table-wrap preview">
        <table>
          <thead>
            <tr>
              {dataset.columns.map((c) => (
                <th key={c}>{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {dataset.preview.map((row, i) => (
              <tr key={i}>
                {dataset.columns.map((c) => (
                  <td key={c}>{formatCell(row[c])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "number") return value.toLocaleString("fr-FR");
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}T00:00:00/.test(value)) {
    return new Date(value).toLocaleDateString("fr-FR");
  }
  return String(value);
}
