import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, errorMessage } from "../api";
import type { Company, Meta, Report } from "../types";

const STATUS = { pending: "En cours de rédaction", done: "Prêt", error: "Échec" } as const;

export default function ReportsTab({ meta, company, canEdit }: { meta: Meta; company: Company; canEdit: boolean }) {
  const base = `/companies/${company.id}/reports`;
  const [reports, setReports] = useState<Report[] | null>(null);
  const [error, setError] = useState("");

  const refresh = () => api<Report[]>(base).then(setReports).catch((err) => setError(errorMessage(err)));
  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company.id]);

  const remove = async (r: Report) => {
    if (!window.confirm(`Supprimer le rapport « ${r.title} » ?`)) return;
    await api(`${base}/${r.id}`, { method: "DELETE" });
    refresh();
  };

  return (
    <section className="card">
      <h2>Rapports d'analyse</h2>
      <p className="muted">
        Ouvrez un tableau de bord puis cliquez sur « Rapport d'analyse » pour obtenir une analyse rédigée, avec des
        recommandations, à télécharger en PDF ou en Word.
      </p>
      {error && <p className="error">{error}</p>}
      {reports?.length === 0 && <p className="muted">Aucun rapport pour l'instant.</p>}
      {reports && reports.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Rapport</th>
                <th>Domaine</th>
                <th>Date</th>
                <th>État</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {reports.map((r) => (
                <tr key={r.id}>
                  <td>
                    <strong>{r.title}</strong>
                  </td>
                  <td>{meta.domains[r.domain]}</td>
                  <td>{new Date(r.created_at).toLocaleDateString("fr-FR")}</td>
                  <td>
                    <span className={`status ${r.status === "done" ? "ok" : r.status === "error" ? "critical" : "warning"}`}>
                      {STATUS[r.status]}
                    </span>
                  </td>
                  <td className="row-actions">
                    <Link className="btn small primary" to={`${base}/${r.id}`}>
                      Ouvrir
                    </Link>
                    {canEdit && (
                      <button className="btn small danger" onClick={() => remove(r)}>
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
  );
}
