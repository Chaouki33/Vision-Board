/** Identité visuelle de chaque secteur : couleurs, icône (tracé 24×24) et décor animé. */
export interface SectorTheme {
  color: string; // couleur principale
  accent: string; // couleur secondaire (lumières, détails)
  icon: string;
  motif: string; // décor animé (voir SectorScene)
}

export const SECTOR_THEMES: Record<string, SectorTheme> = {
  industrie: {
    color: "#4b6584", accent: "#f59e0b", motif: "gears",
    icon: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 0 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 0 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 0 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 0 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z",
  },
  agroalimentaire: {
    color: "#b45309", accent: "#facc15", motif: "wheat",
    icon: "M12 22V8M12 8c0-3 2-5 4-6-.5 3-2 5-4 6zM12 8C12 5 10 3 8 2c.5 3 2 5 4 6zM12 13c1.5-2.5 3.5-3.5 6-3.5-1 2.5-3.5 3.5-6 3.5zM12 13c-1.5-2.5-3.5-3.5-6-3.5 1 2.5 3.5 3.5 6 3.5zM12 18c1.5-2.5 3.5-3.5 6-3.5-1 2.5-3.5 3.5-6 3.5zM12 18c-1.5-2.5-3.5-3.5-6-3.5 1 2.5 3.5 3.5 6 3.5z",
  },
  textile: {
    color: "#9333ea", accent: "#f472b6", motif: "weave",
    icon: "M6 9a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM6 21a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM20 4L8.1 15.9M14.5 14.5L20 20M8.1 8.1L12 12",
  },
  btp: {
    color: "#c2410c", accent: "#facc15", motif: "crane",
    icon: "M2 20h20M5 20V9l5-3v14M10 6l9 0M19 6v4M14 20v-6h4v6M3 6h4",
  },
  commerce: {
    color: "#2563eb", accent: "#38bdf8", motif: "tags",
    icon: "M6 7h12l-1 13H7zM9 7a3 3 0 0 1 6 0",
  },
  services: {
    color: "#4f46e5", accent: "#a5b4fc", motif: "network",
    icon: "M4 8h16v11H4zM9 8V6a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2M4 13h16",
  },
  tic: {
    color: "#0891b2", accent: "#67e8f9", motif: "circuit",
    icon: "M7 7h10v10H7zM10 10h4v4h-4zM10 3v4M14 3v4M10 17v4M14 17v4M3 10h4M3 14h4M17 10h4M17 14h4",
  },
  transport: {
    color: "#0f766e", accent: "#5eead4", motif: "roads",
    icon: "M2 7h12v9H2zM14 10h4l3 3v3h-7zM6 19a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM17 19a2 2 0 1 0 0-4 2 2 0 0 0 0 4z",
  },
  hotellerie_restauration: {
    color: "#db2777", accent: "#fdba74", motif: "stars",
    icon: "M12 3l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.4 6.8 19.1l1-5.8L3.5 9.2l5.9-.9z",
  },
  sante: {
    color: "#dc2626", accent: "#fca5a5", motif: "pulse",
    icon: "M10 3h4v7h7v4h-7v7h-4v-7H3v-4h7z",
  },
  agriculture: {
    color: "#15803d", accent: "#bef264", motif: "fields",
    icon: "M12 21v-9M12 12c0-4 3-7 8-7 0 5-3 7-8 7zM12 15c0-3-2-5-6-5 0 4 2 5 6 5z",
  },
  immobilier: {
    color: "#334155", accent: "#e2bf62", motif: "skyline",
    icon: "M3 21h18M5 21V8l6-4v17M11 21V10h8v11M8 9h.01M8 13h.01M8 17h.01M14 13h2M14 17h2",
  },
};

export const DEFAULT_THEME: SectorTheme = SECTOR_THEMES.commerce;

export function sectorTheme(sector: string | null | undefined): SectorTheme {
  return (sector && SECTOR_THEMES[sector]) || DEFAULT_THEME;
}

/** Variables CSS à poser sur un élément pour le colorer aux couleurs du secteur. */
export function sectorStyle(sector: string | null | undefined): Record<string, string> {
  const t = sectorTheme(sector);
  return { "--s1": t.color, "--s2": t.accent };
}
