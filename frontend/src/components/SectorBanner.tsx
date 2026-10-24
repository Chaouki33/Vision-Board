import type { CSSProperties, ReactNode } from "react";
import { sectorStyle } from "../sectorThemes";
import SectorScene, { SectorIcon } from "./SectorScene";

interface Props {
  sector: string;
  title: string;
  subtitle?: ReactNode;
  tags?: string[];
  back?: ReactNode;
  actions?: ReactNode;
  compact?: boolean;
}

/** En-tête aux couleurs du secteur, avec son décor animé. */
export default function SectorBanner({ sector, title, subtitle, tags, back, actions, compact }: Props) {
  return (
    <header className={`sector-banner ${compact ? "compact" : ""}`} style={sectorStyle(sector) as CSSProperties}>
      <SectorScene sector={sector} />
      <div className="sector-banner-content">
        <span className="sector-badge">
          <SectorIcon sector={sector} size={compact ? 22 : 28} />
        </span>
        <div>
          {back}
          <h1>{title}</h1>
          {subtitle && <p className="banner-sub">{subtitle}</p>}
          {tags && tags.length > 0 && (
            <div className="banner-tags">
              {tags.map((t) => (
                <span key={t}>{t}</span>
              ))}
            </div>
          )}
        </div>
        {actions && <div className="banner-actions">{actions}</div>}
      </div>
    </header>
  );
}
