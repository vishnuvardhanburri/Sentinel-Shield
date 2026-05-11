import type { DeviceContext } from "./types";

export interface ClientAuditEvent {
  event: string;
  device: DeviceContext;
  metadata?: Record<string, unknown>;
  createdAt: string;
}

export function createClientAuditEvent(
  event: string,
  device: DeviceContext,
  metadata: Record<string, unknown> = {}
): ClientAuditEvent {
  return {
    event,
    device,
    metadata,
    createdAt: new Date().toISOString()
  };
}
