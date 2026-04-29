//! Hcode Desktop — Tauri Main Process
//!
//! Responsibilities:
//! - Window lifecycle & single-instance lock
//! - Daemon process supervisor (spawn/restart hcode-daemon)
//! - IPC commands exposed to the React frontend
//! - Secure credential storage via Windows Credential Manager

mod daemon;

use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::sync::Mutex;
use tauri::{AppHandle, State};

// ── State ────────────────────────────────────────────────────────────────────

struct AppState {
    daemon: Mutex<daemon::DaemonSupervisor>,
    work_dir: Mutex<Option<String>>,
}

// ── Types ────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DaemonInfo {
    pub status: String,
    pub uptime: Option<u64>,
    pub pid: Option<u32>,
    pub version: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileEntry {
    pub name: String,
    pub path: String,
    #[serde(rename = "isDirectory")]
    pub is_directory: bool,
    pub children: Option<Vec<FileEntry>>,
}

// ── Daemon Commands ──────────────────────────────────────────────────────────

#[tauri::command]
async fn start_daemon(state: State<'_, AppState>, app: AppHandle) -> Result<DaemonInfo, String> {
    let mut supervisor = state.daemon.lock().map_err(|e| e.to_string())?;
    supervisor.start(&app).map_err(|e| e.to_string())?;
    Ok(DaemonInfo {
        status: "running".to_string(),
        uptime: Some(0),
        pid: supervisor.pid(),
        version: None,
    })
}

#[tauri::command]
async fn stop_daemon(state: State<'_, AppState>) -> Result<(), String> {
    let mut supervisor = state.daemon.lock().map_err(|e| e.to_string())?;
    supervisor.stop().map_err(|e| e.to_string())
}

#[tauri::command]
async fn daemon_health(state: State<'_, AppState>) -> Result<DaemonInfo, String> {
    let supervisor = state.daemon.lock().map_err(|e| e.to_string())?;
    Ok(DaemonInfo {
        status: supervisor.status().to_string(),
        uptime: supervisor.uptime(),
        pid: supervisor.pid(),
        version: None,
    })
}

// ── Task Commands ────────────────────────────────────────────────────────────

#[tauri::command]
async fn run_task(
    task: String,
    mode: String,
    autonomous: bool,
    state: State<'_, AppState>,
) -> Result<(), String> {
    let mut supervisor = state.daemon.lock().map_err(|e| e.to_string())?;
    let msg = serde_json::json!({
        "jsonrpc": "2.0",
        "id": uuid_v4(),
        "method": "run_task",
        "params": { "task": task, "mode": mode, "autonomous": autonomous }
    });
    supervisor.send(&msg.to_string()).map_err(|e| e.to_string())
}

#[tauri::command]
async fn abort_task(state: State<'_, AppState>) -> Result<(), String> {
    let mut supervisor = state.daemon.lock().map_err(|e| e.to_string())?;
    let msg = serde_json::json!({ "jsonrpc": "2.0", "id": uuid_v4(), "method": "abort" });
    supervisor.send(&msg.to_string()).map_err(|e| e.to_string())
}

#[tauri::command]
async fn approve_plan(state: State<'_, AppState>) -> Result<(), String> {
    let mut supervisor = state.daemon.lock().map_err(|e| e.to_string())?;
    let msg = serde_json::json!({ "jsonrpc": "2.0", "id": uuid_v4(), "method": "approve_plan" });
    supervisor.send(&msg.to_string()).map_err(|e| e.to_string())
}

#[tauri::command]
async fn reject_plan(feedback: String, state: State<'_, AppState>) -> Result<(), String> {
    let mut supervisor = state.daemon.lock().map_err(|e| e.to_string())?;
    let msg = serde_json::json!({
        "jsonrpc": "2.0", "id": uuid_v4(), "method": "reject_plan",
        "params": { "feedback": feedback }
    });
    supervisor.send(&msg.to_string()).map_err(|e| e.to_string())
}

#[tauri::command]
async fn accept_patch(path: String, state: State<'_, AppState>) -> Result<(), String> {
    let mut supervisor = state.daemon.lock().map_err(|e| e.to_string())?;
    let msg = serde_json::json!({
        "jsonrpc": "2.0", "id": uuid_v4(), "method": "accept_patch",
        "params": { "path": path }
    });
    supervisor.send(&msg.to_string()).map_err(|e| e.to_string())
}

#[tauri::command]
async fn reject_patch(path: String, state: State<'_, AppState>) -> Result<(), String> {
    let mut supervisor = state.daemon.lock().map_err(|e| e.to_string())?;
    let msg = serde_json::json!({
        "jsonrpc": "2.0", "id": uuid_v4(), "method": "reject_patch",
        "params": { "path": path }
    });
    supervisor.send(&msg.to_string()).map_err(|e| e.to_string())
}

#[tauri::command]
async fn rollback_all(state: State<'_, AppState>) -> Result<(), String> {
    let mut supervisor = state.daemon.lock().map_err(|e| e.to_string())?;
    let msg = serde_json::json!({ "jsonrpc": "2.0", "id": uuid_v4(), "method": "rollback_all" });
    supervisor.send(&msg.to_string()).map_err(|e| e.to_string())
}

// ── File System Commands ─────────────────────────────────────────────────────

#[tauri::command]
async fn open_folder_dialog(app: AppHandle) -> Result<Option<String>, String> {
    use tauri_plugin_dialog::DialogExt;

    let (sender, receiver) = std::sync::mpsc::channel();

    app.dialog()
        .file()
        .set_title("Open Folder")
        .pick_folder(move |folder_path| {
            let result = folder_path.map(|p| p.to_string());
            let _ = sender.send(result);
        });

    // Wait for the dialog result
    let result = receiver.recv().map_err(|e| format!("Dialog error: {}", e))?;
    Ok(result)
}

#[tauri::command]
async fn list_directory(path: String) -> Result<Vec<FileEntry>, String> {
    let dir = PathBuf::from(&path);
    if !dir.is_dir() {
        return Err(format!("Not a directory: {}", path));
    }

    let mut entries = Vec::new();
    let read_dir = std::fs::read_dir(&dir).map_err(|e| e.to_string())?;

    for entry in read_dir {
        let entry = entry.map_err(|e| e.to_string())?;
        let name = entry.file_name().to_string_lossy().to_string();

        // Skip hidden and common ignore patterns
        if name.starts_with('.') || name == "node_modules" || name == "__pycache__" || name == "target" {
            continue;
        }

        let metadata = entry.metadata().map_err(|e| e.to_string())?;
        entries.push(FileEntry {
            name,
            path: entry.path().to_string_lossy().to_string(),
            is_directory: metadata.is_dir(),
            children: None,
        });
    }

    // Sort: directories first, then alphabetical
    entries.sort_by(|a, b| {
        b.is_directory.cmp(&a.is_directory).then(a.name.to_lowercase().cmp(&b.name.to_lowercase()))
    });

    Ok(entries)
}

#[tauri::command]
async fn read_file(path: String) -> Result<String, String> {
    std::fs::read_to_string(&path).map_err(|e| format!("Failed to read {}: {}", path, e))
}

#[tauri::command]
async fn write_file(path: String, content: String) -> Result<(), String> {
    std::fs::write(&path, &content).map_err(|e| format!("Failed to write {}: {}", path, e))
}

// ── Secure Storage ───────────────────────────────────────────────────────────

#[tauri::command]
async fn save_api_key(provider: String, key: String) -> Result<(), String> {
    let entry = keyring::Entry::new("hcode-desktop", &provider).map_err(|e| e.to_string())?;
    entry.set_password(&key).map_err(|e| e.to_string())
}

#[tauri::command]
async fn get_api_key(provider: String) -> Result<Option<String>, String> {
    let entry = keyring::Entry::new("hcode-desktop", &provider).map_err(|e| e.to_string())?;
    match entry.get_password() {
        Ok(key) => Ok(Some(key)),
        Err(keyring::Error::NoEntry) => Ok(None),
        Err(e) => Err(e.to_string()),
    }
}

// ── Helpers ──────────────────────────────────────────────────────────────────

fn uuid_v4() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let t = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos();
    format!("{:x}", t)
}

// ── Main ─────────────────────────────────────────────────────────────────────

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_shell::init())
        .manage(AppState {
            daemon: Mutex::new(daemon::DaemonSupervisor::new()),
            work_dir: Mutex::new(None),
        })
        .invoke_handler(tauri::generate_handler![
            start_daemon,
            stop_daemon,
            daemon_health,
            run_task,
            abort_task,
            approve_plan,
            reject_plan,
            accept_patch,
            reject_patch,
            rollback_all,
            open_folder_dialog,
            list_directory,
            read_file,
            write_file,
            save_api_key,
            get_api_key,
        ])
        .run(tauri::generate_context!())
        .expect("error while running Hcode Desktop");
}
