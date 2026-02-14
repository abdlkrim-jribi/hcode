# Hcode Skills System

The Skills system in Hcode allows you to define reusable prompt templates that the agent can use to perform specific tasks. Skills are essentially instructions packaged with metadata, allowing the agent to "learn" new capabilities without modifying code.

## Directory Structure

Skills are stored in the `.hcode/skills` directory in your project root.

```
project_root/
  .hcode/
    skills/
      hello.md
      refactor.md
      summarize.md
```

## Skill File Format

Each skill is a Markdown file (`.md`) consisting of:
1.  **YAML Frontmatter**: Metadata about the skill.
2.  **Prompt Template**: The actual instructions passed to the AI.

### Example: `hello.md`

```markdown
---
description: A friendly greeting skill
category: communication
---
Hello {name}, welcome to Hcode skills!
```

### Frontmatter Fields

- `description`: A brief explanation of what the skill does.
- `category`: (Optional) logical grouping for the skill (e.g., `coding`, `analysis`, `communication`).

### Prompt Template

The content after the frontmatter is the prompt. You can use placeholders like `{variable_name}` which will be replaced by values provided when the skill is executed.

## How It Works

1.  **Loading**: On startup, Hcode scans `.hcode/skills` and registers all valid `.md` files as skills.
2.  **Execution**: The agent has access to a `SkillTool`. When the agent decides to use a skill (based on your request), it calls this tool with the skill name and required context variables.
3.  **Expansion**: The system replaces placeholders in the prompt with the provided context and sends the result to the LLM or executes the defined logic.

## Usage

To use a skill, simply ask the agent to perform the task described by the skill. For example, if you have a `summarize` skill, you can say:

> "Use the summarize skill on this file."

The agent will recognize the `summarize` skill, extract the necessary context (the file), and execute the skill.
