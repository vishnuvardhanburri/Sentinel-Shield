import Link from 'next/link';
import { ArrowRight, CheckCircle2, FileText, ShieldCheck, Terminal, WalletCards } from 'lucide-react';

const proofCards = [
  {
    title: 'Product Proof',
    value: 'Private LLM Gateway',
    body: 'PII masking, prompt defense, semantic DLP, local routing, audit ledger, and risk scoring in one deployable control plane.',
  },
  {
    title: 'Buyer Verification',
    value: '100/100 Ready Check',
    body: 'Run the end-to-end verifier to test backend compile, dashboard lint/build, API smoke, evidence PDF, and handoff ZIP.',
  },
  {
    title: 'Monetization Signal',
    value: '$499/mo to Custom',
    body: 'Starter, Growth, and Enterprise pricing surfaces show a credible subscription path after acquisition.',
  },
];

const commands = [
  ['Launch local system', 'pnpm launch'],
  ['Print video narrative', 'pnpm demo:narrative'],
  ['Run buyer verification', 'pnpm submit:ready'],
  ['Generate data room', 'pnpm generate:data-room'],
];

const demoLinks = [
  ['Synthetic metrics API', 'http://localhost:8000/demo/metrics'],
  ['Narrative API', 'http://localhost:8000/demo/narrative'],
  ['Readiness API', 'http://localhost:8000/demo/acquisition-readiness'],
  ['API docs', 'http://localhost:8000/api/docs'],
];

export const metadata = {
  title: 'Buyer Demo | Sovereign Shield',
  description: 'Acquisition-ready buyer demo page for Sovereign Shield by Xavira Tech Labs.',
};

export default function DemoPage() {
  return (
    <main className="min-h-screen bg-[#030303] text-white">
      <section className="mx-auto max-w-6xl px-6 py-14">
        <div className="mb-10 flex flex-wrap items-center justify-between gap-4">
          <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-4 py-2 text-sm font-semibold text-emerald-300">
            <ShieldCheck size={16} /> Acquisition Demo
          </div>
          <div className="flex gap-3">
            <Link href="/" className="rounded-xl border border-white/10 px-4 py-2 text-sm font-bold text-slate-300 hover:bg-white/5">
              Dashboard
            </Link>
            <Link href="/pricing" className="rounded-xl bg-emerald-400 px-4 py-2 text-sm font-black text-black hover:bg-emerald-300">
              Pricing <ArrowRight className="ml-1 inline" size={14} />
            </Link>
          </div>
        </div>

        <div className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr]">
          <div>
            <p className="mb-4 text-sm font-semibold uppercase tracking-[0.22em] text-emerald-300">
              Sovereign Shield by Xavira Tech Labs
            </p>
            <h1 className="max-w-4xl text-4xl font-black tracking-tight md:text-6xl">
              Enterprise AI security gateway positioned for a $500K single acquisition.
            </h1>
            <p className="mt-6 max-w-3xl text-lg leading-8 text-slate-300">
              Built for private LLM deployments that need PII protection, local model routing, prompt injection defense,
              and board-ready audit evidence without relying on external LLM API keys.
            </p>
          </div>

          <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-6">
            <div className="flex items-center gap-3">
              <WalletCards className="text-emerald-300" size={24} />
              <h2 className="text-xl font-black">Buyer Positioning</h2>
            </div>
            <dl className="mt-6 space-y-4 text-sm">
              <div>
                <dt className="text-slate-500">Target ask</dt>
                <dd className="text-3xl font-black text-emerald-300">$500K</dd>
              </div>
              <div>
                <dt className="text-slate-500">Replacement-cost story</dt>
                <dd className="text-slate-200">Compresses 6-12 months of AI security, compliance, audit, and dashboard engineering.</dd>
              </div>
              <div>
                <dt className="text-slate-500">Claim discipline</dt>
                <dd className="text-slate-200">No fake customers, no fake revenue, synthetic demo proof clearly labeled.</dd>
              </div>
            </dl>
          </div>
        </div>

        <div className="mt-10 grid gap-4 md:grid-cols-3">
          {proofCards.map((card) => (
            <div key={card.title} className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">{card.title}</p>
              <h2 className="mt-3 text-2xl font-black text-white">{card.value}</h2>
              <p className="mt-3 text-sm leading-6 text-slate-400">{card.body}</p>
            </div>
          ))}
        </div>

        <div className="mt-10 grid gap-5 lg:grid-cols-2">
          <div className="rounded-2xl border border-white/10 bg-[#080808] p-6">
            <div className="mb-5 flex items-center gap-3">
              <Terminal className="text-emerald-300" size={22} />
              <h2 className="text-xl font-black">Video Commands</h2>
            </div>
            <div className="space-y-3">
              {commands.map(([label, command]) => (
                <div key={command} className="rounded-xl bg-white/[0.04] p-4">
                  <p className="mb-2 text-xs font-bold uppercase tracking-[0.16em] text-slate-500">{label}</p>
                  <code className="text-sm font-semibold text-emerald-300">{command}</code>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-[#080808] p-6">
            <div className="mb-5 flex items-center gap-3">
              <FileText className="text-emerald-300" size={22} />
              <h2 className="text-xl font-black">Live Proof Links</h2>
            </div>
            <div className="space-y-3">
              {demoLinks.map(([label, href]) => (
                <a key={href} href={href} className="flex items-center justify-between rounded-xl bg-white/[0.04] p-4 text-sm text-slate-200 hover:bg-white/[0.07]">
                  <span>{label}</span>
                  <ArrowRight className="text-emerald-300" size={16} />
                </a>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-10 rounded-2xl border border-white/10 bg-white/[0.03] p-6">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="mt-1 shrink-0 text-emerald-300" size={20} />
            <p className="text-sm leading-7 text-slate-300">
              This page is a buyer walkthrough surface, not a traction claim. Metrics and events shown by demo endpoints are synthetic
              proof data for diligence. The acquisition value is the working product foundation, security architecture, compliance mapping,
              deployment workflow, and time-to-market advantage.
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}
