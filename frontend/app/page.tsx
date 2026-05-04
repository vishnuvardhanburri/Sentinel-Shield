import Link from "next/link";
import { ArrowRight, FileCheck2, LockKeyhole, ShieldCheck, TerminalSquare } from "lucide-react";

export const metadata = {
  title: "Sovereign Shield | Enterprise AI Security Gateway",
  description:
    "Sovereign Shield by Xavira Tech Labs. Private LLM protection, PII redaction, audit evidence, and local-first AI governance.",
};

const proofSteps = [
  "Intercepts prompts before they reach any model.",
  "Masks PII and sensitive context with stable pseudonyms.",
  "Routes high-sensitivity requests to local models first.",
  "Writes tamper-evident audit evidence for review.",
];

const commandCards = [
  { label: "Launch stack", command: "pnpm launch" },
  { label: "Demo narrative", command: "pnpm demo:narrative" },
  { label: "Buyer verification", command: "pnpm submit:ready" },
  { label: "Data room", command: "pnpm generate:data-room" },
];

export default function Home() {
  return (
    <main className="min-h-screen bg-[#030303] text-white">
      <section className="mx-auto flex max-w-6xl flex-col gap-12 px-6 py-16">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-4 py-2 text-sm font-semibold text-emerald-300">
            <ShieldCheck size={16} />
            Sovereign Shield by Xavira Tech Labs
          </div>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/demo"
              className="rounded-xl border border-white/10 px-4 py-2 text-sm font-bold text-slate-300 hover:bg-white/5"
            >
              Buyer Demo
            </Link>
            <Link
              href="/pricing"
              className="rounded-xl bg-emerald-400 px-4 py-2 text-sm font-black text-black hover:bg-emerald-300"
            >
              Pricing <ArrowRight className="ml-1 inline" size={14} />
            </Link>
          </div>
        </div>

        <div className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr]">
          <div>
            <p className="mb-4 text-sm font-semibold uppercase tracking-[0.22em] text-emerald-300">
              Enterprise AI Security Gateway
            </p>
            <h1 className="max-w-4xl text-4xl font-black tracking-tight md:text-6xl">
              Protect private LLM deployments with local-first governance, redaction, and audit evidence.
            </h1>
            <p className="mt-6 max-w-3xl text-lg leading-8 text-slate-300">
              Sovereign Shield is designed for AI teams and CISOs who need to block sensitive data leakage,
              preserve data residency, and prove internal AI controls without depending on third-party LLM keys.
            </p>
          </div>

          <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-6">
            <div className="flex items-center gap-3">
              <LockKeyhole className="text-emerald-300" size={24} />
              <h2 className="text-xl font-black">Buyer Framing</h2>
            </div>
            <dl className="mt-6 space-y-4 text-sm">
              <div>
                <dt className="text-slate-500">Positioning</dt>
                <dd className="text-slate-200">Private LLM protection, PII control, audit evidence, and compliance workflow in one stack.</dd>
              </div>
              <div>
                <dt className="text-slate-500">Acquisition story</dt>
                <dd className="text-slate-200">A buyer inherits a working foundation instead of building 6-12 months of AI security infrastructure from scratch.</dd>
              </div>
              <div>
                <dt className="text-slate-500">Proof discipline</dt>
                <dd className="text-slate-200">Synthetic demo data only. No fake customers. No fake revenue. No inflated traction claims.</dd>
              </div>
            </dl>
          </div>
        </div>

        <div className="grid gap-5 lg:grid-cols-2">
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">
            <div className="mb-5 flex items-center gap-3">
              <FileCheck2 className="text-emerald-300" size={22} />
              <h2 className="text-xl font-black">Protection Flow</h2>
            </div>
            <ul className="space-y-4">
              {proofSteps.map((step) => (
                <li key={step} className="flex gap-3 text-sm leading-7 text-slate-300">
                  <span className="mt-2 h-2 w-2 rounded-full bg-emerald-300" />
                  <span>{step}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">
            <div className="mb-5 flex items-center gap-3">
              <TerminalSquare className="text-emerald-300" size={22} />
              <h2 className="text-xl font-black">Recording Commands</h2>
            </div>
            <div className="space-y-3">
              {commandCards.map((card) => (
                <div key={card.command} className="rounded-xl bg-white/[0.04] p-4">
                  <p className="mb-2 text-xs font-bold uppercase tracking-[0.16em] text-slate-500">{card.label}</p>
                  <code className="text-sm font-semibold text-emerald-300">{card.command}</code>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
