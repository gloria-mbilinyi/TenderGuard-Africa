import {
  BarChart3,
  FileText,
  LogOut,
  Menu,
  Moon,
  ScanSearch,
  Settings,
  Sun,
  X,
} from "lucide-react";
import type { ReactNode } from "react";
import type { ViewName } from "../types";
import { BrandMark } from "./BrandMark";

const navigation: Array<{ id: ViewName; label: string; icon: typeof BarChart3 }> = [
  { id: "overview", label: "Overview", icon: BarChart3 },
  { id: "evaluate", label: "Tender evaluation", icon: ScanSearch },
  { id: "reports", label: "Reports", icon: FileText },
  { id: "settings", label: "Settings", icon: Settings },
];

interface AppShellProps {
  activeView: ViewName;
  onViewChange: (view: ViewName) => void;
  mobileOpen: boolean;
  onMobileOpenChange: (open: boolean) => void;
  darkMode: boolean;
  onThemeToggle: () => void;
  onLogout: () => void;
  children: ReactNode;
}

export function AppShell({
  activeView,
  onViewChange,
  mobileOpen,
  onMobileOpenChange,
  darkMode,
  onThemeToggle,
  onLogout,
  children,
}: AppShellProps) {
  const current = navigation.find((item) => item.id === activeView) ?? navigation[0];

  function selectView(view: ViewName) {
    onViewChange(view);
    onMobileOpenChange(false);
  }

  return (
    <div className="min-h-screen bg-[#f3f6f4] text-slate-950 dark:bg-[#061511] dark:text-slate-100">
      {mobileOpen && (
        <button
          type="button"
          aria-label="Close navigation"
          className="fixed inset-0 z-30 bg-slate-950/50 backdrop-blur-sm lg:hidden"
          onClick={() => onMobileOpenChange(false)}
        />
      )}

      <aside className={`fixed inset-y-0 left-0 z-40 flex w-[280px] flex-col bg-[#071d18] px-5 py-6 text-white shadow-2xl transition-transform lg:translate-x-0 ${mobileOpen ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="flex items-center justify-between">
          <BrandMark />
          <button type="button" className="rounded-lg p-2 text-slate-400 hover:bg-white/8 hover:text-white lg:hidden" onClick={() => onMobileOpenChange(false)} aria-label="Close navigation">
            <X className="size-5" />
          </button>
        </div>

        <nav aria-label="Main navigation" className="mt-10 space-y-1.5">
          {navigation.map((item) => {
            const Icon = item.icon;
            const active = item.id === activeView;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => selectView(item.id)}
                aria-current={active ? "page" : undefined}
                className={`group flex w-full items-center gap-3 rounded-xl px-3.5 py-3 text-left text-sm font-medium transition ${active ? "bg-emerald-400 text-emerald-950 shadow-lg shadow-emerald-950/20" : "text-slate-300 hover:bg-white/7 hover:text-white"}`}
              >
                <Icon className="size-[18px]" aria-hidden="true" />
                {item.label}
              </button>
            );
          })}
        </nav>

        <div className="mt-auto space-y-4">
          <div className="rounded-2xl border border-emerald-300/10 bg-emerald-300/[0.055] p-4">
            <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-emerald-200">
              <span className="size-2 rounded-full bg-emerald-400 shadow-[0_0_0_4px_rgba(52,211,153,.1)]" />
              Local-first deployment
            </div>
            <p className="text-xs leading-5 text-slate-400">
              Data remains on this machine while Ollama, LangGraph, and MCP evaluate evidence.
            </p>
          </div>
          <button type="button" onClick={onLogout} className="flex w-full items-center gap-3 rounded-xl px-3.5 py-3 text-sm font-medium text-slate-400 transition hover:bg-white/7 hover:text-white">
            <LogOut className="size-[18px]" aria-hidden="true" />
            Sign out
          </button>
        </div>
      </aside>

      <div className="lg:pl-[280px]">
        <header className="sticky top-0 z-20 flex h-[72px] items-center justify-between border-b border-slate-200/80 bg-white/85 px-4 backdrop-blur-xl dark:border-white/8 dark:bg-[#081b16]/85 sm:px-7 lg:px-10">
          <div className="flex items-center gap-3">
            <button type="button" className="rounded-xl border border-slate-200 bg-white p-2.5 text-slate-600 shadow-sm dark:border-white/10 dark:bg-white/5 dark:text-slate-300 lg:hidden" onClick={() => onMobileOpenChange(true)} aria-label="Open navigation">
              <Menu className="size-5" />
            </button>
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.16em] text-emerald-700 dark:text-emerald-300">Workspace</p>
              <h1 className="text-base font-semibold tracking-tight">{current.label}</h1>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden rounded-full border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-800 dark:border-amber-300/15 dark:bg-amber-300/8 dark:text-amber-100 sm:inline-flex">
              Synthetic demo data
            </span>
            <button type="button" onClick={onThemeToggle} className="grid size-10 place-items-center rounded-xl border border-slate-200 bg-white text-slate-600 shadow-sm transition hover:border-emerald-300 hover:text-emerald-700 focus:outline-none focus:ring-4 focus:ring-emerald-500/10 dark:border-white/10 dark:bg-white/5 dark:text-slate-300" aria-label={`Switch to ${darkMode ? "light" : "dark"} theme`}>
              {darkMode ? <Sun className="size-4.5" /> : <Moon className="size-4.5" />}
            </button>
          </div>
        </header>

        <main className="mx-auto max-w-[1500px] px-4 py-7 sm:px-7 lg:px-10 lg:py-10">{children}</main>
      </div>
    </div>
  );
}
