# Hcode Skills System

The Skills system in Hcode allows you to define reusable prompt templates that the agent can use to perform specific tasks. Skills are instructions packaged with metadata and optional auxiliary files, allowing the agent to "learn" new capabilities without modifying code.

## Directory Structure

Skills support two formats. **Folder-based** is preferred for skills that need helper files:

```
project_root/
  .hcode/
    skills/
      systematic-debugging/       ← Folder-based skill
        SKILL.md                  ← Required entry point
        scripts/                  ← Optional helper scripts
        resources/                ← Optional data files, templates
        examples/                 ← Optional usage examples
      hello.md                    ← Legacy flat-file skill (still works)
```

### Folder-Based Skills (Preferred)

Each skill lives in its own folder under `.hcode/skills/`. The folder **must** contain a `SKILL.md` file. Optional subdirectories:

| Directory | Purpose |
|-----------|---------|
| `scripts/` | Helper scripts the agent can execute |
| `resources/` | Data files, templates, reference material |
| `examples/` | Usage examples and sample inputs |

### Legacy Flat-File Skills

Simple skills can still be single `.md` files directly in `.hcode/skills/`. This is convenient for skills that are just a prompt template with no auxiliary files.

## SKILL.md Format

Every skill file (whether `SKILL.md` in a folder or a flat `.md` file) uses YAML frontmatter followed by the prompt template:

### Example: `systematic-debugging/SKILL.md`

```markdown
---
description: Debug code systematically using a structured step-by-step approach
category: coding
---

# Systematic Debugging

## Overview
Random fixes waste time and create new bugs...

Helper scripts are available at `{skill_dir}/scripts/` if needed.
```

### Frontmatter Fields

- `description` — Brief explanation of what the skill does (shown in skill listings).
- `category` — (Optional) Logical grouping (e.g., `coding`, `analysis`, `communication`).

### The `{skill_dir}` Placeholder

For folder-based skills, the `{skill_dir}` placeholder in the prompt is automatically replaced with the **absolute path** to the skill's folder. This allows the skill to reference its own scripts and resources:

```markdown
Use the helper script at `{skill_dir}/scripts/check.sh` to validate.
Reference data is at `{skill_dir}/resources/patterns.json`.
```

> **Note:** For legacy flat-file skills, `{skill_dir}` is left as-is (not substituted) since there is no folder.

## How It Works

1. **Loading** — On startup, Hcode scans `.hcode/skills/`:
   - **Phase 1:** Scans subdirectories for `SKILL.md` files (folder-based skills)
   - **Phase 2:** Scans top-level `.md` files (legacy flat-file skills)
   - If a folder and flat file share the same name, the folder-based skill takes priority.

2. **Execution** — The agent has access to a `SkillTool`. When it decides to use a skill, it calls this tool with the skill name and context variables.

3. **Expansion** — The system replaces `{skill_dir}` (for folder-based skills) and any context placeholders, then sends the result to the LLM.

## Usage

To use a skill, ask the agent to perform the task it describes. For example:

> "Use the systematic-debugging skill to investigate this test failure."

The agent will recognize the skill, provide context, and execute it. Folder-based skills will show a `[folder]` tag in the available skills listing.
