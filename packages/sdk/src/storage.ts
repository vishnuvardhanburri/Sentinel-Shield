import type { SDKStorage } from "./types";

export class MemoryStorage implements SDKStorage {
  private readonly values = new Map<string, string>();

  async get(key: string): Promise<string | null> {
    return this.values.get(key) ?? null;
  }

  async set(key: string, value: string): Promise<void> {
    this.values.set(key, value);
  }

  async delete(key: string): Promise<void> {
    this.values.delete(key);
  }
}

export const SESSION_STORAGE_KEYS = {
  accessToken: "sovereign.accessToken",
  refreshToken: "sovereign.refreshToken",
  deviceId: "sovereign.deviceId"
} as const;
