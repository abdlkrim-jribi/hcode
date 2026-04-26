# Project Architecture Overview

## System Identity

Hcode is a multi-surface AI coding assistant with three delivery surfaces: Python CLI, VS Code Extension, and Tauri Desktop App. The core differentiator is a structured PEV (Planning → Execution → Verification) workflow.

## High-Level Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                         USER                                     │
│                    (Developer)                                   │
└───────┬──────────────────┬───────────────────┬──────────────────┘
        │                  │                   │
        ▼                  ▼                   ▼
┌───────────────┐  ┌───────────────┐  ┌────────────────┐
│  CLI (Rich)   │  │ Desktop App   │  │ VS Code Ext    │
│  main_cli.py  │  │ Tauri v2      │  │ TypeScript     │
│  1579 lines   │  │ React+Monaco  │  │ React Webview  │
└───────┬───────┘  └───────┬───────┘  └────────┬───────┘
        │                  │                    │
        │           ┌──────┴──────┐      ┌─────┴──────┐
        │           │ daemon.rs   │      │ hcodeBridge │
        │           │ JSON-RPC    │      │ Child proc  │
        │           │ stdin/stdout│      │ stdout parse│
        │           └──────┬──────┘      └─────┬──────┘
        │                  │                    │
        ▼                  ▼                    ▼
┌──────────────────────────────────────────────────────────────────┐
│                    PYTHON AGENT CORE                              │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐         │
│  │ HcodeAgent  │→│ Orchestrator │→│ PhaseManager     │         │
│  │ 1935 lines  │  │ 404 lines    │  │ PEV transitions │         │
│  └──────┬──────┘  └──────────────┘  └────────┬────────┘         │
│         │                                     │                  │
│  ┌──────┴──────────────────────┬──────────────┴──────────┐      │
│  ▼                             ▼                          ▼      │
│  ┌────────────┐  ┌──────────────────┐  ┌──────────────────┐     │
│  │ Planning   │  │ Execution        │  │ Verification     │     │
│  │ 772 lines  │  │ 1595 lines       │  │ 1729 lines       │     │
│  │ → task.md  │  │ → file edits     │  │ → walkthrough.md │     │
│  │ → plan.md  │  │ → 35 rounds max  │  │ → 5-phase QA     │     │
│  └────────────┘  └────────┬─────────┘  └──────────────────┘     │
│                           │                                      │
│  ┌────────────────────────┴────────────────────────────┐        │
│  │              TOOL EXECUTOR (430 lines)               │        │
│  │  retry logic • validation • confirmation prompts     │        │
│  └────────────────────────┬────────────────────────────┘        │
│                           │                                      │
│  ┌────────────────────────┴────────────────────────────┐        │
│  │            TOOL MANAGER (36+ tools)                  │        │
│  │  File: Read/Write/Edit/FuzzyEdit/Glob/Grep          │        │
│  │  Terminal: Bash/BashOutput/KillShell/LS              │        │
│  │  Git: Status/Diff/Add/Commit/Log/Checkout/Branch    │        │
│  │  Web: Fetch/Search/Scrape                            │        │
│  │  Notebook: Read/Edit/Execute                         │        │
│  │  Todo: Read/Write                                    │        │
│  │  Diff: Preview/Apply/Reject                          │        │
│  │  System: TaskBoundary/NotifyUser/AskUser/Confirm    │        │
│  └────────────────────────┬────────────────────────────┘        │
│                           │                                      │
│                           ▼                                      │
│                    FILE SYSTEM                                   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │ PROVIDER LAYER                                       │       │
│  │ ResilientProvider (647L) — circuit breaker + failover│       │
│  │ → AnthropicProvider (Claude)                         │       │
│  │ → OpenAIProvider (GPT / OSS models)                  │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │ MEMORY SYSTEM                                        │       │
│  │ MemoryManager (454L) — unified interface              │       │
│  │ → FileMemory (AGENT.md files)                         │       │
│  │ → SessionMemory (conversation persistence)            │       │
│  │ → SemanticMemory (embedding-based recall)             │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │ CONTEXT MANAGER (527L) — SQLite-backed               │       │
│  │ → Smart truncation by importance + recency            │       │
│  │ → Session export/import                               │       │
│  └──────────────────────────────────────────────────────┘       │
└──────────────────────────────────────────────────────────────────┘
```

---

## Core Agent

### Planning System

File: `src/hcode/core/phases/planning_handler.py` (772 lines)

Protocol: 5-phase reasoning

1. **Exploration** — Read project structure with Glob/Grep/Read tools
2. **Analysis** — Understand task requirements and constraints
3. **Architecture** — Design implementation approach
4. **Artifact Generation** — Write `task.md` (subtask checklist) and `implementation_plan.md` (step-by-step)
5. **Validation** — Verify artifacts are complete and well-formed via `ArtifactManager.validate_artifact_content()`

Write gate during planning:
- ALLOWED: ReadTool, GlobTool, GrepTool, WriteTool (only to `.hcode/`)
- BLOCKED: EditTool, BashTool, GitTools

### Tool Execution

File: `src/hcode/execution/tool_executor.py` (430 lines)

The `ToolExecutor` dispatches parsed tool calls to the `ToolManager`:

1. `ToolCallParser.extract_tool_calls()` parses LLM response → `List[ParsedToolCall]`
2. `ToolExecutor._validate_and_suggest_tool()` fuzzy-matches misspelled tool names
3. `ToolCallParser.normalize_arguments()` maps parameter aliases (e.g., `AbsolutePath → file_path`)
4. `ToolExecutor._execute_with_retry()` runs tool with up to 2 retries for transient errors
5. Results displayed via `HcodeDisplay` and fed back to LLM

Safety mechanisms:
- **CircuitBreaker**: 3 consecutive errors → halt execution
- **LoopDetector**: 3 identical responses (first 200 chars) → halt
- **Confirmation workflow**: Write/edit operations can require user approval

### Providers

File: `src/hcode/providers/resilient_provider.py` (647 lines)

`ResilientProvider` wraps multiple AI providers with:
- Circuit breaker pattern (closed → open → half-open)
- Automatic failover between Anthropic and OpenAI
- Exponential backoff with jitter
- Per-provider health statistics
- Configurable timeout and retry limits

Provider selection: `ProviderSelector` auto-selects based on API key availability, model preference, and health status.

### Memory

File: `src/hcode/memory/memory_manager.py` (454 lines)

Three-layer architecture:
- **Layer 1 — FileMemory**: `AGENT.md` files at global/project/local scopes. Persists across sessions.
- **Layer 2 — SessionMemory**: Conversation history with compaction. SQLite-backed via `ContextManager`.
- **Layer 3 — SemanticMemory**: Local embedding-based recall with similarity search.

Context assembly: `ContextInjector` merges memory layers into the system prompt, respecting token budget.

### Verification

File: `src/hcode/core/phases/verification_handler.py` (1729 lines)

5-phase QA protocol:
1. **Compliance** — Does implementation match the plan?
2. **Functional** — Do tests pass?
3. **Quality** — Code style, patterns, edge cases
4. **Regression** — Unintended side effects?
5. **Reporting** — Generate verdict (pass/fail/partial)

Test command extraction from plan's `## Verification Plan` section. Generates `walkthrough.md`.

---

## Desktop Application

### Tauri Backend

Files: `desktop-app/src-tauri/src/main.rs` (257L), `daemon.rs` (198L)

The Rust backend provides:

**AppState:**
```rust
struct AppState {
    daemon: Mutex<DaemonSupervisor>,
    work_dir: Mutex<Option<String>>,
}
```

**16 IPC Commands (registered via `tauri::generate_handler!`):**

| Category | Command | Purpose |
|:---|:---|:---|
| Daemon | `start_daemon` | Spawn Python daemon child process |
| Daemon | `stop_daemon` | Graceful shutdown then kill |
| Daemon | `daemon_health` | Return status/uptime/PID |
| Task | `run_task` | Send JSON-RPC `run_task` to daemon |
| Task | `abort_task` | Send JSON-RPC `abort` to daemon |
| Plan | `approve_plan` | Send JSON-RPC `approve_plan` |
| Plan | `reject_plan` | Send JSON-RPC `reject_plan` with feedback |
| Patch | `accept_patch` | Send JSON-RPC `accept_patch` for file |
| Patch | `reject_patch` | Send JSON-RPC `reject_patch` for file |
| Patch | `rollback_all` | Send JSON-RPC `rollback_all` |
| FS | `open_folder_dialog` | Native folder picker |
| FS | `list_directory` | List files (sorted, filtered) |
| FS | `read_file` | Read file content |
| FS | `write_file` | Write file content |
| Security | `save_api_key` | Store in Windows Credential Manager |
| Security | `get_api_key` | Retrieve from Windows Credential Manager |

All task/plan/patch commands use JSON-RPC 2.0 protocol over the daemon's stdin.

### Daemon Supervisor

`DaemonSupervisor` manages the Python hcode-daemon as a child process:

```
DaemonSupervisor
├── start() — find executable, spawn with piped stdin/stdout/stderr
├── stop() — graceful shutdown msg → wait 500ms → kill
├── send() — write JSON-RPC to daemon stdin
├── spawn_output_reader() — thread reads stdout, emits Tauri events
└── find_daemon_executable()
    ├── 1. Bundled resource (hcode-daemon.exe)
    ├── 2. In PATH (hcode-daemon)
    └── 3. Fallback (python -m hcode.daemon)
```

### Python Agent Bridge

Communication protocol: **JSON-RPC 2.0 over stdin/stdout**

```
Desktop (Rust) ──stdin──→ Python Daemon
Desktop (Rust) ←stdout── Python Daemon (line-by-line JSON)
```

### Frontend (React)

File: `desktop-app/src-ui/src/App.tsx` (429 lines)

**3-column resizable layout:**
```
┌──────────┬─────────────────────────┬────────────────┐
│ Explorer │       Editor            │  Agent Panel   │
│ (200px)  │   (Monaco/DiffReview)   │  (360px)       │
│ Ctrl+B   │      Flex               │  Ctrl+J        │
├──────────┴─────────────────────────┴────────────────┤
│  StatusBar                                          │
└─────────────────────────────────────────────────────┘
```

**IPC Bridge** (`ipc/bridge.ts`, 246L): Detects Tauri vs browser environment. In browser mode, returns mock data for standalone UI development.

**Components:**
- `AgentPanel` — Linear task stream with Plan/Diff/Verification cards
- `DiffReviewer` — Monaco-powered side-by-side diff with file tabs
- `FileExplorer` — File tree with lazy loading
- `StatusBar` — Phase dots, daemon status, working directory
- `SettingsPanel` — API key management overlay

---

## VS Code Extension

### Extension Activation Flow

File: `vscode-extension/src/extension.ts` (82 lines)

```
activate(context)
├── AssetManager.promptSetupIfMissing()
├── SecretStorageManager(context.secrets)
├── GitIntegration()
├── HcodeBridge(secretStorage) — lazy, spawns on first use
├── WebviewPanelManager(context, bridge, git)
├── Register sidebar providers:
│   ├── hcode.sidebar
│   └── hcode.history
└── Register commands:
    ├── hcode.runTask → openRunTaskPanel()
    ├── hcode.openChat → openChatPanel()
    ├── hcode.openSettings → openSettingsPanel()
    └── hcode.refactorSelection → extract text → openRunTaskPanel(prompt)
```

### Webview Architecture

File: `vscode-extension/src/webviewPanelManager.ts` (299 lines)

```
WebviewPanelManager
├── openRunTaskPanel(initialTask?) — create/reveal WebviewPanel
├── openChatPanel() — create/reveal chat panel
├── openSettingsPanel() — create/reveal settings panel
├── setupMessageHandlers(panel)
│   ├── Webview → Extension messages:
│   │   ├── runTask → bridge.runTask()
│   │   ├── abort → bridge.kill()
│   │   ├── approve → bridge.sendApproval()
│   │   ├── reject → bridge.sendRejection()
│   │   ├── acceptPatch → bridge.sendFileDecision()
│   │   ├── rejectPatch → bridge.sendFileDecision()
│   │   ├── rollback → bridge.sendRollback()
│   │   ├── listDirectory → listDirectorySync()
│   │   └── getEditorContext → getActiveEditorContext()
│   │
│   └── Extension → Webview events:
│       └── bridge.onMessage → panel.webview.postMessage()
│
├── getWebviewHtml() — generate HTML with CSP nonce
└── getActiveEditorContext() — file, selection, language
```

### Communication with Agent

File: `vscode-extension/src/backend/hcodeBridge.ts` (261 lines)

```
HcodeBridge
├── runTask(task, autonomous)
│   ├── Build env with API keys from SecretStorage
│   ├── Spawn: python -m hcode run --stream --output-format=jsonl
│   ├── Setup readline on stdout
│   ├── Each line → parseLine()
│   └── Events: plan/task_update/file_patch/verification/error/done
│
├── parseLine(line)
│   ├── Try JSON.parse()
│   │   ├── type: plan → emit { type: 'plan', payload }
│   │   ├── type: file_patch → emit { type: 'file_patch', payload }
│   │   ├── type: verification → emit { type: 'verification', payload }
│   │   ├── type: error → emit { type: 'error', payload }
│   │   └── type: done → emit { type: 'done' }
│   └── Fallback: raw text → check PROGRESS_MARKERS regex
│       ├── /planning/i → emit { type: 'progress', phase: 'planning' }
│       ├── /thinking/i → emit { type: 'progress', phase: 'thinking' }
│       └── /verifying/i → emit { type: 'progress', phase: 'verifying' }
│
├── sendApproval() → write "APPROVE\n" to stdin
├── sendRejection(comment) → write "REJECT: comment\n" to stdin
├── sendFileDecision(path, accepted) → write to stdin
├── sendRollback() → write "ROLLBACK\n" to stdin
└── kill() → process.kill()
```

**Message Types flowing from Python to Extension:**

| Type | Payload | Trigger |
|:---|:---|:---|
| `plan` | `{ markdown }` | Planning phase produces plan |
| `task_update` | `{ markdown }` | Task progress change |
| `file_patch` | `{ path, diff, backup, originalContent, newContent }` | File edit proposed |
| `verification` | `{ markdown, passed, testResults? }` | Verification complete |
| `error` | `{ message, suggestion }` | Error occurred |
| `circuit_break` | `{ reason }` | Circuit breaker tripped |
| `log` | `{ line, stream }` | Raw output line |
| `progress` | `{ label, increment? }` | Phase progress |
| `ready` | — | Agent ready |
| `done` | — | Task complete |
