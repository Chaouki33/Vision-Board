import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, downloadFile, errorMessage, loadMeta } from "../api";
import Chart from "../components/Chart";
import SectorBanner from "../components/SectorBanner";
import FinancialStatements from "../components/FinancialStatements";
import { UploadForm } from "../components/DataTab";
import DataGuide from "../components/DataGuide";
import DataEntry from "../components/DataEntry";
import { formatDelta, formatExact, formatValue } from "../format";
import type { ChartData, Company, DashboardData, KpiValue, Meta, Report } from "../types";
import Skeleton from "../components/Skeleton";
import AnimatedNumber from "../components/AnimatedNumber";

const STATUS = {
  ok: { icon: "✓", label: "Bon niveau" },
  warning: { icon: "!", label: "À surveiller" },
  critical: { icon: "✕", label: "Critique" },
} as const;

export default function DashboardPage() {
  const params = useParams();
  const companyId = Number(params.companyId);
  const dashboardId = Number(params.dashboardId);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [company, setCompany] = useState<Company | null>(null);
  const [data, setData] = useState<DashboardData | null>(null);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [asking, setAsking] = useState(false);
  const [importing, setImporting] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    Promise.all([loadMeta(), api<Company>(`/companies/${companyId}`)])
      .then(([m, c]) => {
        setMeta(m);
        setCompany(c);
      })
      .catch((err) => setError(errorMessage(err)));
  }, [companyId]);

  useEffect(() => {
    const query = new URLSearchParams();
    if (start) query.set("start", start);
    if (end) query.set("end", end);
    setLoading(true);
    api<DashboardData>(`/companies/${companyId}/dashboards/${dashboardId}/data?${query}`)
      .then(setData)
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }, [companyId, dashboardId, start, end, reloadKey]);

  if (error) return <p className="error">{error}</p>;
  if (!meta || !company || !data) return <Skeleton variant="dashboard" label="Calcul des indicateurs" />;

  // Un même graphique peut servir à deux KPI (ex. effectif par département) : on ne l'affiche qu'une fois.
  const charts = data.kpis.filter(
    (k, i) => k.chart && k.chart.values.length > 0 && data.kpis.findIndex((o) => o.chart?.title === k.chart!.title) === i,
  );
  const computed = data.kpis.filter((k) => !k.error).length;
  const noData = computed === 0 && data.kpis.every((k) => k.error === "Données manquantes");
  const alerts = data.kpis.filter((k) => k.status === "warning" || k.status === "critical");

  return (
    <>
      <SectorBanner
        compact
        sector={company.sector}
        title={data.title}
        back={<Link to={`/companies/${companyId}?tab=tableaux`} className="back">← {company.name}</Link>}
        subtitle={
          <>
            {meta.domains[data.domain]} · {computed} indicateurs calculés sur {data.kpis.length}
            {data.data_start && data.data_end && <> · données du {frDate(data.data_start)} au {frDate(data.data_end)}</>}
          </>
        }
        actions={
          computed > 0 ? (
            <>
              <ExportMenu companyId={companyId} dashboardId={dashboardId} start={start} end={end} />
              {company.role !== "viewer" && (
                <>
                  <button className="btn" onClick={() => setImporting(!importing)}>
                    Importer un fichier
                  </button>
                  <button className="btn primary" onClick={() => setAsking(!asking)}>
                    Rapport d'analyse
                  </button>
                </>
              )}
            </>
          ) : undefined
        }
      />

      {(noData || importing) && company.role !== "viewer" && (
        <ImportPanel
          meta={meta}
          companyId={companyId}
          domain={data.domain}
          empty={noData}
          onUploaded={() => {
            setImporting(false);
            setReloadKey((k) => k + 1);
          }}
          onCancel={noData ? undefined : () => setImporting(false)}
        />
      )}
      {noData && company.role === "viewer" && (
        <p className="notice">Aucune donnée n'a encore été importée pour ce tableau de bord.</p>
      )}

      {asking && (
        <ReportRequest companyId={companyId} dashboardId={dashboardId} start={start} end={end} onCancel={() => setAsking(false)} />
      )}

      {data.data_start && (
      <div className="filters">
        <label>
          Du
          <input type="date" value={start} min={data.data_start ?? undefined} max={end || data.data_end || undefined}
            onChange={(e) => setStart(e.target.value)} />
        </label>
        <label>
          Au
          <input type="date" value={end} min={start || data.data_start || undefined} max={data.data_end ?? undefined}
            onChange={(e) => setEnd(e.target.value)} />
        </label>
        <button className="btn ghost" disabled={!start && !end} onClick={() => { setStart(""); setEnd(""); }}>
          Toute la période
        </button>
        {loading && <span className="muted small">Mise à jour…</span>}
      </div>
      )}

      {alerts.length > 0 && (
        <div className="alert-strip">
          <strong>Points d'attention :</strong>{" "}
          {alerts.map((k) => `${k.name} (${formatValue(k.value, k.unit)})`).join(" · ")}
        </div>
      )}

      <div className="tiles">
        {data.kpis.map((k) => (
          <Tile key={k.code} kpi={k} />
        ))}
      </div>

      <div className="charts">
        {charts.map((k) => (
          <ChartCard key={k.code} chart={k.chart!} kpi={k} />
        ))}
      </div>

      {data.domain === "comptabilite" && <FinancialStatements companyId={companyId} start={start} end={end} />}
    </>
  );
}

function frDate(iso: string): string {
  return new Date(iso).toLocaleDateString("fr-FR");
}

function Tile({ kpi }: { kpi: KpiValue }) {
  const status = kpi.status ? STATUS[kpi.status] : null;
  // La couleur de la variation dépend du sens souhaité : une hausse des impayés est mauvaise.
  const deltaGood = kpi.delta !== null && kpi.higher_is_better !== null ? (kpi.delta >= 0) === kpi.higher_is_better : null;

  return (
    <article className={`tile ${kpi.error ? "empty" : ""} ${kpi.status ? `is-${kpi.status}` : ""}`} title={`${kpi.description}\nFormule : ${kpi.formula}`}>
      <div className="tile-label">{kpi.name}</div>
      {kpi.error ? (
        <div className="tile-error">{kpi.error}</div>
      ) : (
        <>
          <div className="tile-value"><AnimatedNumber value={kpi.value} unit={kpi.unit} /></div>
          <div className="tile-meta">
            {kpi.delta !== null && (
              <span className={`delta ${deltaGood === null ? "" : deltaGood ? "good" : "bad"}`}>
                {kpi.delta >= 0 ? "▲" : "▼"} {formatDelta(kpi.delta)} <span className="muted">vs mois précédent</span>
              </span>
            )}
            {status && (
              <span className={`status ${kpi.status}`}>
                <span aria-hidden="true">{status.icon}</span> {status.label}
              </span>
            )}
          </div>
          {kpi.detail && <div className="tile-detail">{kpi.detail}</div>}
        </>
      )}
    </article>
  );
}

function ChartCard({ chart, kpi }: { chart: ChartData; kpi: KpiValue }) {
  const [table, setTable] = useState(false);
  return (
    <section className={`card chart-card ${chart.type === "bar" ? "" : "wide"}`}>
      <div className="card-head">
        <div>
          <h3>{chart.title}</h3>
          <p className="muted small">{kpi.name}</p>
        </div>
        <button className="btn small ghost" onClick={() => setTable(!table)}>
          {table ? "Graphique" : "Tableau"}
        </button>
      </div>
      {table ? (
        <div className="table-wrap">
          <table>
            <tbody>
              {chart.labels.map((label, i) => (
                <tr key={label}>
                  <td>{label}</td>
                  <td className="num">{formatExact(chart.values[i], chart.unit)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <Chart chart={chart} />
      )}
    </section>
  );
}

interface RequestProps {
  companyId: number;
  dashboardId: number;
  start: string;
  end: string;
  onCancel: () => void;
}

function ReportRequest({ companyId, dashboardId, start, end, onCancel }: RequestProps) {
  const navigate = useNavigate();
  const [instructions, setInstructions] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [engine, setEngine] = useState<"claude" | "regles" | null>(null);

  useEffect(() => {
    api<{ engine: "claude" | "regles" }>(`/companies/${companyId}/reports-config`)
      .then((c) => setEngine(c.engine))
      .catch(() => setEngine("regles"));
  }, [companyId]);
  const ai = engine === "claude";

  const submit = async () => {
    setBusy(true);
    setError("");
    try {
      const report = await api<Report>(`/companies/${companyId}/dashboards/${dashboardId}/reports`, {
        body: { start: start || null, end: end || null, instructions: instructions.trim() || null },
      });
      navigate(`/companies/${companyId}/reports/${report.id}`);
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  };

  return (
    <section className="card highlight">
      <h2>{ai ? "Rapport d'analyse rédigé par l'IA" : "Rapport d'analyse automatique"}</h2>
      <p className="muted">
        {ai
          ? "L'IA analyse les indicateurs de ce tableau de bord"
          : "Vision Board analyse les indicateurs de ce tableau de bord à partir de seuils de référence et de règles d'expert"}
        {start || end ? " sur la période sélectionnée" : ""}, identifie les points forts et les risques, et propose des
        recommandations priorisées. Le rapport est téléchargeable en PDF et en Word.
      </p>
      {engine === "regles" && (
        <p className="small notice">
          Mode gratuit, sans IA ni connexion internet : le rapport est prêt instantanément. Pour une rédaction plus
          nuancée par l'IA Claude, ajoutez une clé API dans <code>backend/.env</code> (voir le README).
        </p>
      )}
      {ai && (
        <label>
          Points à approfondir (facultatif)
          <textarea
            rows={3}
            maxLength={2000}
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            placeholder="Ex. : expliquer la baisse des ventes à Agadir, proposer un plan de réduction des impayés…"
          />
        </label>
      )}
      {error && <p className="error">{error}</p>}
      <div className="actions">
        <button className="btn ghost" onClick={onCancel} disabled={busy}>
          Annuler
        </button>
        <button className="btn primary" onClick={submit} disabled={busy}>
          {busy ? "Préparation…" : ai ? "Rédiger le rapport" : "Générer le rapport"}
        </button>
      </div>
    </section>
  );
}

const EXAMPLES: Record<string, string> = {
  commercial: "votre journal des ventes ou l'export de facturation",
  production: "vos rapports de production (par jour, ligne ou ordre de fabrication)",
  stock: "votre état de stock ou inventaire",
  rh: "la liste du personnel (export paie ou fichier RH)",
  tresorerie: "vos relevés bancaires ou le journal de caisse",
  comptabilite: "votre balance générale ou grand livre",
};

interface ImportProps {
  meta: Meta;
  companyId: number;
  domain: string;
  empty: boolean;
  onUploaded: () => void;
  onCancel?: () => void;
}

function ImportPanel({ meta, companyId, domain, empty, onUploaded, onCancel }: ImportProps) {
  const [mode, setMode] = useState<"fichier" | "saisie">("fichier");
  const [showGuide, setShowGuide] = useState(empty);
  return (
    <section className="card highlight import-panel">
      <div className="card-head">
        <div>
          <h2>{empty ? "Ajoutez vos données pour ce tableau de bord" : "Ajouter des données"}</h2>
          <p className="muted">
            Importez {EXAMPLES[domain]} (CSV ou Excel), ou saisissez les données directement ici. Les indicateurs se
            calculent aussitôt.
          </p>
        </div>
        {onCancel && (
          <button className="btn ghost" onClick={onCancel}>
            Fermer
          </button>
        )}
      </div>

      <div className="tabs">
        <button className={mode === "fichier" ? "active" : ""} onClick={() => setMode("fichier")}>
          Importer un fichier
        </button>
        <button className={mode === "saisie" ? "active" : ""} onClick={() => setMode("saisie")}>
          Saisir dans l'application
        </button>
      </div>

      {mode === "fichier" ? (
        <>
          <button className="btn link guide-toggle" onClick={() => setShowGuide(!showGuide)} aria-expanded={showGuide}>
            {showGuide ? "▾" : "▸"} Quelle forme doit avoir mon fichier ?
          </button>
          {showGuide && <DataGuide domain={domain} onManualEntry={() => setMode("saisie")} />}
          <UploadForm
            meta={meta}
            url={`/companies/${companyId}/datasets`}
            fixedDomain={domain}
            title="Choisir le fichier"
            onUploaded={onUploaded}
          />
          <p className="small muted">
            Pour vérifier ou corriger les colonnes reconnues, ouvrez l'onglet « Données importées » de la société.
          </p>
        </>
      ) : (
        <DataEntry
          companyId={companyId}
          domain={domain}
          domainLabel={meta.domains[domain]}
          onSaved={onUploaded}
          onCancel={() => setMode("fichier")}
        />
      )}
    </section>
  );
}

const EXPORTS = [
  { format: "xlsx", label: "Classeur Excel", hint: "Indicateurs, graphiques et données sources (.xlsx)", file: "tableau_de_bord.xlsx" },
  { format: "powerbi", label: "Projet Power BI", hint: "Rapport au design Vision Board (.zip) : clic droit > « Extraire tout », puis ouvrez le fichier .pbip", file: "tableau_de_bord_PowerBI.zip" },
] as const;

/** Export du tableau de bord (période affichée) en Excel ou en projet Power BI. */
function ExportMenu({ companyId, dashboardId, start, end }: { companyId: number; dashboardId: number; start: string; end: string }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent ? e.key === "Escape" : !ref.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [open]);

  const download = async (format: string, file: string) => {
    const query = new URLSearchParams({ format });
    if (start) query.set("start", start);
    if (end) query.set("end", end);
    setBusy(format);
    setError("");
    try {
      await downloadFile(`/companies/${companyId}/dashboards/${dashboardId}/export?${query}`, file);
      setOpen(false);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy("");
    }
  };

  return (
    <div className="export-menu" ref={ref}>
      <button className="btn" aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen(!open)}>
        Exporter ▾
      </button>
      {open && (
        <div className="export-list" role="menu">
          {EXPORTS.map((e) => (
            <button key={e.format} role="menuitem" disabled={!!busy} onClick={() => download(e.format, e.file)}>
              <strong>{busy === e.format ? "Préparation…" : e.label}</strong>
              <span>{e.hint}</span>
            </button>
          ))}
          {error && <p className="error small">{error}</p>}
        </div>
      )}
    </div>
  );
}
