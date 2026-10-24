import { useEffect, useRef, useState } from "react";
import { formatValue } from "../format";

const DURATION_MS = 900;

export function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** Valeur de KPI qui « défile » jusqu'à sa valeur finale (désactivé si l'utilisateur réduit les animations). */
export default function AnimatedNumber({ value, unit }: { value: number | null; unit: string }) {
  const [shown, setShown] = useState<number | null>(value === null || prefersReducedMotion() ? value : 0);
  const frame = useRef(0);

  useEffect(() => {
    if (value === null || prefersReducedMotion()) {
      setShown(value);
      return;
    }
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / DURATION_MS);
      const eased = 1 - Math.pow(1 - t, 3); // départ rapide, arrivée douce
      setShown(t < 1 ? value * eased : value);
      if (t < 1) frame.current = requestAnimationFrame(tick);
    };
    frame.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame.current);
  }, [value]);

  return (
    <span className="animated-number" aria-label={formatValue(value, unit)}>
      {formatValue(shown, unit)}
    </span>
  );
}
