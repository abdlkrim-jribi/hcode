# HCode — Universal AI Coding Assistant

> A production-ready AI coding agent that runs entirely in your terminal.  
> Supports **Anthropic Claude** and **OpenAI GPT** models for autonomous coding tasks.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Skills System](#skills-system)
  - [What Are Skills?](#what-are-skills)
  - [Available Skills](#available-skills)
  - [Skill Structure](#skill-structure)
  - [How to Use a Skill](#how-to-use-a-skill)
  - [How to Create a Skill](#how-to-create-a-skill)
- [Project Structure](#project-structure)
- [Contributing](#contributing)

---

## Overview

HCode is a terminal-based AI coding assistant built for developers who want autonomous, production-grade code assistance without leaving their shell. It connects to your preferred LLM provider (Anthropic or OpenAI) and can autonomously:

- Read, write, and edit files
- Run terminal commands
- Search the web
- Analyze code
- Execute Git operations
- Apply reusable **skills** (structured prompt strategies)

HCode is designed around a **Plan → Execute → Verify** agent loop with full memory, session management, and a rich terminal UI built on [Rich](https://github.com/Textualize/rich).

---

## Architecture

```
hcode/
├── src/hcode/
│   ├── agents/          # Sub-agent orchestration
│   ├── cli/             # CLI shell, autocomplete, display
│   ├── core/            # Main agent loop, phases, reasoning, safety
│   │   ├── agent.py     # Central HcodeAgent class
│   │   ├── phases/      # Plan / Execute / Verify phase logic
│   │   ├── reasoning/   # Chain-of-thought reasoning modules
│   │   ├── orchestration/
│   │   └── safety/      # Safety guards and validation
│   ├── memory/          # Embeddings, session, file, semantic memory
│   ├── providers/       # OpenAI + Anthropic adapters with resilient fallback
│   ├── tools/           # All tool categories (files, git, terminal, web, …)
│   └── ui/              # Terminal UI: panels, animations, themes, banners
└── .hcode/
    └── skills/          # Folder-based skills (see Skills System below)
```

**Key design decisions:**
- **Provider Resilience** — Automatic fallback between providers on failure (`resilient_provider.py`)
- **Phase-driven agent loop** — Each task goes through Plan → Execute → Verify before completion
- **Memory layers** — Separate session, file, semantic, and embedding-based memory
- **Folder-based skills** — Skills are self-contained folders, not just prompt files

---

## Installation

### Prerequisites

- Python 3.10+
- An API key for [Anthropic](https://www.anthropic.com/) or [OpenAI](https://platform.openai.com/)

### Steps

```bash
# Clone the repository
git clone https://github.com/abdlkrim-jribi/hcode.git
cd hcode

# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux / macOS

# Install in development mode
pip install -e .
```

---

## Configuration

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Choose your provider: "anthropic" or "openai"
HCODE_PROVIDER=anthropic

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# OpenAI (or OpenAI-compatible, e.g. Cerebras, Groq)
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1   # override for compatible endpoints
OPENAI_MODEL=gpt-4o
```

---

## Usage

```bash
# Run the interactive agent
hcode

# Or directly via the entry point
python hcode_cli.py
```

Inside the HCode shell you can type natural language tasks:

```
> Refactor the authentication module to use JWT tokens
> Use the systematic-debugging skill to investigate this test failure
> Write unit tests for src/hcode/memory/session_memory.py
```

---

## Skills System

### What Are Skills?

Skills are **reusable, structured prompt strategies** packaged as simple Markdown files.  
Instead of writing long instructions from scratch every time, you define a skill once and invoke it by name.

When you invoke a skill, HCode:
1. Loads the skill's `SKILL.md` content
2. Replaces any `{skill_dir}` placeholders with the absolute path to the skill's folder
3. Prepends the expanded content to the agent's context as a guiding instruction set

This allows skills to reference their own helper scripts, resources, and examples — making them fully self-contained.

---

### Available Skills

HCode ships with **19 built-in skills** covering the full software development lifecycle:

| Skill | Category | Description |
|---|---|---|
| `api-design-principles` | coding | REST/RPC API design guidelines and best practices |
| `architecture-decision-records` | documentation | Write structured ADRs for technical decisions |
| `async-python-patterns` | coding | Correct async/await usage patterns in Python |
| `clean-code` | coding | Apply clean code principles to any codebase |
| `code-review-excellence` | quality | Systematic, thorough code review methodology |
| `code-simplifier` | coding | Reduce complexity while preserving all functionality |
| `concise-planning` | planning | Produce clear, scoped implementation plans |
| `error-handling-patterns` | coding | Robust error handling strategies for Python |
| `find-bugs` | debugging | Structured approach to locating and classifying bugs |
| `git-advanced-workflows` | tooling | Advanced Git strategies (rebase, bisect, stash) |
| `legacy-modernizer` | refactoring | Safe, incremental modernization of legacy code |
| `postmortem-writing` | communication | Write blameless post-mortems after incidents |
| `production-code-audit` | quality | Full audit checklist for production readiness |
| `python-patterns` | coding | Idiomatic Python patterns and anti-patterns |
| `python-performance-optimization` | performance | Profile and optimize Python code |
| `python-testing-patterns` | testing | pytest patterns, fixtures, and test design |
| `systematic-debugging` | debugging | 4-phase root-cause-first debugging methodology |
| `tdd-workflow` | testing | Test-Driven Development cycle (Red → Green → Refactor) |
| `verification-before-completion` | quality | Checklist for verifying work before marking done |

---

### Skill Structure

Every skill lives in its own folder under `.hcode/skills/`:

```
.hcode/
└── skills/
    └── systematic-debugging/       ← skill folder
        ├── SKILL.md                ← required: the skill definition
        ├── scripts/                ← optional: helper scripts the agent can run
        ├── resources/              ← optional: data files, templates, references
        └── examples/               ← optional: usage examples
```

#### `SKILL.md` Format

```markdown
---
description: Brief one-line description shown in skill listings
category: coding | debugging | testing | quality | documentation | ...
---

# Skill Title

Your full skill instructions here.
Use Markdown freely — headers, lists, code blocks.

# Referencing skill resources
Scripts are at `{skill_dir}/scripts/`
Reference data is at `{skill_dir}/resources/`
```

The `{skill_dir}` placeholder is automatically replaced at runtime with the absolute path to the skill's folder, so scripts and resources are always reachable regardless of where you run HCode from.

---

### How to Use a Skill

Just ask the agent naturally:

```
> Use the systematic-debugging skill to investigate this test failure
> Apply the code-review-excellence skill to src/hcode/core/agent.py
> Run the tdd-workflow skill to add tests for the memory module
```

The agent will load the skill, internalize its methodology, and apply it to your request.

---

### How to Create a Skill

1. Create a folder under `.hcode/skills/` with your skill name (use kebab-case):

```bash
mkdir .hcode/skills/my-skill
mkdir .hcode/skills/my-skill/scripts
mkdir .hcode/skills/my-skill/resources
```

2. Create `.hcode/skills/my-skill/SKILL.md`:

```markdown
---
description: One-line description of what this skill does
category: coding
---

# My Skill

## Overview
Explain the goal and when to use this skill.

## Process
1. Step one
2. Step two
3. Step three

## Notes
Any helper scripts are at `{skill_dir}/scripts/`
```

3. Use it immediately — no restart needed:

```
> Use the my-skill skill to ...
```

---

## Project Structure

```
hcode/
├── .hcode/                    # HCode runtime data (gitignored in production)
│   └── skills/                # 19 built-in skills
├── config/                    # Default configuration files
├── docs/                      # Extended documentation
│   └── SKILLS.md              # Full skills system reference
├── examples/                  # Usage examples
├── scripts/                   # Dev/maintenance scripts
├── src/
│   └── hcode/
│       ├── agents/            # Sub-agent coordination
│       ├── cli/               # Shell interface and autocomplete
│       ├── config/            # Configuration loading and validation
│       ├── core/              # Agent loop, phases, reasoning, safety
│       ├── memory/            # Session, file, semantic, and embedding memory
│       ├── providers/         # LLM provider adapters (OpenAI, Anthropic)
│       ├── tools/             # Tool implementations (files, git, web, terminal…)
│       ├── ui/                # Terminal UI components (Rich-based)
│       └── utils/             # Shared utilities
├── tests/                     # Unit and integration tests
├── .env.example               # Environment variable template
├── pyproject.toml             # Package metadata and dependencies
├── requirements.txt           # Pinned dependencies
└── setup.py                   # Legacy setup (pyproject.toml is canonical)
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Branch naming conventions
- Code style (PEP 8, type hints, docstrings)
- How to add new skills
- Running the test suite

```bash
# Run all tests
pytest tests/

# Run only skill-related tests
pytest tests/unit/tools/test_folder_skills.py -v
```

---

## License

[MIT License](LICENSE) — © HCode Team