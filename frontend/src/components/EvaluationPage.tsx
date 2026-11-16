import {
  AlertCircle,
  ArrowRight,
  Building2,
  CalendarClock,
  Check,
  FileCheck2,
  LoaderCircle,
  ScanSearch,
  WalletCards,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { CatalogTender, EvaluationResult } from "../types";
import { EvaluationResults } from "./EvaluationResults";

interface EvaluationPageProps {
  tenders: CatalogTender[];
  result: EvaluationResult | null;
  onEvaluate: (tenderId: string, bidId: string) => Promise<void>;
}

function money(amount: number, currency: string) {
  return new Intl.NumberFormat("en-TZ", { style: "currency", currency, maximumFractionDigits: 0 }).format(amount);
}

function date(value: string) {
  return new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short", timeZone: "Africa/Nairobi" }).format(new Date(value));
}

export function EvaluationPage({ tenders, result, onEvaluate }: EvaluationPageProps) {
  const [tenderId, setTenderId] = useState(tenders[0]?.tender_id ?? "");
  const tender = useMemo(() => tenders.find((item) => item.tender_id === tenderId) ?? tenders[0], [tenderId, tenders]);
  const [bidId, setBidId] = useState(tender?.bids[0]?.bid_id ?? "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (tender && !tender.bids.some((bid) => bid.bid_id === bidId)) {
      setBidId(tender.bids[0]?.bid_id ?? "");
    }
  }, [bidId, tender]);

  async function evaluate() {
    if (!tender || !bidId) return;
    setLoading(true);
    setError(null);
    try {
      await onEvaluate(tender.tender_id, bidId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Evaluation failed.");
    } finally {
      setLoading(false);
    }
  }

  if (!tender) {
    return <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center dark:border-white/8 dark:bg-white/[0.035]">No synthetic tenders are available.</div>;
  }

  return (
    <div>
      <div className="mb-7 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div><p className="text-xs font-semibold uppercase tracking-[0.17em] text-emerald-700 dark:text-emerald-300">Real local agent execution</p><h2 className="mt-2 text-3xl font-semibold tracking-[-0.04em]">Evaluate tender evidence</h2><p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600 dark:text-slate-400">Choose a synthetic record. The backend will invoke the existing LangGraph workflow, Procurement MCP tools, and Ollama model.</p></div>
        <span className="inline-flex w-fit items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-800 dark:border-amber-300/12 dark:bg-amber-300/7 dark:text-amber-100"><AlertCircle className="size-3.5" />Synthetic demonstration</span>
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.86fr_1.14fr]">
        <section className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm dark:border-white/8 dark:bg-white/[0.035] sm:p-6">
          <label htmlFor="tender-select" className="text-sm font-semibold">Available tender</label>
          <select id="tender-select" value={tender.tender_id} onChange={(event) => setTenderId(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3.5 py-3 text-sm outline-none focus:border-emerald-500 focus:ring-4 focus:ring-emerald-500/10 dark:border-white/10 dark:bg-[#0a211b]">
            {tenders.map((item) => <option key={item.tender_id} value={item.tender_id}>{item.title} · {item.tender_id}</option>)}
          </select>

          <div className="mt-6 border-t border-slate-100 pt-6 dark:border-white/7">
            <div className="flex items-start justify-between gap-3"><div><p className="font-mono text-xs text-emerald-700 dark:text-emerald-300">{tender.tender_id}</p><h3 className="mt-1 text-xl font-semibold tracking-tight">{tender.title}</h3></div><span className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-semibold capitalize text-emerald-800 dark:bg-emerald-400/10 dark:text-emerald-200">{tender.status}</span></div>
            <p className="mt-4 text-sm leading-6 text-slate-600 dark:text-slate-400">{tender.description}</p>
            <dl className="mt-6 grid gap-4 sm:grid-cols-2">
              <div className="flex gap-3"><Building2 className="mt-0.5 size-4 text-slate-400" /><div><dt className="text-xs text-slate-500">Procuring entity</dt><dd className="mt-1 text-sm font-medium">{tender.procuring_entity}</dd></div></div>
              <div className="flex gap-3"><WalletCards className="mt-0.5 size-4 text-slate-400" /><div><dt className="text-xs text-slate-500">Estimated value</dt><dd className="mt-1 text-sm font-medium">{money(tender.amount, tender.currency)}</dd></div></div>
              <div className="flex gap-3"><CalendarClock className="mt-0.5 size-4 text-slate-400" /><div><dt className="text-xs text-slate-500">Submission deadline</dt><dd className="mt-1 text-sm font-medium">{date(tender.submission_deadline)} EAT</dd></div></div>
              <div className="flex gap-3"><FileCheck2 className="mt-0.5 size-4 text-slate-400" /><div><dt className="text-xs text-slate-500">Mandatory documents</dt><dd className="mt-1 text-sm font-medium">{tender.required_documents.length} required</dd></div></div>
            </dl>
            <div className="mt-6 flex flex-wrap gap-2">{tender.required_documents.map((requirement) => <span key={requirement.code} className="rounded-lg bg-slate-100 px-2.5 py-1.5 text-[11px] font-medium text-slate-600 dark:bg-white/6 dark:text-slate-400">{requirement.code}</span>)}</div>
            <p className="mt-5 truncate font-mono text-[11px] text-slate-400">Source: {tender.source_file}</p>
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm dark:border-white/8 dark:bg-white/[0.035] sm:p-6">
          <div><p className="text-sm font-semibold">Select bid under review</p><p className="mt-1 text-xs text-slate-500">Supplier records are synthetic and contain no live procurement data.</p></div>
          <fieldset className="mt-5 space-y-3">
            <legend className="sr-only">Available supplier bids</legend>
            {tender.bids.map((bid) => {
              const active = bid.bid_id === bidId;
              return (
                <label key={bid.bid_id} className={`block cursor-pointer rounded-2xl border p-4 transition ${active ? "border-emerald-500 bg-emerald-50/70 ring-4 ring-emerald-500/8 dark:border-emerald-400 dark:bg-emerald-400/7" : "border-slate-200 hover:border-slate-300 dark:border-white/8 dark:hover:border-white/16"}`}>
                  <input type="radio" name="bid" value={bid.bid_id} checked={active} onChange={() => setBidId(bid.bid_id)} className="sr-only" />
                  <div className="flex items-start justify-between gap-4">
                    <div><div className="flex items-center gap-2"><h3 className="font-semibold">{bid.supplier_name}</h3>{active && <span className="grid size-5 place-items-center rounded-full bg-emerald-600 text-white"><Check className="size-3" /></span>}</div><p className="mt-1 font-mono text-xs text-slate-500">{bid.bid_id}</p></div>
                    <p className="text-sm font-semibold">{money(bid.amount, bid.currency)}</p>
                  </div>
                  <div className="mt-4 grid gap-2 text-xs text-slate-500 sm:grid-cols-2"><span>Submitted {date(bid.submitted_at)} EAT</span><span className="sm:text-right">{bid.submitted_document_codes.length} documents supplied</span></div>
                </label>
              );
            })}
          </fieldset>

          {error && <div role="alert" className="mt-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-400/15 dark:bg-red-400/8 dark:text-red-200"><strong>Evaluation could not complete.</strong><p className="mt-1">{error}</p></div>}

          <button type="button" onClick={evaluate} disabled={!bidId || loading} className="mt-6 flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-700 px-5 py-3.5 text-sm font-semibold text-white shadow-lg shadow-emerald-900/10 transition hover:bg-emerald-800 focus:outline-none focus:ring-4 focus:ring-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-emerald-400 dark:text-emerald-950 dark:hover:bg-emerald-300">
            {loading ? <><LoaderCircle className="size-4 animate-spin" />Evaluating with local AI…</> : <><ScanSearch className="size-4" />Evaluate tender<ArrowRight className="size-4" /></>}
          </button>
          {loading && <div aria-live="polite" className="mt-4 rounded-xl bg-slate-50 px-4 py-3 text-xs leading-5 text-slate-500 dark:bg-white/[0.035] dark:text-slate-400"><strong className="text-slate-700 dark:text-slate-200">A real workflow is running.</strong> LangGraph is calling MCP tools and Ollama. Intermediate progress is not streamed, so no percentage is shown. This can take up to three minutes.</div>}
        </section>
      </div>

      {result && <EvaluationResults result={result} />}
    </div>
  );
}
