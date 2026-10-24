import { useEffect, useRef, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth";
import AppBackground from "../components/AppBackground";
import ExplainerVideo from "../components/ExplainerVideo";
import { LogoFull, LogoMark } from "../components/Logo";
import ThemeToggle from "../components/ThemeToggle";

const FEATURES = [
  { color: "c-commercial", icon: "M4 19h16M7 16V9M12 16V5M17 16v-4", title: "Commercial et ventes",
    text: "Chiffre d'affaires, marges, clients, impayés, performance des commerciaux et des régions." },
  { color: "c-production", icon: "M3 21V10l6 4V10l6 4V6l6 4v11zM7 17h2M13 17h2", title: "Production",
    text: "Volumes, respect du plan, TRS, rebuts, temps d'arrêt et coût de revient par ligne." },
  { color: "c-stock", icon: "M3 7l9-4 9 4-9 4zM3 7v10l9 4 9-4V7M12 11v10", title: "Gestion des stocks",
    text: "Valeur du stock, ruptures, articles sous le seuil, rotation et péremption." },
  { color: "c-rh", icon: "M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM2 21c0-4 3-6 7-6s7 2 7 6M17 11a3 3 0 1 0 0-6M22 21c0-3-2-5-5-5",
    title: "Ressources humaines", text: "Effectif, contrats, stagiaires, recrutements, masse salariale, absences et congés." },
  { color: "c-tresorerie", icon: "M3 7h18v12H3zM3 11h18M7 15h3", title: "Trésorerie",
    text: "Soldes bancaires, encaissements, décaissements, flux nets et autonomie en mois." },
  { color: "c-comptabilite", icon: "M12 3v18M5 7h14M7 7l-4 8a4 4 0 0 0 8 0zM17 7l-4 8a4 4 0 0 0 8 0z",
    title: "Comptabilité et finance", text: "Balance PCM, CPC, bilan CGNC, soldes de gestion et 15 ratios financiers." },
];

const STEPS = [
  { n: "1", title: "Décrivez votre société", text: "Secteur, taille, ville : Vision Board sélectionne les tableaux de bord et les indicateurs pertinents." },
  { n: "2", title: "Ajoutez vos données", text: "Importez vos fichiers Excel ou CSV, utilisez nos modèles, ou saisissez directement dans l'application." },
  { n: "3", title: "Pilotez et décidez", text: "Indicateurs, alertes et graphiques en temps réel, puis un rapport d'analyse avec des recommandations." },
];

const SECTORS = ["Commerce", "Industrie", "Agroalimentaire", "Textile", "BTP", "Services et conseil", "Informatique",
  "Transport et logistique", "Hôtellerie et restauration", "Santé et pharmacie", "Agriculture", "Immobilier"];

const STATS = [
  { value: "6", label: "domaines d'analyse" },
  { value: "70+", label: "indicateurs prêts à l'emploi" },
  { value: "12", label: "secteurs d'activité" },
  { value: "PDF · Word", label: "rapports d'analyse" },
];

function Icon({ d }: { d: string }) {
  return (
    <svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={d} />
    </svg>
  );
}

/** Fait apparaître les blocs quand ils entrent dans l'écran. */
function Reveal({ children, className = "" }: { children: ReactNode; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const node = ref.current;
    if (!node || !("IntersectionObserver" in window)) {
      node?.classList.add("visible");
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => entries.forEach((e) => e.isIntersecting && (e.target.classList.add("visible"), observer.unobserve(e.target))),
      { threshold: 0.15 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  return (
    <div ref={ref} className={`reveal ${className}`}>
      {children}
    </div>
  );
}

export default function LandingPage() {
  const { user } = useAuth();
  const primary = user
    ? { to: "/", label: "Accéder à mon espace" }
    : { to: "/login?inscription=1", label: "Commencer gratuitement" };

  return (
    <div className="landing">
      <AppBackground variant="login" />

      <header className="landing-nav">
        <Link to="/bienvenue" className="brand">
          <LogoMark size={36} />
          <span className="wordmark">Vision Board</span>
        </Link>
        <nav className="landing-links">
          <a href="#fonctionnalites">Fonctionnalités</a>
          <a href="#comment">Comment ça marche</a>
          <a href="#secteurs">Secteurs</a>
        </nav>
        <div className="landing-actions">
          <ThemeToggle />
          {user ? (
            <Link className="btn primary" to="/">Mon espace</Link>
          ) : (
            <>
              <Link className="btn ghost" to="/login">Se connecter</Link>
              <Link className="btn primary hide-small" to="/login?inscription=1">Créer un compte</Link>
            </>
          )}
        </div>
      </header>

      <section className="hero">
        <div className="hero-text">
          <span className="eyebrow">Tableaux de bord · Analyse · Aide à la décision</span>
          <h1>
            Pilotez votre entreprise avec des <span className="gradient-text">tableaux de bord intelligents</span>
          </h1>
          <p className="hero-lead">
            Vision Board transforme vos fichiers Excel, CSV ou balances comptables en indicateurs clairs, adaptés à votre
            secteur et à la taille de votre entreprise, puis rédige l'analyse pour vous aider à décider.
          </p>
          <div className="hero-ctas">
            <Link className="btn primary big" to={primary.to}>{primary.label}</Link>
            <a className="btn ghost big" href="#comment">Voir comment ça marche</a>
          </div>
          <ul className="hero-stats">
            {STATS.map((s) => (
              <li key={s.label}>
                <strong>{s.value}</strong>
                <span>{s.label}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="hero-media">
          <ExplainerVideo />
        </div>
      </section>

      <section id="fonctionnalites" className="landing-section">
        <Reveal>
          <h2>Six domaines, une vision complète</h2>
          <p className="section-lead">Choisissez les analyses dont vous avez besoin : les indicateurs sont sélectionnés pour vous.</p>
        </Reveal>
        <div className="feature-grid">
          {FEATURES.map((f, i) => (
            <Reveal key={f.title} className={`feature-card ${f.color} delay-${i % 3}`}>
              <span className="feature-icon"><Icon d={f.icon} /></span>
              <h3>{f.title}</h3>
              <p>{f.text}</p>
            </Reveal>
          ))}
        </div>
      </section>

      <section id="comment" className="landing-section">
        <Reveal>
          <h2>Comment ça marche</h2>
          <p className="section-lead">De vos fichiers à la décision, en trois étapes.</p>
        </Reveal>
        <div className="steps">
          {STEPS.map((s, i) => (
            <Reveal key={s.n} className={`step-card delay-${i}`}>
              <span className="step-num">{s.n}</span>
              <h3>{s.title}</h3>
              <p>{s.text}</p>
            </Reveal>
          ))}
        </div>
      </section>

      <section id="secteurs" className="landing-section">
        <Reveal>
          <h2>Adapté à votre secteur</h2>
          <p className="section-lead">
            Chaque secteur a ses priorités : panier moyen pour le commerce, TRS pour l'industrie, taux de rebut pour
            l'agroalimentaire, délais clients pour les services…
          </p>
        </Reveal>
        <Reveal className="sector-cloud">
          {SECTORS.map((s, i) => (
            <span key={s} className={`sector-chip tone-${i % 6}`}>{s}</span>
          ))}
        </Reveal>
      </section>

      <section className="landing-section">
        <Reveal className="cta-band">
          <LogoFull size={150} />
          <div>
            <h2>Prêt à y voir plus clair ?</h2>
            <p>Créez votre espace, ajoutez une première société et obtenez vos premiers indicateurs en quelques minutes.</p>
            <Link className="btn primary big" to={primary.to}>{primary.label}</Link>
          </div>
        </Reveal>
      </section>

      <footer className="landing-footer">
        <span>© {new Date().getFullYear()} Vision Board</span>
        <span>Tableaux de bord et analyses pour les entreprises marocaines</span>
      </footer>
    </div>
  );
}
