import { lazy, Suspense, useState } from "react";
import {
  Navigate,
  NavLink,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  ArrowRight,
  ClipboardPlus,
  FileDown,
  LayoutDashboard,
  LogOut,
  Menu,
  Package,
  Pill,
  ShieldAlert,
  X,
} from "lucide-react";
import { useAuth } from "./auth";
import { api } from "./api";
import { Loading, Notice } from "./components/ui";
import SidebarNavigation, { type NavigationItem } from "./components/SidebarNavigation";
import type { Role } from "./types";
const Overview = lazy(() => import("./pages/Overview"));
const Reporting = lazy(() => import("./pages/Reporting"));
const Inventory = lazy(() => import("./pages/Inventory"));
const Safety = lazy(() => import("./pages/Safety"));
const Recalls = lazy(() => import("./pages/Recalls"));
const Exports = lazy(() => import("./pages/Exports"));
const admin = "SAFETY_OFFICER_ADMIN";
const nav: NavigationItem[] = [
  {
    path: "/",
    name: "Overview",
    icon: LayoutDashboard,
    roles: ["DOCTOR_PATIENT", "PHARMACIST", admin],
  },
  {
    path: "/adverse-reports",
    name: "Adverse reports",
    icon: ClipboardPlus,
    roles: ["DOCTOR_PATIENT", admin],
  },
  {
    path: "/inventory",
    name: "Inventory",
    icon: Package,
    roles: ["PHARMACIST", admin],
    children: [
      { name: "Stock inventory", value: "stock" },
      { name: "Import batches", value: "import" },
      { name: "Dispatch stock", value: "dispatch" },
    ],
  },
  {
    path: "/safety",
    name: "Safety monitoring",
    icon: Activity,
    roles: [admin],
    children: [
      { name: "Signal detection", value: "signals" },
      { name: "Clinical search", value: "clinical" },
    ],
  },
  {
    path: "/recalls", name: "Recalls", icon: ShieldAlert, roles: [admin],
    children: [
      { name: "Recall management", value: "management" },
      { name: "Affected hospital stock", value: "stock" },
    ],
  },
  {
    path: "/exports",
    name: "Reports & exports",
    icon: FileDown,
    roles: [admin],
  },
];
const roleNames: Record<Role, string> = {
  DOCTOR_PATIENT: "Doctor & patient",
  PHARMACIST: "Hospital pharmacist",
  SAFETY_OFFICER_ADMIN: "Safety officer",
};
function Login() {
  const auth = useAuth();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function signIn(username: string, password: string) {
    setBusy(true);
    setError("");
    try {
      await auth.login(username, password);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="login-page">
      <section className="login-form">
        <div className="brand">
          <span className="brand-mark">
            <Pill />
          </span>
          Pharmavigil
        </div>
        <div className="login-content">
          <span className="eyebrow">Medicine safety workspace</span>
          <h1>Sign in</h1>
          <p>Welcome back. Keep medicine safety moving.</p>
          {error ? <Notice>{error}</Notice> : null}
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              const d = new FormData(e.currentTarget);
              await signIn(String(d.get("username")), String(d.get("password")));
            }}
          >
            <label>
              Username
              <input
                name="username"
                required
                autoComplete="username"
                placeholder="Enter your username"
              />
            </label>
            <label>
              Password
              <input
                name="password"
                type="password"
                required
                autoComplete="current-password"
                placeholder="Enter your password"
              />
            </label>
            <button className="primary full" disabled={busy}>
              {busy ? "Signing in…" : "Sign in"}
              <ArrowRight size={18} />
            </button>
          </form>
          <p className="small muted">
            Use your existing Pharmavigil account. Your role determines which
            sections you can access.
          </p>
          <section className="test-profiles" aria-label="Test profile logins">
            <h2>Test profiles</h2>
            <p className="small muted">Choose a profile to try its workspace.</p>
            <div className="test-profile-list">
              {[
                { name: "Doctor / patient", username: "doctor_smith", password: "doctor123", description: "Submit adverse reaction reports", icon: ClipboardPlus },
                { name: "Pharmacist", username: "pharmacist_jane", password: "pharmacist123", description: "Manage inventory and dispatches", icon: Package },
                { name: "Safety officer", username: "admin_officer", password: "admin123", description: "Review safety signals and recalls", icon: ShieldAlert },
              ].map((profile) => (
                <button
                  key={profile.username}
                  type="button"
                  className="test-profile"
                  disabled={busy}
                  onClick={() => void signIn(profile.username, profile.password)}
                >
                  <profile.icon size={20} aria-hidden="true" />
                  <span><strong>{profile.name}</strong><small>{profile.description}</small></span>
                  <ArrowRight size={16} aria-hidden="true" />
                </button>
              ))}
            </div>
          </section>
        </div>
        <small className="login-footer">
          Pharmavigil · Medicine inventory & safety monitoring
        </small>
      </section>
      <aside className="login-art">
        <div className="login-pattern" />
        <div className="login-art-content">
          <span className="art-mark">
            <Pill size={42} />
          </span>
          <h2>
            Safer medicines.
            <br />
            Connected care.
          </h2>
          <p>
            One workspace for adverse reporting, stock visibility, and safety
            decisions.
          </p>
          <div className="art-features">
            <span>
              <ClipboardPlus size={19} />
              Report with confidence
            </span>
            <span>
              <Package size={19} />
              Track every batch
            </span>
            <span>
              <ShieldAlert size={19} />
              Act on safety signals
            </span>
          </div>
        </div>
      </aside>
    </main>
  );
}
export default function App() {
  const auth = useAuth();
  const [open, setOpen] = useState(false);
  const [error, setError] = useState("");
  const location = useLocation();
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => api<{ mysql: boolean; mongodb: boolean }>("/health"),
    enabled: !!auth.user,
    refetchInterval: 60000,
  });
  if (auth.loading) return <Loading />;
  if (auth.error)
    return (
      <div className="error-screen">
        <Notice>
          Unable to verify your account. Check your connection and try again.
        </Notice>
        <button onClick={auth.refresh}>Try again</button>
      </div>
    );
  if (!auth.user) return <Login />;
  const user = auth.user;
  const allowed = nav.filter((n) => n.roles.includes(user.role));
  const currentSection = allowed.find((item) => item.path === location.pathname);
  const currentSubsection = currentSection?.children?.find(
    (child) => child.value === new URLSearchParams(location.search).get("tab"),
  ) ?? currentSection?.children?.[0];
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      {open ? (
        <button
          className="mobile-backdrop"
          aria-label="Close navigation"
          onClick={() => setOpen(false)}
        />
      ) : null}
      <aside className={`sidebar ${open ? "sidebar-open" : ""}`}>
        <NavLink to="/" className="brand">
          <span className="brand-mark">
            <Pill size={25} />
          </span>
          Pharmavigil
        </NavLink>
        <button
          className="sidebar-close icon-button"
          aria-label="Close navigation"
          onClick={() => setOpen(false)}
        >
          <X />
        </button>
        <p className="nav-caption">Workspace</p>
        <SidebarNavigation items={allowed} onNavigate={() => setOpen(false)} />
        <div className="sidebar-bottom">
          <div className="system-status">
            <span
              className={`status-dot ${health.data?.mysql && health.data?.mongodb ? "online" : ""}`}
            />
            {health.isPending
              ? "Checking connections"
              : health.data?.mysql && health.data?.mongodb
                ? "Systems connected"
                : "Connection needs attention"}
          </div>
          <p className="small muted">
            MySQL {health.data?.mysql ? "connected" : "unavailable"}
            <br />
            MongoDB {health.data?.mongodb ? "connected" : "unavailable"}
          </p>
          <div className="sidebar-note">
            <ShieldAlert size={21} />
            <p>
              Every batch matters.
              <br />
              <span>Keep safety at the center.</span>
            </p>
          </div>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <button
            className="icon-button mobile-menu"
            onClick={() => setOpen(!open)}
            aria-label="Open navigation"
          >
            <Menu />
          </button>
          <div className="header-breadcrumb">
            Workspace <span>/</span>{" "}
            <strong>
              {currentSection?.name ?? "Pharmavigil"}
            </strong>
            {currentSubsection ? (
              <><span>/</span>{" "}{currentSubsection.name}</>
            ) : null}
          </div>
          <div className="user-menu">
            <div className="avatar">
              {user.full_name
                .split(" ")
                .filter(Boolean)
                .slice(0, 2)
                .map((n) => n[0])
                .join("")}
            </div>
            <div className="user-details">
              <strong>{user.full_name}</strong>
              <span>{roleNames[user.role]}</span>
            </div>
            <button
              className="icon-button"
              title="Sign out"
              aria-label="Sign out"
              onClick={async () => {
                try {
                  await auth.logout();
                } catch (e) {
                  setError((e as Error).message);
                }
              }}
            >
              <LogOut size={19} />
            </button>
          </div>
        </header>
        <main id="main" className="main-content">
          {error ? <Notice>{error}</Notice> : null}
          <Suspense fallback={<Loading />}>
            <Routes>
              <Route path="/" element={<Overview />} />
              {allowed.some((n) => n.path === "/adverse-reports") ? (
                <Route path="/adverse-reports" element={<Reporting />} />
              ) : null}
              {allowed.some((n) => n.path === "/inventory") ? (
                <Route path="/inventory" element={<Inventory />} />
              ) : null}
              {user.role === admin ? (
                <>
                  <Route path="/safety" element={<Safety />} />
                  <Route path="/recalls" element={<Recalls />} />
                  <Route path="/exports" element={<Exports />} />
                </>
              ) : null}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </main>
        <footer className="workspace-footer">
          Pharmavigil<span>Medicine safety, clearly connected.</span>
        </footer>
      </div>
    </div>
  );
}
