import { useEffect, useState, type CSSProperties } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, errorMessage, loadMeta } from "../api";
import CompanyForm from "../components/CompanyForm";
import SectorScene, { SectorIcon } from "../components/SectorScene";
import { sectorStyle } from "../sectorThemes";
import type { Company, CompanyInput, Meta } from "../types";
import Skeleton from "../components/Skeleton";

/** Message de confirmation commun à toutes les suppressions de sociétés. */
export function confirmDeletion(names: string[]): string {
  const what = names.length === 1 ? `la société « ${names[0]} »` : `${names.length} sociétés (${names.join(", ")})`;
  const their = names.length === 1 ? "Ses" : "Leurs";
  return `Supprimer définitivement ${what} ?

${their} fichiers importés, tableaux de bord et rapports seront effacés. Cette action est irréversible.`;
}

export const ROLE_LABELS = { owner: "Propriétaire", editor: "Éditeur", viewer: "Lecteur" } as const;

export default function CompaniesPage() {
  const navigate = useNavigate();
  const [meta, setMeta] = useState<Meta | null>(null);
  const [companies, setCompanies] = useState<Company[] | null>(null);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([loadMeta(), api<Company[]>("/companies")])
      .then(([m, c]) => {
        setMeta(m);
        setCompanies(c);
        setCreating(c.length === 0);
      })
      .catch((err) => setError(errorMessage(err)));
  }, []);

  const create = async (data: CompanyInput) => {
    const company = await api<Company>("/companies", { body: data });
    navigate(`/companies/${company.id}?tab=tableaux`);
  };

  const remove = async (c: Company) => {
    if (!window.confirm(confirmDeletion([c.name]))) return;
    try {
      await api(`/companies/${c.id}`, { method: "DELETE" });
      setCompanies((list) => (list ?? []).filter((x) => x.id !== c.id));
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  if (error) return <p className="error">{error}</p>;
  if (!meta || !companies) return <Skeleton variant="cards" />;

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Mes sociétés</h1>
          <p className="muted">Choisissez une société pour importer ses données et construire ses tableaux de bord.</p>
        </div>
        {!creating && (
          <button className="btn primary" onClick={() => setCreating(true)}>
            + Nouvelle société
          </button>
        )}
      </div>

      {creating && (
        <section className="card">
          <h2>Nouvelle société</h2>
          <p className="muted">
            Le secteur et la taille servent à choisir automatiquement les indicateurs (KPI) adaptés.
          </p>
          <CompanyForm
            meta={meta}
            submitLabel="Créer la société"
            withDomains
            onSubmit={create}
            onCancel={companies.length ? () => setCreating(false) : undefined}
          />
        </section>
      )}

      <div className="grid cards">
        {companies.map((c) => (
          <div key={c.id} className="company-card-wrap">
            <Link to={`/companies/${c.id}`} className="card company-card themed" style={sectorStyle(c.sector) as CSSProperties}>
              <div className="card-art">
                <SectorScene sector={c.sector} />
              </div>
              <span className="sector-badge">
                <SectorIcon sector={c.sector} size={24} />
              </span>
              <div className="card-body">
              <h3>{c.name}</h3>
              <p className="sector-name">{meta.sectors[c.sector]}</p>
              <div className="tags">
                <span className="tag">{c.size.toUpperCase()}</span>
                {c.city && <span className="tag">{c.city}</span>}
                <span className="tag soft">{ROLE_LABELS[c.role]}</span>
              </div>
              </div>
            </Link>
            {c.role === "owner" && (
              <button
                className="btn small danger card-delete"
                title={`Supprimer « ${c.name} »`}
                aria-label={`Supprimer « ${c.name} »`}
                onClick={() => remove(c)}
              >
                Supprimer
              </button>
            )}
          </div>
        ))}
      </div>
    </>
  );
}
