# HCode Skills System: Deep Dive

The **Skills** system in HCode is a powerful extensibility mechanism that allows the agent to acquire new, reusable capabilities through prompt engineering rather than code modifications. This document provides a technical deep dive into how skills are implemented, loaded, and executed.

## 1. Technical Architecture

### 1.1 Core Classes (`src/hcode/tools/system/command_system.py`)
- **`Skill`**: A domain object representing a single skill. It stores the skill's name, description, category, and the raw prompt template.
- **`CommandRegistry`**: The central repository for all skills. It is responsible for scanning the filesystem and instantiating `Skill` objects.
- **`SkillTool`**: A specialized `BaseTool` that the LLM can call. It acts as the bridge between the AI's intent and the skill's execution.

### 1.2 The Registry Lifecycle
1. **Initialization**: When `ToolManager` is created, it instantiates a `CommandRegistry`.
2. **Discovery**: The registry scans the `.hcode/skills/` directory (relative to the project root) for all `.md` files.
3. **Parsing**: For each file, the registry:
   - Reads the file content.
   - Parses the **YAML Frontmatter** (delimited by `---`) to extract `description` and `category`.
   - Treats the remainder of the file as the **Prompt Template**.
4. **Registration**: Valid skills are stored in a dictionary within the registry, keyed by their filename (stem).

## 2. Skill Definition Format
Skills are defined as Markdown files. The file stem becomes the skill name.

```markdown
---
description: Refactor a Python function for better readability
category: coding
---
Please refactor the following code to improve its readability and follow PEP 8 standards.
Focus on: {focus_areas}

Code:
{code}
```

### Placeholder Substitution
The system uses standard Python-style braces `{variable_name}` for placeholders.
- During execution, the `Skill.execute(context)` method performs string replacement.
- **Smart Context Handling**: If the context provided is a single string and the prompt only has one placeholder, HCode automatically maps the string to that placeholder.

## 3. Execution Flow
The execution of a skill typically involves the following steps:

1. **Detection**: The agent (LLM) decides to use a skill based on the user's request. It sees the list of available skills in its system prompt (injected via `SkillTool.get_description()`).
2. **Tool Call**: The agent calls `SkillTool` with the `skill` name and a `context` object containing values for the placeholders.
3. **Expansion**: `SkillTool` retrieves the `Skill` object from the registry and calls `skill.execute(context)`, producing a fully expanded prompt string.
4. **LLM Invocation**:
   - The `SkillTool` uses the `agent_orchestrator` to select a provider.
   - It sends the expanded prompt as a new user message to the LLM.
   - The result of this LLM call is returned as the `ToolResult` output.
5. **Observation**: The original agent receives the output of the skill as a tool observation and continues the conversation.

## 4. Integration with Core HCode
- **Dynamic Documentation**: The `SkillTool` dynamically appends all registered skills to its own description. This ensures the LLM always "knows" what skills are currently available in the project.
- **Project-Specific**: Skills are loaded from the `.hcode/` directory in the *current* project, allowing developers to define project-specific workflows (e.g., `/run-internal-tests` or `/generate-migration-script`) without touching the HCode source code.

## 5. Comparison: Skills vs. Slash Commands
| Feature | Skills | Slash Commands |
| :--- | :--- | :--- |
| **Storage** | `.hcode/skills/*.md` | `.hcode/commands/*.md` |
| **Invoked By** | AI (via `SkillTool`) | User (via `/command` in CLI) |
| **Arguments** | Keyed dictionary (JSON) | Positional string (`{args}`) |
| **Output** | Processed by AI | Processed by AI |

---
*Technical analysis by Jules, AI Engineer.*
