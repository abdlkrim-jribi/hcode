# HCode Project Overview

## 1. Executive Summary
**HCode** is an intelligent, high-performance AI coding agent designed for the terminal. It provides a comprehensive suite of tools for software development, including filesystem manipulation, shell command execution, codebase exploration, and web search. HCode is built with a focus on reliability, transparency (via thinking blocks), and a structured workflow called PEV (Planning, Execution, Verification).

## 2. Technical Architecture

### 2.1 Core Orchestration (`src/hcode/core/`)
The `HcodeAgent` is the central hub of the system. It coordinates between LLM providers, tools, and the workflow state.
- **PEV Workflow (SOLID)**: A modern, structured approach to task execution:
  - **Planning**: Generates `task.md` and `implementation_plan.md`.
  - **Execution**: Performs actual code changes using tools.
  - **Verification**: Runs tests and generates a `walkthrough.md`.
- **Loop Controller**: Manages agent iterations, detects loops, and prevents runaway executions.
- **Response Processing**: Features advanced parsing of `<thinking>` blocks to provide transparency into the AI's reasoning.

### 2.2 Providers (`src/hcode/providers/`)
HCode supports multiple AI providers with a sophisticated **Resilient Provider** system:
- **Anthropic Claude**: Primary provider (e.g., Claude 3.5 Sonnet).
- **OpenAI GPT**: Secondary provider (e.g., GPT-4o).
- **Failover Logic**: Automatic hot-swapping between providers if one encounters rate limits or API errors, using a circuit-breaker pattern.

### 2.3 Tools System (`src/hcode/tools/`)
A robust set of over 20+ tools categorized by function:
- **Filesystem**: `Read`, `Write`, `Edit`, `Glob`, `Grep`, `LS`.
- **Terminal**: `Bash` (with persistent sessions), `KillShell`.
- **Workflow**: `TaskBoundary`, `TodoWrite`, `TodoRead`.
- **Web**: `WebFetch`, `WebSearch`, `WebScrape`.
- **Interactive**: `AskUserQuestion`, `NotifyUser`.
- **Advanced**: Jupyter Notebook support (`NotebookRead`, `NotebookEdit`).

### 2.4 Three-Layer Memory (`src/hcode/memory/`)
A sophisticated state management system:
1. **Layer 1 (File Memory)**: Reads project-level context from `AGENT.md` or `.hcode/hcode.md`.
2. **Layer 2 (Session Memory)**: Persists conversation history with smart summarization/compaction.
3. **Layer 3 (Semantic Memory)**: Uses vector-like retrieval (via SQLite and local embeddings) to recall relevant facts and code patterns across sessions.

### 2.5 Skills & Slash Commands
- **Skills**: Markdown-based prompt templates in `.hcode/skills` that allow the agent to learn new reusable capabilities without code changes.
- **Slash Commands**: Interactive CLI commands (e.g., `/help`, `/stats`, `/init`, `/debug`) for controlling the agent.

## 3. UI/UX (`src/hcode/ui/`)
HCode features a beautiful, highly informative terminal interface:
- **Themed Panels**: Support for themes like Cyberpunk, Neon, Matrix, and Frost.
- **Live Todo Bar**: A persistent progress bar that updates in real-time as tasks are completed.
- **Thinking Animations**: Visual indicators of the model's "thought" process.
- **Syntax Highlighting**: Rich formatting for code blocks and diff previews.

## 4. Project Structure
```text
.
├── config/             # YAML configurations (tools, prompts)
├── docs/               # Technical documentation
├── scripts/            # Utility scripts (e.g., installation)
├── src/hcode/
│   ├── agents/         # Specialized sub-agents (Explore, Plan, Implement)
│   ├── cli/            # CLI-specific logic (autocomplete, tool display)
│   ├── core/           # Core agent logic, protocols, and PEV workflow
│   ├── memory/         # Three-layer memory system
│   ├── providers/      # LLM provider implementations
│   ├── tools/          # Tool definitions and execution logic
│   ├── ui/             # Rich UI components and themes
│   └── utils/          # Shared utilities (config loading, logging)
└── setup.py            # Package installation
```

## 5. Usage & Configuration
- **CLI Commands**:
  - `hcode run "task"`: Execute a one-off task.
  - `hcode chat`: Start an interactive multi-turn session.
  - `hcode analyze .`: Perform codebase analysis.
  - `hcode explore "query"`: Semantic codebase search.
- **Environment Variables**:
  - `ANTHROPIC_API_KEY`: Required for Claude models.
  - `OPENAI_API_KEY`: Required for GPT models.
  - `HCODE_LLM_PROVIDER`: Force a specific provider.

## 6. Observations & Recommendations

### Improvements
- **Dead Code Cleanup**: The project contains a significant amount of unreferenced code (approx. 66% according to `dead_code_report.json`). A thorough refactoring to remove obsolete legacy components is recommended.
- **SOLID Migration**: The system is currently in transition between legacy "Sub-agents" and the new "PEV Workflow" handlers. Fully migrating to the phase-based architecture would improve maintainability.
- **Thinking Parsing**: Consolidation of thinking block parsing logic across `agent.py` and `base_handler.py` would reduce duplication.

### Potential Issues
- **Context Pollution**: While there is logic to clear context for new tasks, very long sessions might still hit context window limits despite the compaction logic.
- **Tool Parameter Inconsistencies**: Some tools use `arguments` while others use `parameters` in their JSON schemas; the adapter handles this, but standardization at the source would be cleaner.

---
*Overview generated by Jules, AI Engineer.*
