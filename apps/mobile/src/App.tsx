import { sovereignTokens } from "@sovereign-shield/design-system";
import { SovereignShieldClient } from "@sovereign-shield/sdk";
import { SafeAreaView, ScrollView, StyleSheet, Text, View } from "react-native";
import { mobileNetworkSecurity } from "./networkSecurity";
import { SecureStoreStorage } from "./secureStorage";

const client = new SovereignShieldClient({
  baseUrl: "https://gateway.internal.example",
  storage: new SecureStoreStorage(),
  device: {
    deviceId: "mobile-development",
    platform: "ios",
    appVersion: "0.1.0",
    deviceName: "Sovereign Mobile Console"
  }
});

const cards = [
  "Executive security dashboard",
  "Push alerts for high-risk prompts",
  "Quarantine approvals",
  "Incident summaries",
  "Compliance report preview",
  "Read-only audit trail"
];

export default function App() {
  void client;
  void mobileNetworkSecurity;
  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.shell}>
        <Text style={styles.badge}>Xavira Tech Labs | Mobile Console</Text>
        <Text style={styles.title}>Sovereign Shield Mobile</Text>
        <Text style={styles.lede}>
          Executive and incident-response console for Android and iOS. Enforcement remains centralized in the FastAPI backend.
        </Text>
        <View style={styles.grid}>
          {cards.map((card) => (
            <View style={styles.panel} key={card}>
              <Text style={styles.panelTitle}>{card}</Text>
              <Text style={styles.panelText}>Read-only by default, approval actions require server authorization.</Text>
            </View>
          ))}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: sovereignTokens.color.background
  },
  shell: {
    padding: 20,
    gap: 16
  },
  badge: {
    color: sovereignTokens.color.muted,
    borderColor: sovereignTokens.color.border,
    borderWidth: 1,
    borderRadius: 20,
    paddingVertical: 8,
    paddingHorizontal: 12,
    alignSelf: "flex-start"
  },
  title: {
    color: sovereignTokens.color.text,
    fontSize: 42,
    fontWeight: "700"
  },
  lede: {
    color: "#bfccda",
    fontSize: 17,
    lineHeight: 25
  },
  grid: {
    gap: 12
  },
  panel: {
    backgroundColor: sovereignTokens.color.surface,
    borderColor: sovereignTokens.color.border,
    borderWidth: 1,
    borderRadius: 8,
    padding: 16
  },
  panelTitle: {
    color: sovereignTokens.color.text,
    fontSize: 18,
    fontWeight: "700"
  },
  panelText: {
    color: sovereignTokens.color.muted,
    marginTop: 6
  }
});
