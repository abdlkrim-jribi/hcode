# Readiness Map

## Production-Ready

These components could be deployed with minimal additional work:

| Component | Evidence | Risk |
|:---|:---|:---|
| **ResilientProvider** | Circuit breaker, failover, backoff — production patterns. Import verified. | LOW |
| **MemoryManager** | 3-layer architecture, AGENT.md persistence. Import verified. | LOW |
| **ReadTool / GrepTool / GlobTool** | Deterministic read operations, high reliability. | MINIMAL |
| **Git tools suite** | All 7 tools directly wrap `git` CLI. Well-isolated. | MINIMAL |
| **DiffPreviewTool** | Safety analysis, syntax checking, preview-only. | MINIMAL |
| **CLI core** | `hcode run` + `hcode chat` functional. Metadata tests pass. | LOW |
| **Design token system** | Clean, unified hsl(228) palette. Used in both frontends. | MINIMAL |

---

## Ready for Refactor

These work but need restructuring before they can scale or be maintained:

| Component | Issue | Suggested Refactor |
|:---|:---|:---|
| **HcodeAgent** (1935L) | God object handling 8+ responsibilities | Extract: `PromptBuilder`, `ResponseProcessor`, `TaskRouter`, `ContinuationManager` |
| **ExecutionPhaseHandler** (1595L) | Monolithic with embedded prompts | Extract prompt templates to YAML files |
| **VerificationPhaseHandler** (1729L) | Monolithic, duplicates tool extraction | Consolidate `_extract_tool_calls()` into shared `ToolCallExtractor` |
| **main_cli.py** (1579L) | Display + logic + state interleaved | Extract display layer from business logic |
| **Tool call parser** | 3-4 separate implementations across handlers | Create single `ToolCallExtractor` class |

---

## Ready for Prompt-Driven Improvement

These are well-defined tasks an AI engineer could implement with a clear prompt:

| Task | Why It Matters | Complexity |
|:---|:---|:---|
| **Fix EditTool → line-range** | Single highest-impact reliability improvement | MEDIUM |
| **Add tiktoken token counting** | Fixes context overflow/underutilization | SMALL |
| **Implement DaemonSupervisor.send()** | Unblocks desktop app backend | SMALL |
| **Implement spawn_output_reader()** | Enables real daemon communication | MEDIUM |
| **Fix test suite imports** | Restores 108 broken tests | MEDIUM |
| **Install pytest-cov** | Unblocks CI test execution | SMALL |
| **Add streaming display** | Most visible UX improvement | MEDIUM |
| **Add command palette** | Key editor-grade feature | MEDIUM |
| **Upgrade VS Code diff to Monaco** | Consistency with desktop app | SMALL |
| **Auto-discover test commands** | Fixes verification phase limitations | SMALL |

---

## Blocked by External Dependency

| Component | Blocker | Impact |
|:---|:---|:---|
| **End-to-end agent test** | Requires live LLM API keys (Anthropic/OpenAI) | Cannot verify full PEV workflow without API access |
| **WebSearchTool** | Requires Brave/Google search API key | Web research capability untestable |
| **NotebookExecuteTool** | Requires Jupyter kernel | Notebook execution untestable |
| **VS Code extension runtime** | Requires VS Code Extension Development Host | Cannot verify activation flow outside VS Code |
| **Cargo build (Windows)** | Linker file lock issue in current environment | Transient — retry should work |

---

## Blocked by Architecture Issue

| Component | Architecture Blocker | Required Before Fix |
|:---|:---|:---|
| **Desktop app task execution** | `DaemonSupervisor.send()` is a stub | Must implement real stdin write to child process |
| **Multi-file transactional edits** | No edit set / rollback model | Requires new `EditTransaction` abstraction |
| **Dynamic replanning** | PEV workflow is fixed (plan once) | Requires new `ReplanDetector` + `PlanReviser` services |
| **AST-aware editing** | No tree-sitter integration | Requires new `SemanticEditTool` with language grammars |
| **Self-debugging loop** | Error feedback is unstructured | Requires new `ErrorAnalyzer` + repair strategy engine |
| **Shared design token build** | Two separate `tokens.css` copies | Requires shared token package or build step |
