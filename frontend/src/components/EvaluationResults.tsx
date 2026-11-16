import {
  AlertTriangle,
  CheckCircle2,
  CircleDollarSign,
  Database,
  FileWarning,
  Flag,
  Scale,
  ShieldCheck,
  UserRoundCheck,
  XCircle,
} from "lucide-react";
import type { EvaluationResult } from "../types";


function money(amount: number, currency: string) {
  return new Intl.NumberFormat("en-TZ", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(amount);
}

function SourcePill({ source }: { source: string }) {
  return (
    <span className="inline-flex max-w-full items-center gap-1.5 rounded-lg bg-slate-100 px-2.5 py-1.5 font-mono text-[11px] text-slate-600 dark:bg-white/7 dark:text-slate-400">
      <Database className="size-3 shrink-0" aria-hidden="true" />
      <span className="truncate">{source}</span>
    </span>
  );
}

export function EvaluationResults({ result }: { result: EvaluationResult }) {
  const compliance = result.compliance;
  const price = result.price_analysis;
  const supplier = result.supplier_risk;
  const sources = new Set<string>();
  compliance?.source_files.forEach((source) => sources.add(source));
  if (price) {
    sources.add(price.sources.bid);
    sources.add(price.sources.historical_awards);
  }
  supplier?.source_files.forEach((source) => sources.add(source));

  const pricePosition = price
    ? Math.max(
        0,
        Math.min(
          100,
          ((price.bid_price - price.historical_statistics.minimum) /
            Math.max(
              price.historical_statistics.maximum - price.historical_statistics.minimum,
              1,
            )) *
            100,
        ),
      )
    : 0;

  return (
    <section aria-labelledby="evaluation-results-title" className="mt-7 space-y-6">
      <div className="overflow-hidden rounded-2xl border border-amber-200 bg-gradient-to-r from-amber-50 to-white shadow-sm dark:border-amber-300/15 dark:from-amber-300/10 dark:to-white/[0.025]">
        <div className="grid gap-6 p-6 lg:grid-cols-[1fr_auto] lg:items-center lg:p-8">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-amber-800 dark:text-amber-200">
              <UserRoundCheck className="size-4" aria-hidden="true" />
              Mandatory human-review gate
            </div>
            <h2 id="evaluation-results-title" className="mt-2 text-2xl font-semibold tracking-[-0.03em]">
              {result.status.replaceAll("_", " ")}
            </h2>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-600 dark:text-slate-300">
              {result.decision_support.summary}
            </p>
          </div>
          <div className="grid min-w-64 gap-2 rounded-xl border border-amber-200/80 bg-white/75 p-4 text-sm dark:border-amber-300/10 dark:bg-black/10">
            <div className="flex items-center justify-between gap-5"><span className="text-slate-500">Review priority</span><strong className="text-amber-800 dark:text-amber-200">{result.decision_support.review_priority}</strong></div>
            <div className="flex items-center justify-between gap-5"><span className="text-slate-500">Committee required</span><strong>TRUE</strong></div>
            <div className="flex items-center justify-between gap-5"><span className="text-slate-500">Award decision</span><strong className="font-mono">NULL</strong></div>
          </div>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <article className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm dark:border-white/8 dark:bg-white/[0.035] sm:p-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.15em] text-slate-500">Mandatory compliance</p>
              <h3 className="mt-2 text-xl font-semibold">{compliance?.status ?? "Unavailable"}</h3>
            </div>
            <span className={`grid size-10 place-items-center rounded-xl ${compliance?.status === "COMPLIANT" ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-400/10 dark:text-emerald-300" : "bg-red-100 text-red-700 dark:bg-red-400/10 dark:text-red-300"}`}>
              {compliance?.status === "COMPLIANT" ? <ShieldCheck className="size-5" /> : <FileWarning className="size-5" />}
            </span>
          </div>
          {compliance && (
            <>
              <div className="mt-5 flex items-center gap-3 text-sm text-slate-500"><strong className="text-2xl text-slate-900 dark:text-white">{compliance.summary.passed_checks}/{compliance.summary.total_checks}</strong>checks passed</div>
              <div className="mt-5 space-y-3">
                {compliance.checks.map((check) => (
                  <div key={check.criterion} className="flex gap-3 rounded-xl bg-slate-50 p-3 dark:bg-white/[0.035]">
                    {check.passed ? <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-600" aria-hidden="true" /> : <XCircle className="mt-0.5 size-4 shrink-0 text-red-600" aria-hidden="true" />}
                    <div><p className="text-xs font-semibold">{check.criterion.replaceAll("_", " ")}</p><p className="mt-1 text-xs leading-5 text-slate-500 dark:text-slate-400">{check.finding}</p></div>
                  </div>
                ))}
              </div>
            </>
          )}
        </article>

        <article className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm dark:border-white/8 dark:bg-white/[0.035] sm:p-6">
          <div className="flex items-start justify-between gap-4">
            <div><p className="text-xs font-semibold uppercase tracking-[0.15em] text-slate-500">Historical price context</p><h3 className="mt-2 text-xl font-semibold">{price?.risk_level.replaceAll("_", " ") ?? "Unavailable"}</h3></div>
            <span className="grid size-10 place-items-center rounded-xl bg-sky-100 text-sky-700 dark:bg-sky-400/10 dark:text-sky-300"><CircleDollarSign className="size-5" /></span>
          </div>
          {price && (
            <>
              <div className="mt-6 grid grid-cols-2 gap-3">
                <div className="rounded-xl bg-slate-50 p-3 dark:bg-white/[0.035]"><p className="text-[11px] uppercase tracking-wider text-slate-500">Submitted</p><p className="mt-1 text-sm font-semibold">{money(price.bid_price, price.currency)}</p></div>
                <div className="rounded-xl bg-slate-50 p-3 dark:bg-white/[0.035]"><p className="text-[11px] uppercase tracking-wider text-slate-500">Median</p><p className="mt-1 text-sm font-semibold">{money(price.historical_statistics.median, price.currency)}</p></div>
              </div>
              <div className="mt-6">
                <div className="mb-2 flex justify-between text-[10px] font-medium text-slate-500"><span>{money(price.historical_statistics.minimum, price.currency)}</span><span>{money(price.historical_statistics.maximum, price.currency)}</span></div>
                <div className="relative h-2 rounded-full bg-slate-200 dark:bg-white/10"><div className="absolute inset-y-0 left-0 rounded-full bg-sky-400" style={{ width: `${pricePosition}%` }} /><span className="absolute top-1/2 size-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white bg-sky-700 shadow" style={{ left: `${pricePosition}%` }} /></div>
                <p className="mt-3 text-xs leading-5 text-slate-500 dark:text-slate-400">{price.finding} Sample: {price.historical_statistics.sample_size} historical awards.</p>
              </div>
            </>
          )}
        </article>

        <article className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm dark:border-white/8 dark:bg-white/[0.035] sm:p-6">
          <div className="flex items-start justify-between gap-4">
            <div><p className="text-xs font-semibold uppercase tracking-[0.15em] text-slate-500">Supplier-data review</p><h3 className="mt-2 text-xl font-semibold">{supplier?.risk_level ?? "Unavailable"}</h3></div>
            <span className="grid size-10 place-items-center rounded-xl bg-violet-100 text-violet-700 dark:bg-violet-400/10 dark:text-violet-300"><Flag className="size-5" /></span>
          </div>
          {supplier && (
            <div className="mt-5">
              <p className="text-sm text-slate-500"><strong className="text-2xl text-slate-900 dark:text-white">{supplier.flag_count}</strong> sourced flag{supplier.flag_count === 1 ? "" : "s"}</p>
              <div className="mt-4 space-y-3">
                {supplier.flags.length === 0 ? (
                  <div className="flex gap-3 rounded-xl bg-emerald-50 p-3 text-xs leading-5 text-emerald-800 dark:bg-emerald-400/8 dark:text-emerald-200"><CheckCircle2 className="mt-0.5 size-4 shrink-0" />No supplier-data inconsistency flags were found in the available history.</div>
                ) : supplier.flags.map((flag) => (
                  <div key={flag.code} className="rounded-xl border border-amber-200 bg-amber-50 p-3 dark:border-amber-300/10 dark:bg-amber-300/7"><div className="flex items-center gap-2 text-xs font-semibold text-amber-900 dark:text-amber-100"><AlertTriangle className="size-3.5" />{flag.code.replaceAll("_", " ")}</div><p className="mt-2 text-xs leading-5 text-amber-900/75 dark:text-amber-100/65">{flag.finding}</p></div>
                ))}
              </div>
            </div>
          )}
        </article>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.25fr_0.75fr]">
        <article className="rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm dark:border-white/8 dark:bg-white/[0.035]">
          <div className="flex items-center gap-2"><Scale className="size-4 text-emerald-700 dark:text-emerald-300" /><h3 className="font-semibold">Evidence-based reasons</h3></div>
          <ul className="mt-4 space-y-3">
            {result.decision_support.reasons.map((reason) => <li key={reason} className="flex gap-3 text-sm leading-6 text-slate-600 dark:text-slate-300"><span className="mt-2 size-1.5 shrink-0 rounded-full bg-emerald-500" />{reason}</li>)}
          </ul>
        </article>
        <article className="rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm dark:border-white/8 dark:bg-white/[0.035]">
          <h3 className="font-semibold">Source references</h3>
          <div className="mt-4 flex flex-wrap gap-2">{[...sources].map((source) => <SourcePill key={source} source={source} />)}</div>
          <p className="mt-4 text-xs leading-5 text-slate-500">References identify the synthetic files used by the executed MCP tools. Audit files are not exposed here.</p>
        </article>
      </div>

      <div className="flex items-center gap-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900 dark:border-emerald-300/12 dark:bg-emerald-300/7 dark:text-emerald-100">
        <ShieldCheck className="size-5 shrink-0" aria-hidden="true" />
        <p><strong>Safety contract preserved:</strong> this result contains no award, rejection, disqualification, or winning-bidder selection.</p>
      </div>
    </section>
  );
}
