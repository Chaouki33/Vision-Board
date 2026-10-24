import { useEffect, useRef, type CSSProperties } from "react";
import { sectorStyle } from "../sectorThemes";
import SectorScene from "./SectorScene";
import { prefersReducedMotion } from "./AnimatedNumber";

// Courbes « de marché » qui traversent l'écran (repère 1440 × 900, étiré à la fenêtre).
const CURVES = [
  { d: "M-20 520 C160 470 290 565 470 485 S760 335 960 390 S1250 260 1460 300", className: "c1" },
  { d: "M-20 590 C200 565 330 620 520 560 S820 470 1010 520 S1280 430 1460 455", className: "c2" },
  { d: "M-20 420 C140 440 300 350 480 390 S790 480 990 300 S1260 210 1460 160", className: "c3" },
];

// Points de données posés sur les courbes (ils pulsent doucement).
const POINTS = [
  { x: 470, y: 485, c: "c1" }, { x: 960, y: 390, c: "c1" }, { x: 1250, y: 300, c: "c1" },
  { x: 520, y: 560, c: "c2" }, { x: 1010, y: 520, c: "c2" },
  { x: 480, y: 390, c: "c3" }, { x: 990, y: 300, c: "c3" }, { x: 1300, y: 195, c: "c3" },
];

/** Fond animé de l'application : halos lumineux, courbes financières et trame de points. */
export default function AppBackground({ variant = "app", sector }: { variant?: "app" | "login"; sector?: string | null }) {
  const ref = useRef<HTMLDivElement>(null);
  const reduced = prefersReducedMotion();

  // Léger effet de profondeur : les halos suivent le pointeur de la souris.
  useEffect(() => {
    const node = ref.current;
    if (!node || prefersReducedMotion() || window.matchMedia("(pointer: coarse)").matches) return;
    let frame = 0;
    const move = (e: PointerEvent) => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        node.style.setProperty("--mx", (e.clientX / window.innerWidth - 0.5).toFixed(3));
        node.style.setProperty("--my", (e.clientY / window.innerHeight - 0.5).toFixed(3));
      });
    };
    window.addEventListener("pointermove", move, { passive: true });
    return () => {
      window.removeEventListener("pointermove", move);
      cancelAnimationFrame(frame);
    };
  }, []);

  return (
    <div ref={ref} className={`bg-scene ${variant} ${sector ? "sector" : ""}`} aria-hidden="true"
      style={sector ? (sectorStyle(sector) as CSSProperties) : undefined}>
      <div className="bg-grid" />
      {sector && <SectorScene key={sector} sector={sector} variant="background" />}
      <div className="bg-orb o1" />
      <div className="bg-orb o2" />
      <div className="bg-orb o3" />
      <svg className="bg-curves" viewBox="0 0 1440 900" preserveAspectRatio="none">
        <defs>
          <linearGradient id="vb-fade" x1="0" x2="1" y1="0" y2="0">
            <stop offset="0" stopColor="white" stopOpacity="0" />
            <stop offset="0.15" stopColor="white" stopOpacity="1" />
            <stop offset="0.85" stopColor="white" stopOpacity="1" />
            <stop offset="1" stopColor="white" stopOpacity="0" />
          </linearGradient>
          <mask id="vb-edges">
            <rect width="1440" height="900" fill="url(#vb-fade)" />
          </mask>
          <mask id="vb-reveal">
            <rect width={reduced ? 1440 : 0} height="900" fill="white">
              {!reduced && <animate attributeName="width" from="0" to="1440" dur="3.2s" begin="0.2s" fill="freeze"
                calcMode="spline" keyTimes="0;1" keySplines="0.22 1 0.36 1" />}
            </rect>
          </mask>
        </defs>
        <g mask="url(#vb-edges)" className="bg-wave">
          {/* Courbes pleines dévoilées de gauche à droite au chargement */}
          <g mask="url(#vb-reveal)">
            {CURVES.filter((c) => c.className !== "c3").map((c) => (
              <path key={c.className} d={c.d} className={`bg-curve ${c.className}`} />
            ))}
          </g>
          {CURVES.filter((c) => c.className === "c3").map((c) => (
            <path key={c.className} d={c.d} className={`bg-curve ${c.className}`} />
          ))}
          {POINTS.map((p, i) => (
            <circle key={i} cx={p.x} cy={p.y} r="3.5" className={`bg-point ${p.c}`} style={{ animationDelay: `${1.6 + i * 0.35}s` }} />
          ))}
        </g>
      </svg>
      <div className="bg-vignette" />
    </div>
  );
}
