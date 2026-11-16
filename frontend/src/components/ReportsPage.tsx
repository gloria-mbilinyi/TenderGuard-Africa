import { Download, FileCheck2, FileText, LockKeyhole, UserRoundCheck } from "lucide-react";
import type { ReportItem } from "../types";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export function ReportsPage({ reports }: { reports: ReportItem[] }) {
  return (
    <div>
      <div className="mb-7"><p className="text-xs font-semibold uppercase tracking-[0.17em] text-emerald-700 dark:text-emerald-300">Protected output library</p><h2 className="mt-2 text-3xl font-semibold tracking-[-0.04em]">Evaluation reports</h2><p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600 dark:text-slate-400">Only legitimately generated draft reports are listed. Audit logs and supplier datasets are never exposed through this endpoint.</p></div>

      <div className="mb-6 flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-900 dark:border-amber-300/12 dark:bg-amber-300/7 dark:text-amber-100">
        <UserRoundCheck className="mt-0.5 size-5 shrink-0" />
        <p><strong>Report authorization is not available in the browser.</strong> The existing named-approver string does not verify identity, so production approval actions remain disabled until role-based identity is implemented.</p>
      </div>

      <section className="overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-sm dark:border-white/8 dark:bg-white/[0.035]">
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4 dark:border-white/7 sm:px-6"><div><h3 className="font-semibold">Available drafts</h3><p className="mt-1 text-xs text-slate-500">Session-protected Markdown downloads</p></div><span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600 dark:bg-white/8 dark:text-slate-300">{reports.length}</span></div>
        {reports.length === 0 ? (
          <div className="flex min-h-72 flex-col items-center justify-center px-6 py-12 text-center"><span className="grid size-14 place-items-center rounded-2xl bg-slate-100 text-slate-400 dark:bg-white/6"><FileText className="size-6" /></span><h4 className="mt-4 font-semibold">No generated draft reports</h4><p className="mt-2 max-w-md text-sm leading-6 text-slate-500">A report appears here only after the separate local human-review CLI gate has legitimately generated it.</p></div>
        ) : (
          <div className="divide-y divide-slate-100 dark:divide-white/7">
            {reports.map((report) => (
              <article key={report.filename} className="flex flex-col gap-4 px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
                <div className="flex min-w-0 items-start gap-4"><span className="grid size-11 shrink-0 place-items-center rounded-xl bg-emerald-100 text-emerald-700 dark:bg-emerald-400/10 dark:text-emerald-300"><FileCheck2 className="size-5" /></span><div className="min-w-0"><h4 className="truncate font-semibold">{report.filename}</h4><div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500"><span>{report.bid_id}</span><span>{formatDate(report.modified_at)}</span><span>{Math.ceil(report.size_bytes / 1024)} KB</span></div><span className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-amber-100 px-2.5 py-1 text-[11px] font-semibold text-amber-800 dark:bg-amber-400/10 dark:text-amber-200"><LockKeyhole className="size-3" />Draft for committee review</span></div></div>
                <a href={report.download_url} download className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:border-emerald-400 hover:text-emerald-700 focus:outline-none focus:ring-4 focus:ring-emerald-500/10 dark:border-white/12 dark:bg-white/5 dark:text-slate-200"><Download className="size-4" />Download</a>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
