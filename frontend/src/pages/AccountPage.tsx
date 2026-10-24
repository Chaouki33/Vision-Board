import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api, errorMessage } from "../api";
import { useAuth } from "../auth";
import type { User } from "../types";

export default function AccountPage() {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const forced = user?.must_change_password;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (next !== confirm) {
      setError("Les deux nouveaux mots de passe ne correspondent pas");
      return;
    }
    try {
      const updated = await api<User>("/auth/password", { body: { current_password: current, new_password: next } });
      setUser(updated);
      setCurrent("");
      setNext("");
      setConfirm("");
      setDone(true);
      if (forced) navigate("/", { replace: true });
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Mon compte</h1>
          <p className="muted">
            {user?.full_name} · {user?.email} · {user?.is_admin ? "Administrateur" : "Utilisateur"}
          </p>
        </div>
      </div>
      <section className="card narrow">
        <h2>{forced ? "Choisissez votre mot de passe" : "Changer le mot de passe"}</h2>
        {forced && (
          <p className="notice">
            Vous vous êtes connecté avec un mot de passe provisoire. Choisissez un mot de passe personnel (8 caractères
            minimum) pour accéder à l'application.
          </p>
        )}
        <form className="stack" onSubmit={submit}>
          <label>
            {forced ? "Mot de passe provisoire" : "Mot de passe actuel"}
            <input type="password" value={current} onChange={(e) => setCurrent(e.target.value)} required autoComplete="current-password" />
          </label>
          <label>
            Nouveau mot de passe
            <input type="password" value={next} onChange={(e) => setNext(e.target.value)} required minLength={8} autoComplete="new-password" />
          </label>
          <label>
            Confirmer le nouveau mot de passe
            <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required minLength={8} autoComplete="new-password" />
          </label>
          {error && <p className="error">{error}</p>}
          {done && !forced && <p className="ok">Mot de passe modifié ✓</p>}
          <div className="actions left">
            <button className="btn primary">Enregistrer</button>
          </div>
        </form>
      </section>
    </>
  );
}
