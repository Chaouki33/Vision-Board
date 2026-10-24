import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, errorMessage } from "../api";
import type { Company, Dashboard, Dataset, Meta, Recommendation, Recommendations } from "../types";
import DomainPicker from "./DomainPicker";
import Skeleton from "./Skeleton";

interface Props {
  meta: Meta;
  company: Company;
  canEdit: boolean;
}

const PRIORITY = { 1: "Essentiel", 2: "Important", 3: "Approfondi" } as Record<number, string>;

export default function DashboardsTab({ meta, company, canEdit }: Props) {
  const base = `/companies/${company.id}/dashboards`;
  const [dashboards, setDashboards] = useState<Dashboard[] | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [editing, setEditing] = useState<{ domain: string; dashboard?: Dashboard } | null>(null);
  const [toCreate, setToCreate] = useState<string[]>([]);
  const [error, setError] = useState("");

  const refresh = () =>
    Promise.all([api<Dashboard[]>(base), api<Dataset[]>(`/companies/${company.id}/datasets`)]).then(([d, ds]) => {
      setDashboards(d);
      setDatasets(ds);
    });
  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company.id]);

  const remove = async (d: Dashboard) => {
    if (!window.confirm(`Supprimer le tableau de bord « ${d.title} » ?`)) return;
    await api(`${base}/${d.id}`, { method: "DELETE" });
    refresh();
  };

  const createSelected = async () => {
    setError("");
    try {
      await api(`${base}/bulk`, { body: { domains: toCreate } });
      setToCreate([]);
      refresh();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  if (editing) {
    return (
      <KpiSelector
        meta={meta}
        company={company}
        canEdit={canEdit}
        domain={editing.domain}
        dashboard={editing.dashboard}
        onDone={() => {
          setEditing(null);
          refresh();
        }}
      />
    );
  }
  if (!dashboards) return <Skeleton variant="cards" />;

  const existing = dashboards.map((d) => d.domain);
  const rows = (domain: string) => datasets.filter((d) => d.domain === domain).reduce((n, d) => n + d.row_count, 0);
  const allCreated = Object.keys(meta.domains).every((d) => existing.includes(d));

  return (
    <>
      {dashboards.length === 0 && (
        <p className="notice">
          Cette société n'a pas encore de tableau de bord. Cochez ci-dessous les analyses souhaitées : l'application
          choisit les indicateurs adaptés, puis il suffira d'importer vos fichiers.
        </p>
      )}

      {dashboards.length > 0 && (
        <section className="card">
          <h2>Tableaux de bord de la société</h2>
          <div className="grid cards">
            {dashboards.map((d) => {
              const lines = rows(d.domain);
              return (
                <div key={d.id} className="card inner dash-card">
                  <div className="dash-card-head">
                    <h3>{d.title}</h3>
                    <span className={`tag ${lines ? "ok" : "warn"}`}>{lines ? "Données importées" : "À alimenter"}</span>
                  </div>
                  <p className="muted small">
                    {meta.domains[d.domain]} · {d.kpi_codes.length} indicateurs
                    {lines > 0 && ` · ${lines.toLocaleString("fr-FR")} lignes`}
                  </p>
                  <div className="actions left">
                    <Link className="btn small primary" to={`/companies/${company.id}/dashboards/${d.id}`}>
                      {lines || !canEdit ? "Ouvrir" : "Importer les données"}
                    </Link>
                    <button className="btn small" onClick={() => setEditing({ domain: d.domain, dashboard: d })}>
                      {canEdit ? "Indicateurs" : "Voir les indicateurs"}
                    </button>
                    {canEdit && (
                      <button className="btn small danger" onClick={() => remove(d)}>
                        Supprimer
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {canEdit && !allCreated && (
        <section className="card">
          <h2>{dashboards.length ? "Ajouter des tableaux de bord" : "Choisir les tableaux de bord"}</h2>
          <p className="muted">
            Cochez une ou plusieurs analyses. Les indicateurs sont choisis automatiquement selon le secteur et la taille
            de l'entreprise ; vous pourrez les ajuster ensuite avec « Indicateurs ».
          </p>
          <DomainPicker meta={meta} sector={company.sector} selected={toCreate} onChange={setToCreate} existing={existing} />
          {error && <p className="error">{error}</p>}
          <div className="actions">
            <button className="btn primary" onClick={createSelected} disabled={toCreate.length === 0}>
              {toCreate.length > 1
                ? `Créer les ${toCreate.length} tableaux de bord`
                : toCreate.length === 1
                  ? "Créer le tableau de bord"
                  : "Cochez au moins un tableau de bord"}
            </button>
          </div>
        </section>
      )}
    </>
  );
}

interface SelectorProps {
  meta: Meta;
  company: Company;
  canEdit: boolean;
  domain: string;
  dashboard?: Dashboard;
  onDone: () => void;
}

function KpiSelector({ meta, company, canEdit, domain, dashboard, onDone }: SelectorProps) {
  const navigate = useNavigate();
  const [recs, setRecs] = useState<Recommendations | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [title, setTitle] = useState(dashboard?.title ?? `Tableau de bord ${meta.domains[domain].toLowerCase()}`);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Recommendations>(`/companies/${company.id}/recommendations?domain=${domain}`)
      .then((r) => {
        setRecs(r);
        setSelected(new Set(dashboard ? dashboard.kpi_codes : r.kpis.filter((k) => k.selected).map((k) => k.code)));
      })
      .catch((err) => setError(errorMessage(err)));
  }, [company.id, domain, dashboard]);

  const fieldLabel = (code: string) => meta.fields[domain].find((f) => f.code === code)?.label ?? code;

  const toggle = (code: string) =>
    setSelected((s) => {
      const next = new Set(s);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });

  const save = async () => {
    setError("");
    const body = { domain, title: title.trim(), kpi_codes: recs!.kpis.filter((k) => selected.has(k.code)).map((k) => k.code) };
    try {
      const saved = dashboard
        ? await api<Dashboard>(`/companies/${company.id}/dashboards/${dashboard.id}`, { method: "PUT", body })
        : await api<Dashboard>(`/companies/${company.id}/dashboards`, { body });
      navigate(`/companies/${company.id}/dashboards/${saved.id}`);
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  if (error && !recs) return <p className="error">{error}</p>;
  if (!recs) return <p className="muted">Analyse du profil…</p>;

  const recommended = recs.kpis.filter((k) => k.selected);
  const others = recs.kpis.filter((k) => !k.selected);
  const available = recs.kpis.filter((k) => selected.has(k.code) && k.available).length;

  return (
    <>
      <button className="back" onClick={onDone}>
        ← Retour aux tableaux de bord
      </button>
      <section className="card">
        <h2>{meta.domains[domain]}</h2>
        <p className="muted">
          Sélection proposée pour une entreprise du secteur <strong>{meta.sectors[recs.sector]}</strong>, taille{" "}
          <strong>{meta.sizes[recs.size]}</strong>. Vous pouvez ajouter ou retirer des indicateurs.
        </p>
        {recs.kpis.length === 0 && <p className="muted">Aucun indicateur de ce domaine ne concerne votre secteur.</p>}
        {recs.datasets === 0 && recs.kpis.length > 0 && (
          <p className="notice">
            Aucun fichier de ce type n'est encore importé : importez vos données dans l'onglet « Données importées » pour
            que les indicateurs puissent être calculés.
          </p>
        )}

        <label className="title-input">
          Nom du tableau de bord
          <input value={title} onChange={(e) => setTitle(e.target.value)} disabled={!canEdit} />
        </label>

        <h3>Indicateurs recommandés</h3>
        <KpiList kpis={recommended} selected={selected} toggle={toggle} fieldLabel={fieldLabel} disabled={!canEdit} />
        {others.length > 0 && (
          <>
            <h3>Autres indicateurs disponibles</h3>
            <KpiList kpis={others} selected={selected} toggle={toggle} fieldLabel={fieldLabel} disabled={!canEdit} />
          </>
        )}

        {canEdit && recs.kpis.length > 0 && (
          <div className="actions sticky">
            <span className="muted">
              {selected.size} indicateurs sélectionnés, dont {available} calculables avec vos données
            </span>
            <button className="btn primary" onClick={save} disabled={selected.size === 0 || !title.trim()}>
              Enregistrer et afficher
            </button>
          </div>
        )}
        {error && <p className="error">{error}</p>}
      </section>
    </>
  );
}

interface KpiListProps {
  kpis: Recommendation[];
  selected: Set<string>;
  toggle: (code: string) => void;
  fieldLabel: (code: string) => string;
  disabled: boolean;
}

function KpiList({ kpis, selected, toggle, fieldLabel, disabled }: KpiListProps) {
  return (
    <div className="kpi-list">
      {kpis.map((k) => (
        <label key={k.code} className={`kpi ${selected.has(k.code) ? "on" : ""}`}>
          <input type="checkbox" checked={selected.has(k.code)} onChange={() => toggle(k.code)} disabled={disabled} />
          <div className="kpi-body">
            <div className="kpi-title">
              <strong>{k.name}</strong>
              <span className={`tag p${k.priority}`}>{PRIORITY[k.priority]}</span>
              {k.available ? (
                <span className="tag ok">Calculable</span>
              ) : (
                <span className="tag warn">Données manquantes</span>
              )}
            </div>
            <p className="muted small">{k.description}</p>
            <p className="small formula">
              Formule : {k.formula} <span className="muted">({k.unit})</span>
            </p>
            {!k.available && (
              <p className="small warn-text">À fournir : {k.missing_fields.map(fieldLabel).join(", ")}</p>
            )}
            {k.reasons.length > 0 && <p className="small reason">{k.reasons.join(" · ")}</p>}
          </div>
        </label>
      ))}
    </div>
  );
}
