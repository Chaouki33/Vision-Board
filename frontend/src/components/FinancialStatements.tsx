import { useEffect, useState } from "react";
import { api, errorMessage } from "../api";
import { formatValue } from "../format";

type RowType = "header" | "subheader" | "row" | "total" | "result" | "final";

interface StatementRow {
  label: string;
  value?: number;
  type: RowType;
}

interface AssetRow {
  label: string;
  brut: number | null;
  amort: number | null;
  net: number;
  type: RowType;
}

interface BalanceRow {
  compte: string;
  libelle: string;
  classe: string;
  debit: number;
  credit: number;
  solde_debiteur: number;
  solde_crediteur: number;
}

interface Ratio {
  key: string;
  label: string;
  unit: string;
  formula: string;
  value: number | null;
}

interface AccountingData {
  dataset: { id: number; name: string; source_filename: string };
  balance: { rows: BalanceRow[]; totals: Record<"debit" | "credit" | "solde_debiteur" | "solde_crediteur", number> };
  cpc: StatementRow[];
  esg: StatementRow[];
  bilan: { actif: AssetRow[]; passif: StatementRow[] };
  ratios: Ratio[];
  notes: string[];
  checks: string[];
}

const TABS = { bilan: "Bilan", cpc: "CPC", esg: "Soldes de gestion", ratios: "Ratios", balance: "Balance" } as const;
type Tab = keyof typeof TABS;

const amount = new Intl.NumberFormat("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function money(value: number | null | undefined): string {
  if (value === null || value === undefined) return "";
  if (Math.abs(value) < 0.005) return "—";
  return amount.format(value);
}

interface Props {
  companyId: number;
  start: string;
  end: string;
}

export default function FinancialStatements({ companyId, start, end }: Props) {
  const [data, setData] = useState<AccountingData | null>(null);
  const [tab, setTab] = useState<Tab>("bilan");
  const [error, setError] = useState("");

  useEffect(() => {
    const query = new URLSearchParams();
    if (start) query.set("start", start);
    if (end) query.set("end", end);
    api<AccountingData>(`/companies/${companyId}/accounting?${query}`)
      .then((d) => {
        setData(d);
        setError("");
      })
      .catch((err) => setError(errorMessage(err)));
  }, [companyId, start, end]);

  if (error) return <p className="error">{error}</p>;
  if (!data) return <p className="muted">Préparation des états financiers…</p>;

  return (
    <section className="card statements">
      <div className="card-head">
        <div>
          <h2>États financiers</h2>
          <p className="muted small">
            Établis selon le CGNC à partir de « {data.dataset.name} » · montants en MAD
          </p>
        </div>
      </div>
      {data.checks.map((c) => (
        <p key={c} className="error">
          {c}
        </p>
      ))}
      <nav className="tabs">
        {(Object.keys(TABS) as Tab[]).map((key) => (
          <button key={key} className={key === tab ? "active" : ""} onClick={() => setTab(key)}>
            {TABS[key]}
          </button>
        ))}
      </nav>

      {tab === "bilan" && <Bilan data={data} />}
      {tab === "cpc" && <Statement title="Compte de produits et charges (CPC)" rows={data.cpc} />}
      {tab === "esg" && <Statement title="État des soldes de gestion — formation des résultats" rows={data.esg} />}
      {tab === "ratios" && <Ratios ratios={data.ratios} />}
      {tab === "balance" && <Balance data={data} />}

      {data.notes.length > 0 && <p className="muted small">{data.notes.join(" · ")}</p>}
    </section>
  );
}

function Statement({ title, rows }: { title: string; rows: StatementRow[] }) {
  return (
    <div className="table-wrap">
      <table className="statement">
        <caption>{title}</caption>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className={`st-${r.type}`}>
              <td>{r.label}</td>
              <td className="num">{r.value !== undefined ? money(r.value) : ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Bilan({ data }: { data: AccountingData }) {
  return (
    <div className="bilan">
      <div className="table-wrap">
        <table className="statement">
          <caption>Actif</caption>
          <thead>
            <tr>
              <th />
              <th className="num">Brut</th>
              <th className="num">Amort. et prov.</th>
              <th className="num">Net</th>
            </tr>
          </thead>
          <tbody>
            {data.bilan.actif.map((r, i) => (
              <tr key={i} className={`st-${r.type}`}>
                <td>{r.label}</td>
                <td className="num">{money(r.brut)}</td>
                <td className="num">{money(r.amort)}</td>
                <td className="num">{money(r.net)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="table-wrap">
        <table className="statement">
          <caption>Passif</caption>
          <thead>
            <tr>
              <th />
              <th className="num">Montant</th>
            </tr>
          </thead>
          <tbody>
            {data.bilan.passif.map((r, i) => (
              <tr key={i} className={`st-${r.type}`}>
                <td>{r.label}</td>
                <td className="num">{money(r.value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Ratios({ ratios }: { ratios: Ratio[] }) {
  return (
    <div className="table-wrap">
      <table className="statement">
        <caption>Ratios d'analyse financière</caption>
        <thead>
          <tr>
            <th>Indicateur</th>
            <th>Calcul</th>
            <th className="num">Valeur</th>
          </tr>
        </thead>
        <tbody>
          {ratios.map((r) => (
            <tr key={r.key}>
              <td>{r.label}</td>
              <td className="muted small">{r.formula}</td>
              <td className="num">
                <strong>{formatValue(r.value, r.unit)}</strong>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Balance({ data }: { data: AccountingData }) {
  const { rows, totals } = data.balance;
  let currentClass = "";
  return (
    <div className="table-wrap balance">
      <table className="statement">
        <caption>Balance générale ({rows.length} comptes)</caption>
        <thead>
          <tr>
            <th>Compte</th>
            <th>Intitulé</th>
            <th className="num">Débit</th>
            <th className="num">Crédit</th>
            <th className="num">Solde débiteur</th>
            <th className="num">Solde créditeur</th>
          </tr>
        </thead>
        <tbody>
          {rows.flatMap((r) => {
            const out = [];
            if (r.classe !== currentClass) {
              currentClass = r.classe;
              out.push(
                <tr key={`c-${r.compte}`} className="st-subheader">
                  <td colSpan={6}>
                    Classe {r.compte[0]} — {r.classe}
                  </td>
                </tr>,
              );
            }
            out.push(
              <tr key={r.compte}>
                <td className="mono">{r.compte}</td>
                <td>{r.libelle}</td>
                <td className="num">{money(r.debit)}</td>
                <td className="num">{money(r.credit)}</td>
                <td className="num">{money(r.solde_debiteur)}</td>
                <td className="num">{money(r.solde_crediteur)}</td>
              </tr>,
            );
            return out;
          })}
          <tr className="st-final">
            <td colSpan={2}>Totaux</td>
            <td className="num">{money(totals.debit)}</td>
            <td className="num">{money(totals.credit)}</td>
            <td className="num">{money(totals.solde_debiteur)}</td>
            <td className="num">{money(totals.solde_crediteur)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
