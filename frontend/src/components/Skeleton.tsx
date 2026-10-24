/** Écran de chargement animé (blocs gris qui scintillent) à la place d'un simple « Chargement… ». */
export default function Skeleton({ variant = "cards", label = "Chargement" }: { variant?: "cards" | "dashboard" | "page"; label?: string }) {
  const count = variant === "dashboard" ? 8 : variant === "cards" ? 6 : 3;
  return (
    <div className="skeleton-page" role="status" aria-live="polite">
      <span className="sr-only">{label}…</span>
      <div className="sk sk-title" />
      <div className="sk sk-line" />
      <div className={variant === "dashboard" ? "tiles" : "grid cards"}>
        {Array.from({ length: count }, (_, i) => (
          <div key={i} className={`sk sk-card ${variant === "dashboard" ? "small" : ""}`} />
        ))}
      </div>
      {variant === "dashboard" && (
        <div className="charts">
          <div className="sk sk-chart" />
          <div className="sk sk-chart" />
        </div>
      )}
    </div>
  );
}
