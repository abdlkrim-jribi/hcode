# Prompt Backlog

Prioritized list of improvement prompts for a second AI engineer, ordered by value and risk.

---

## Priority 1 — Blocking Issues (Do First)

### P1.1 — Fix Test Suite Imports
- **Why**: 108/225 sanity tests and all unit tests are broken due to stale imports. No code quality gate exists.
- **Files**: `tests/sanity/*.py`, `tests/unit/**/*.py`
- **Root causes**: `AIProvider` renamed, `hcode.utils.project_analyzer` deleted, `hcode.cli_enhanced` deleted, `hcode.ui.animations` API changed, `hcode_path` missing
- **Expected outcome**: All 225 sanity tests pass, all unit tests collect and run
- **Effort**: MEDIUM (2-3 hours)
- **Prerequisite**: Must be done before any other improvement

### P1.2 — Install pytest-cov and Fix pyproject.toml
- **Why**: Default `pytest` invocation fails due to `--cov` flag without `pytest-cov` installed. CI cannot run tests.
- **Files**: `pyproject.toml`, `requirements.txt` (or `requirements-dev.txt`)
- **Expected outcome**: `python -m pytest` works without `addopts` override
- **Effort**: SMALL (15 minutes)
- **Prerequisite**: Must be done before any CI-dependent work

### P1.3 — Implement DaemonSupervisor.send()
- **Why**: Desktop app cannot execute any tasks. All `run_task`, `approve_plan`, `accept_patch` IPC commands hit a no-op stub.
- **Files**: `desktop-app/src-tauri/src/daemon.rs` (line 108-118)
- **What to implement**: Take stdin from `self.process`, write the JSON-RPC message as a line, flush
- **Expected outcome**: Tauri backend can send commands to Python daemon
- **Effort**: SMALL (30 minutes)
- **Prerequisite**: Must be done before any desktop app feature work

### P1.4 — Implement spawn_output_reader()
- **Why**: Desktop app receives no output from the Python daemon. The current implementation is a fake 5s loop.
- **Files**: `desktop-app/src-tauri/src/daemon.rs` (lines 161-177)
- **What to implement**: Take stdout from child process, spawn thread that reads lines via `BufReader`, parse as JSON, emit as Tauri events
- **Expected outcome**: Desktop frontend receives real-time agent messages
- **Effort**: MEDIUM (1-2 hours)
- **Prerequisite**: Must be done before any desktop app feature work

---

## Priority 2 — High-Impact Improvements

### P2.1 — Replace EditTool String-Match with Line-Range
- **Why**: EditTool has ~30-40% first-attempt failure rate. It's the single biggest reliability bottleneck.
- **Files**: `src/hcode/tools/files/file_tools.py` (EditTool class, lines 586-1074)
- **Change**: Accept `{file, start_line, end_line, new_content}` instead of `{old_string, new_string}`
- **Expected outcome**: Edit success rate improves from ~60% to ~90%+
- **Effort**: MEDIUM (3-4 hours)
- **Should be done after**: P1.1 (tests must pass first to verify change doesn't break things)

### P2.2 — Add Token Counting via tiktoken
- **Why**: `len(text) / 4` heuristic causes context overflow or underutilization. Code is ~2.5-3 chars/token, not 4.
- **Files**: `src/hcode/memory/memory_manager.py` (line ~304), `src/hcode/core/optimization/token_counter.py`
- **Expected outcome**: Accurate context window management
- **Effort**: SMALL (1 hour)

### P2.3 — Add Streaming Display to Desktop App
- **Why**: Most visible UX improvement. Users see nothing during agent execution.
- **Files**: `desktop-app/src-ui/src/components/AgentPanel.tsx`
- **Change**: Accept incremental messages from daemon, render token-by-token
- **Expected outcome**: Live agent response rendering
- **Effort**: MEDIUM (3-4 hours)
- **Should be done after**: P1.4 (needs working output reader)

### P2.4 — Structured Error Feedback for Tool Failures
- **Why**: When EditTool fails, the raw error is passed to the LLM which often repeats the same mistake
- **Files**: `src/hcode/core/execution/feedback.py`, `src/hcode/execution/tool_executor.py`
- **Change**: Create `ErrorAnalyzer` that extracts: what failed, why, correction hint
- **Expected outcome**: Fewer retry loops, faster convergence
- **Effort**: MEDIUM (2-3 hours)

---

## Priority 3 — Architecture Refactors

### P3.1 — Decompose HcodeAgent
- **Why**: 1935-line God object inhibits testing and extensibility
- **Files**: `src/hcode/core/agent.py`
- **Extract**: `PromptBuilder`, `ResponseProcessor`, `TaskRouter`, `ContinuationManager`
- **Expected outcome**: `HcodeAgent` reduced to ~400 lines
- **Effort**: LARGE (6-8 hours)

### P3.2 — Unify Tool Call Extraction
- **Why**: 3-4 separate `_extract_tool_calls()` implementations cause inconsistent behavior
- **Files**: `planning_handler.py`, `execution_handler.py`, `verification_handler.py`, `tool_call_parser.py`
- **Change**: Create single `ToolCallExtractor` used by all handlers
- **Expected outcome**: Consistent parsing, single maintenance point
- **Effort**: MEDIUM (2-3 hours)

### P3.3 — Auto-Discover Verification Commands
- **Why**: Verification only runs commands explicitly written in the plan. Missing tests = skipped QA.
- **Files**: `src/hcode/core/phases/verification_handler.py`
- **Change**: Add fallback detection of `pytest`, `npm test`, `cargo test`, `go test`, `Makefile` targets
- **Expected outcome**: Verification catches untested changes
- **Effort**: SMALL (1-2 hours)

---

## Priority 4 — UI/UX Polish

### P4.1 — Add Command Palette to Desktop App
- **Why**: Core editor-grade feature missing. Ctrl+Shift+P is expected in every IDE.
- **Files**: `desktop-app/src-ui/src/App.tsx`, new `CommandPalette.tsx` component
- **Expected outcome**: Fuzzy-search command palette
- **Effort**: MEDIUM (3-4 hours)

### P4.2 — Upgrade VS Code Extension Diff to Monaco
- **Why**: Extension uses `<pre>` blocks while desktop uses Monaco. Inconsistent experience.
- **Files**: `vscode-extension/src/webview/app.tsx`
- **Expected outcome**: Professional diff experience in VS Code
- **Effort**: MEDIUM (2-3 hours)

### P4.3 — Create Shared Design Token Package
- **Why**: Two separate copies of `tokens.css` will drift. Single source of truth needed.
- **Files**: New `packages/design-tokens/` package
- **Expected outcome**: Both frontends import from same source
- **Effort**: SMALL (1-2 hours)

---

## Priority 5 — Infrastructure

### P5.1 — Add Desktop App CI
- **Why**: No automated build/test for 397 files of Tauri/React code
- **Files**: New `.github/workflows/build-desktop.yml`
- **Expected outcome**: PR-level TypeScript type checking + Rust build
- **Effort**: SMALL (1-2 hours)

### P5.2 — Add VS Code Extension CI
- **Why**: No automated build/test for 46 files of extension code
- **Files**: New `.github/workflows/build-extension.yml`
- **Expected outcome**: PR-level TypeScript compilation check
- **Effort**: SMALL (1 hour)

### P5.3 — Commit desktop-app and vscode-extension
- **Why**: 400+ files of engineering work are unversioned. Data loss risk.
- **Expected outcome**: All code under version control
- **Effort**: SMALL (15 minutes)

---

## Summary: Recommended Execution Order

```
Phase 1 (Day 1):
  P1.1  Fix test suite imports
  P1.2  Install pytest-cov
  P5.3  Commit desktop-app + vscode-extension

Phase 2 (Day 1-2):
  P1.3  Implement DaemonSupervisor.send()
  P1.4  Implement spawn_output_reader()
  P2.2  Add tiktoken token counting

Phase 3 (Day 2-3):
  P2.1  Replace EditTool with line-range
  P2.4  Structured error feedback
  P3.3  Auto-discover verification commands

Phase 4 (Day 3-4):
  P2.3  Streaming display
  P3.2  Unify tool call extraction
  P5.1  Add Desktop CI
  P5.2  Add Extension CI

Phase 5 (Week 2):
  P3.1  Decompose HcodeAgent
  P4.1  Command palette
  P4.2  VS Code diff upgrade
  P4.3  Shared design tokens
```
