# Subsystem Inventory

## 1. Core Agent

| Property | Value |
|:---|:---|
| **File** | `src/hcode/core/agent.py` |
| **Class** | `HcodeAgent` |
| **Lines** | 1935 |
| **Status** | ✅ WORKING |
| **Import test** | `from hcode.core.agent import HcodeAgent` succeeds |
| **Responsibilities** | Entry point, provider init, prompt construction, tool loop, mode routing, response processing, sub-agent coordination |
| **Known issues** | God object (1935L handles too many responsibilities). Duplicate logic with `AgentOrchestrator`. |

## 2. Orchestration

| Property | Value |
|:---|:---|
| **File** | `src/hcode/core/orchestration/agent_orchestrator.py` |
| **Class** | `AgentOrchestrator` |
| **Lines** | 404 |
| **Status** | ✅ WORKING |
| **Responsibility** | PEV workflow coordinator, phase delegation, checkpoint mgmt |
| **Known issues** | Dual control-plane with `HcodeAgent` |

## 3. Phase Handlers

| Handler | File | Lines | Status | Notes |
|:---|:---|:---|:---|:---|
| `PlanningPhaseHandler` | `core/phases/planning_handler.py` | 772 | ✅ WORKING | 5-phase reasoning protocol |
| `ExecutionPhaseHandler` | `core/phases/execution_handler.py` | 1595 | ✅ WORKING | 4-phase protocol, max 35 rounds |
| `VerificationPhaseHandler` | `core/phases/verification_handler.py` | 1729 | ✅ WORKING | 5-phase QA, walthrough generation |
| `FastHandler` | `core/phases/fast_handler.py` | ~200 | ✅ WORKING | Bypass planning |

## 4. Tool System

| Property | Value |
|:---|:---|
| **Registry** | `src/hcode/tools/core/tool_manager.py` (265L) |
| **Tool count** | 36+ registered |
| **Status** | ✅ WORKING (import verified) |
| **Executor** | `src/hcode/execution/tool_executor.py` (430L) |
| **Parser** | `src/hcode/core/tools/tool_call_parser.py` (284L) |
| **Known issues** | `EditTool` fragile; `FuzzyEditTool` has ambiguity risk; `tool_callbacks.py` has import error in unit tests |

## 5. Provider Layer

| Property | Value |
|:---|:---|
| **File** | `src/hcode/providers/resilient_provider.py` (647L) |
| **Status** | ✅ WORKING (import verified) |
| **Supported** | Anthropic (Claude), OpenAI (GPT/OSS) |
| **Features** | Circuit breaker, failover, exponential backoff, health stats |
| **Known issues** | Tests reference `AIProvider` but export name may have changed |

## 6. Memory System

| Property | Value |
|:---|:---|
| **File** | `src/hcode/memory/memory_manager.py` (454L) |
| **Status** | ✅ WORKING (import verified) |
| **Layers** | FileMemory (AGENT.md) → SessionMemory → SemanticMemory |
| **Known issues** | Token estimation uses `len/4` heuristic. Semantic memory untested. |

## 7. Context Manager

| Property | Value |
|:---|:---|
| **File** | `src/hcode/core/context/manager.py` (527L) |
| **Status** | ✅ WORKING (import verified) |
| **Backend** | SQLite |
| **Features** | Smart truncation, session export/import |

## 8. CLI

| Property | Value |
|:---|:---|
| **File** | `src/hcode/main_cli.py` (1579L) |
| **Status** | ✅ WORKING |
| **Commands** | `run`, `chat`, `analyze`, `explore`, `init`, `config` |
| **Evidence** | `test_module_help` and `test_module_version` pass |
| **Known issues** | Monolithic (1579L). `--stream` and `--output-format=jsonl` flags needed by VS Code bridge may not be implemented |

## 9. Desktop Application

| Component | Status | Evidence |
|:---|:---|:---|
| React UI | ✅ WORKING | `tsc --noEmit` passes, 0 errors |
| Tauri backend (main.rs) | ⚠️ PARTIAL | Compiles (with Cargo lock issues), 16 IPC handlers registered |
| DaemonSupervisor.send() | ❌ BROKEN | Stub — `eprintln!` only (line 116) |
| spawn_output_reader() | ❌ BROKEN | Simulation — hardcoded 5s loop (line 167) |
| IPC bridge (bridge.ts) | ✅ WORKING | Detects Tauri/browser, provides mock data in dev |
| Credential storage | ✅ WORKING | Uses `keyring` crate → Windows Credential Manager |
| File operations | ✅ WORKING | `list_directory`, `read_file`, `write_file` via Rust `std::fs` |

## 10. VS Code Extension

| Component | Status | Evidence |
|:---|:---|:---|
| TypeScript compilation | ✅ WORKING | `tsc --noEmit` passes, 0 errors |
| Extension activation | 🔍 UNVERIFIED | 4 commands + 2 sidebar providers registered |
| WebviewPanelManager | 🔍 UNVERIFIED | 3 panel types, message forwarding |
| HcodeBridge | 🔍 UNVERIFIED | Spawns `python -m hcode run --stream --output-format=jsonl` |
| SecretStorage | ✅ WORKING | Wraps vscode.SecretStorage API |
| GitIntegration | 🔍 UNVERIFIED | Depends on VS Code Git extension |

## 11. Packaging

| Property | Value |
|:---|:---|
| **File** | `pyproject.toml` (3977 bytes) |
| **Status** | ⚠️ PARTIAL |
| **Issue** | `pytest-cov` referenced in test config but not installed |
| **Build** | `pip install -e .` works (imports succeed) |

## 12. Tests

| Suite | Files | Status | Evidence |
|:---|:---|:---|:---|
| Sanity | 13 | ❌ BROKEN | 108 failed, 115 passed, 2 skipped |
| Unit | 17 | ❌ BROKEN | 5 import errors, collection failed |
| Integration | 9 | 🔍 UNVERIFIED | Not executed (would require API keys) |
| Desktop UI | 0 | ❌ MISSING | No tests exist |
| VS Code extension | 1 | 🔍 UNVERIFIED | E2E suite structure exists but untested |

## 13. CI/CD

| Workflow | Status | Evidence |
|:---|:---|:---|
| `release.yml` | ⚠️ PARTIAL | Exists but references `--cov` without `pytest-cov` installed |
| Desktop build CI | ❌ MISSING | No workflow file |
| VS Code extension CI | ❌ MISSING | No workflow file |
| Code signing | ❌ MISSING | No signing configuration |
