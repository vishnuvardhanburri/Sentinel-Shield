export const sovereignTokens = {
  color: {
    background: "#090b10",
    surface: "#101620",
    surfaceRaised: "#141d2a",
    border: "#243044",
    text: "#f8fafc",
    muted: "#9fb1c7",
    success: "#26d07c",
    warning: "#ffb84d",
    danger: "#ff5c70",
    accent: "#8bd4ff"
  },
  radius: {
    sm: 4,
    md: 8,
    lg: 12
  },
  spacing: {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32
  },
  typography: {
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
    monoFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"
  }
} as const;

export type SovereignTokens = typeof sovereignTokens;
