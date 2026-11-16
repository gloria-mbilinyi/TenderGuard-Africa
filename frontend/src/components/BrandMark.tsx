import { ShieldCheck } from "lucide-react";

export function BrandMark({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-emerald-400 text-emerald-950 shadow-lg shadow-emerald-950/20">
        <ShieldCheck aria-hidden="true" className="size-5" strokeWidth={2.2} />
      </span>
      {!compact && (
        <span>
          <strong className="block text-[15px] font-semibold tracking-tight text-white">
            TenderGuard Africa
          </strong>
          <span className="block text-[11px] font-medium uppercase tracking-[0.16em] text-emerald-200/65">
            Procurement intelligence
          </span>
        </span>
      )}
    </div>
  );
}
