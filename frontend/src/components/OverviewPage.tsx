import {
  ArrowRight,
  Bot,
  CheckCircle2,
  FileCheck2,
  FileText,
  ScanSearch,
  ShieldCheck,
} from "lucide-react";
import type {
  CatalogTender,
  EvaluationSummary,
  ReportItem,
  SystemStatus,
} from "../types";

interface OverviewPageProps {
  tenders: CatalogTender[];
  evaluations: EvaluationSummary[];
  reports: ReportItem[];
  systemStatus: SystemStatus | null;
  onStartEvaluation: () => void;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function OverviewPage({ tenders, evaluations, reports, systemStatus, onStartEvaluation }: OverviewPageProps) {
  const cards = [
    { label: "Synthetic tenders", value: tenders.length, note: "Available for local review", icon: FileCheck2, tone: "emerald" },
    { label: "Completed evaluations", value: evaluations.length, note: "This server session", icon: ScanSearch, tone: "blue" },
    { label: "Generated reports", value: reports.length, note: "Protected draft downloads", icon: FileText, tone: "amber" },
    { label: "Local AI model", value: systemStatus?.model_status === "AVAILABLE" ? "Ready" : "Check", note: systemStatus?.model ?? "Loading status", icon: Bot, tone: "violet" },
  ];

  return (
    <div className="space-y-7">
      <section className="relative overflow-hidden rounded-[28px] bg-[#09271f] px-6 py-8 text-white shadow-xl shadow-emerald-950/10 sm:px-9 lg:flex lg:items-center lg:justify-between lg:px-11 lg:py-10">
        <div className="pointer-events-none absolute right-0 top-0 h-full w-1/2 opacity-30 [background-image:radial-gradient(circle_at_70%_20%,rgba(52,211,153,.3),transparent_38%)]" />
        <div className="relative max-w-3xl">
          <div className="mb-4 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.17em] text-emerald-200/80">
            <ShieldCheck className="size-4" aria-hidden="true" />
            Human-governed procurement intelligence
          </div>
          <h2 className="text-3xl font-semibold tracking-[-0.035em] sm:text-4xl">
            Evidence prepared by AI. Decisions retained by people.
          </h2>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300 sm:text-base">
            Run a source-grounded local evaluation across mandatory compliance, historical price context, and supplier-data consistency.
          </p>
        </div>
        <button type="button" onClick={onStartEvaluation} className="relative mt-7 inline-flex items-center gap-2 rounded-xl bg-emerald-400 px-5 py-3 text-sm font-semibold text-emerald-950 shadow-lg shadow-black/15 transition hover:bg-emerald-300 focus:outline-none focus:ring-4 focus:ring-emerald-300/25 lg:mt-0 lg:ml-8">
          Evaluate a tender
          <ArrowRight className="size-4" aria-hidden="true" />
        </button>
      </section>

      <section aria-label="Overview metrics" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => {
          const Icon = card.icon;
          const tones: Record<string, string> = {
            emerald: "bg-emerald-50 text-emerald-700 dark:bg-emerald-400/10 dark:text-emerald-300",
            blue: "bg-sky-50 text-sky-700 dark:bg-sky-400/10 dark:text-sky-300",
            amber: "bg-amber-50 text-amber-700 dark:bg-amber-400/10 dark:text-amber-300",
            violet: "bg-violet-50 text-violet-700 dark:bg-violet-400/10 dark:text-violet-300",
          };
          return (
            <article key={card.label} className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm dark:border-white/8 dark:bg-white/[0.035]">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{card.label}</p>
                  <p className="mt-2 text-3xl font-semibold tracking-[-0.04em]">{card.value}</p>
                </div>
                <span className={`grid size-10 place-items-center rounded-xl ${tones[card.tone]}`}>
                  <Icon className="size-[18px]" aria-hidden="true" />
                </span>
              </div>
              <p className="mt-4 text-xs text-slate-500 dark:text-slate-500">{card.note}</p>
            </article>
          );
        })}
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.55fr_0.85fr]">
        <section className="rounded-2xl border border-slate-200/80 bg-white shadow-sm dark:border-white/8 dark:bg-white/[0.035]">
          <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4 dark:border-white/7 sm:px-6">
            <div>
              <h3 className="font-semibold tracking-tight">Recent evaluations</h3>
              <p className="mt-1 text-xs text-slate-500">Only completed executions from this server session</p>
            </div>
            <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600 dark:bg-white/8 dark:text-slate-300">{evaluations.length} total</span>
          </div>
          {evaluations.length === 0 ? (
            <div className="flex min-h-64 flex-col items-center justify-center px-6 py-10 text-center">
              <span className="grid size-12 place-items-center rounded-2xl bg-slate-100 text-slate-500 dark:bg-white/6 dark:text-slate-400">
                <ScanSearch className="size-5" aria-hidden="true" />
              </span>
              <h4 className="mt-4 font-semibold">No evaluations yet</h4>
              <p className="mt-2 max-w-sm text-sm leading-6 text-slate-500">Run the local AI agent to populate this activity list with real results.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[670px] text-left text-sm">
                <thead className="bg-slate-50/80 text-xs uppercase tracking-wider text-slate-500 dark:bg-white/[0.025] dark:text-slate-500">
                  <tr><th className="px-6 py-3 font-medium">Supplier</th><th className="px-4 py-3 font-medium">Bid</th><th className="px-4 py-3 font-medium">Priority</th><th className="px-4 py-3 font-medium">Completed</th><th className="px-6 py-3 font-medium">Status</th></tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-white/6">
                  {evaluations.map((evaluation) => (
                    <tr key={evaluation.evaluation_id} className="hover:bg-slate-50/70 dark:hover:bg-white/[0.025]">
                      <td className="px-6 py-4 font-medium">{evaluation.supplier ?? "Supplier unavailable"}</td>
                      <td className="px-4 py-4 font-mono text-xs text-slate-500">{evaluation.bid_id}</td>
                      <td className="px-4 py-4"><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${evaluation.review_priority === "ATTENTION_REQUIRED" ? "bg-amber-100 text-amber-800 dark:bg-amber-400/10 dark:text-amber-200" : "bg-emerald-100 text-emerald-800 dark:bg-emerald-400/10 dark:text-emerald-200"}`}>{evaluation.review_priority.replace("_", " ")}</span></td>
                      <td className="px-4 py-4 text-xs text-slate-500">{formatDate(evaluation.completed_at)}</td>
                      <td className="px-6 py-4"><span className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-700 dark:text-emerald-300"><CheckCircle2 className="size-3.5" />Human review</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm dark:border-white/8 dark:bg-white/[0.035]">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-emerald-700 dark:text-emerald-300">Governance by design</p>
          <h3 className="mt-2 text-xl font-semibold tracking-tight">The final action is always human.</h3>
          <div className="mt-6 space-y-5">
            {["AI compiles source-grounded findings", "Deterministic guards preserve review priority", "Procurement committee retains the award decision"].map((item, index) => (
              <div key={item} className="flex gap-3">
                <span className="grid size-7 shrink-0 place-items-center rounded-full bg-emerald-100 text-xs font-bold text-emerald-800 dark:bg-emerald-400/10 dark:text-emerald-200">{index + 1}</span>
                <p className="pt-1 text-sm leading-6 text-slate-600 dark:text-slate-400">{item}</p>
              </div>
            ))}
          </div>
          <div className="mt-7 rounded-xl border border-emerald-200 bg-emerald-50 p-4 dark:border-emerald-300/12 dark:bg-emerald-300/[0.055]">
            <p className="font-mono text-xs font-semibold text-emerald-800 dark:text-emerald-200">final_award_decision = null</p>
          </div>
        </section>
      </div>
    </div>
  );
}
