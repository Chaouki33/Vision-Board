import { useEffect, useState, type CSSProperties } from "react";
import { Link, NavLink, Outlet, useLocation, useMatch } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import type { Company, Dashboard } from "../types";
import { sectorStyle } from "../sectorThemes";
import AppBackground from "./AppBackground";
import Icon, { type IconName } from "./Icons";
import { LogoMark } from "./Logo";
import ThemeToggle from "./ThemeToggle";

const COLLAPSE_KEY = "visionboard_sidebar_collapsed";

function readCollapsed(): boolean {
  try {
    return localStorage.getItem(COLLAPSE_KEY) === "1";
  } catch {
    return false;
  }
}

const COMPANY_SECTIONS: { tab: string; label: string; icon: IconName }[] = [
  { tab: "tableaux", label: "Tableaux de bord", icon: "dashboard" },
  { tab: "donnees", label: "Données importées", icon: "data" },
  { tab: "rapports", label: "Rapports", icon: "report" },
  { tab: "profil", label: "Profil et membres", icon: "profile" },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const companyMatch = useMatch("/companies/:companyId/*");
  const companyId = companyMatch?.params.companyId ? Number(companyMatch.params.companyId) : null;
  const [collapsed, setCollapsed] = useState(readCollapsed);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [company, setCompany] = useState<Company | null>(null);
  const [dashboards, setDashboards] = useState<Dashboard[]>([]);

  // Société en cours : nom et tableaux de bord, rafraîchis à chaque navigation (création, suppression…).
  useEffect(() => {
    if (!companyId) {
      setCompany(null);
      setDashboards([]);
      return;
    }
    Promise.all([api<Company>(`/companies/${companyId}`), api<Dashboard[]>(`/companies/${companyId}/dashboards`)])
      .then(([c, d]) => {
        setCompany(c);
        setDashboards(d);
      })
      .catch(() => {
        setCompany(null);
        setDashboards([]);
      });
  }, [companyId, location.pathname, location.search]);

  useEffect(() => setMobileOpen(false), [location.pathname, location.search]);

  const toggleCollapsed = () => {
    setCollapsed((value) => {
      try {
        localStorage.setItem(COLLAPSE_KEY, value ? "0" : "1");
      } catch {
        /* préférence non mémorisée */
      }
      return !value;
    });
  };

  const tab = new URLSearchParams(location.search).get("tab") ?? "tableaux";
  const onCompanyHome = companyId !== null && location.pathname === `/companies/${companyId}`;

  return (
    <div className={`app ${collapsed ? "collapsed" : ""} ${mobileOpen ? "nav-open" : ""}`}>
      <AppBackground sector={company?.sector} />
      <aside className="sidebar" aria-label="Navigation principale">
        <Link to="/" className="brand sidebar-brand" title="Vision Board">
          <LogoMark size={34} />
          <span className="wordmark">Vision Board</span>
        </Link>

        <nav className="side-nav">
          <NavLink to="/" end className="side-link" title="Mes sociétés">
            <Icon name="companies" />
            <span>Mes sociétés</span>
          </NavLink>
          {user?.is_admin && (
            <NavLink to="/admin" className="side-link" title="Administration">
              <Icon name="admin" />
              <span>Administration</span>
            </NavLink>
          )}

          {company && (
            <div className="side-group">
              <div className="side-title" title={company.name} style={sectorStyle(company.sector) as CSSProperties}>
                <span className="sector-dot" />
                {company.name}
              </div>
              {COMPANY_SECTIONS.map((s) => (
                <Link
                  key={s.tab}
                  to={`/companies/${company.id}?tab=${s.tab}`}
                  className={`side-link ${onCompanyHome && tab === s.tab ? "active" : ""}`}
                  title={s.label}
                >
                  <Icon name={s.icon} />
                  <span>{s.label}</span>
                </Link>
              ))}
              {dashboards.length > 0 && (
                <div className="side-sub">
                  {dashboards.map((d) => (
                    <NavLink key={d.id} to={`/companies/${company.id}/dashboards/${d.id}`} className="side-link sub"
                      title={d.title}>
                      <Icon name="chart" size={15} />
                      <span>{d.title}</span>
                    </NavLink>
                  ))}
                </div>
              )}
            </div>
          )}
        </nav>

        <div className="side-footer">
          <NavLink to="/compte" className="side-link user" title="Mon compte">
            <span className="avatar" aria-hidden="true">
              {user?.full_name.trim().charAt(0).toUpperCase()}
            </span>
            <span className="user-text">
              {user?.full_name}
              <small>{user?.is_admin ? "Administrateur" : "Utilisateur"}</small>
            </span>
          </NavLink>
          <div className="side-actions">
            <ThemeToggle />
            <button className="btn ghost icon-btn" onClick={logout} title="Déconnexion" aria-label="Déconnexion">
              <Icon name="logout" />
            </button>
            <button className="btn ghost icon-btn collapse-btn" onClick={toggleCollapsed}
              title={collapsed ? "Déplier le menu" : "Replier le menu"} aria-label={collapsed ? "Déplier le menu" : "Replier le menu"}>
              <Icon name="collapse" />
            </button>
          </div>
        </div>
      </aside>

      <div className="scrim" onClick={() => setMobileOpen(false)} aria-hidden="true" />

      <div className="app-main">
        <header className="mobile-bar">
          <button className="btn ghost icon-btn" onClick={() => setMobileOpen(true)} aria-label="Ouvrir le menu">
            <Icon name="menu" />
          </button>
          <Link to="/" className="brand">
            <LogoMark size={28} />
            <span className="wordmark">Vision Board</span>
          </Link>
        </header>
        <main className="container">
          {/* La clé relance l'animation d'entrée à chaque changement de page. */}
          <div key={location.pathname + location.search} className="page-enter">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
