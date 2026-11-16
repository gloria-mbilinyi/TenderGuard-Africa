import { CalendarDays, Download, FileCheck2, FileText, LockKeyhole, UserRoundCheck } from "lucide-react";
import type { ReportItem } from "../types";

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Date unavailable";
  return new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export function ReportsPage({ reports }: { reports: ReportItem[] }) {
  return (
    <div>
      <div className="mb-7">
        <p className="text-xs font-semibold uppercase tracking-[0.17em] text-emerald-700 dark:text-emerald-300">Committee review library</p>
        <h2 className="mt-2 text-3xl font-semibold tracking-[-0.04em]">Evaluation reports</h2>
        <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600 dark:text-slate-400">Find a tender, review the suppliers involved, and download its draft evidence report for human committee review.</p>
      </div>

      <div className="mb-6 flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-900 dark:border-amber-300/12 dark:bg-amber-300/7 dark:text-amber-100">
        <UserRoundCheck className="mt-0.5 size-5 shrink-0" />
        <p><strong>Human committee review remains required.</strong> Draft report generation is authorized separately through the local CLI. Recorded authorizer names are not independently verified identities.</p>
      </div>

      <section className="overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-sm dark:border-white/8 dark:bg-white/[0.035]">
        <div className="flex items-center justify-between gap-4 border-b border-slate-100 px-5 py-4 dark:border-white/7 sm:px-6">
          <div><h3 className="font-semibold">Available drafts</h3><p className="mt-1 text-xs text-slate-500">Session-protected report downloads</p></div>
          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600 dark:bg-white/8 dark:text-slate-300">{reports.length}</span>
        </div>
        {reports.length === 0 ? (
          <div className="flex min-h-72 flex-col items-center justify-center px-6 py-12 text-center">
            <span className="grid size-14 place-items-center rounded-2xl bg-slate-100 text-slate-400 dark:bg-white/6"><FileText className="size-6" /></span>
            <h4 className="mt-4 font-semibold">No generated draft reports</h4>
            <p className="mt-2 max-w-md text-sm leading-6 text-slate-500">A report appears here after the separate human-review CLI step generates a draft.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100 dark:divide-white/7">
            {reports.map((report) => (
              <article key={report.filename} className="px-5 py-6 sm:px-6 sm:py-7">
                <div className="flex items-start gap-3 sm:gap-4">
                  <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-emerald-100 text-emerald-700 dark:bg-emerald-400/10 dark:text-emerald-300 sm:size-12"><FileCheck2 className="size-5" /></span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-col items-start gap-3 xl:flex-row xl:justify-between xl:gap-6">
                      <div className="min-w-0">
                        <h4 className="break-words text-lg font-semibold leading-7 tracking-tight sm:text-xl">{report.tender_title || report.filename}</h4>
                        <p className="mt-1.5 break-words text-sm leading-6 text-slate-600 dark:text-slate-300">{report.supplier_names?.length ? report.supplier_names.join(" vs ") : "Supplier details unavailable for this archived report"}</p>
                      </div>
                      <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-amber-100 px-2.5 py-1 text-[11px] font-semibold text-amber-800 dark:bg-amber-400/10 dark:text-amber-200"><LockKeyhole className="size-3" />Draft for committee review</span>
                    </div>

                    <p className="mt-3 break-all font-mono text-[11px] leading-5 text-slate-500 dark:text-slate-400">{report.workspace_id ? `Workspace: ${report.workspace_id}` : `Bid reference: ${report.bid_id}`}</p>

                    <div className="mt-5 flex flex-col gap-5 border-t border-slate-100 pt-4 dark:border-white/7 lg:flex-row lg:items-end lg:justify-between">
                      <dl className="grid min-w-0 gap-x-8 gap-y-4 text-xs sm:grid-cols-2">
                        <div>
                          <dt className="flex items-center gap-1.5 text-slate-500"><CalendarDays className="size-3.5" />{report.generated_at ? "Report generated" : "File last updated"}</dt>
                          <dd className="mt-1.5 font-medium text-slate-700 dark:text-slate-200"><time dateTime={report.generated_at || report.modified_at}>{formatDate(report.generated_at || report.modified_at)}</time></dd>
                        </div>
                        <div>
                          <dt className="text-slate-500">Report generation authorized by</dt>
                          <dd className="mt-1.5 break-words font-medium text-slate-700 dark:text-slate-200">{report.approved_by || "Not recorded in this report"}</dd>
                          {report.approved_by && <dd className="mt-1 text-[11px] leading-5 text-slate-500">Recorded name; identity not independently verified</dd>}
                        </div>
                      </dl>
                      <a href={report.download_url} download aria-label={`Download draft report: ${report.tender_title || report.filename}`} className="inline-flex w-full shrink-0 items-center justify-center gap-2 rounded-xl bg-emerald-700 px-4 py-3 text-sm font-semibold text-white transition hover:bg-emerald-800 focus:outline-none focus:ring-4 focus:ring-emerald-500/20 dark:bg-emerald-400 dark:text-emerald-950 dark:hover:bg-emerald-300 sm:w-fit"><Download className="size-4" />Download draft report<span className="text-xs font-normal opacity-80">· {Math.max(1, Math.ceil(report.size_bytes / 1024))} KB</span></a>
                    </div>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
