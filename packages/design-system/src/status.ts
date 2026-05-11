export type RiskTone = "success" | "warning" | "danger" | "neutral";

export function riskTone(score: number): RiskTone {
  if (score >= 8) return "danger";
  if (score >= 5) return "warning";
  if (score > 0) return "success";
  return "neutral";
}

export function formatRiskScore(score: number): string {
  return `${Math.round(score * 10) / 10}/10`;
}
