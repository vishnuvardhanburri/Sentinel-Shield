import Dashboard from '../components/Dashboard';

export const metadata = {
  title: 'Sovereign Shield v2 | Enterprise AI Security Gateway',
  description: 'HIPAA · DPDP 2026 · GDPR compliant AI governance platform with real-time PII redaction, immutable audit ledger, and department-level policy enforcement.',
};

export default function Home() {
  return (
    <main>
      <Dashboard />
    </main>
  );
}
