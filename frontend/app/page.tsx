import Dashboard from '../components/Dashboard';

export const metadata = {
  title: 'Sentinel Vault Version 1 | Enterprise Security AI',
  description: 'Air-gapped security monitoring and document intelligence.',
};

export default function Home() {
  return (
    <main>
      <Dashboard />
    </main>
  );
}
