import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, errorMessage, loadMeta } from "../api";
import { useAuth } from "../auth";
import { ROLE_LABELS, confirmDeletion } from "./CompaniesPage";
import type { AdminUser, Company, Meta, Role } from "../types";
import Skeleton from "../components/Skeleton";

interface Created {
  user: AdminUser;
  temporary_password: string;
}

type Access = Record<number, Role | "">;

export default function AdminPage() {
  const { user: me } = useAuth();
  const [users, setUsers] = useState<AdminUser[] | null>(null);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [credentials, setCredentials] = useState<Created | null>(null);
  const [editing, setEditing] = useState<AdminUser | null>(null);
  const [error, setError] = useState("");

  const refresh = () =>
    Promise.all([api<AdminUser[]>("/admin/users"), api<Company[]>("/companies")])
      .then(([u, c]) => {
        setUsers(u);
        setCompanies(c);
      })
      .catch((err) => setError(errorMessage(err)));

  useEffect(() => {
    refresh();
  }, []);

  const act = async (fn: () => Promise<unknown>) => {
    setError("");
    try {
      await fn();
      await refresh();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const resetPassword = (u: AdminUser) =>
    window.confirm(`Générer un nouveau mot de passe provisoire pour ${u.full_name} ?`) &&
    act(async () => setCredentials(await api<Created>(`/admin/users/${u.id}/reset-password`, { method: "POST" })));

  const toggleActive = (u: AdminUser) =>
    act(() => api(`/admin/users/${u.id}`, { method: "PATCH", body: { is_active: !u.is_active } }));

  const toggleAdmin = (u: AdminUser) =>
    window.confirm(u.is_admin ? `Retirer les droits d'administrateur à ${u.full_name} ?` : `Nommer ${u.full_name} administrateur ?`) &&
    act(() => api(`/admin/users/${u.id}`, { method: "PATCH", body: { is_admin: !u.is_admin } }));

  const remove = (u: AdminUser) =>
    window.confirm(`Supprimer définitivement le compte de ${u.full_name} ?`) &&
    act(() => api(`/admin/users/${u.id}`, { method: "DELETE" }));

  if (!users) return error ? <p className="error">{error}</p> : <Skeleton variant="page" />;

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Administration</h1>
          <p className="muted">
            Créez les comptes de vos utilisateurs et choisissez les sociétés auxquelles ils ont accès. En tant
            qu'administrateur, vous accédez à toutes les sociétés.
          </p>
        </div>
      </div>

      {credentials && <CredentialsBox created={credentials} onClose={() => setCredentials(null)} />}

      <CreateUserForm companies={companies} onCreated={(c) => { setCredentials(c); refresh(); }} />

      {editing && (
        <AccessEditor
          user={editing}
          companies={companies}
          onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); refresh(); }}
        />
      )}

      <section className="card">
        <h2>Comptes ({users.length})</h2>
        {error && <p className="error">{error}</p>}
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Utilisateur</th>
                <th>Profil</th>
                <th>Sociétés</th>
                <th>Dernière connexion</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className={u.is_active ? "" : "inactive"}>
                  <td>
                    <strong>{u.full_name}</strong>
                    <div className="muted small">{u.email}</div>
                  </td>
                  <td>
                    <div className="tags">
                      <span className={`tag ${u.is_admin ? "soft" : ""}`}>{u.is_admin ? "Administrateur" : "Utilisateur"}</span>
                      {!u.is_active && <span className="tag warn">Désactivé</span>}
                      {u.must_change_password && u.is_active && <span className="tag">Mot de passe provisoire</span>}
                    </div>
                  </td>
                  <td className="small">
                    {u.is_admin
                      ? "Toutes"
                      : u.companies.length
                        ? u.companies.map((c) => `${c.name} (${ROLE_LABELS[c.role].toLowerCase()})`).join(", ")
                        : <span className="muted">Aucune</span>}
                  </td>
                  <td className="small">{u.last_login_at ? new Date(u.last_login_at).toLocaleString("fr-FR") : "Jamais"}</td>
                  <td className="row-actions admin-actions">
                    {!u.is_admin && <button className="btn small" onClick={() => setEditing(u)}>Accès</button>}
                    <button className="btn small" onClick={() => resetPassword(u)}>Nouveau mot de passe</button>
                    {u.id !== me?.id && (
                      <>
                        <button className="btn small" onClick={() => toggleAdmin(u)}>{u.is_admin ? "Retirer admin" : "Nommer admin"}</button>
                        <button className="btn small" onClick={() => toggleActive(u)}>{u.is_active ? "Désactiver" : "Réactiver"}</button>
                        <button className="btn small danger" onClick={() => remove(u)}>Supprimer</button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <AdminCompanies onChanged={refresh} />
    </>
  );
}

interface AdminCompany {
  id: number;
  name: string;
  sector: string;
  size: string;
  city: string | null;
  created_at: string;
  owners: string[];
  members: number;
  dashboards: number;
  datasets: number;
  reports: number;
}

function AdminCompanies({ onChanged }: { onChanged: () => void }) {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [companies, setCompanies] = useState<AdminCompany[] | null>(null);
  const [selected, setSelected] = useState<number[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const refresh = () =>
    api<AdminCompany[]>("/admin/companies").then(setCompanies).catch((err) => setError(errorMessage(err)));
  useEffect(() => {
    loadMeta().then(setMeta).catch(() => undefined);
    refresh();
  }, []);

  const remove = async (ids: number[]) => {
    const names = (companies ?? []).filter((c) => ids.includes(c.id)).map((c) => c.name);
    if (!ids.length || !window.confirm(confirmDeletion(names))) return;
    setBusy(true);
    setError("");
    try {
      await api("/admin/companies/delete", { body: { ids } });
      setSelected((s) => s.filter((id) => !ids.includes(id)));
      await refresh();
      onChanged();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  if (!companies) return null;
  const allSelected = companies.length > 0 && selected.length === companies.length;
  const toggle = (id: number) => setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  return (
    <section className="card">
      <h2>Sociétés ({companies.length})</h2>
      <p className="muted">
        Toutes les sociétés enregistrées sur la plateforme. La suppression efface aussi leurs fichiers, tableaux de bord
        et rapports.
      </p>
      {error && <p className="error">{error}</p>}
      {companies.length === 0 ? (
        <p className="muted">Aucune société.</p>
      ) : (
        <>
          <div className="bulk-bar">
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={allSelected}
                onChange={() => setSelected(allSelected ? [] : companies.map((c) => c.id))}
              />
              Tout sélectionner
            </label>
            <button className="btn small danger" disabled={!selected.length || busy} onClick={() => remove(selected)}>
              {selected.length ? `Supprimer la sélection (${selected.length})` : "Supprimer la sélection"}
            </button>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th />
                  <th>Société</th>
                  <th>Secteur</th>
                  <th>Propriétaires</th>
                  <th>Contenu</th>
                  <th>Créée le</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {companies.map((c) => (
                  <tr key={c.id}>
                    <td>
                      <input type="checkbox" checked={selected.includes(c.id)} onChange={() => toggle(c.id)}
                        aria-label={`Sélectionner ${c.name}`} />
                    </td>
                    <td>
                      <strong>{c.name}</strong>
                      <div className="muted small">{c.size.toUpperCase()}{c.city ? ` · ${c.city}` : ""}</div>
                    </td>
                    <td className="small">{meta?.sectors[c.sector] ?? c.sector}</td>
                    <td className="small">{c.owners.join(", ") || <span className="muted">Aucun</span>}</td>
                    <td className="small">
                      {c.dashboards} tableaux · {c.datasets} fichiers · {c.reports} rapports
                    </td>
                    <td className="small">{new Date(c.created_at).toLocaleDateString("fr-FR")}</td>
                    <td className="row-actions admin-actions">
                      <Link className="btn small" to={`/companies/${c.id}`}>Ouvrir</Link>
                      <button className="btn small danger" disabled={busy} onClick={() => remove([c.id])}>
                        Supprimer
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}

function CredentialsBox({ created, onClose }: { created: Created; onClose: () => void }) {
  const [copied, setCopied] = useState(false);
  const text =
    `Bonjour ${created.user.full_name},\n\nVotre accès à Vision Board :\n` +
    `Adresse : ${window.location.origin}\nE-mail : ${created.user.email}\n` +
    `Mot de passe provisoire : ${created.temporary_password}\n\n` +
    `Vous choisirez votre propre mot de passe à la première connexion.`;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };

  return (
    <section className="card highlight credentials">
      <div className="card-head">
        <div>
          <h2>Identifiants à communiquer</h2>
          <p className="muted">
            Ce mot de passe provisoire n'est affiché qu'une seule fois. Transmettez-le à {created.user.full_name} ; il
            devra le changer à sa première connexion.
          </p>
        </div>
        <button className="btn ghost" onClick={onClose}>Fermer</button>
      </div>
      <dl className="credential-list">
        <dt>E-mail</dt>
        <dd className="mono">{created.user.email}</dd>
        <dt>Mot de passe provisoire</dt>
        <dd className="mono big">{created.temporary_password}</dd>
      </dl>
      <div className="actions left">
        <button className="btn primary" onClick={copy}>{copied ? "Message copié ✓" : "Copier le message à envoyer"}</button>
      </div>
    </section>
  );
}

function AccessFields({ companies, access, setAccess }: { companies: Company[]; access: Access; setAccess: (a: Access) => void }) {
  if (!companies.length) return <p className="muted small">Aucune société pour l'instant : créez-en une depuis « Mes sociétés ».</p>;
  return (
    <div className="access-grid">
      {companies.map((c) => (
        <label key={c.id} className="access-row">
          <span>{c.name}</span>
          <select value={access[c.id] ?? ""} onChange={(e) => setAccess({ ...access, [c.id]: e.target.value as Role | "" })}>
            <option value="">Pas d'accès</option>
            <option value="viewer">Lecteur (consultation)</option>
            <option value="editor">Éditeur (import, tableaux, rapports)</option>
            <option value="owner">Propriétaire</option>
          </select>
        </label>
      ))}
    </div>
  );
}

const toPayload = (access: Access) =>
  Object.entries(access).filter(([, role]) => role).map(([id, role]) => ({ company_id: Number(id), role }));

function CreateUserForm({ companies, onCreated }: { companies: Company[]; onCreated: (c: Created) => void }) {
  const [open, setOpen] = useState(false);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [isAdmin, setIsAdmin] = useState(false);
  const [access, setAccess] = useState<Access>({});
  const [error, setError] = useState("");

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      const created = await api<Created>("/admin/users", {
        body: { full_name: fullName, email, is_admin: isAdmin, companies: isAdmin ? [] : toPayload(access) },
      });
      setFullName("");
      setEmail("");
      setIsAdmin(false);
      setAccess({});
      setOpen(false);
      onCreated(created);
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  if (!open) {
    return (
      <div className="actions left" style={{ marginBottom: 20 }}>
        <button className="btn primary" onClick={() => setOpen(true)}>+ Créer un compte utilisateur</button>
      </div>
    );
  }

  return (
    <section className="card">
      <h2>Nouveau compte</h2>
      <form className="form-grid" onSubmit={submit}>
        <label>
          Nom complet
          <input value={fullName} onChange={(e) => setFullName(e.target.value)} required minLength={2} />
        </label>
        <label>
          E-mail (identifiant de connexion)
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label className="span-2 checkbox-row">
          <input type="checkbox" checked={isAdmin} onChange={(e) => setIsAdmin(e.target.checked)} />
          Administrateur (accès à toutes les sociétés et à cette page)
        </label>
        {!isAdmin && (
          <div className="span-2">
            <h3>Accès aux sociétés</h3>
            <AccessFields companies={companies} access={access} setAccess={setAccess} />
          </div>
        )}
        <p className="muted small span-2">Un mot de passe provisoire sera généré et affiché une seule fois.</p>
        {error && <p className="error span-2">{error}</p>}
        <div className="actions span-2">
          <button type="button" className="btn ghost" onClick={() => setOpen(false)}>Annuler</button>
          <button className="btn primary">Créer le compte</button>
        </div>
      </form>
    </section>
  );
}

function AccessEditor({ user, companies, onClose, onSaved }: { user: AdminUser; companies: Company[]; onClose: () => void; onSaved: () => void }) {
  const [access, setAccess] = useState<Access>(Object.fromEntries(user.companies.map((c) => [c.company_id, c.role])));
  const [error, setError] = useState("");

  const save = async () => {
    setError("");
    try {
      await api(`/admin/users/${user.id}/companies`, { method: "PUT", body: toPayload(access) });
      onSaved();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <section className="card highlight">
      <h2>Accès de {user.full_name}</h2>
      <AccessFields companies={companies} access={access} setAccess={setAccess} />
      {error && <p className="error">{error}</p>}
      <div className="actions">
        <button className="btn ghost" onClick={onClose}>Annuler</button>
        <button className="btn primary" onClick={save}>Enregistrer les accès</button>
      </div>
    </section>
  );
}
