import { useEffect, useState, type FormEvent } from "react";
import { Link, Navigate, useLocation } from "react-router-dom";
import { api, errorMessage } from "../api";
import { useAuth } from "../auth";
import AppBackground from "../components/AppBackground";
import { LogoFull } from "../components/Logo";
import ThemeToggle from "../components/ThemeToggle";

export default function LoginPage() {
  const { user, login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [config, setConfig] = useState({ registration_open: false, first_install: false });
  const wantsSignup = new URLSearchParams(useLocation().search).has("inscription");

  useEffect(() => {
    api<{ registration_open: boolean; first_install: boolean }>("/auth/config")
      .then((c) => {
        setConfig(c);
        if (c.first_install || (c.registration_open && wantsSignup)) setMode("register");
      })
      .catch((err) => setError(errorMessage(err)));
  }, []);

  if (user) return <Navigate to="/" replace />;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(fullName, email, password);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-page">
      <AppBackground variant="login" />
      <div className="auth-theme">
        <Link to="/bienvenue" className="btn ghost small">← Découvrir Vision Board</Link>
        <ThemeToggle />
      </div>
      <form className="card auth-card" onSubmit={submit}>
        <div className="auth-logo">
          <LogoFull size={230} />
        </div>
        <p className="muted tagline">Tableaux de bord et analyses pour piloter votre entreprise.</p>
        <h2>{mode === "login" ? "Connexion" : config.first_install ? "Créer le compte administrateur" : "Créer un compte"}</h2>
        {mode === "register" && config.first_install && (
          <p className="notice small">
            Première utilisation : ce compte sera l'administrateur de Vision Board. Vous créerez ensuite les comptes de
            vos utilisateurs depuis la page « Administration ».
          </p>
        )}
        {mode === "register" && (
          <label>
            Nom complet
            <input value={fullName} onChange={(e) => setFullName(e.target.value)} required minLength={2} />
          </label>
        )}
        <label>
          E-mail
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
        </label>
        <label>
          Mot de passe
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={mode === "register" ? 8 : 1}
            autoComplete={mode === "login" ? "current-password" : "new-password"}
          />
        </label>
        {error && <p className="error">{error}</p>}
        <button className="btn primary" disabled={busy}>
          {mode === "login" ? "Se connecter" : "Créer le compte"}
        </button>
        {config.registration_open && !config.first_install && (
          <button
            type="button"
            className="btn link"
            onClick={() => {
              setMode(mode === "login" ? "register" : "login");
              setError("");
            }}
          >
            {mode === "login" ? "Pas encore de compte ? Inscrivez-vous" : "Déjà inscrit ? Connectez-vous"}
          </button>
        )}
        {!config.registration_open && (
          <p className="muted small center-text">Pas de compte ? Demandez vos identifiants à l'administrateur.</p>
        )}
      </form>
    </div>
  );
}
