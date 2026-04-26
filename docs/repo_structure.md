# Repository Structure

## Root Level

```
hcode/
├── .env.example              Environment variable template (API keys)
├── .github/workflows/
│   └── release.yml           GitHub Actions release workflow
├── CHANGELOG.md              Version history
├── CONTRIBUTING.md            Contribution guide
├── LICENSE                    MIT License
├── MANIFEST.in                Python packaging manifest
├── README.md                  Project readme
├── hcode_cli.py               CLI entry wrapper
├── pyproject.toml             Python project config + dependencies
├── requirements.txt           Python dependencies
├── setup.py                   Legacy setup script
├── config/tools.yaml          Global tool definitions
├── docs/                      Documentation files
├── examples/                  Example configurations
└── scripts/                   Utility scripts (quick_start.ps1, etc.)
```

---

## Python Agent Core: `src/hcode/`

### `src/hcode/core/` — Agent Orchestration (~8,500 lines)

```
core/
├── agent.py                   HcodeAgent — main agent class (1935L)
│                              Entry point, prompt construction, tool loop,
│                              mode routing, response processing
│
├── protocols.py               Protocol interfaces (402L)
│                              ToolResult, ParsedToolCall, AgentContext,
│                              PhaseResult, PhaseHandlerProtocol,
│                              PhaseManagerProtocol, ArtifactManagerProtocol
│
├── session_manager.py         Singleton session state management
│
├── adapters/
│   └── agent_adapter.py       PEV adapter bridge — maps old API to new
│
├── classification/
│   └── task_classifier.py     Task complexity routing
│                              Classifies: simple → fast, complex → PEV
│
├── context/
│   ├── budget_manager.py      Token budget tracking
│   └── manager.py             ContextManager (527L)
│                              SQLite-backed conversation history
│                              Smart truncation by importance + recency
│                              Session export/import
│
├── execution/
│   ├── circuit_breaker.py     Error threshold halting (3 errors → stop)
│   ├── feedback.py            Error feedback formatting for LLM
│   ├── loop_detector.py       Stuck-loop detection (3 identical responses)
│   ├── state_machine.py       Execution state tracking
│   └── tool_executor.py       ToolExecutor (430L)
│                              Dispatch, retry, validation, confirmation
│
├── loop/
│   └── agent_loop.py          AgentLoopController (205L)
│                              PEV state machine: Phase enum, StopReason
│                              tick(), should_stop(), record_error()
│
├── observability/
│   ├── analytics.py           Usage analytics collection
│   └── logger.py              Structured logging
│
├── optimization/
│   ├── batch_writer.py        Batched file write operations
│   ├── result_cache.py        Tool result caching
│   └── token_counter.py       Token estimation (len/4 heuristic)
│
├── orchestration/
│   ├── agent_orchestrator.py  AgentOrchestrator (404L)
│                              PEV workflow coordinator
│                              Delegates to phase handlers
│   └── phase_manager.py       Phase transition logic
│
├── phases/
│   ├── base_handler.py        BasePhaseHandler abstract class
│   ├── planning_handler.py    PlanningPhaseHandler (772L)
│                              5-phase reasoning protocol
│                              Produces: task.md, implementation_plan.md
│   ├── execution_handler.py   ExecutionPhaseHandler (1595L)
│                              4-phase protocol, max 35 rounds
│                              Produces: file modifications
│   ├── verification_handler.py VerificationPhaseHandler (1729L)
│                              5-phase QA protocol
│                              Produces: walkthrough.md
│   ├── fast_handler.py        FastHandler (~200L)
│                              Bypasses planning for simple tasks
│   └── init_handler.py        Initialization handler
│
├── prompt/
│   ├── context_injector.py    Memory → system prompt injection
│   └── user_task_formatter.py Task formatting for prompts
│
├── reasoning/
│   └── structured.py          ReasoningParser, TodoIntegrator
│
├── response/
│   ├── cleaner.py             Response text cleaning
│   ├── completion_detector.py Task completion detection
│   ├── continuation.py        Auto-continuation for truncated responses
│   ├── parser.py              Response parsing utilities
│   └── thinking_processor.py  Thinking block extraction
│
├── safety/
│   └── guard.py               Operation safety checks
│
├── services/
│   ├── artifact_manager.py    ArtifactManager (223L)
│                              Create/load/validate: task.md, plan.md, walkthrough.md
│   └── checkpoint.py          Checkpoint/rollback management
│
├── todo/
│   ├── auto_updater.py        Automatic todo checkbox updates
│   └── manager.py             TodoManager
│
└── tools/
    └── tool_call_parser.py    ToolCallParser (284L)
                               Extract tool calls from LLM responses
                               Strategy 1: native API, Strategy 2: JSON text
```

### `src/hcode/tools/` — Tool Implementations (~4,500 lines)

```
tools/
├── __init__.py                Tool registration exports
├── base/
│   └── base_tool.py           BaseTool abstract, ToolResult, ToolParameter, ToolCategory
│
├── core/
│   ├── tool_manager.py        ToolManager (265L) — central registry, dispatch
│   ├── tool_callbacks.py      Tool lifecycle hooks
│   ├── validator.py           Parameter validation
│   └── executor.py            Low-level tool execution
│
├── files/
│   ├── file_tools.py          ReadTool, WriteTool, EditTool, MultiEditTool, GrepTool (1590L)
│   ├── diff_tools.py          DiffPreviewTool, ApplyChangeTool, RejectChangeTool (791L)
│   ├── fuzzy_edit_tool.py     FuzzyEditTool — difflib sliding-window matcher (162L)
│   └── smart_glob_tool.py     SmartGlobTool — context-aware file search
│
├── terminal/
│   └── bash_tools.py          BashTool, BashOutputTool, KillShellTool, LSTool, SearchOutputTool (915L)
│                              Background shell management, Windows command translation
│
├── git/
│   └── git_tools.py           GitStatus, GitDiff, GitAdd, GitCommit, GitLog, GitCheckout, GitBranch
│
├── web/
│   └── web_tools.py           WebFetchTool, WebSearchTool, WebScrapeTool (320L)
│                              html2text conversion, Brave/Google API search, CSS selector scraping
│
├── notebook/
│   ├── notebook_tools.py      NotebookReadTool, NotebookEditTool
│   └── interactive_tools.py   NotebookExecuteTool
│
├── todo/
│   ├── todo_read.py           TodoReadTool
│   └── todo_write.py          TodoWriteTool
│
├── system/
│   ├── agent_tools.py         TaskTool, ExitPlanModeTool
│   ├── command_system.py      SlashCommandTool, SkillTool
│   └── hcode_tools.py         TaskBoundaryTool, NotifyUserTool
│
└── analysis/
    └── outline_tool.py        ViewFileOutlineTool — file structure outline
```

### `src/hcode/providers/` — LLM Provider Layer (~1,200 lines)

```
providers/
├── base.py                    AIProvider abstract, Message, CompletionResponse
├── anthropic_provider.py      AnthropicProvider (Claude API)
├── openai_provider.py         OpenAIProvider (GPT, OSS models)
├── provider_selector.py       Auto-selection based on keys, health
└── resilient_provider.py      ResilientProvider (647L)
                               Circuit breaker, failover, backoff, health stats
```

### `src/hcode/memory/` — Memory System (~1,100 lines)

```
memory/
├── config.py                  MemoryConfig dataclass
├── file_memory.py             AGENT.md file-based memory (global/project/local)
├── session_memory.py          Conversation persistence with compaction
├── semantic_memory.py         Embedding-based recall with similarity search
├── embeddings.py              Local embedding computation
└── memory_manager.py          MemoryManager (454L) — unified interface
```

### `src/hcode/ui/` — CLI Display Layer (~1,500 lines)

```
ui/
├── chat_ui.py                 Chat mode display formatting
├── hcode_display.py           Tool result formatting
├── components.py              Rich reusable components (panels, tables)
├── panels.py                  Panel formatting
├── syntax.py                  Syntax highlighting
├── theme.py                   Color theme definitions
├── icons.py                   Windows-safe icon system (emoji → ASCII fallback)
├── banners.py                 ASCII art startup banners
├── animations.py              Progress animations
├── confirmation_display.py    User confirmation prompts for edits
├── interactive_selector.py    Multi-choice selector
├── live_todo_bar.py           Live todo status bar
└── todo_display.py            Todo list rendering
```

### `src/hcode/config/` — Configuration (~800 lines)

```
config/
├── settings.py                Settings management
├── defaults.py                Default values
├── tools.py                   Tool configuration
├── tools.yaml                 Tool definitions in YAML
├── prompts.py                 Prompt loading utilities
├── prompt_loader.py           YAML/MD prompt file loader
├── reasoning_prompts.py       Reasoning chain prompts
├── thinking.py                Thinking block configuration
├── task_classification.yaml   Classification rules
└── core_prompts/core/         PEV protocol prompts
    ├── phases.yaml            Phase definitions
    ├── system.yaml            Identity/system prompt
    ├── reasoning.yaml         Reasoning instructions
    ├── templates.yaml         Template strings
    ├── tool_format.md         Tool call format instructions
    └── pev_prompts/           Per-phase protocol files
        ├── planning_mode.md
        ├── execution_handler.md
        ├── verification_handler.md
        ├── implementation_plan.md
        ├── task.md
        └── walkthrough.md
```

---

## Desktop Application: `desktop-app/`

```
desktop-app/
├── package.json               Root package — Tauri CLI commands
│
├── src-tauri/                 RUST BACKEND
│   ├── Cargo.toml             Dependencies: tauri, serde, keyring, tokio
│   ├── tauri.conf.json        Window config, plugins, permissions
│   ├── build.rs               Windows resource file (icon) generation
│   └── src/
│       ├── main.rs            16 IPC command handlers (257L)
│       │                      AppState, daemon/task/fs/security commands
│       │                      tauri::generate_handler! registration
│       └── daemon.rs          DaemonSupervisor (198L)
│                              Spawn/stop/send/health
│                              Executable discovery (bundled → PATH → python)
│                              Output reader thread → Tauri events
│
├── src-ui/                    REACT FRONTEND
│   ├── vite.config.ts         Vite build config
│   ├── tsconfig.json          TypeScript configuration
│   ├── index.html             Entry HTML
│   └── src/
│       ├── main.tsx           React entry point
│       ├── App.tsx            Root component (429L)
│       │                      3-column resizable layout
│       │                      Keyboard shortcuts (Ctrl+B/J/1/2/3)
│       │                      State management (phase, messages, selectedFile)
│       ├── types.ts           TypeScript types (152L)
│       │                      AppState, AgentPhase, HcodeMessage
│       │                      FilePatchPayload, VerificationPayload
│       ├── components/
│       │   ├── AgentPanel.tsx     Task stream with inline cards
│       │   ├── DiffReviewer.tsx   Monaco side-by-side diff
│       │   ├── MonacoEditor.tsx   Code editor wrapper
│       │   ├── FileExplorer.tsx   File tree with lazy loading
│       │   ├── StatusBar.tsx      Phase dots, daemon status
│       │   └── SettingsPanel.tsx  API key management
│       ├── ipc/
│       │   └── bridge.ts         IPC abstraction (246L)
│       │                         Tauri detection vs browser mock
│       └── styles/
│           ├── tokens.css        Design tokens (hsl(228) palette, 4px grid)
│           └── global.css        IDE-grade layout, focus model
│
└── scripts/
    ├── launch.ps1             Dev mode launcher
    └── build-daemon.ps1       PyInstaller daemon bundling
```

---

## VS Code Extension: `vscode-extension/`

```
vscode-extension/
├── package.json               Extension manifest, commands, views
├── tsconfig.json              TypeScript config
│
├── src/
│   ├── extension.ts           Entry point (82L)
│   │                          activate(): register commands + sidebar providers
│   │                          Commands: runTask, openChat, openSettings, refactorSelection
│   │
│   ├── webviewPanelManager.ts Panel lifecycle management (299L)
│   │                          3 panel types: RunTask, Chat, Settings
│   │                          setupMessageHandlers: Webview ↔ Extension bridge
│   │                          getWebviewHtml: CSP nonce generation
│   │
│   ├── backend/
│   │   ├── hcodeBridge.ts     Python agent bridge (261L)
│   │   │                      Spawns: python -m hcode run --stream --output-format=jsonl
│   │   │                      Parses stdout line-by-line
│   │   │                      Emits: plan/file_patch/verification/error/done events
│   │   │                      Sends: APPROVE/REJECT/ROLLBACK via stdin
│   │   ├── secretStorage.ts   VS Code SecretStorage wrapper
│   │   ├── gitIntegration.ts  VS Code Git extension integration
│   │   ├── progressManager.ts VS Code progress notification management
│   │   ├── sidebarProvider.ts Sidebar webview provider (4,484 bytes)
│   │   └── assetManager.ts    Asset/setup checks
│   │
│   └── webview/
│       ├── app.tsx            Root webview component (369L)
│       │                      Task stream, phase tracking, message rendering
│       ├── components/
│       │   ├── TaskComposer.tsx  Task input with Plan/Fast mode selector
│       │   └── GitPanel.tsx     Git status popover with commit dialog
│       └── styles/
│           ├── tokens.css      Design tokens (with VS Code variable fallbacks)
│           └── global.css      Webview-scoped global styles
│
└── test/
    └── e2e/                   End-to-end test infrastructure
        └── suite/
            └── index.ts       Test runner configuration
```

---

## Tests: `tests/`

```
tests/
├── conftest.py                Shared pytest fixtures
├── sanity/                    Quick smoke tests (13 files)
│   ├── test_sanity.py         Core module imports
│   └── ...                    Provider, tool, config sanity checks
├── unit/                      Unit tests (17 files)
│   ├── tools/                 Tool-specific tests
│   ├── display/               UI display tests
│   ├── memory/                Memory system tests
│   ├── context/               Context manager tests
│   └── output_processing/     Response processing tests
└── integration/               Integration tests (9 files)
    └── ...                    End-to-end workflow tests
```
