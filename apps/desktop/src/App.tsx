import { MemoryStorage, SovereignShieldClient } from "@sovereign-shield/sdk";
import { formatRiskScore, sovereignTokens } from "@sovereign-shield/design-system";

const client = new SovereignShieldClient({
  baseUrl: import.meta.env.VITE_SOVEREIGN_API_URL ?? "https://gateway.internal.example",
  storage: new MemoryStorage(),
  device: {
    deviceId: "desktop-development",
    platform: "macos",
    appVersion: "0.1.0",
    deviceName: "Sovereign Desktop Console"
  }
});

const modules = [
  "Native CISO notifications",
  "Quarantine review center",
  "Risk heatmaps",
  "Ledger verification viewer",
  "Secure evidence export",
  "mTLS certificate management"
];

export function App() {
  void client;
  return (
    <main className="shell">
      <p className="badge">Desktop Operator Console</p>
      <h1>Sovereign Shield Desktop</h1>
      <p className="lede">
        Tauri shell for macOS, Windows, and Linux. It consumes the centralized FastAPI API and stores
        only non-sensitive UI state locally.
      </p>
      <section className="grid">
        {modules.map((module) => (
          <article className="panel" key={module}>
            <span style={{ color: sovereignTokens.color.accent }}>{formatRiskScore(0)}</span>
            <h2>{module}</h2>
            <p>Security decisions remain enforced by the backend.</p>
          </article>
        ))}
      </section>
    </main>
  );
}
