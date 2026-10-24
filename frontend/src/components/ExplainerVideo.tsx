import { useEffect, useState } from "react";
import { prefersReducedMotion } from "./AnimatedNumber";

const SCENE_MS = 4800;

const SCENES = [
  { title: "Importez vos fichiers", text: "Excel, CSV ou saisie directe : les colonnes sont reconnues automatiquement." },
  { title: "Les bons indicateurs", text: "Vision Board choisit les KPI adaptés à votre secteur et à votre taille." },
  { title: "Des graphiques clairs", text: "Évolutions, classements, alertes : tout se calcule et se dessine pour vous." },
  { title: "Un rapport prêt à partager", text: "Synthèse, points de vigilance et recommandations, en PDF ou Word." },
];

/**
 * « Vidéo » explicative animée en boucle (4 scènes), construite en HTML/SVG : légère, nette à toutes les
 * tailles et adaptée aux thèmes clair et sombre. Si un fichier public/intro.mp4 est ajouté au projet,
 * il est lu à la place.
 */
export default function ExplainerVideo() {
  const reduced = prefersReducedMotion();
  const [scene, setScene] = useState(0);
  const [paused, setPaused] = useState(reduced);
  const [hasVideo, setHasVideo] = useState(false);

  useEffect(() => {
    if (paused || hasVideo) return;
    const timer = window.setTimeout(() => setScene((s) => (s + 1) % SCENES.length), SCENE_MS);
    return () => window.clearTimeout(timer);
  }, [scene, paused, hasVideo]);

  return (
    <div className={`explainer ${paused ? "paused" : ""}`} aria-label="Présentation animée de Vision Board">
      <video
        className={`explainer-video ${hasVideo ? "ready" : ""}`}
        src="/intro.mp4"
        autoPlay
        muted
        loop
        playsInline
        aria-hidden={!hasVideo}
        onLoadedData={() => setHasVideo(true)}
        onError={() => setHasVideo(false)}
      />

      {!hasVideo && (
        <>
          <div className="explainer-stage">
            {/* La clé relance les animations de la scène à chaque passage */}
            <div key={scene} className={`scene scene-${scene}`}>
              {scene === 0 && <SceneImport />}
              {scene === 1 && <SceneKpis />}
              {scene === 2 && <SceneCharts />}
              {scene === 3 && <SceneReport />}
            </div>
          </div>

          <div className="explainer-caption" aria-live="polite">
            <span className="step">
              Étape {scene + 1}/{SCENES.length}
            </span>
            <strong>{SCENES[scene].title}</strong>
            <span>{SCENES[scene].text}</span>
          </div>

          <div className="explainer-controls">
            <button
              className="play-btn"
              onClick={() => setPaused(!paused)}
              aria-label={paused ? "Lire la présentation" : "Mettre en pause"}
              title={paused ? "Lire" : "Pause"}
            >
              {paused ? "▶" : "❚❚"}
            </button>
            <div className="timeline">
              {SCENES.map((s, i) => (
                <button key={s.title} className={`chapter ${i < scene ? "done" : ""} ${i === scene ? "current" : ""}`}
                  onClick={() => setScene(i)} aria-label={`Aller à l'étape ${i + 1} : ${s.title}`}>
                  <span key={i === scene ? `p${scene}` : undefined} style={{ animationDuration: `${SCENE_MS}ms` }} />
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function SceneImport() {
  const files = [
    { name: "ventes_2026.xlsx", kind: "XLS", cls: "f1" },
    { name: "personnel.csv", kind: "CSV", cls: "f2" },
    { name: "balance_2025.xlsx", kind: "XLS", cls: "f3" },
  ];
  return (
    <div className="sc-import">
      <div className="files">
        {files.map((f) => (
          <div key={f.name} className={`file-chip ${f.cls}`}>
            <span className="file-kind">{f.kind}</span>
            {f.name}
          </div>
        ))}
      </div>
      <div className="dropzone">
        <svg viewBox="0 0 24 24" width="44" height="44" aria-hidden="true">
          <path d="M12 16V4M7 9l5-5 5 5M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" fill="none" stroke="currentColor"
            strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <span>Déposez vos fichiers</span>
        <div className="recognised">
          <span>✓ 12 colonnes reconnues</span>
          <span>✓ 1 418 lignes importées</span>
        </div>
      </div>
    </div>
  );
}

function SceneKpis() {
  const tiles = [
    { label: "Chiffre d'affaires", value: "1,8 M MAD", tag: "▲ +5,4 %", tone: "good", color: "c-commercial" },
    { label: "Marge brute", value: "26,9 %", tag: "✓ Bon niveau", tone: "good", color: "c-comptabilite" },
    { label: "Taux d'impayés", value: "20 %", tag: "! À surveiller", tone: "warn", color: "c-tresorerie" },
    { label: "TRS des lignes", value: "77,4 %", tag: "✓ Bon niveau", tone: "good", color: "c-production" },
    { label: "Ruptures de stock", value: "7,1 %", tag: "! À surveiller", tone: "warn", color: "c-stock" },
    { label: "Effectif", value: "39", tag: "6 stagiaires", tone: "neutral", color: "c-rh" },
  ];
  return (
    <div className="sc-kpis">
      <div className="sector-pill">Agroalimentaire · PME · 41 salariés</div>
      <div className="kpi-grid">
        {tiles.map((t) => (
          <div key={t.label} className={`kpi-tile ${t.color}`}>
            <span className="kpi-label">{t.label}</span>
            <span className="kpi-value">{t.value}</span>
            <span className={`kpi-tag ${t.tone}`}>{t.tag}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function SceneCharts() {
  const bars = [62, 78, 55, 90, 70, 96, 84];
  const line = "M10 112 L60 96 L110 102 L160 70 L210 78 L260 44 L310 30";
  return (
    <div className="sc-charts">
      <div className="chart-panel">
        <span className="panel-title">CA mensuel</span>
        <svg viewBox="0 0 320 130" aria-hidden="true">
          {[30, 60, 90, 120].map((y) => (
            <line key={y} x1="0" x2="320" y1={y} y2={y} className="grid-line" />
          ))}
          {bars.map((h, i) => (
            <rect key={i} x={14 + i * 44} y={120 - h} width="24" height={h} rx="4" className="bar"
              style={{ animationDelay: `${0.15 + i * 0.12}s` }} />
          ))}
        </svg>
      </div>
      <div className="chart-panel">
        <span className="panel-title">Trésorerie</span>
        <svg viewBox="0 0 320 130" aria-hidden="true">
          {[30, 60, 90, 120].map((y) => (
            <line key={y} x1="0" x2="320" y1={y} y2={y} className="grid-line" />
          ))}
          <path d={`${line} L310 125 L10 125 Z`} className="area" />
          <path d={line} className="trend" pathLength={1} />
          <circle cx="310" cy="30" r="5" className="end-dot" />
        </svg>
      </div>
    </div>
  );
}

function SceneReport() {
  return (
    <div className="sc-report">
      <div className="doc">
        <div className="doc-brand">VISION BOARD</div>
        <div className="doc-title">Analyse commerciale</div>
        <div className="doc-verdict">! Appréciation : à surveiller</div>
        <div className="doc-lines">
          <span style={{ width: "92%" }} />
          <span style={{ width: "86%" }} />
          <span style={{ width: "64%" }} />
        </div>
        <div className="doc-subtitle">Recommandations</div>
        <ul className="doc-recos">
          <li><b className="prio high">Haute</b> Renforcer le recouvrement</li>
          <li><b className="prio mid">Moyenne</b> Diversifier les clients</li>
          <li><b className="prio low">Basse</b> Suivi mensuel du tableau</li>
        </ul>
      </div>
      <div className="exports">
        <span className="badge pdf">PDF</span>
        <span className="badge word">Word</span>
      </div>
    </div>
  );
}
