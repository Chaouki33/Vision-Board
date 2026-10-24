import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api, errorMessage, loadMeta } from "../api";
import DashboardsTab from "../components/DashboardsTab";
import SectorBanner from "../components/SectorBanner";
import DataTab from "../components/DataTab";
import ProfileTab from "../components/ProfileTab";
import ReportsTab from "../components/ReportsTab";
import type { Company, Meta } from "../types";
import Skeleton from "../components/Skeleton";

const TABS = {
  tableaux: "Tableaux de bord",
  donnees: "Données importées",
  rapports: "Rapports",
  profil: "Profil et membres",
} as const;
type Tab = keyof typeof TABS;

export default function CompanyPage() {
  const companyId = Number(useParams().companyId);
  const [params, setParams] = useSearchParams();
  const tab: Tab = (params.get("tab") as Tab) in TABS ? (params.get("tab") as Tab) : "tableaux";
  const [meta, setMeta] = useState<Meta | null>(null);
  const [company, setCompany] = useState<Company | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([loadMeta(), api<Company>(`/companies/${companyId}`)])
      .then(([m, c]) => {
        setMeta(m);
        setCompany(c);
      })
      .catch((err) => setError(errorMessage(err)));
  }, [companyId]);

  if (error) return <p className="error">{error}</p>;
  if (!meta || !company) return <Skeleton variant="cards" />;

  const canEdit = company.role !== "viewer";

  return (
    <>
      <SectorBanner
        sector={company.sector}
        title={company.name}
        back={<Link to="/" className="back">← Mes sociétés</Link>}
        subtitle={meta.sectors[company.sector]}
        tags={[meta.sizes[company.size], ...(company.city ? [company.city] : []),
          ...(company.employees ? [`${company.employees} salariés`] : [])]}
      />

      <nav className="tabs">
        {(Object.keys(TABS) as Tab[]).map((key) => (
          <button key={key} className={key === tab ? "active" : ""} onClick={() => setParams({ tab: key })}>
            {TABS[key]}
          </button>
        ))}
      </nav>

      {tab === "tableaux" && <DashboardsTab meta={meta} company={company} canEdit={canEdit} />}
      {tab === "donnees" && <DataTab meta={meta} company={company} canEdit={canEdit} />}
      {tab === "rapports" && <ReportsTab meta={meta} company={company} canEdit={canEdit} />}
      {tab === "profil" && <ProfileTab meta={meta} company={company} onUpdated={setCompany} />}
    </>
  );
}
