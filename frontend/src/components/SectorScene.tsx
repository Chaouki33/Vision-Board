import type { CSSProperties, ReactElement } from "react";
import { sectorStyle, sectorTheme } from "../sectorThemes";

/**
 * Décor animé propre à chaque secteur, dessiné dans un repère 1440 × 900.
 * - « banner » : rempli l'en-tête d'une carte ou d'une bannière (recadré) ;
 * - « background » : décor discret en fond d'écran.
 * Les couleurs viennent des variables --s1 (principale) et --s2 (secondaire).
 */
export default function SectorScene({ sector, variant = "banner" }: { sector: string; variant?: "banner" | "background" }) {
  const { motif } = sectorTheme(sector);
  const Motif = MOTIFS[motif] ?? Network;
  return (
    <svg
      className={`sector-scene ${variant} motif-${motif}`}
      viewBox="0 0 1440 900"
      preserveAspectRatio="xMidYMid slice"
      style={sectorStyle(sector) as CSSProperties}
      aria-hidden="true"
      focusable="false"
    >
      <Motif />
    </svg>
  );
}

/** Icône du secteur (trait), couleur héritée. */
export function SectorIcon({ sector, size = 22 }: { sector: string; size?: number }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={sectorTheme(sector).icon} />
    </svg>
  );
}

// ---------------------------------------------------------------- Décors
function Gear({ x, y, r, cls }: { x: number; y: number; r: number; cls: string }) {
  // Des dents obtenues par un trait épais en pointillés autour d'un cercle.
  const teeth = (2 * Math.PI * r) / 24;
  return (
    <g className={cls} style={{ transformOrigin: `${x}px ${y}px` }}>
      <circle cx={x} cy={y} r={r} className="m-stroke-2" strokeWidth={r * 0.32} strokeDasharray={`${teeth * 0.5} ${teeth * 0.5}`} fill="none" />
      <circle cx={x} cy={y} r={r * 0.82} className="m-fill" />
      <circle cx={x} cy={y} r={r * 0.3} className="m-hole" />
    </g>
  );
}

function Gears() {
  return (
    <>
      <Gear x={1080} y={300} r={210} cls="spin" />
      <Gear x={1395} y={560} r={130} cls="spin-rev" />
      <Gear x={830} y={660} r={95} cls="spin-rev" />
      {[0, 1, 2, 3, 4].map((i) => (
        <circle key={i} cx={900 + i * 90} cy={760 - (i % 2) * 60} r="7" className="m-spark" style={{ animationDelay: `${i * 0.5}s` }} />
      ))}
    </>
  );
}

function Wheat() {
  const stalks = Array.from({ length: 9 }, (_, i) => 760 + i * 80);
  return (
    <>
      {stalks.map((x, i) => (
        <g key={x} className="sway" style={{ transformOrigin: `${x}px 900px`, animationDelay: `${i * 0.25}s` }}>
          <path d={`M${x} 900 Q${x + 10} 600 ${x + 20} ${330 + (i % 3) * 40}`} className="m-stroke" strokeWidth="6" fill="none" />
          {[0, 1, 2, 3, 4, 5].map((k) => {
            const y = 360 + (i % 3) * 40 + k * 42;
            return (
              <g key={k}>
                <ellipse cx={x + 6} cy={y} rx="14" ry="26" transform={`rotate(-28 ${x + 6} ${y})`} className="m-fill" />
                <ellipse cx={x + 34} cy={y + 10} rx="14" ry="26" transform={`rotate(28 ${x + 34} ${y + 10})`} className="m-fill-2" />
              </g>
            );
          })}
        </g>
      ))}
    </>
  );
}

function Weave() {
  const rows = Array.from({ length: 9 }, (_, i) => 120 + i * 85);
  const cols = Array.from({ length: 9 }, (_, i) => 700 + i * 90);
  return (
    <>
      {rows.map((y, i) => (
        <path key={`r${y}`} d={`M600 ${y} q45 -30 90 0 t90 0 t90 0 t90 0 t90 0 t90 0 t90 0 t90 0 t90 0`}
          className={i % 2 ? "m-stroke flow" : "m-stroke-2 flow-rev"} strokeWidth="14" fill="none" strokeDasharray="60 30" />
      ))}
      {cols.map((x, i) => (
        <path key={`c${x}`} d={`M${x} 60 q-30 45 0 90 t0 90 t0 90 t0 90 t0 90 t0 90 t0 90 t0 90`}
          className={i % 2 ? "m-stroke-2 flow" : "m-stroke flow-rev"} strokeWidth="10" fill="none" strokeDasharray="40 50" opacity="0.7" />
      ))}
    </>
  );
}

function Crane() {
  const floors = Array.from({ length: 7 }, (_, i) => i);
  return (
    <>
      <path d="M980 900 V140 M940 900 V140 M940 140 H1400 M960 140 L1100 60 L1400 140 M940 200 L980 160 M940 300 L980 260 M940 400 L980 360 M940 500 L980 460 M940 600 L980 560 M940 700 L980 660 M940 800 L980 760"
        className="m-stroke" strokeWidth="10" fill="none" />
      <g className="swing" style={{ transformOrigin: "1300px 140px" }}>
        <path d="M1300 140 V430" className="m-stroke-2" strokeWidth="5" />
        <rect x="1250" y="430" width="100" height="56" rx="6" className="m-fill-2" />
      </g>
      {floors.map((f) => (
        <rect key={f} x="1080" y={820 - f * 90} width="300" height="80" rx="4" className="m-fill rise" style={{ animationDelay: `${f * 0.4}s` }} />
      ))}
    </>
  );
}

function Tags() {
  const tags = [
    { x: 760, y: 620, s: 1.1 }, { x: 980, y: 340, s: 1.4 }, { x: 1210, y: 560, s: 1 }, { x: 1300, y: 200, s: 0.9 },
    { x: 880, y: 180, s: 0.8 }, { x: 1120, y: 780, s: 0.9 },
  ];
  return (
    <>
      {tags.map((t, i) => (
        <g key={i} className="float" style={{ animationDelay: `${i * 0.7}s` }}>
          <g transform={`translate(${t.x} ${t.y}) scale(${t.s}) rotate(${i % 2 ? 12 : -14})`}>
            <path d="M0 -60 H120 L170 0 L120 60 H0 Z" className={i % 2 ? "m-fill" : "m-fill-2"} />
            <circle cx="125" cy="0" r="12" className="m-hole" />
            <path d="M24 -18 H80 M24 14 H64" className="m-hole-stroke" strokeWidth="10" strokeLinecap="round" />
          </g>
        </g>
      ))}
    </>
  );
}

function Network() {
  const nodes = [
    [820, 220], [1040, 140], [1260, 260], [1380, 470], [1180, 520], [960, 430], [790, 560], [1020, 720], [1300, 760],
  ];
  const links = [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 0], [5, 6], [6, 7], [7, 4], [7, 8], [8, 3], [1, 5], [2, 4]];
  return (
    <>
      {links.map(([a, b], i) => (
        <line key={i} x1={nodes[a][0]} y1={nodes[a][1]} x2={nodes[b][0]} y2={nodes[b][1]} className="m-stroke flow"
          strokeWidth="4" strokeDasharray="14 12" />
      ))}
      {nodes.map(([x, y], i) => (
        <g key={i}>
          <circle cx={x} cy={y} r={i % 3 === 0 ? 34 : 24} className="m-fill" />
          <circle cx={x} cy={y} r={i % 3 === 0 ? 34 : 24} className="m-ring pulse-ring" style={{ animationDelay: `${i * 0.4}s` }} />
        </g>
      ))}
    </>
  );
}

function Circuit() {
  const paths = [
    "M700 160 H900 V300 H1100 V200 H1440", "M700 420 H860 V520 H1040 V420 H1440", "M760 900 V700 H980 V620 H1200 V760 H1440",
    "M1100 0 V120 H1260 V340 H1440", "M640 640 H760 V560 H900",
  ];
  return (
    <>
      {paths.map((d, i) => (
        <g key={i}>
          <path d={d} className="m-stroke" strokeWidth="6" fill="none" />
          <path d={d} className="m-stroke-2 pulse-run" strokeWidth="8" fill="none" pathLength={1}
            strokeDasharray="0.08 0.92" style={{ animationDelay: `${i * 0.9}s` }} />
        </g>
      ))}
      <rect x="1040" y="380" width="170" height="170" rx="18" className="m-fill" />
      <rect x="1085" y="425" width="80" height="80" rx="8" className="m-hole" />
      {[0, 1, 2, 3].map((k) => (
        <path key={k} d={`M${1065 + k * 40} 380 V350 M${1065 + k * 40} 550 V580`} className="m-stroke" strokeWidth="8" />
      ))}
    </>
  );
}

function Roads() {
  const roads = ["M560 760 C820 700 960 520 1180 500 S1440 380 1500 300", "M640 900 C900 820 1100 760 1300 640 S1480 560 1520 520"];
  return (
    <>
      {roads.map((d, i) => (
        <g key={i}>
          <path d={d} className="m-road" strokeWidth={i ? 46 : 56} fill="none" />
          <path d={d} className="m-stroke-2 flow" strokeWidth="5" fill="none" strokeDasharray="34 26" />
          {[0, 1].map((k) => (
            <g key={k}>
              <rect x="-34" y="-18" width="68" height="36" rx="8" className="m-fill">
                <animateMotion dur={`${9 + i * 3}s`} begin={`${k * 4.5}s`} repeatCount="indefinite" rotate="auto" path={d} />
              </rect>
            </g>
          ))}
        </g>
      ))}
      <circle cx="1240" cy="180" r="18" className="m-spark" />
      <circle cx="900" cy="320" r="12" className="m-spark" style={{ animationDelay: "1.2s" }} />
    </>
  );
}

function Stars() {
  const stars = [[820, 160], [940, 300], [1100, 120], [1250, 260], [1380, 140], [1000, 470], [1320, 430], [880, 560]];
  return (
    <>
      <g className="spin-slow" style={{ transformOrigin: "1180px 640px" }}>
        {Array.from({ length: 12 }, (_, i) => (
          <rect key={i} x="1172" y="420" width="16" height="70" rx="8" className="m-fill-2" transform={`rotate(${i * 30} 1180 640)`} />
        ))}
      </g>
      <circle cx="1180" cy="640" r="110" className="m-fill-2" />
      {stars.map(([x, y], i) => (
        <path key={i} d={`M${x} ${y - 26} L${x + 7} ${y - 7} L${x + 26} ${y} L${x + 7} ${y + 7} L${x} ${y + 26} L${x - 7} ${y + 7} L${x - 26} ${y} L${x - 7} ${y - 7} Z`}
          className="m-fill twinkle" style={{ animationDelay: `${i * 0.45}s`, transformOrigin: `${x}px ${y}px` }} />
      ))}
      <path d="M560 900 Q900 760 1440 820 V900 Z" className="m-fill" opacity="0.5" />
    </>
  );
}

function Pulse() {
  const ecg = "M560 520 H820 L860 440 L900 600 L950 300 L1000 700 L1040 520 H1180 L1210 470 L1240 560 L1270 520 H1500";
  return (
    <>
      <path d={ecg} className="m-stroke" strokeWidth="5" fill="none" opacity="0.35" />
      <path d={ecg} className="m-stroke-2 ecg" strokeWidth="9" fill="none" pathLength={1} strokeDasharray="0.25 0.75" />
      {[[900, 200, 1], [1250, 220, 0.8], [1340, 720, 1.1], [820, 760, 0.7]].map(([x, y, s], i) => (
        <g key={i} className="float" style={{ animationDelay: `${i * 0.8}s` }}>
          <path transform={`translate(${x} ${y}) scale(${s})`} d="M-22 -66 H22 V-22 H66 V22 H22 V66 H-22 V22 H-66 V-22 H-22 Z" className="m-fill" />
        </g>
      ))}
    </>
  );
}

function Fields() {
  const rows = Array.from({ length: 7 }, (_, i) => i);
  return (
    <>
      <circle cx="1220" cy="200" r="100" className="m-fill-2 glow" />
      {rows.map((i) => (
        <path key={i} d={`M560 ${560 + i * 55} Q1000 ${470 + i * 70} 1500 ${520 + i * 62}`} className={i % 2 ? "m-stroke" : "m-stroke-2"}
          strokeWidth={10 + i * 2} fill="none" opacity={0.5 + i * 0.07} />
      ))}
      {[820, 980, 1140, 1300].map((x, i) => (
        <g key={x} className="sway" style={{ transformOrigin: `${x}px 560px`, animationDelay: `${i * 0.5}s` }}>
          <path d={`M${x} 560 V450`} className="m-stroke" strokeWidth="7" />
          <path d={`M${x} 470 c0-50 40-80 90-80 0 55-40 80-90 80z`} className="m-fill" />
          <path d={`M${x} 500 c0-40-30-60-70-60 0 45 30 60 70 60z`} className="m-fill-2" />
        </g>
      ))}
    </>
  );
}

function Skyline() {
  const buildings = [
    { x: 700, w: 120, h: 300 }, { x: 830, w: 150, h: 470 }, { x: 990, w: 110, h: 360 }, { x: 1110, w: 170, h: 620 },
    { x: 1290, w: 130, h: 420 }, { x: 1430, w: 120, h: 300 },
  ];
  const windows: ReactElement[] = [];
  buildings.forEach((b, i) => {
    for (let row = 0; row < Math.floor(b.h / 60) - 1; row++) {
      for (let col = 0; col < Math.floor(b.w / 40); col++) {
        const k = i * 100 + row * 10 + col;
        windows.push(
          <rect key={k} x={b.x + 14 + col * 40} y={900 - b.h + 30 + row * 60} width="20" height="28" rx="3"
            className="m-window" style={{ animationDelay: `${(k * 0.37) % 6}s` }} />,
        );
      }
    }
  });
  return (
    <>
      {buildings.map((b, i) => (
        <rect key={i} x={b.x} y={900 - b.h} width={b.w} height={b.h} rx="6" className={i % 2 ? "m-fill" : "m-fill-dark"} />
      ))}
      {windows}
      <path d="M1195 280 V220" className="m-stroke-2" strokeWidth="6" />
      <circle cx="1195" cy="214" r="9" className="m-spark" />
    </>
  );
}

const MOTIFS: Record<string, () => ReactElement> = {
  gears: Gears, wheat: Wheat, weave: Weave, crane: Crane, tags: Tags, network: Network, circuit: Circuit,
  roads: Roads, stars: Stars, pulse: Pulse, fields: Fields, skyline: Skyline,
};
