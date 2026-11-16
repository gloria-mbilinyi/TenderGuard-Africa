import { Bot, CheckCircle2, KeyRound, LockKeyhole, Server, ShieldCheck, TriangleAlert } from "lucide-react";
import type { SystemStatus } from "../types";

export function SettingsPage({ status }: { status: SystemStatus | null }) {
  const modelReady = status?.model_status === "AVAILABLE";
  return (
    <div>
      <div className="mb-7"><p className="text-xs font-semibold uppercase tracking-[0.17em] text-emerald-700 dark:text-emerald-300">Local service configuration</p><h2 className="mt-2 text-3xl font-semibold tracking-[-0.04em]">Settings & service status</h2><p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600 dark:text-slate-400">Operational information is safe to display. Credentials, session identifiers, API keys, and internal logs remain server-side.</p></div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm dark:border-white/8 dark:bg-white/[0.035]">
          <div className="flex items-center gap-3"><span className="grid size-10 place-items-center rounded-xl bg-emerald-100 text-emerald-700 dark:bg-emerald-400/10 dark:text-emerald-300"><Server className="size-5" /></span><div><h3 className="font-semibold">API service</h3><p className="text-xs text-slate-500">FastAPI backend-for-frontend</p></div></div>
          <dl className="mt-6 divide-y divide-slate-100 text-sm dark:divide-white/7">
            <div className="flex items-center justify-between py-3"><dt className="text-slate-500">Status</dt><dd className="flex items-center gap-1.5 font-semibold text-emerald-700 dark:text-emerald-300"><CheckCircle2 className="size-4" />{status?.api_status ?? "Loading"}</dd></div>
            <div className="flex items-center justify-between py-3"><dt className="text-slate-500">Version</dt><dd className="font-mono text-xs">{status?.api_version ?? "—"}</dd></div>
            <div className="flex items-center justify-between py-3"><dt className="text-slate-500">Browser auth</dt><dd className="font-mono text-xs">{status?.authentication ?? "—"}</dd></div>
            <div className="flex items-center justify-between py-3"><dt className="text-slate-500">Browser secrets</dt><dd className="font-semibold text-emerald-700 dark:text-emerald-300">NOT EXPOSED</dd></div>
          </dl>
        </section>

        <section className="rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm dark:border-white/8 dark:bg-white/[0.035]">
          <div className="flex items-center gap-3"><span className="grid size-10 place-items-center rounded-xl bg-violet-100 text-violet-700 dark:bg-violet-400/10 dark:text-violet-300"><Bot className="size-5" /></span><div><h3 className="font-semibold">Local AI provider</h3><p className="text-xs text-slate-500">Open-weights inference through Ollama</p></div></div>
          <dl className="mt-6 divide-y divide-slate-100 text-sm dark:divide-white/7">
            <div className="flex items-center justify-between py-3"><dt className="text-slate-500">Provider</dt><dd className="font-semibold">{status?.ai_provider ?? "—"}</dd></div>
            <div className="flex items-center justify-between py-3"><dt className="text-slate-500">Configured model</dt><dd className="font-mono text-xs">{status?.model ?? "—"}</dd></div>
            <div className="flex items-center justify-between py-3"><dt className="text-slate-500">Connectivity</dt><dd className={`flex items-center gap-1.5 font-semibold ${modelReady ? "text-emerald-700 dark:text-emerald-300" : "text-amber-700 dark:text-amber-200"}`}>{modelReady ? <CheckCircle2 className="size-4" /> : <TriangleAlert className="size-4" />}{status?.model_status.replaceAll("_", " ") ?? "Checking"}</dd></div>
          </dl>
        </section>
      </div>

      <section className="mt-6 rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm dark:border-white/8 dark:bg-white/[0.035]">
        <div className="flex items-center gap-2"><ShieldCheck className="size-5 text-emerald-700 dark:text-emerald-300" /><h3 className="font-semibold">Security boundary</h3></div>
        <div className="mt-5 grid gap-4 md:grid-cols-3">
          {[{ icon: LockKeyhole, title: "HttpOnly session", text: "The browser receives an opaque cookie that JavaScript cannot read." }, { icon: KeyRound, title: "CSRF protection", text: "State-changing dashboard requests require an in-memory CSRF token." }, { icon: ShieldCheck, title: "Human authority", text: "No dashboard route can approve reports or make an award decision." }].map((item) => { const Icon = item.icon; return <div key={item.title} className="rounded-xl bg-slate-50 p-4 dark:bg-white/[0.035]"><Icon className="size-4 text-emerald-700 dark:text-emerald-300" /><h4 className="mt-3 text-sm font-semibold">{item.title}</h4><p className="mt-2 text-xs leading-5 text-slate-500">{item.text}</p></div>; })}
        </div>
        <p className="mt-5 text-xs leading-5 text-slate-500">This is a local single-operator demonstration mechanism—not production identity, multi-user authorization, or institutional role-based access control.</p>
      </section>
    </div>
  );
}
