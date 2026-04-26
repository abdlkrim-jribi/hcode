# Project Status Baseline

**Date**: 2026-03-31
**Method**: Code inspection + runtime verification
**Audit scope**: Python core, desktop app, VS Code extension, tests, CI/CD

---

## Executive Summary

Hcode is a multi-surface AI coding assistant with a genuine PEV (Planning → Execution → Verification) workflow. The Python agent core is **partially working** — the main architecture imports and runs, but the test suite has significant rot (108/225 sanity tests failing). The desktop app and VS Code extension **compile cleanly** but their IPC backends are **incomplete stubs**. There is no CI for either frontend product.

**Bottom line**: The Python agent core works for end-to-end task execution, but the project has accumulated technical debt in tests, removed modules, and unfinished IPC plumbing. The desktop app and VS Code extension are functional UIs with broken backend bridges.

---

## Subsystem Status Table

| Subsystem | Status | Evidence | Confidence |
|:---|:---|:---|:---|
| Python core agent (`HcodeAgent`) | ✅ WORKING | Imports cleanly, 1935L, orchestrates PEV | HIGH |
| Agent orchestrator | ✅ WORKING | `AgentOrchestrator` imports cleanly | HIGH |
| Planning phase handler | ✅ WORKING | `PlanningPhaseHandler` 772L, generates artifacts | MEDIUM |
| Execution phase handler | ✅ WORKING | `ExecutionPhaseHandler` 1595L, multi-round loop | MEDIUM |
| Verification phase handler | ✅ WORKING | `VerificationPhaseHandler` 1729L, 5-phase QA | MEDIUM |
| Tool system (`ToolManager`) | ✅ WORKING | Imports cleanly, 36+ tools registered | HIGH |
| File tools (Read/Write/Edit) | ⚠️ PARTIAL | Read/Write reliable; EditTool fragile (string-match) | HIGH |
| Provider layer (`ResilientProvider`) | ✅ WORKING | Imports cleanly, circuit breaker pattern | HIGH |
| Memory system (`MemoryManager`) | ✅ WORKING | Imports cleanly, 3-layer architecture | HIGH |
| Context manager | ✅ WORKING | `ContextManager` imports, SQLite-backed | HIGH |
| CLI (`main_cli.py`) | ✅ WORKING | 1579L, `hcode run`/`chat`/`analyze` | MEDIUM |
| Desktop app — React UI | ✅ WORKING | `tsc --noEmit` passes with 0 errors | HIGH |
| Desktop app — Tauri IPC | ❌ BROKEN | `DaemonSupervisor.send()` is stub (`eprintln!` only) | HIGH |
| Desktop app — Daemon bridge | ❌ BROKEN | `spawn_output_reader()` is simulation loop | HIGH |
| VS Code extension — Webview | ✅ WORKING | `tsc --noEmit` passes with 0 errors | HIGH |
| VS Code extension — Agent bridge | 🔍 UNVERIFIED | `hcodeBridge.ts` spawns `python -m hcode run --stream`, cannot verify without runtime | MEDIUM |
| Packaging (pyproject.toml) | ⚠️ PARTIAL | Package installs, but `pytest-cov` missing from deps | HIGH |
| Test suite — Sanity | ❌ BROKEN | **108 failed**, 115 passed, 2 skipped (out of 225) | HIGH |
| Test suite — Unit | ❌ BROKEN | **5 import errors** prevent collection | HIGH |
| CI/CD — Python | ⚠️ PARTIAL | `release.yml` exists but uses `--cov` without `pytest-cov` | HIGH |
| CI/CD — Desktop | ❌ BROKEN | No CI workflow exists | HIGH |
| CI/CD — VS Code Extension | ❌ BROKEN | No CI workflow exists | HIGH |

---

## Verified Evidence

### WORKING

1. **Core Python imports** — All 5 critical classes import without error:
   - `hcode.core.agent.HcodeAgent` ✅
   - `hcode.tools.core.tool_manager.ToolManager` ✅
   - `hcode.providers.resilient_provider.ResilientProvider` ✅
   - `hcode.memory.memory_manager.MemoryManager` ✅
   - `hcode.core.orchestration.agent_orchestrator.AgentOrchestrator` ✅
   - **Verified by**: `python -c "from hcode.core.agent import HcodeAgent; ..."` — exit 0

2. **Desktop app TypeScript** — Compiles with zero errors:
   - **Verified by**: `npx tsc --noEmit` in `desktop-app/src-ui/` — exit 0

3. **VS Code extension TypeScript** — Compiles with zero errors:
   - **Verified by**: `npx tsc --noEmit` in `vscode-extension/` — exit 0

4. **CLI entry point** — Package metadata tests pass:
   - `test_package_has_version` ✅
   - `test_package_name` ✅
   - `test_module_help` ✅
   - `test_module_version` ✅

### PARTIAL

5. **Test configuration**: `pyproject.toml` includes `--cov=src/hcode` in addopts but `pytest-cov` is not installed. Running `python -m pytest` without `addopts` override fails immediately.
   - **Verified by**: `python -c "import pytest_cov"` → `ModuleNotFoundError`

### BROKEN

6. **Sanity test suite**: 108/225 failures. Root causes:
   - `AIProvider` export name changed — tests import old name from `hcode.providers.base`
   - `hcode.utils.project_analyzer` module deleted — tests still reference it
   - `hcode.cli_enhanced` module deleted — tests still reference it
   - Animation/progress imports broken — `hcode.ui.animations` API changed
   - `hcode_path` fixture/utility missing
   - **Verified by**: `python -m pytest -o "addopts=" tests/sanity -v --tb=line` → 108 failed

7. **Unit test suite**: 5 import errors prevent all collection:
   - `hcode.ui.todo_display` import failure
   - `hcode.tools.core.tool_callbacks` import failure
   - **Verified by**: `python -m pytest -o "addopts=" tests/unit -v --tb=line` → 5 errors

8. **DaemonSupervisor.send()** (desktop-app/src-tauri/src/daemon.rs line 116):
   ```rust
   // The actual stdin write happens here as a proof of concept.
   eprintln!("[DaemonSupervisor] Would send: {}", message);
   Ok(())
   ```
   This is a **no-op stub**. No data reaches the Python daemon.

9. **spawn_output_reader()** (daemon.rs lines 167-176):
   ```rust
   std::thread::spawn(move || {
       loop {
           std::thread::sleep(std::time::Duration::from_secs(5));
           let _ = app.emit("daemon-status", ...);
       }
   });
   ```
   This is a **simulation**. It does not read from the child process stdout.

### UNVERIFIED

10. **VS Code bridge** (`hcodeBridge.ts`): Spawns `python -m hcode run --stream --output-format=jsonl`. Cannot verify without VS Code runtime. The `--stream` and `--output-format=jsonl` flags may or may not be implemented in `main_cli.py`.

11. **Agent end-to-end task execution**: Requires API keys for Anthropic/OpenAI. Not verifiable without live LLM access.

12. **Semantic memory embedding quality**: `semantic_memory.py` uses local embeddings but accuracy/recall is untested.
