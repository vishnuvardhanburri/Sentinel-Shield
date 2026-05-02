import { CheckCircle2, ShieldCheck } from 'lucide-react';

const plans = [
  {
    name: 'Starter',
    price: '$499/mo',
    description: 'For teams piloting private LLM governance.',
    features: ['PII redaction gateway', 'Local LLM routing', 'Audit ledger', 'Basic policy presets'],
  },
  {
    name: 'Growth',
    price: '$999/mo',
    description: 'For regulated teams deploying across departments.',
    features: ['Everything in Starter', 'Risk heatmap', 'Evidence reports', 'API-key integrations', 'Policy bundles'],
    featured: true,
  },
  {
    name: 'Enterprise',
    price: 'Contact Sales',
    description: 'For air-gapped, multi-tenant, and board-level compliance needs.',
    features: ['Everything in Growth', 'mTLS deployment pack', 'Custom compliance mapping', 'Buyer-controlled data residency', 'Priority handoff'],
  },
];

export const metadata = {
  title: 'Pricing | Sovereign Shield',
  description: 'Pricing signal for Sovereign Shield, an enterprise AI security gateway for PII protection, compliance, audit, and local LLM deployments.',
};

export default function PricingPage() {
  return (
    <main className="min-h-screen bg-[#030303] text-white">
      <section className="mx-auto max-w-6xl px-6 py-16">
        <div className="mb-12 max-w-3xl">
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-4 py-2 text-sm font-semibold text-emerald-300">
            <ShieldCheck size={16} /> Enterprise AI Security Gateway
          </div>
          <h1 className="text-4xl font-black tracking-tight md:text-6xl">
            Private LLM protection priced like enterprise compliance infrastructure.
          </h1>
          <p className="mt-5 text-lg leading-8 text-slate-300">
            Sovereign Shield helps regulated teams mask PII, route high-sensitivity prompts to local models,
            and produce audit evidence without sending protected data to external LLM APIs.
          </p>
        </div>
        <div className="grid gap-5 md:grid-cols-3">
          {plans.map((plan) => (
            <div
              key={plan.name}
              className={`rounded-2xl border p-7 ${plan.featured ? 'border-emerald-400 bg-emerald-500/10' : 'border-white/10 bg-white/[0.03]'}`}
            >
              <h2 className="text-2xl font-black">{plan.name}</h2>
              <p className="mt-2 min-h-14 text-sm text-slate-400">{plan.description}</p>
              <div className="mt-7 text-4xl font-black text-emerald-300">{plan.price}</div>
              <ul className="mt-7 space-y-3 text-sm text-slate-200">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex gap-3">
                    <CheckCircle2 className="mt-0.5 shrink-0 text-emerald-400" size={16} />
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <p className="mt-8 text-sm text-slate-500">
          Pricing page is included as a monetization signal for acquisition diligence. Production billing can connect to the license validation API.
        </p>
      </section>
    </main>
  );
}
