import { AlertTriangle, LoaderCircle, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import * as api from "./lib/api";
import { AppShell } from "./components/AppShell";
import { EvaluationPage } from "./components/EvaluationPage";
import { LoginPage } from "./components/LoginPage";
import { OverviewPage } from "./components/OverviewPage";
import { ReportsPage } from "./components/ReportsPage";
import { SettingsPage } from "./components/SettingsPage";
import type {
  CatalogTender,
  EvaluationResult,
  EvaluationSummary,
  ReportItem,
  SystemStatus,
  ViewName,
} from "./types";

type AuthenticationState = "checking" | "guest" | "authenticated";

function preferredDarkMode(): boolean {
  const savedTheme = window.localStorage.getItem("tenderguard-theme");
  if (savedTheme === "dark" || savedTheme === "light") {
    return savedTheme === "dark";
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export default function App() {
  const [authentication, setAuthentication] = useState<AuthenticationState>("checking");
  const [activeView, setActiveView] = useState<ViewName>("overview");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [darkMode, setDarkMode] = useState(preferredDarkMode);
  const [tenders, setTenders] = useState<CatalogTender[]>([]);
  const [evaluations, setEvaluations] = useState<EvaluationSummary[]>([]);
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [latestResult, setLatestResult] = useState<EvaluationResult | null>(null);
  const [dataError, setDataError] = useState<string | null>(null);
  const [loadingData, setLoadingData] = useState(false);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
    window.localStorage.setItem("tenderguard-theme", darkMode ? "dark" : "light");
  }, [darkMode]);

  const loadDashboard = useCallback(async () => {
    setLoadingData(true);
    setDataError(null);
    try {
      const [catalog, evaluationItems, reportItems, status] = await Promise.all([
        api.getCatalog(),
        api.getEvaluations(),
        api.getReports(),
        api.getSystemStatus(),
      ]);
      setTenders(catalog.tenders);
      setEvaluations(evaluationItems);
      setReports(reportItems);
      setSystemStatus(status);
    } catch (error) {
      if (error instanceof api.AuthenticationError) {
        api.clearSessionMemory();
        setAuthentication("guest");
        return;
      }
      setDataError(error instanceof Error ? error.message : "Dashboard data could not be loaded.");
    } finally {
      setLoadingData(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    api.restoreSession()
      .then(() => {
        if (active) setAuthentication("authenticated");
      })
      .catch(() => {
        api.clearSessionMemory();
        if (active) setAuthentication("guest");
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (authentication === "authenticated") {
      void loadDashboard();
    }
  }, [authentication, loadDashboard]);

  async function handleLogin(password: string) {
    await api.login(password);
    setAuthentication("authenticated");
  }

  async function handleLogout() {
    try {
      await api.logout();
    } finally {
      api.clearSessionMemory();
      setLatestResult(null);
      setAuthentication("guest");
    }
  }

  async function handleEvaluation(tenderId: string, bidId: string) {
    const result = await api.createEvaluation(tenderId, bidId);
    setLatestResult(result);
    setEvaluations(await api.getEvaluations());
  }

  if (authentication === "checking") {
    return (
      <main className="grid min-h-screen place-items-center bg-[#061713] px-6 text-slate-100">
        <div className="text-center">
          <LoaderCircle className="mx-auto size-7 animate-spin text-emerald-400" aria-hidden="true" />
          <p className="mt-4 text-sm text-slate-300">Checking the local dashboard session…</p>
        </div>
      </main>
    );
  }

  if (authentication === "guest") {
    return <LoginPage onLogin={handleLogin} />;
  }

  let content;
  if (activeView === "evaluate") {
    content = <EvaluationPage tenders={tenders} result={latestResult} onEvaluate={handleEvaluation} />;
  } else if (activeView === "reports") {
    content = <ReportsPage reports={reports} />;
  } else if (activeView === "settings") {
    content = <SettingsPage status={systemStatus} />;
  } else {
    content = (
      <OverviewPage
        tenders={tenders}
        evaluations={evaluations}
        reports={reports}
        systemStatus={systemStatus}
        onStartEvaluation={() => setActiveView("evaluate")}
      />
    );
  }

  return (
    <AppShell
      activeView={activeView}
      onViewChange={setActiveView}
      mobileOpen={mobileOpen}
      onMobileOpenChange={setMobileOpen}
      darkMode={darkMode}
      onThemeToggle={() => setDarkMode((value) => !value)}
      onLogout={() => void handleLogout()}
    >
      {dataError && (
        <div role="alert" className="mb-6 flex flex-col gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-300/15 dark:bg-amber-300/8 dark:text-amber-100 sm:flex-row sm:items-center">
          <AlertTriangle className="size-5 shrink-0" aria-hidden="true" />
          <p className="flex-1"><strong>Some live data is unavailable.</strong> {dataError}</p>
          <button type="button" onClick={() => void loadDashboard()} disabled={loadingData} className="inline-flex items-center justify-center gap-2 rounded-lg border border-amber-300 px-3 py-2 text-xs font-semibold transition hover:bg-amber-100 disabled:opacity-60 dark:border-amber-200/20 dark:hover:bg-amber-200/10">
            <RefreshCw className={`size-3.5 ${loadingData ? "animate-spin" : ""}`} />Retry
          </button>
        </div>
      )}
      {content}
    </AppShell>
  );
}
