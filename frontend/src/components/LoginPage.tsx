import { ArrowRight, KeyRound, LockKeyhole, ShieldCheck, Sparkles } from "lucide-react";
import { useState, type FormEvent } from "react";

interface LoginPageProps {
  onLogin: (password: string) => Promise<void>;
}

export function LoginPage({ onLogin }: LoginPageProps) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await onLogin(password);
      setPassword("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Sign-in failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#061713] text-slate-100">
      <div className="grid min-h-screen lg:grid-cols-[1.08fr_0.92fr]">
        <section className="relative hidden overflow-hidden border-r border-white/8 px-14 py-12 lg:flex lg:flex-col lg:justify-between xl:px-20">
          <div className="pointer-events-none absolute -left-32 top-1/3 size-[34rem] rounded-full bg-emerald-400/10 blur-3xl" />
          <div className="pointer-events-none absolute right-0 top-0 h-full w-3/5 opacity-25 [background-image:linear-gradient(rgba(52,211,153,.12)_1px,transparent_1px),linear-gradient(90deg,rgba(52,211,153,.12)_1px,transparent_1px)] [background-size:42px_42px]" />

          <div className="relative">
            <div className="flex items-center gap-3">
              <span className="grid size-11 place-items-center rounded-xl bg-emerald-400 text-emerald-950">
                <ShieldCheck className="size-6" aria-hidden="true" />
              </span>
              <div>
                <p className="font-semibold tracking-tight">TenderGuard Africa</p>
                <p className="text-xs uppercase tracking-[0.18em] text-emerald-200/60">
                  Decision support, not decision replacement
                </p>
              </div>
            </div>
          </div>

          <div className="relative max-w-2xl pb-10">
            <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-emerald-300/15 bg-emerald-300/8 px-3 py-1.5 text-xs font-medium text-emerald-200">
              <Sparkles className="size-3.5" aria-hidden="true" />
              Local open-weights AI · Human-governed outcomes
            </div>
            <h1 className="max-w-xl text-5xl font-semibold leading-[1.04] tracking-[-0.045em] text-white xl:text-6xl">
              Evidence-first tender evaluation, built for accountability.
            </h1>
            <p className="mt-7 max-w-xl text-lg leading-8 text-slate-300/80">
              Review compliance, price context, and supplier-data inconsistencies through
              a traceable LangGraph and MCP workflow running on your machine.
            </p>
          </div>

          <p className="relative max-w-lg border-l-2 border-emerald-400/50 pl-4 text-sm leading-6 text-slate-400">
            TenderGuard prepares the evaluation file. The authorised human procurement
            committee makes the final decision.
          </p>
        </section>

        <section className="flex items-center justify-center bg-slate-50 px-5 py-12 text-slate-900 dark:bg-[#081c17] dark:text-slate-100 sm:px-10">
          <div className="w-full max-w-md">
            <div className="mb-10 flex items-center gap-3 lg:hidden">
              <span className="grid size-10 place-items-center rounded-xl bg-emerald-500 text-white">
                <ShieldCheck className="size-5" aria-hidden="true" />
              </span>
              <strong>TenderGuard Africa</strong>
            </div>

            <div className="mb-8">
              <div className="mb-5 grid size-12 place-items-center rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-white/10 dark:bg-white/5">
                <LockKeyhole className="size-5 text-emerald-600 dark:text-emerald-300" aria-hidden="true" />
              </div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700 dark:text-emerald-300">
                Local dashboard access
              </p>
              <h2 className="mt-2 text-3xl font-semibold tracking-[-0.035em]">Welcome back</h2>
              <p className="mt-3 leading-7 text-slate-600 dark:text-slate-400">
                Sign in with the local dashboard password configured on this server.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label htmlFor="dashboard-password" className="mb-2 block text-sm font-medium">
                  Dashboard password
                </label>
                <div className="relative">
                  <KeyRound className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
                  <input
                    id="dashboard-password"
                    type="password"
                    autoComplete="current-password"
                    required
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    className="w-full rounded-xl border border-slate-300 bg-white py-3.5 pl-10 pr-4 text-sm outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-500/10 dark:border-white/12 dark:bg-white/5 dark:focus:border-emerald-400"
                    placeholder="Enter your local password"
                  />
                </div>
              </div>

              {error && (
                <div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-400/20 dark:bg-red-400/10 dark:text-red-200">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={submitting}
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-700 px-5 py-3.5 text-sm font-semibold text-white shadow-lg shadow-emerald-900/15 transition hover:bg-emerald-800 focus:outline-none focus:ring-4 focus:ring-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-emerald-500 dark:text-emerald-950 dark:hover:bg-emerald-400"
              >
                {submitting ? "Verifying locally…" : "Open dashboard"}
                {!submitting && <ArrowRight className="size-4" aria-hidden="true" />}
              </button>
            </form>

            <div className="mt-8 rounded-xl border border-amber-200/80 bg-amber-50 px-4 py-3 text-xs leading-5 text-amber-900 dark:border-amber-300/15 dark:bg-amber-300/8 dark:text-amber-100/80">
              <strong className="font-semibold">Synthetic demonstration data.</strong> This
              local access mechanism is not production identity or role-based authorization.
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
