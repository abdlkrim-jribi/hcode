# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

HCode is an autonomous AI coding assistant CLI that supports both Anthropic Claude and OpenAI GPT providers. It executes coding tasks through a rich terminal UI with a comprehensive tool system, persistent memory, and safety guards.

## Development Setup

```bash
# Install with dev dependencies (uses setuptools, not Poetry despite CONTRIBUTING.md)
pip install -e ".[dev]"

# Copy and configure environment variables
cp .env.example .env
```

Required env vars: `ANTHROPIC_API_KEY` and/or `OPENAI_API_KEY`. Optional: `HCODE_PROVIDER` (auto/anthropic/openai), `OPENAI_MODEL`, `HCODE_OPTIMIZE_COST`.

## Commands

```bash
# Run all tests with coverage
pytest

# Run a single test file
pytest tests/unit/tools/test_folder_skills.py

# Run tests matching a pattern
pytest -k "test_execute_task"

# Format and lint
black src/ && isort src/
ruff check src/
mypy src/hcode/

# Run the CLI
hcode --help
python -m hcode
```

Pytest is configured in `pyproject.toml` with `asyncio_mode = "auto"` — all async tests work without explicit `@pytest.mark.asyncio`.

## Code Style

- Line length: 100 characters (black + ruff enforce this)
- Python 3.10+ required; use modern type hints
- Ruff rules: E, W, F, I, B, C4, UP (E501 and B008 ignored)

## Architecture

### Core Execution Flow

```
User input → ProviderSelector (picks best model/provider)
           → HcodeAgent (main orchestrator in core/agent.py)
               ├── AgentLoopController (phases: thinking → planning → executing)
               ├── ToolManager / ToolExecutor (validates + runs tool calls)
               ├── ContextManager (SQLite-backed conversation history)
               ├── LoopDetector + CircuitBreaker (prevents runaway execution)
               ├── SafetyGuard (backups before destructive changes)
               ├── ResponseParser (handles thinking blocks + tool calls)
               └── TodoManager (extracts todos from responses)
```

### Key Modules

| Module | Purpose |
|--------|---------|
| `src/hcode/core/agent.py` | Main `HcodeAgent` class — entry point for task execution |
| `src/hcode/providers/` | AI provider abstraction: `anthropic_provider.py`, `openai_provider.py`, `provider_selector.py`, `resilient_provider.py` |
| `src/hcode/tools/core/` | Tool registration (`tool_manager.py`) and execution (`executor.py`) |
| `src/hcode/tools/` | All tools grouped by category: `files/`, `git/`, `terminal/`, `web/`, `notebook/`, `system/`, `todo/` |
| `src/hcode/core/loop/` | `AgentLoopController` — manages execution phases |
| `src/hcode/core/context/` | `ContextManager` — SQLite-backed conversation persistence |
| `src/hcode/core/safety/` | Backup and transaction management before file modifications |
| `src/hcode/memory/` | Semantic memory and cross-session persistence |
| `src/hcode/ui/` | Rich terminal UI, theming, progress bars |
| `src/hcode/main_cli.py` | CLI entry point (largest file ~2000 LOC) |
| `config/tools.yaml` | Tool definitions and configurations |

### Tool System

Tools are registered in `ToolManager` and executed by `ToolExecutor`. To add a new tool:
1. Create a class in the appropriate `src/hcode/tools/<category>/` directory
2. Register it in `src/hcode/tools/core/tool_manager.py`

Tool categories: file ops (`ReadTool`, `WriteTool`, `EditTool`, `GlobTool`, `GrepTool`), git, terminal/bash, web, notebook, interactive UI, analysis, todo, slash commands/skills.

### Provider System

`ProviderSelector` chooses between Anthropic and OpenAI based on task complexity and cost optimization settings. `ResilientProvider` wraps providers with retry/fallback logic. To add a new provider, implement `AIProvider` base class from `providers/base.py` and register in `provider_selector.py`.

### Testing Structure

```
tests/
├── conftest.py          # Shared fixtures (temp_dir, mock providers)
├── sanity/              # Import and component sanity checks
├── integration/         # End-to-end tests (require API keys)
└── unit/                # Unit tests mirroring src/ structure
```

Integration tests require real API keys. Unit tests use mocks and fixtures from `conftest.py`.
