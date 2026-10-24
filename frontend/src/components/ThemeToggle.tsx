import { useState } from "react";

export type Theme = "system" | "light" | "dark";

const KEY = "visionboard_theme";
const NEXT: Record<Theme, Theme> = { system: "light", light: "dark", dark: "system" };
const LABEL: Record<Theme, string> = { system: "Thème : automatique", light: "Thème : clair", dark: "Thème : sombre" };
const ICON: Record<Theme, string> = { system: "◐", light: "☀", dark: "☾" };

function readTheme(): Theme {
  try {
    const value = localStorage.getItem(KEY);
    return value === "light" || value === "dark" ? value : "system";
  } catch {
    return "system";
  }
}

/** Applique le thème sur <html data-theme> ; « system » suit le réglage du système. */
export function applyTheme(theme: Theme = readTheme()) {
  if (theme === "system") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.setAttribute("data-theme", theme);
}

export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(readTheme);

  const cycle = () => {
    const next = NEXT[theme];
    try {
      if (next === "system") localStorage.removeItem(KEY);
      else localStorage.setItem(KEY, next);
    } catch {
      /* préférence non mémorisée */
    }
    applyTheme(next);
    setTheme(next);
  };

  return (
    <button type="button" className="btn ghost theme-toggle" onClick={cycle} title={LABEL[theme]} aria-label={LABEL[theme]}>
      <span aria-hidden="true">{ICON[theme]}</span>
    </button>
  );
}
