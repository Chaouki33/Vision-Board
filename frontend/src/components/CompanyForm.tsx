import { useState, type FormEvent } from "react";
import { errorMessage } from "../api";
import type { CompanyInput, Meta } from "../types";
import DomainPicker, { suggestedDomains } from "./DomainPicker";

interface Props {
  meta: Meta;
  initial?: Partial<CompanyInput>;
  submitLabel: string;
  disabled?: boolean;
  /** Création : propose de choisir d'emblée les tableaux de bord. */
  withDomains?: boolean;
  onSubmit: (data: CompanyInput) => Promise<void>;
  onCancel?: () => void;
}

const toNumber = (v: string) => (v.trim() === "" ? null : Number(v));

export default function CompanyForm({ meta, initial = {}, submitLabel, disabled, withDomains, onSubmit, onCancel }: Props) {
  const [name, setName] = useState(initial.name ?? "");
  const [sector, setSector] = useState(initial.sector ?? "");
  const [size, setSize] = useState(initial.size ?? "");
  const [employees, setEmployees] = useState(initial.employees?.toString() ?? "");
  const [revenue, setRevenue] = useState(initial.annual_revenue?.toString() ?? "");
  const [city, setCity] = useState(initial.city ?? "");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [domains, setDomains] = useState<string[]>([]);
  const [domainsTouched, setDomainsTouched] = useState(false);

  const changeSector = (value: string) => {
    setSector(value);
    // Tant que l'utilisateur n'a pas modifié la sélection, on coche les tableaux recommandés.
    if (!domainsTouched) setDomains(suggestedDomains(meta, value));
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await onSubmit({
        name: name.trim(),
        sector,
        size: size || null,
        employees: toNumber(employees),
        annual_revenue: toNumber(revenue),
        city: city.trim() || null,
        ...(withDomains ? { domains } : {}),
      });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="form-grid" onSubmit={submit}>
      <label className="span-2">
        Raison sociale
        <input value={name} onChange={(e) => setName(e.target.value)} required disabled={disabled} />
      </label>
      <label>
        Secteur d'activité
        <select value={sector} onChange={(e) => changeSector(e.target.value)} required disabled={disabled}>
          <option value="">— Choisir —</option>
          {Object.entries(meta.sectors).map(([code, label]) => (
            <option key={code} value={code}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <label>
        Ville
        <input value={city} onChange={(e) => setCity(e.target.value)} disabled={disabled} />
      </label>
      <label>
        Effectif (salariés)
        <input type="number" min={0} value={employees} onChange={(e) => setEmployees(e.target.value)} disabled={disabled} />
      </label>
      <label>
        Chiffre d'affaires annuel (MAD)
        <input type="number" min={0} value={revenue} onChange={(e) => setRevenue(e.target.value)} disabled={disabled} />
      </label>
      <label className="span-2">
        Taille de l'entreprise
        <select value={size} onChange={(e) => setSize(e.target.value)} disabled={disabled}>
          <option value="">Déterminer automatiquement (effectif ou CA)</option>
          {Object.entries(meta.sizes).map(([code, label]) => (
            <option key={code} value={code}>
              {label}
            </option>
          ))}
        </select>
      </label>
      {withDomains && (
        <div className="span-2">
          <h3>Tableaux de bord souhaités</h3>
          {sector ? (
            <>
              <p className="muted small">
                Les analyses recommandées pour ce secteur sont pré-cochées. Vous pouvez en choisir plusieurs, et en
                ajouter d'autres plus tard.
              </p>
              <DomainPicker
                meta={meta}
                sector={sector}
                selected={domains}
                onChange={(d) => {
                  setDomains(d);
                  setDomainsTouched(true);
                }}
              />
            </>
          ) : (
            <p className="muted small">Choisissez d'abord le secteur d'activité.</p>
          )}
        </div>
      )}
      {error && <p className="error span-2">{error}</p>}
      {!disabled && (
        <div className="actions span-2">
          {onCancel && (
            <button type="button" className="btn ghost" onClick={onCancel}>
              Annuler
            </button>
          )}
          <button className="btn primary" disabled={busy}>
            {submitLabel}
          </button>
        </div>
      )}
    </form>
  );
}
