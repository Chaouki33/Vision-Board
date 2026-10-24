import { useEffect, useState, type FormEvent } from "react";
import { api, errorMessage } from "../api";
import { useNavigate } from "react-router-dom";
import { ROLE_LABELS, confirmDeletion } from "../pages/CompaniesPage";
import type { Company, CompanyInput, Member, Meta, Role } from "../types";
import CompanyForm from "./CompanyForm";

interface Props {
  meta: Meta;
  company: Company;
  onUpdated: (c: Company) => void;
}

export default function ProfileTab({ meta, company, onUpdated }: Props) {
  const [members, setMembers] = useState<Member[]>([]);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<Role>("viewer");
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const isOwner = company.role === "owner";
  const base = `/companies/${company.id}`;
  const navigate = useNavigate();

  const refresh = () => api<Member[]>(`${base}/members`).then(setMembers);
  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company.id]);

  const update = async (data: CompanyInput) => {
    onUpdated(await api<Company>(base, { method: "PUT", body: data }));
    setSaved(true);
  };

  const invite = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await api(`${base}/members`, { body: { email, role } });
      setEmail("");
      refresh();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const removeCompany = async () => {
    if (!window.confirm(confirmDeletion([company.name]))) return;
    try {
      await api(base, { method: "DELETE" });
      navigate("/", { replace: true });
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const remove = async (m: Member) => {
    if (!window.confirm(`Retirer ${m.full_name} de la société ?`)) return;
    try {
      await api(`${base}/members/${m.user_id}`, { method: "DELETE" });
      refresh();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <>
      <section className="card">
        <h2>Profil de la société</h2>
        <CompanyForm
          key={company.id}
          meta={meta}
          initial={company}
          submitLabel="Enregistrer"
          disabled={company.role === "viewer"}
          onSubmit={update}
        />
        {saved && <p className="ok">Profil enregistré ✓ Les recommandations de KPI tiennent compte du nouveau profil.</p>}
      </section>

      <section className="card">
        <h2>Membres</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Nom</th>
                <th>E-mail</th>
                <th>Rôle</th>
                {isOwner && <th />}
              </tr>
            </thead>
            <tbody>
              {members.map((m) => (
                <tr key={m.user_id}>
                  <td>{m.full_name}</td>
                  <td>{m.email}</td>
                  <td>{ROLE_LABELS[m.role]}</td>
                  {isOwner && (
                    <td className="row-actions">
                      <button className="btn small danger" onClick={() => remove(m)}>
                        Retirer
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {isOwner && (
          <form className="upload-row" onSubmit={invite}>
            <label className="grow">
              E-mail d'un utilisateur inscrit
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </label>
            <label>
              Rôle
              <select value={role} onChange={(e) => setRole(e.target.value as Role)}>
                <option value="viewer">Lecteur (consultation)</option>
                <option value="editor">Éditeur (import et tableaux)</option>
                <option value="owner">Propriétaire</option>
              </select>
            </label>
            <button className="btn primary">Ajouter</button>
          </form>
        )}
        {error && <p className="error">{error}</p>}
      </section>

      {isOwner && (
        <section className="card danger-zone">
          <h2>Supprimer la société</h2>
          <p className="muted">
            Supprime définitivement « {company.name} » avec ses fichiers importés, ses tableaux de bord et ses rapports.
          </p>
          <button className="btn danger" onClick={removeCompany}>
            Supprimer cette société
          </button>
        </section>
      )}
    </>
  );
}
