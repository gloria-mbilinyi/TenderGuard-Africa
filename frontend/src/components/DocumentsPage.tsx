import {
  AlertTriangle,
  CheckCircle2,
  FilePlus2,
  FileSearch,
  Files,
  LoaderCircle,
  Plus,
  ScanSearch,
  ShieldCheck,
  Upload,
  XCircle,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import * as api from "../lib/api";
import type {
  DocumentEvaluationResult,
  DocumentSupplierEvaluation,
  DocumentWorkspace,
  PageCitation,
  RequirementFinding,
} from "../types";

interface DocumentsPageProps {
  workspaces: DocumentWorkspace[];
  onWorkspacesChange: (workspaces: DocumentWorkspace[]) => void;
}

function money(amount: number, currency: string) {
  return new Intl.NumberFormat("en-TZ", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(amount);
}

function Citation({ source }: { source: PageCitation }) {
  return (
    <details className="rounded-lg bg-slate-100 px-2.5 py-1.5 text-[11px] dark:bg-white/7">
      <summary className="cursor-pointer font-mono text-slate-600 dark:text-slate-300">
        {source.filename} · page {source.page}
      </summary>
      <p className="mt-2 border-t border-slate-200 pt-2 leading-5 text-slate-500 dark:border-white/8 dark:text-slate-400">
        “{source.quote}”
      </p>
    </details>
  );
}

function Finding({ finding }: { finding: RequirementFinding }) {
  const positive = finding.status === "VERIFIED_COMPLIANT";
  const Icon = positive ? CheckCircle2 : finding.status === "VERIFIED_NONCOMPLIANT" ? XCircle : AlertTriangle;
  return (
    <div className="rounded-xl border border-slate-200 p-3 dark:border-white/8">
      <div className="flex gap-2.5">
        <Icon className={`mt-0.5 size-4 shrink-0 ${positive ? "text-emerald-600" : finding.status === "VERIFIED_NONCOMPLIANT" ? "text-red-600" : "text-amber-600"}`} />
        <div className="min-w-0">
          <p className="text-xs font-semibold">{finding.code} · {finding.status.replaceAll("_", " ")}</p>
          <p className="mt-1 text-xs leading-5 text-slate-500 dark:text-slate-400">{finding.finding}</p>
          <div className="mt-2 flex flex-wrap gap-2">{finding.sources.map((source, index) => <Citation key={`${source.document_id}-${source.page}-${index}`} source={source} />)}</div>
        </div>
      </div>
    </div>
  );
}

function supplierFindings(supplier: DocumentSupplierEvaluation) {
  return [...supplier.document_checks, ...supplier.eligibility_checks, ...supplier.technical_checks, supplier.financial_check];
}

function statusCount(supplier: DocumentSupplierEvaluation, status: RequirementFinding["status"]) {
  return supplierFindings(supplier).filter((item) => item.status === status).length;
}

function DocumentResults({ result }: { result: DocumentEvaluationResult }) {
  return (
    <section className="mt-8 space-y-6" aria-labelledby="document-results-title">
      <div className="rounded-2xl border border-amber-200 bg-gradient-to-r from-amber-50 to-white p-6 shadow-sm dark:border-amber-300/15 dark:from-amber-300/10 dark:to-white/[0.025] sm:p-8">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div><p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-amber-800 dark:text-amber-200"><ShieldCheck className="size-4" />Human-review state</p><h3 id="document-results-title" className="mt-2 text-2xl font-semibold tracking-tight">{result.status.replaceAll("_", " ")}</h3><p className="mt-3 max-w-3xl text-sm leading-7 text-slate-600 dark:text-slate-300">{result.decision_support.summary}</p></div>
          <dl className="min-w-64 rounded-xl border border-amber-200 bg-white/70 p-4 text-sm dark:border-amber-300/10 dark:bg-black/10"><div className="flex justify-between gap-5"><dt className="text-slate-500">Priority</dt><dd className="font-semibold">{result.decision_support.review_priority}</dd></div><div className="mt-2 flex justify-between gap-5"><dt className="text-slate-500">Award decision</dt><dd className="font-mono font-semibold">NULL</dd></div></dl>
        </div>
      </div>

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-white/8 dark:bg-white/[0.035]">
        <div className="border-b border-slate-100 px-5 py-4 dark:border-white/7"><h3 className="font-semibold">Supplier evidence comparison</h3><p className="mt-1 text-xs text-slate-500">Evidence states are descriptive; they are not an award ranking.</p></div>
        <div className="overflow-x-auto"><table className="w-full min-w-[850px] text-left text-sm"><thead className="bg-slate-50 text-xs uppercase tracking-wider text-slate-500 dark:bg-white/[0.025]"><tr><th className="px-5 py-3">Supplier</th><th className="px-4 py-3">Evidence state</th><th className="px-4 py-3">Price</th><th className="px-4 py-3">Verified checks</th><th className="px-4 py-3">Missing evidence</th><th className="px-5 py-3">Risk flags</th></tr></thead><tbody className="divide-y divide-slate-100 dark:divide-white/7">{result.suppliers.map((supplier) => <tr key={supplier.document_id}><td className="px-5 py-4 font-semibold">{String(supplier.supplier_name.value ?? supplier.filename)}</td><td className="px-4 py-4"><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${supplier.evidence_status === "COMPLIANT_WITH_AVAILABLE_EVIDENCE" ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-400/10 dark:text-emerald-200" : "bg-amber-100 text-amber-800 dark:bg-amber-400/10 dark:text-amber-200"}`}>{supplier.evidence_status.replaceAll("_", " ")}</span></td><td className="px-4 py-4 font-medium">{typeof supplier.bid_price.value === "number" && typeof supplier.currency.value === "string" ? money(supplier.bid_price.value, supplier.currency.value) : "Unverified"}</td><td className="px-4 py-4">{statusCount(supplier, "VERIFIED_COMPLIANT")}</td><td className="px-4 py-4">{supplier.missing_documents.length ? supplier.missing_documents.join(", ") : "None identified"}</td><td className="px-5 py-4">{supplier.risk_flags.length}</td></tr>)}</tbody></table></div>
      </section>

      <div className="grid gap-6 xl:grid-cols-2">{result.suppliers.map((supplier) => <article key={supplier.document_id} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-white/8 dark:bg-white/[0.035]"><h3 className="font-semibold">{String(supplier.supplier_name.value ?? supplier.filename)}</h3><p className="mt-1 font-mono text-xs text-slate-500">{supplier.filename}</p>{supplier.risk_flags.map((flag) => <div key={flag.code} className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900 dark:border-amber-300/12 dark:bg-amber-300/7 dark:text-amber-100"><strong>{flag.code}</strong><p className="mt-1 leading-5">{flag.finding}</p><div className="mt-2 flex flex-wrap gap-2">{flag.sources.map((source, index) => <Citation key={`${source.document_id}-${source.page}-${index}`} source={source} />)}</div></div>)}<details className="mt-4"><summary className="cursor-pointer text-sm font-semibold text-emerald-700 dark:text-emerald-300">Inspect all page-cited findings</summary><div className="mt-3 space-y-2">{supplierFindings(supplier).map((finding) => <Finding key={`${finding.code}-${finding.status}`} finding={finding} />)}</div></details></article>)}</div>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-white/8 dark:bg-white/[0.035]"><h3 className="font-semibold">Direct submitted-price context</h3>{result.comparison.price_order.length > 0 && <div className="mt-4 grid gap-3 sm:grid-cols-2">{result.comparison.price_order.map((item) => <div key={item.document_id} className="rounded-xl bg-slate-50 p-4 dark:bg-white/[0.035]"><p className="text-sm font-semibold">{item.supplier_name}</p><p className="mt-1 text-xl font-semibold">{money(item.amount, item.currency)}</p><div className="mt-3"><Citation source={item.source} /></div></div>)}</div>}<ul className="mt-5 space-y-2">{result.comparison.notes.map((note) => <li key={note} className="flex gap-2 text-xs leading-5 text-slate-500"><span className="mt-2 size-1.5 shrink-0 rounded-full bg-emerald-500" />{note}</li>)}</ul></section>
    </section>
  );
}

export function DocumentsPage({ workspaces, onWorkspacesChange }: DocumentsPageProps) {
  const [selectedId, setSelectedId] = useState(workspaces[0]?.workspace_id ?? "");
  const selected = useMemo(() => workspaces.find((item) => item.workspace_id === selectedId) ?? workspaces[0], [selectedId, workspaces]);
  const [title, setTitle] = useState("Nairobi synthetic PDF evaluation");
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DocumentEvaluationResult | null>(null);

  useEffect(() => {
    if (!selectedId && workspaces[0]) setSelectedId(workspaces[0].workspace_id);
  }, [selectedId, workspaces]);

  function updateWorkspace(workspace: DocumentWorkspace) {
    onWorkspacesChange([workspace, ...workspaces.filter((item) => item.workspace_id !== workspace.workspace_id)]);
    setSelectedId(workspace.workspace_id);
  }

  async function create() {
    setBusy("create"); setError(null); setMessage(null);
    try { const workspace = await api.createDocumentWorkspace(title); updateWorkspace(workspace); setResult(null); setMessage("Workspace created. Upload one tender PDF and at least two supplier bid PDFs."); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Workspace could not be created."); }
    finally { setBusy(null); }
  }

  async function upload(files: FileList | null, type: "TENDER_REQUIREMENTS" | "SUPPLIER_BID") {
    if (!selected || !files?.length) return;
    setBusy(type); setError(null); setMessage(null);
    try {
      let workspace = selected;
      for (const file of Array.from(files)) {
        if (!file.name.toLowerCase().endsWith(".pdf") || (file.type && file.type !== "application/pdf")) throw new Error(`${file.name} is not a PDF.`);
        if (file.size > 10 * 1024 * 1024) throw new Error(`${file.name} exceeds the 10 MB demonstration limit.`);
        workspace = await api.uploadDocument(workspace.workspace_id, file, type);
        updateWorkspace(workspace);
      }
      setMessage(`${files.length} PDF${files.length === 1 ? "" : "s"} uploaded and text-extracted.`);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "PDF upload failed."); }
    finally { setBusy(null); }
  }

  async function evaluate() {
    if (!selected) return;
    setBusy("evaluate"); setError(null); setMessage(null);
    try { const evaluation = await api.evaluateDocuments(selected.workspace_id); setResult(evaluation); const refreshed = await api.getDocumentWorkspace(selected.workspace_id); updateWorkspace(refreshed); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Document evaluation failed."); }
    finally { setBusy(null); }
  }

  async function loadResult() {
    if (!selected) return;
    setBusy("result"); setError(null);
    try { setResult(await api.getDocumentResult(selected.workspace_id)); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Result could not be loaded."); }
    finally { setBusy(null); }
  }

  const tenderUploaded = selected?.documents.some((item) => item.document_type === "TENDER_REQUIREMENTS");
  const bidCount = selected?.documents.filter((item) => item.document_type === "SUPPLIER_BID").length ?? 0;

  return (
    <div>
      <div className="mb-7"><p className="text-xs font-semibold uppercase tracking-[0.17em] text-emerald-700 dark:text-emerald-300">Real searchable-PDF evidence</p><h2 className="mt-2 text-3xl font-semibold tracking-[-0.04em]">Document evaluation workspaces</h2><p className="mt-3 max-w-3xl text-sm leading-7 text-slate-600 dark:text-slate-400">Upload one tender requirements PDF and two or more supplier bids. Files are validated, stored outside source code, text-extracted page by page, and evaluated through LangGraph, Procurement MCP, and local Ollama.</p></div>

      <div className="grid gap-6 xl:grid-cols-[0.72fr_1.28fr]">
        <aside className="space-y-5"><section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-white/8 dark:bg-white/[0.035]"><label htmlFor="workspace-title" className="text-sm font-semibold">New workspace</label><input id="workspace-title" value={title} onChange={(event) => setTitle(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3.5 py-3 text-sm outline-none focus:border-emerald-500 focus:ring-4 focus:ring-emerald-500/10 dark:border-white/10 dark:bg-[#0a211b]" /><button type="button" onClick={create} disabled={busy !== null || !title.trim()} className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-700 px-4 py-3 text-sm font-semibold text-white disabled:opacity-60 dark:bg-emerald-400 dark:text-emerald-950">{busy === "create" ? <LoaderCircle className="size-4 animate-spin" /> : <Plus className="size-4" />}Create workspace</button></section>
          <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-white/8 dark:bg-white/[0.035]"><h3 className="px-1 text-sm font-semibold">Evaluation history</h3><div className="mt-3 space-y-2">{workspaces.length === 0 ? <p className="px-1 py-4 text-xs leading-5 text-slate-500">No PDF workspaces yet.</p> : workspaces.map((workspace) => <button key={workspace.workspace_id} type="button" onClick={() => { setSelectedId(workspace.workspace_id); setResult(null); }} className={`w-full rounded-xl border p-3 text-left transition ${workspace.workspace_id === selected?.workspace_id ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-400/7" : "border-slate-200 hover:border-slate-300 dark:border-white/8"}`}><p className="truncate text-sm font-semibold">{workspace.title}</p><p className="mt-1 font-mono text-[10px] text-slate-500">{workspace.workspace_id}</p><p className="mt-2 text-[10px] font-semibold text-emerald-700 dark:text-emerald-300">{workspace.status.replaceAll("_", " ")}</p></button>)}</div></section></aside>

        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-white/8 dark:bg-white/[0.035] sm:p-6">{!selected ? <div className="grid min-h-96 place-items-center text-center"><div><Files className="mx-auto size-8 text-slate-400" /><h3 className="mt-4 font-semibold">Create a document workspace</h3><p className="mt-2 text-sm text-slate-500">Your uploaded evidence and extraction preview will appear here.</p></div></div> : <><div className="flex flex-col gap-4 border-b border-slate-100 pb-5 dark:border-white/7 sm:flex-row sm:items-start sm:justify-between"><div><p className="font-mono text-xs text-emerald-700 dark:text-emerald-300">{selected.workspace_id}</p><h3 className="mt-1 text-xl font-semibold">{selected.title}</h3></div><span className="w-fit rounded-full bg-slate-100 px-3 py-1.5 text-xs font-semibold dark:bg-white/7">{selected.status.replaceAll("_", " ")}</span></div>
          <div className="mt-5 grid gap-4 sm:grid-cols-2"><label className={`cursor-pointer rounded-2xl border border-dashed p-5 transition ${tenderUploaded ? "border-emerald-300 bg-emerald-50 dark:border-emerald-300/15 dark:bg-emerald-300/7" : "border-slate-300 hover:border-emerald-400 dark:border-white/15"}`}><input type="file" accept="application/pdf,.pdf" className="sr-only" disabled={Boolean(tenderUploaded) || busy !== null} onChange={(event) => void upload(event.target.files, "TENDER_REQUIREMENTS")} /><FilePlus2 className="size-5 text-emerald-700 dark:text-emerald-300" /><p className="mt-3 text-sm font-semibold">Tender requirements PDF</p><p className="mt-1 text-xs text-slate-500">{tenderUploaded ? "Uploaded and text extracted" : "One searchable PDF, maximum 10 MB"}</p></label><label className="cursor-pointer rounded-2xl border border-dashed border-slate-300 p-5 transition hover:border-emerald-400 dark:border-white/15"><input type="file" accept="application/pdf,.pdf" multiple className="sr-only" disabled={busy !== null} onChange={(event) => void upload(event.target.files, "SUPPLIER_BID")} /><Upload className="size-5 text-emerald-700 dark:text-emerald-300" /><p className="mt-3 text-sm font-semibold">Supplier bid PDFs</p><p className="mt-1 text-xs text-slate-500">{bidCount} uploaded · at least two required</p></label></div>
          {busy && busy !== "evaluate" && busy !== "result" && <p className="mt-4 flex items-center gap-2 text-xs text-slate-500"><LoaderCircle className="size-3.5 animate-spin" />Validating PDF structure and extracting searchable page text…</p>}
          <div className="mt-6 space-y-3">{selected.documents.map((document) => <details key={document.document_id} className="rounded-xl border border-slate-200 p-4 dark:border-white/8"><summary className="cursor-pointer list-none"><div className="flex items-start justify-between gap-3"><div className="flex min-w-0 gap-3"><span className="grid size-9 shrink-0 place-items-center rounded-lg bg-slate-100 text-slate-500 dark:bg-white/7"><FileSearch className="size-4" /></span><div className="min-w-0"><p className="truncate text-sm font-semibold">{document.filename}</p><p className="mt-1 text-xs text-slate-500">{document.document_type.replaceAll("_", " ")} · {document.page_count} page{document.page_count === 1 ? "" : "s"} · {Math.ceil(document.size_bytes / 1024)} KB</p></div></div><span className="shrink-0 text-[10px] font-semibold text-emerald-700 dark:text-emerald-300">TEXT EXTRACTED</span></div></summary><pre className="mt-4 max-h-56 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 font-mono text-[10px] leading-5 text-slate-600 dark:bg-black/15 dark:text-slate-400">{document.extracted_preview || "Preview unavailable."}</pre></details>)}</div>
          {message && <p className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800 dark:border-emerald-300/12 dark:bg-emerald-300/7 dark:text-emerald-100">{message}</p>}{error && <p role="alert" className="mt-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-400/15 dark:bg-red-400/8 dark:text-red-200">{error}</p>}
          <button type="button" onClick={selected.status === "AWAITING_HUMAN_REVIEW" && !result ? loadResult : evaluate} disabled={busy !== null || selected.status === "DOCUMENTS_PENDING"} className="mt-6 flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-700 px-5 py-3.5 text-sm font-semibold text-white shadow-lg disabled:cursor-not-allowed disabled:opacity-60 dark:bg-emerald-400 dark:text-emerald-950">{busy === "evaluate" || busy === "result" ? <><LoaderCircle className="size-4 animate-spin" />Running real local workflow…</> : <><ScanSearch className="size-4" />{selected.status === "AWAITING_HUMAN_REVIEW" && !result ? "Load completed result" : "Evaluate supplier PDFs"}</>}</button>{busy === "evaluate" && <p className="mt-3 text-xs leading-5 text-slate-500">Actual stages: open-model planning, Procurement MCP page-cited checks, supplier comparison, and Ollama synthesis. Intermediate stages are not streamed, so no fabricated percentage is shown.</p>}</>}</section>
      </div>
      {result && <DocumentResults result={result} />}
    </div>
  );
}
