# Integration Map

## System Overview

Hcode consists of 3 independent systems that share the Python agent core:

```
┌──────────────────────────────────────────────────────────────┐
│                      PYTHON CORE                              │
│  src/hcode/                                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐  │
│  │ Agent    │ │ Tools    │ │Providers │ │ Memory/Context │  │
│  └──────────┘ └──────────┘ └──────────┘ └────────────────┘  │
└──────────┬───────────────────────────┬───────────────────────┘
           │                           │
     ┌─────┴─────┐              ┌─────┴──────┐
     │           │              │            │
┌────▼────┐ ┌───▼─────┐   ┌───▼──────┐ ┌──▼──────────┐
│  CLI    │ │ Daemon  │   │ hcode    │ │ Direct      │
│ (Rich)  │ │ Process │   │ run      │ │ import      │
│ stdin/  │ │ JSON-RPC│   │ --stream │ │ (future)    │
│ stdout  │ │ stdin/  │   │ --jsonl  │ │             │
│         │ │ stdout  │   │ stdout   │ │             │
└─────────┘ └────┬────┘   └────┬─────┘ └─────────────┘
                 │              │
            ┌────▼────┐   ┌────▼──────────┐
            │ Tauri   │   │ VS Code       │
            │ Desktop │   │ Extension     │
            │ App     │   │ Host          │
            └─────────┘   └───────────────┘
```

---

## Integration 1: CLI ↔ Python Core

**Type**: Direct Python import (in-process)

```
main_cli.py
├── from hcode.core.agent import HcodeAgent
├── agent = HcodeAgent(provider, model, ...) 
├── agent.execute_task(task)     # Synchronous call
└── Display results via Rich
```

- No IPC — CLI runs the agent in the same Python process
- Output via Rich console (panels, tables, syntax highlighting)
- Interactive input via `prompt_toolkit` in chat mode

---

## Integration 2: Desktop App ↔ Python Core

**Type**: Child process with JSON-RPC 2.0 over stdin/stdout

### Process Lifecycle

```
┌────────────────────┐          ┌─────────────────────┐
│   TAURI (Rust)     │          │  PYTHON DAEMON       │
│   main.rs          │          │  hcode-daemon(.exe)  │
│                    │          │                      │
│ start_daemon() ────┼──spawn──→│ Process starts       │
│                    │          │ Reads stdin           │
│ AppState {         │          │ Writes stdout         │
│   daemon: Mutex    │          │                      │
│   <DaemonSuperv>   │          │                      │
│ }                  │          │                      │
└────────────────────┘          └──────────────────────┘
```

### Communication Protocol

**Tauri → Python (via stdin):**
```json
{
    "jsonrpc": "2.0",
    "id": "hex-timestamp",
    "method": "run_task",
    "params": {
        "task": "add logging to main.py",
        "mode": "plan",
        "autonomous": false
    }
}
```

Supported methods:
- `run_task` — execute a coding task
- `abort` — cancel running task
- `approve_plan` — accept planning output
- `reject_plan` — reject plan with feedback
- `accept_patch` — accept file change
- `reject_patch` — reject file change
- `rollback_all` — undo all changes
- `shutdown` — graceful daemon shutdown

**Python → Tauri (via stdout, line-delimited JSON):**
```json
{"type": "plan", "payload": {"markdown": "..."}}
{"type": "file_patch", "payload": {"path": "...", "diff": "...", "originalContent": "...", "newContent": "..."}}
{"type": "verification", "payload": {"markdown": "...", "passed": true}}
{"type": "done"}
```

**Tauri → React Frontend (via Tauri events):**
```
daemon.spawn_output_reader() thread → app.emit("daemon-status", payload)
```

**React → Tauri (via IPC invoke):**
```typescript
invoke('run_task', { task, mode, autonomous })
invoke('approve_plan')
invoke('accept_patch', { path })
```

### File System Access

| Accessor | Mechanism | Scope |
|:---|:---|:---|
| Tauri Backend | `std::fs` (Rust) | `list_directory`, `read_file`, `write_file` |
| Python Daemon | Python `open()` | Tool execution (Read/Write/Edit/Bash) |
| React Frontend | Via IPC only | No direct FS access |

### Credential Storage

```
React UI → invoke('save_api_key', {provider, key})
         → main.rs → keyring::Entry::new("hcode-desktop", provider)
         → Windows Credential Manager
```

---

## Integration 3: VS Code Extension ↔ Python Core

**Type**: Child process with stdout line parsing

### Process Lifecycle

```
┌─────────────────────────┐       ┌──────────────────────────┐
│ VS CODE Extension Host  │       │ PYTHON PROCESS            │
│ extension.ts            │       │ python -m hcode run       │
│                         │       │   --stream                │
│ activate() {            │       │   --output-format=jsonl   │
│   bridge = HcodeBridge()│       │                           │
│ }                       │       │                           │
│                         │       │                           │
│ bridge.runTask(task) ───┼─spawn─→ Process starts            │
│                         │       │ Writes JSONL to stdout    │
│ bridge.parseLine(line)←─┼─read──│ Each line is JSON or text │
│                         │       │                           │
│ bridge.sendApproval() ──┼─write─→ Reads "APPROVE\n" stdin   │
└─────────────────────────┘       └──────────────────────────┘
```

### Communication Protocol

**Extension → Python (via stdin):**
Simple text commands:
```
APPROVE\n
REJECT: feedback text\n
ROLLBACK\n
ACCEPT:filepath\n
REJECT:filepath\n
```

**Python → Extension (via stdout):**
JSONL lines or raw text:
```json
{"type": "plan", "payload": {"markdown": "..."}}
{"type": "file_patch", "payload": {"path": "...", "diff": "..."}}
{"type": "verification", "payload": {"markdown": "...", "passed": true}}
{"type": "done"}
```

If a line is not valid JSON, `parseLine()` checks PROGRESS_MARKERS:
```typescript
PROGRESS_MARKERS = [
    { pattern: /planning/i, phase: 'planning' },
    { pattern: /thinking/i, phase: 'thinking' },
    { pattern: /verifying/i, phase: 'verifying' },
    { pattern: /completed successfully/i, phase: 'done' },
]
```

### Message Flow

```
User types task in TaskComposer
    │
    ▼
Webview sends postMessage({ type: 'runTask', task, autonomous })
    │
    ▼
WebviewPanelManager.setupMessageHandlers() receives message
    │
    ▼
bridge.runTask(task, autonomous)
    │ Spawns: python -m hcode run "$task" --stream --output-format=jsonl
    │ Sets up readline on stdout
    │
    ▼
Python agent executes PEV workflow
    │ Writes JSONL to stdout
    │
    ▼
bridge.parseLine(line) → emits HcodeMessage
    │
    ▼
WebviewPanelManager.onMsg(msg) → panel.webview.postMessage(msg)
    │
    ▼
Webview app.tsx receives message → updates state → re-renders UI
```

### File System Access

| Accessor | Mechanism | Scope |
|:---|:---|:---|
| Extension Host | Node.js `fs` | `listDirectorySync`, `getActiveEditorContext` |
| Python Process | Python `open()` | Tool execution (Read/Write/Edit/Bash) |
| Webview | Via postMessage only | No direct FS access |

### Credential Storage

```
Webview → postMessage({ type: 'saveApiKey', provider, key })
        → Extension Host → SecretStorageManager
        → vscode.SecretStorage API (OS keychain)
```

### VS Code API Integration

| Feature | VS Code API | Usage |
|:---|:---|:---|
| Active editor | `vscode.window.activeTextEditor` | Get file, selection, language for refactoring |
| Git | Built-in Git extension | `GitIntegration` class |
| Secrets | `vscode.SecretStorage` | API key storage |
| Progress | `vscode.window.withProgress` | `ProgressManager` shows progress notifications |
| Commands | `vscode.commands.registerCommand` | 4 commands registered |
| Sidebar | `vscode.window.registerWebviewViewProvider` | 2 sidebar views |
| Webview | `vscode.WebviewPanel` | 3 panel types (task, chat, settings) |

---

## Comparison of Integration Approaches

| Aspect | CLI | Desktop App | VS Code Extension |
|:---|:---|:---|:---|
| **Process model** | In-process | Child process (daemon) | Child process (per-task) |
| **Protocol** | Direct Python call | JSON-RPC 2.0 (stdin/stdout) | JSONL (stdout) + text (stdin) |
| **Process lifetime** | One-shot or REPL | Long-lived daemon | Spawned per task |
| **User output** | Rich terminal | Tauri events → React | stdout lines → postMessage |
| **User input** | stdin / prompt_toolkit | IPC invoke → JSON-RPC | postMessage → stdin text |
| **Credentials** | `.env` / env vars | Windows Credential Mgr | VS Code SecretStorage |
| **File access** | Direct Python FS | Rust FS + Python FS | Node.js FS + Python FS |
| **State persistence** | SQLite session DB | SQLite + daemon state | SQLite session DB |

---

## Shared Resources

| Resource | Location | Shared By |
|:---|:---|:---|
| SQLite session DB | `.hcode/sessions/` | All 3 surfaces |
| AGENT.md memory | `.hcode/AGENT.md` | All 3 surfaces |
| PEV artifacts | `.hcode/{task,implementation_plan,walkthrough}.md` | All 3 surfaces |
| Design tokens | `tokens.css` | Desktop + VS Code (separate copies) |
| Python agent | `src/hcode/` | All 3 surfaces (same codebase) |
