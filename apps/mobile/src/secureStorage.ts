import * as SecureStore from "expo-secure-store";
import type { SDKStorage } from "@sovereign-shield/sdk";

export class SecureStoreStorage implements SDKStorage {
  async get(key: string): Promise<string | null> {
    return SecureStore.getItemAsync(key);
  }

  async set(key: string, value: string): Promise<void> {
    await SecureStore.setItemAsync(key, value, {
      keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY
    });
  }

  async delete(key: string): Promise<void> {
    await SecureStore.deleteItemAsync(key);
  }
}
