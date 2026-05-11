#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::Serialize;

#[derive(Serialize)]
struct DesktopSecurityPosture {
    ipc_boundary: &'static str,
    secrets_policy: &'static str,
    evidence_export: &'static str,
    local_cache: &'static str,
}

#[tauri::command]
fn desktop_security_posture() -> DesktopSecurityPosture {
    DesktopSecurityPosture {
        ipc_boundary: "deny-by-default commands; no arbitrary shell execution exposed",
        secrets_policy: "no API keys or LLM provider secrets are stored in the desktop client",
        evidence_export: "exports must be produced by the FastAPI backend and downloaded with RBAC",
        local_cache: "non-sensitive UI state only; auth tokens stay in memory unless buyer enables OS keychain storage",
    }
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .invoke_handler(tauri::generate_handler![desktop_security_posture])
        .run(tauri::generate_context!())
        .expect("failed to run Sovereign Shield desktop console");
}
