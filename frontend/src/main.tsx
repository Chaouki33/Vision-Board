import { StrictMode, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import LandingPage from "./pages/LandingPage";
import CompaniesPage from "./pages/CompaniesPage";
import CompanyPage from "./pages/CompanyPage";
import DashboardPage from "./pages/DashboardPage";
import ReportPage from "./pages/ReportPage";
import AccountPage from "./pages/AccountPage";
import AdminPage from "./pages/AdminPage";
import "./styles.css";
import "./animations.css";
import "./background.css";
import "./landing.css";
import "./sector.css";

function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <p className="center muted">Chargement…</p>;
  // Visiteur non connecté : page de présentation de l'application.
  if (!user) return <Navigate to="/bienvenue" replace />;
  // Mot de passe provisoire : il faut le changer avant d'utiliser l'application.
  if (user.must_change_password && location.pathname !== "/compte") return <Navigate to="/compte" replace />;
  return <>{children}</>;
}

function RequireAdmin({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  return user?.is_admin ? <>{children}</> : <Navigate to="/" replace />;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/bienvenue" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route
            element={
              <RequireAuth>
                <Layout />
              </RequireAuth>
            }
          >
            <Route path="/" element={<CompaniesPage />} />
            <Route path="/companies/:companyId" element={<CompanyPage />} />
            <Route path="/companies/:companyId/dashboards/:dashboardId" element={<DashboardPage />} />
            <Route path="/companies/:companyId/reports/:reportId" element={<ReportPage />} />
            <Route path="/compte" element={<AccountPage />} />
            <Route
              path="/admin"
              element={
                <RequireAdmin>
                  <AdminPage />
                </RequireAdmin>
              }
            />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
