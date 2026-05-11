export const mobileNetworkSecurity = {
  certificatePinning: "required-for-production-native-builds",
  directOllamaAccess: "forbidden",
  allowedHostsSource: "buyer-mdm-or-release-config",
  tlsMinimum: "TLSv1.2",
  notes: [
    "React Native clients call only the Sovereign Shield FastAPI gateway.",
    "Production mobile builds must pin the buyer gateway certificate or public key.",
    "No LLM provider key, database credential, or signing secret is embedded in the app."
  ]
} as const;
