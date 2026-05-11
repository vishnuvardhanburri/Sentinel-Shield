import { sovereignTokens } from "@sovereign-shield/design-system";

const cards = [
  "Risk heatmap",
  "Quarantine review",
  "Ledger verification",
  "Evidence export",
  "mTLS certificate center",
  "Emergency controls"
];

export default function Page() {
  return (
    <main className="shell">
      <p className="badge">Xavira Tech Labs | Web Console</p>
      <h1>Sovereign Shield operator console</h1>
      <p className="lede">
        The web dashboard remains the primary control plane. It consumes the centralized FastAPI backend
        through the shared TypeScript SDK; all security enforcement stays server-side.
      </p>
      <section className="grid">
        {cards.map((card) => (
          <article className="panel" key={card}>
            <span style={{ color: sovereignTokens.color.accent }}>Backend-first</span>
            <h2>{card}</h2>
            <p>No business logic is duplicated in the client.</p>
          </article>
        ))}
      </section>
    </main>
  );
}
