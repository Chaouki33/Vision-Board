import { useEffect, useState, type ClipboardEvent } from "react";
import { api, errorMessage } from "../api";
import { loadGuide, type GuideColumn } from "./DataGuide";

type Row = Record<string, string>;

interface Props {
  companyId: number;
  domain: string;
  domainLabel: string;
  /** Modification d'une saisie existante. */
  datasetId?: number;
  onSaved: () => void;
  onCancel: () => void;
}

const emptyRows = (n: number): Row[] => Array.from({ length: n }, () => ({}));

function display(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "number") return value.toLocaleString("fr-FR", { maximumFractionDigits: 2 }).replace(/ /g, " ");
  return String(value);
}

/** Tableau éditable pour saisir (ou coller depuis Excel) les données d'un domaine, sans fichier. */
export default function DataEntry({ companyId, domain, domainLabel, datasetId, onSaved, onCancel }: Props) {
  const [columns, setColumns] = useState<GuideColumn[]>([]);
  const [rows, setRows] = useState<Row[]>(emptyRows(5));
  const [name, setName] = useState(`Saisie ${domainLabel.toLowerCase()} du ${new Date().toLocaleDateString("fr-FR")}`);
  const [allColumns, setAllColumns] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    loadGuide(domain).then((g) => setColumns(g.columns)).catch((err) => setError(errorMessage(err)));
    if (datasetId) {
      api<{ name: string; rows: Record<string, unknown>[] }>(`/companies/${companyId}/datasets/${datasetId}/rows`)
        .then((d) => {
          setName(d.name);
          setRows([...d.rows.map((r) => Object.fromEntries(Object.entries(r).map(([k, v]) => [k, display(v)]))), ...emptyRows(2)]);
          setAllColumns(true);
        })
        .catch((err) => setError(errorMessage(err)));
    }
  }, [companyId, domain, datasetId]);

  const visible = allColumns ? columns : columns.filter((c) => c.essential);
  const filled = rows.filter((r) => Object.values(r).some((v) => v.trim())).length;

  const setCell = (row: number, code: string, value: string) =>
    setRows((rs) => rs.map((r, i) => (i === row ? { ...r, [code]: value } : r)));

  // Coller un bloc copié depuis Excel : remplit les cellules à partir de celle sélectionnée.
  const paste = (e: ClipboardEvent<HTMLInputElement>, row: number, col: number) => {
    const text = e.clipboardData.getData("text/plain");
    if (!text.includes("\t") && !text.includes("\n")) return;
    e.preventDefault();
    let lines = text.replace(/\r/g, "").split("\n").filter((l, i, all) => l !== "" || i < all.length - 1);
    // Si la première ligne collée contient les titres des colonnes, on associe par nom plutôt que par position.
    const norm = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
    const header = lines[0].split("\t").map((h) => columns.find((c) => norm(c.label) === norm(h)));
    let targets: (GuideColumn | undefined)[] = visible.slice(col);
    if (header.filter(Boolean).length >= 2) {
      targets = header;
      lines = lines.slice(1);
      setAllColumns(true);
    }
    setRows((rs) => {
      const next = [...rs];
      while (next.length < row + lines.length) next.push({});
      lines.forEach((line, i) => {
        const target = { ...next[row + i] };
        line.split("\t").forEach((value, j) => {
          const column = targets[j];
          if (column) target[column.code] = value.trim();
        });
        next[row + i] = target;
      });
      return next;
    });
  };

  const save = async () => {
    setError("");
    setBusy(true);
    const body = rows.filter((r) => Object.values(r).some((v) => v.trim()));
    try {
      if (datasetId) await api(`/companies/${companyId}/datasets/${datasetId}/rows`, { method: "PUT", body: { rows: body } });
      else await api(`/companies/${companyId}/datasets/manual`, { body: { domain, name, rows: body } });
      onSaved();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="data-entry">
      <div className="entry-head">
        {!datasetId && (
          <label className="grow">
            Nom de ces données
            <input value={name} onChange={(e) => setName(e.target.value)} maxLength={255} />
          </label>
        )}
        <label className="checkbox-row">
          <input type="checkbox" checked={allColumns} onChange={(e) => setAllColumns(e.target.checked)} />
          Afficher toutes les colonnes ({columns.length})
        </label>
      </div>
      <p className="small muted">
        Une ligne par enregistrement. Dates au format JJ/MM/AAAA, montants sans « MAD ». Astuce : copiez un tableau dans
        Excel et collez-le dans la première cellule, les lignes se remplissent toutes seules.
      </p>

      <div className="table-wrap entry-grid">
        <table>
          <thead>
            <tr>
              <th className="row-num">#</th>
              {visible.map((c) => (
                <th key={c.code} title={c.format}>
                  {c.label}
                  {c.essential && <span className="req" title="Essentielle">*</span>}
                </th>
              ))}
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i}>
                <td className="row-num">{i + 1}</td>
                {visible.map((c, j) => (
                  <td key={c.code}>
                    <input
                      value={row[c.code] ?? ""}
                      onChange={(e) => setCell(i, c.code, e.target.value)}
                      onPaste={(e) => paste(e, i, j)}
                      placeholder={i === 0 ? c.example : c.type === "date" ? "JJ/MM/AAAA" : ""}
                      inputMode={c.type === "number" ? "decimal" : undefined}
                      className={c.type === "number" ? "num" : ""}
                      aria-label={`${c.label}, ligne ${i + 1}`}
                    />
                  </td>
                ))}
                <td>
                  <button className="btn small ghost" title="Supprimer la ligne" aria-label={`Supprimer la ligne ${i + 1}`}
                    onClick={() => setRows((rs) => (rs.length > 1 ? rs.filter((_, k) => k !== i) : emptyRows(1)))}>
                    ✕
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="actions">
        <button className="btn small" onClick={() => setRows((rs) => [...rs, ...emptyRows(5)])}>
          + Ajouter 5 lignes
        </button>
        <span className="muted small">{filled} ligne(s) remplie(s)</span>
        <span className="grow" />
        <button className="btn ghost" onClick={onCancel} disabled={busy}>
          Annuler
        </button>
        <button className="btn primary" onClick={save} disabled={busy || filled === 0}>
          {busy ? "Enregistrement…" : datasetId ? "Enregistrer les modifications" : "Enregistrer les données"}
        </button>
      </div>
      {error && <p className="error">{error}</p>}
    </div>
  );
}
