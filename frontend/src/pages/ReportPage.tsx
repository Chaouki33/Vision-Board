import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, downloadFile, errorMessage } from "../api";
import type { Company, Report } from "../types";
import Skeleton from "../components/Skeleton";

const POLL_MS = 3000;

const ASSESSMENT = {
  favorable: { icon: "✓", className: "is-ok" },
  "à surveiller": { icon: "!", className: "is-warning" },
  préoccupante: { icon: "✕", className: "is-critical" },
} as const;

export default function ReportPage() {
  const params = useParams();
  const companyId = Number(params.companyId);
  const reportId = Number(params.reportId);
  const [company, setCompany] = useState<Company | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState("");
  const [downloading, setDownloading] = useState("");

  useEffect(() => {
    api<Company>(`/companies/${companyId}`).then(setCompany).catch((err) => setError(errorMessage(err)));
  }, [companyId]);

  // Tant que l'IA rédige, on interroge le serveur toutes les quelques secondes.
  useEffect(() => {
    let timer: number | undefined;
    let cancelled = false;
    const load = () =>
      api<Report>(`/companies/${companyId}/reports/${reportId}`)
        .then((r) => {
          if (cancelled) return;
          setReport(r);
          if (r.status === "pending") timer = window.setTimeout(load, POLL_MS);
        })
        .catch((err) => setError(errorMessage(err)));
    load();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [companyId, reportId]);

  const download = async (format: "pdf" | "docx") => {
    setDownloading(format);
    try {
      await downloadFile(`/companies/${companyId}/reports/${reportId}/export?format=${format}`, `rapport.${format}`);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setDownloading("");
    }
  };

  if (error && !report) return <p className="error">{error}</p>;
  if (!report || !company) return <Skeleton variant="page" />;

  const back = report.dashboard_id
    ? { to: `/companies/${companyId}/dashboards/${report.dashboard_id}`, label: "Tableau de bord" }
    : { to: `/companies/${companyId}?tab=rapports`, label: company.name };

  return (
    <>
      <Link to={back.to} className="back">
        ← {back.label}
      </Link>

      {report.status === "pending" && (
        <section className="card report-pending">
          <div className="spinner" aria-hidden="true" />
          <div>
            <h2>Rédaction du rapport en cours…</h2>
            <p className="muted">
              L'IA analyse les indicateurs du tableau de bord. Cela prend généralement entre 30 secondes et 2 minutes ;
              vous pouvez quitter cette page, le rapport sera disponible dans l'onglet « Rapports ».
            </p>
          </div>
        </section>
      )}

      {report.status === "error" && (
        <section className="card">
          <h2>Le rapport n'a pas pu être rédigé</h2>
          <p className="error">{report.error}</p>
          {report.dashboard_id && (
            <Link className="btn primary" to={`/companies/${companyId}/dashboards/${report.dashboard_id}`}>
              Revenir au tableau de bord pour réessayer
            </Link>
          )}
        </section>
      )}

      {report.status === "done" && report.content && (
        <ReportView
          report={report}
          company={company}
          onDownload={download}
          downloading={downloading}
          error={error}
        />
      )}
    </>
  );
}

interface ViewProps {
  report: Report;
  company: Company;
  onDownload: (format: "pdf" | "docx") => void;
  downloading: string;
  error: string;
}

function ReportView({ report, company, onDownload, downloading, error }: ViewProps) {
  const c = report.content!;
  const assessment = ASSESSMENT[c.appreciation_globale];
  return (
    <article className="report">
      <div className="report-head">
        <div>
          <div className="report-brand">Rapport d'analyse · {company.name}</div>
          <h1>{c.titre}</h1>
          <p className="muted small">
            Rédigé le {new Date(report.created_at).toLocaleDateString("fr-FR")}
            {report.period_start || report.period_end
              ? ` · période ${report.period_start ? `du ${frDate(report.period_start)}` : ""}${report.period_end ? ` au ${frDate(report.period_end)}` : ""}`
              : " · toutes les données disponibles"}
          </p>
        </div>
        <div className="actions">
          <button className="btn" onClick={() => onDownload("docx")} disabled={!!downloading}>
            {downloading === "docx" ? "Préparation…" : "Télécharger Word"}
          </button>
          <button className="btn primary" onClick={() => onDownload("pdf")} disabled={!!downloading}>
            {downloading === "pdf" ? "Préparation…" : "Télécharger PDF"}
          </button>
        </div>
      </div>
      {error && <p className="error">{error}</p>}

      <section className="card">
        <span className={`status ${assessment.className.replace("is-", "")}`}>
          <span aria-hidden="true">{assessment.icon}</span> Appréciation globale : {c.appreciation_globale}
        </span>
        <h2 className="report-h">Synthèse</h2>
        <p className="lead">{c.synthese}</p>
      </section>

      {c.chiffres_cles.length > 0 && (
        <div className="tiles">
          {c.chiffres_cles.map((k) => (
            <article key={k.indicateur} className="tile">
              <div className="tile-label">{k.indicateur}</div>
              <div className="tile-value">{k.valeur}</div>
              <div className="tile-detail">{k.commentaire}</div>
            </article>
          ))}
        </div>
      )}

      <section className="card report-body">
        {c.sections.map((s) => (
          <div key={s.titre}>
            <h2 className="report-h">{s.titre}</h2>
            {s.paragraphes.map((p, i) => (
              <p key={i}>{p}</p>
            ))}
          </div>
        ))}
      </section>

      <div className="report-columns">
        <section className="card">
          <h2 className="report-h">Points forts</h2>
          <ul className="report-list good">
            {c.points_forts.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        </section>
        <section className="card">
          <h2 className="report-h">Points de vigilance</h2>
          <ul className="report-list bad">
            {c.points_de_vigilance.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        </section>
      </div>

      <section className="card">
        <h2 className="report-h">Recommandations</h2>
        <ol className="recommendations">
          {c.recommandations.map((r, i) => (
            <li key={i}>
              <div className="rec-head">
                <strong>{r.action}</strong>
                <span className={`tag prio-${r.priorite}`}>Priorité {r.priorite}</span>
                <span className="tag">{r.horizon}</span>
              </div>
              <p>{r.justification}</p>
            </li>
          ))}
        </ol>
      </section>

      {c.limites_des_donnees.length > 0 && (
        <section className="card muted-card">
          <h3>Limites de l'analyse</h3>
          <ul>
            {c.limites_des_donnees.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        </section>
      )}

      <section className="card">
        <h2 className="report-h">Conclusion</h2>
        <p className="lead">{c.conclusion}</p>
      </section>

      <p className="muted small center-text">
        {report.model?.startsWith("Vision Board")
          ? "Rapport généré automatiquement par Vision Board (analyse par règles, sans IA) à partir des données importées. À relire avant diffusion."
          : `Rapport rédigé par l'IA (${report.model}) à partir des données importées dans Vision Board. À relire avant diffusion.`}
      </p>
    </article>
  );
}

function frDate(iso: string): string {
  return new Date(iso).toLocaleDateString("fr-FR");
}
