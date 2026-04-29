//! Daemon Supervisor — manages the Hcode Python daemon process.
//!
//! Responsibilities:
//! - Spawn hcode-daemon as a child process
//! - Communicate via stdin/stdout JSON-RPC
//! - Monitor health with periodic pings
//! - Restart with exponential backoff on crash

use std::io::{BufRead, BufReader};
use std::process::{Child, Command, Stdio};
use std::time::Instant;
use tauri::{AppHandle, Emitter, Manager};

pub struct DaemonSupervisor {
    process: Option<Child>,
    status: DaemonStatus,
    start_time: Option<Instant>,
    restart_count: u32,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum DaemonStatus {
    Stopped,
    Starting,
    Running,
    Error,
}

impl std::fmt::Display for DaemonStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            DaemonStatus::Stopped => write!(f, "stopped"),
            DaemonStatus::Starting => write!(f, "starting"),
            DaemonStatus::Running => write!(f, "running"),
            DaemonStatus::Error => write!(f, "error"),
        }
    }
}

impl DaemonSupervisor {
    pub fn new() -> Self {
        Self {
            process: None,
            status: DaemonStatus::Stopped,
            start_time: None,
            restart_count: 0,
        }
    }

    /// Start the daemon process
    pub fn start(&mut self, app: &AppHandle) -> Result<(), String> {
        if self.status == DaemonStatus::Running {
            return Ok(());
        }

        self.status = DaemonStatus::Starting;

        // Try to find hcode-daemon executable
        // Priority: 1) bundled with app, 2) in PATH, 3) Python script
        let daemon_path = self.find_daemon_executable(app)?;

        let child = Command::new(&daemon_path)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|e| format!("Failed to start daemon at {}: {}", daemon_path, e))?;

        self.process = Some(child);
        self.status = DaemonStatus::Running;
        self.start_time = Some(Instant::now());
        self.restart_count = 0;

        // Spawn stdout reader thread that emits events to frontend
        self.spawn_output_reader(app.clone());

        Ok(())
    }

    /// Stop the daemon process
    pub fn stop(&mut self) -> Result<(), String> {
        if let Some(ref mut child) = self.process {
            // Try graceful shutdown first
            if let Some(ref mut stdin) = child.stdin {
                let shutdown_msg = serde_json::json!({
                    "jsonrpc": "2.0",
                    "method": "shutdown"
                });
                use std::io::Write;
                let _ = writeln!(stdin, "{}", shutdown_msg);
            }

            // Wait briefly, then kill
            std::thread::sleep(std::time::Duration::from_millis(500));

            let _ = child.kill();
            let _ = child.wait();
        }

        self.process = None;
        self.status = DaemonStatus::Stopped;
        self.start_time = None;

        Ok(())
    }

    /// Send a JSON-RPC message to the daemon via stdin
    pub fn send(&mut self, message: &str) -> Result<(), String> {
        if self.status != DaemonStatus::Running {
            return Err("Daemon is not running".to_string());
        }

        if let Some(ref mut child) = self.process {
            if let Some(ref mut stdin) = child.stdin {
                use std::io::Write;
                writeln!(stdin, "{}", message)
                    .map_err(|e| format!("Failed to write to daemon stdin: {}", e))?;
                stdin.flush()
                    .map_err(|e| format!("Failed to flush daemon stdin: {}", e))?;
                eprintln!("[DaemonSupervisor] Sent: {}", message);
                Ok(())
            } else {
                Err("Daemon stdin not available".to_string())
            }
        } else {
            // No process — log for debugging and succeed silently (mock mode)
            eprintln!("[DaemonSupervisor] Mock send: {}", message);
            Ok(())
        }
    }

    pub fn status(&self) -> &DaemonStatus {
        &self.status
    }

    pub fn pid(&self) -> Option<u32> {
        self.process.as_ref().map(|p| p.id())
    }

    pub fn uptime(&self) -> Option<u64> {
        self.start_time.map(|t| t.elapsed().as_secs())
    }

    // ── Private ──────────────────────────────────────────────────────────────

    fn find_daemon_executable(&self, app: &AppHandle) -> Result<String, String> {
        // 1. Check bundled resource
        if let Ok(resource_dir) = app.path().resource_dir() {
            let bundled = resource_dir.join("hcode-daemon.exe");
            if bundled.exists() {
                return Ok(bundled.to_string_lossy().to_string());
            }
            // Also check without .exe for cross-platform
            let bundled_unix = resource_dir.join("hcode-daemon");
            if bundled_unix.exists() {
                return Ok(bundled_unix.to_string_lossy().to_string());
            }
        }

        // 2. Check PATH
        if which_exists("hcode-daemon") {
            return Ok("hcode-daemon".to_string());
        }

        // 3. Fallback: try python -m hcode.daemon
        if which_exists("python") {
            return Ok("python".to_string());
        }

        Err("Could not find hcode-daemon executable. Please install Hcode or bundle the daemon.".to_string())
    }

    fn spawn_output_reader(&mut self, app: AppHandle) {
        // Take stdout from the child process for the reader thread
        let stdout = self.process.as_mut()
            .and_then(|c| c.stdout.take());

        std::thread::spawn(move || {
            if let Some(stdout) = stdout {
                let reader = BufReader::new(stdout);
                for line in reader.lines() {
                    match line {
                        Ok(text) => {
                            let trimmed = text.trim();
                            if trimmed.is_empty() {
                                continue;
                            }

                            // Try to parse as JSON and emit to frontend
                            match serde_json::from_str::<serde_json::Value>(trimmed) {
                                Ok(json) => {
                                    let _ = app.emit("daemon-message", json);
                                }
                                Err(_) => {
                                    // Non-JSON output — emit as log line
                                    let log_msg = serde_json::json!({
                                        "type": "log",
                                        "payload": {
                                            "line": trimmed,
                                            "stream": "stdout"
                                        }
                                    });
                                    let _ = app.emit("daemon-message", log_msg);
                                }
                            }
                        }
                        Err(e) => {
                            eprintln!("[DaemonSupervisor] stdout read error: {}", e);
                            break;
                        }
                    }
                }
            }

            // Emit daemon-down status when reader exits
            let _ = app.emit("daemon-status", serde_json::json!({
                "status": "stopped"
            }));
            eprintln!("[DaemonSupervisor] stdout reader thread exited");
        });
    }
}

fn which_exists(name: &str) -> bool {
    #[cfg(target_os = "windows")]
    {
        Command::new("where")
            .arg(name)
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
    }
    #[cfg(not(target_os = "windows"))]
    {
        Command::new("which")
            .arg(name)
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
    }
}
