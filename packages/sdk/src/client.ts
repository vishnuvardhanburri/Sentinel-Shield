import { SESSION_STORAGE_KEYS } from "./storage";
import type {
  AuditEntry,
  ControlRoomSnapshot,
  DeviceSession,
  DeviceContext,
  EvidenceReportResponse,
  LoginResponse,
  RiskHeatmap,
  SDKStorage,
  TokenSet
} from "./types";

export interface SovereignClientOptions {
  baseUrl: string;
  storage: SDKStorage;
  device: DeviceContext;
  fetchImpl?: typeof fetch;
}

export class SovereignShieldClient {
  private readonly baseUrl: string;
  private readonly storage: SDKStorage;
  private readonly device: DeviceContext;
  private readonly fetchImpl: typeof fetch;

  constructor(options: SovereignClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/$/, "");
    this.storage = options.storage;
    this.device = options.device;
    this.fetchImpl = options.fetchImpl ?? fetch;
  }

  async login(email: string, password: string): Promise<LoginResponse> {
    const response = await this.request<LoginResponse>("/api/v2/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password, device: this.serverDeviceContext() }),
      skipAuth: true
    });
    await this.persistTokens(response.tokens);
    return response;
  }

  async logout(): Promise<void> {
    await this.request("/api/v2/auth/logout", { method: "POST" });
    await this.clearTokens();
  }

  async refreshSession(): Promise<TokenSet> {
    const refreshToken = await this.storage.get(SESSION_STORAGE_KEYS.refreshToken);
    if (!refreshToken) throw new Error("No refresh token is available");
    const response = await this.request<LoginResponse>("/api/v2/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken, device: this.serverDeviceContext() }),
      skipAuth: true
    });
    await this.persistTokens(response.tokens);
    return response.tokens;
  }

  async riskHeatmap(): Promise<RiskHeatmap> {
    return this.request<RiskHeatmap>("/api/v2/risk/heatmap");
  }

  async controlRoom(): Promise<ControlRoomSnapshot> {
    return this.request<ControlRoomSnapshot>("/api/v2/enterprise/control-room");
  }

  async auditTrail(): Promise<AuditEntry[]> {
    const response = await this.request<{ entries?: AuditEntry[] }>("/audit/log");
    return response.entries ?? [];
  }

  async generateEvidenceReport(): Promise<EvidenceReportResponse> {
    return this.request<EvidenceReportResponse>("/api/v2/audit/report", {
      method: "POST",
      body: JSON.stringify({})
    });
  }

  async quarantineAction(actorHash: string, action: "release" | "extend" | "deny"): Promise<unknown> {
    return this.request("/api/v2/enterprise/quarantine/action", {
      method: "POST",
      body: JSON.stringify({ actor_hash: actorHash, action })
    });
  }

  async deviceSessions(): Promise<DeviceSession[]> {
    const response = await this.request<{ sessions?: DeviceSession[] }>("/api/v2/devices/sessions");
    return response.sessions ?? [];
  }

  async revokeDeviceSession(sessionId: string): Promise<unknown> {
    return this.request("/api/v2/devices/sessions/revoke", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId })
    });
  }

  async emergencyKillSwitch(reason: string): Promise<unknown> {
    return this.request("/api/v2/enterprise/kill-switch", {
      method: "POST",
      body: JSON.stringify({ reason, device: this.device })
    });
  }

  private async persistTokens(tokens: TokenSet): Promise<void> {
    await this.storage.set(SESSION_STORAGE_KEYS.accessToken, tokens.accessToken);
    if (tokens.refreshToken) {
      await this.storage.set(SESSION_STORAGE_KEYS.refreshToken, tokens.refreshToken);
    }
  }

  private async clearTokens(): Promise<void> {
    await this.storage.delete(SESSION_STORAGE_KEYS.accessToken);
    await this.storage.delete(SESSION_STORAGE_KEYS.refreshToken);
  }

  private serverDeviceContext() {
    return {
      device_id: this.device.deviceId,
      platform: this.device.platform,
      app_version: this.device.appVersion,
      device_name: this.device.deviceName
    };
  }

  private async request<T = unknown>(
    path: string,
    init: RequestInit & { skipAuth?: boolean } = {}
  ): Promise<T> {
    const headers = new Headers(init.headers);
    headers.set("Content-Type", "application/json");
    headers.set("X-Sovereign-Device", JSON.stringify(this.device));

    if (!init.skipAuth) {
      const token = await this.storage.get(SESSION_STORAGE_KEYS.accessToken);
      if (token) headers.set("Authorization", `Bearer ${token}`);
    }

    const response = await this.fetchImpl(`${this.baseUrl}${path}`, {
      ...init,
      headers
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Sovereign Shield API ${response.status}: ${text}`);
    }

    if (response.status === 204) return undefined as T;
    return response.json() as Promise<T>;
  }
}
