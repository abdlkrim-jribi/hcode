# Tool Calling Guide

This document provides comprehensive documentation for all Hcode agent tools, including usage examples, best practices, and troubleshooting tips.

## Tool Call Format

All tool calls use JSON format:

```json
{"tool": "ToolName", "parameters": {"ParameterName": "value"}}
```

**Parameter Naming Convention:**
- **Primary parameters**: PascalCase (e.g., `DirectoryPath`, `CommandLine`, `TargetFile`)
- **Legacy aliases**: snake_case (e.g., `path`, `command`, `file_path`)

Both formats are accepted, but prefer PascalCase for consistency.

---

## File Operations Tools

### Read

View file contents with optional line range selection.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `AbsolutePath` | string | Yes | Absolute path to file |
| `StartLine` | integer | No | Starting line (1-indexed) |
| `EndLine` | integer | No | Ending line (inclusive) |

**Example:**
```json
{"tool": "Read", "parameters": {"AbsolutePath": "D:/project/src/main.py"}}
```

**With line range:**
```json
{"tool": "Read", "parameters": {"AbsolutePath": "D:/project/src/main.py", "StartLine": 50, "EndLine": 100}}
```

---

## CRITICAL: Anti-Hallucination Rules

> [!CAUTION]
> **YOU MUST NEVER SHOW CODE BLOCKS WITHOUT USING A TOOL**
>
> These rules are MANDATORY and violations will cause task failure.

### Rule 1: ALWAYS Use Tools for Code

When you want to show, create, or modify code:

| Intent | CORRECT Action | WRONG Action |
|--------|----------------|--------------|
| Show existing code | Use `Read` tool first, then reference it | Pasting code in markdown |
| Create new file | Use `Write` tool | Showing code in ``` block |
| Modify file | Use `Edit` tool | Showing "before/after" code |
| Explain code | Use `Read` first, then summarize | Reproducing file content |

### Rule 2: Explanatory Responses

When explaining or answering questions about code:

✅ **CORRECT**: "The file contains 143 lines. It defines a `main()` function that..."
❌ **WRONG**: "Here is the code: ```python def main(): ...```"

If user asks "show me" or "count lines":
1. First use `Read` tool to read the file
2. Then summarize what you found in plain text
3. Do NOT reproduce the file content in markdown code blocks

### Rule 3: When Code Blocks ARE Allowed

You MAY use code blocks ONLY for:
- Terminal commands to run: `python script.py`
- Configuration examples the user needs to copy
- Error messages you are explaining
- Short snippets (< 5 lines) as examples AFTER using Read tool

### Rule 4: Self-Check Before Responding

Before completing your response, verify:
- [ ] Did I use a tool for every file operation?
- [ ] Am I showing code that should be in a file? → Use Write/Edit
- [ ] Am I quoting a file's content? → Did I use Read first?

---

### Write

Create or overwrite files with content validation.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `TargetFile` | string | Yes | Absolute path to file |
| `CodeContent` | string | Yes | Content to write |
| `mode` | string | No | "overwrite" (default) or "append" |

**Example:**
```json
{"tool": "Write", "parameters": {"TargetFile": "D:/project/config.json", "CodeContent": "{\"version\": \"1.0\"}"}}
```

> [!TIP]
> Write validates content before saving and detects potential truncation issues.

---

### Edit

Replace exact string matches in files with fuzzy matching fallback.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `TargetFile` | string | Yes | Absolute path to file |
| `TargetContent` | string | Yes | Exact string to find |
| `ReplacementContent` | string | Yes | Replacement string |
| `replace_all` | boolean | No | Replace all occurrences |

**Example:**
```json
{"tool": "Edit", "parameters": {
  "TargetFile": "D:/project/src/config.py",
  "TargetContent": "DEBUG = False",
  "ReplacementContent": "DEBUG = True"
}}
```

> [!IMPORTANT]
> `TargetContent` must match exactly (including whitespace). If ambiguous matches exist, provide more context or use `replace_all`.

---

### MultiEdit

Apply multiple sequential edits to a single file efficiently.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_path` | string | Yes | Absolute path to file |
| `edits` | array | Yes | Array of edit objects |

**Example:**
```json
{"tool": "MultiEdit", "parameters": {
  "file_path": "D:/project/src/utils.py",
  "edits": [
    {"old_string": "import os", "new_string": "import os\nimport sys"},
    {"old_string": "def old_func():", "new_string": "def new_func():"}
  ]
}}
```

> [!TIP]
> Use MultiEdit for multiple non-contiguous changes to the same file. It's more efficient than multiple Edit calls.

---

### LS

List directory contents with optional filtering.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `DirectoryPath` | string | Yes | Absolute path to directory |
| `ignore` | string | No | Comma-separated glob patterns to exclude |

**Example:**
```json
{"tool": "LS", "parameters": {"DirectoryPath": "."}}
```

**With filtering:**
```json
{"tool": "LS", "parameters": {"DirectoryPath": "D:/project", "ignore": "*.pyc,__pycache__"}}
```

> [!WARNING]
> Always use `DirectoryPath` (not `path`) to avoid parameter errors. The tool auto-normalizes `.` to the current working directory.

---

### Glob

Find files matching glob patterns.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `Pattern` | string | Yes | Glob pattern (e.g., `**/*.py`) |
| `SearchDirectory` | string | No | Directory to search in |

**Example:**
```json
{"tool": "Glob", "parameters": {"Pattern": "**/*.py"}}
```

**Search specific directory:**
```json
{"tool": "Glob", "parameters": {"Pattern": "*.yaml", "SearchDirectory": "D:/project/config"}}
```

---

### Grep

Search for patterns in files using regex.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `Query` | string | Yes | Search pattern (regex) |
| `SearchPath` | string | Yes | File or directory to search |
| `Includes` | array | No | Glob patterns to filter files |
| `MatchPerLine` | boolean | No | Show each matching line |
| `case_insensitive` | boolean | No | Case-insensitive search |

**Example:**
```json
{"tool": "Grep", "parameters": {"Query": "def main", "SearchPath": "D:/project/src"}}
```

**With file filtering:**
```json
{"tool": "Grep", "parameters": {
  "Query": "TODO",
  "SearchPath": "D:/project",
  "Includes": ["*.py"],
  "MatchPerLine": true
}}
```

---

## Execution Tools

### Bash

Execute shell commands with timeout support.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `CommandLine` | string | Yes | Command to execute |
| `description` | string | No | Brief description (5-10 words) |
| `timeout` | number | No | Timeout in ms (default: 120000, max: 600000) |
| `run_in_background` | boolean | No | Run in background |

**Example:**
```json
{"tool": "Bash", "parameters": {"CommandLine": "python -m pytest tests/test_main.py", "description": "Run main tests"}}
```

**Background execution:**
```json
{"tool": "Bash", "parameters": {
  "CommandLine": "npm run dev",
  "run_in_background": true,
  "description": "Start dev server"
}}
```

> [!CAUTION]
> Commands require user approval before execution. Avoid running lengthy test suites unless specifically requested.

---

### BashOutput

Retrieve output from background shells.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `bash_id` | string | Yes | Background shell ID |
| `filter` | string | No | Regex to filter output lines |
| `tail` | number | No | Return last N lines |

**Example:**
```json
{"tool": "BashOutput", "parameters": {"bash_id": "shell_abc123"}}
```

---

### KillShell

Terminate a running background shell.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `shell_id` | string | Yes | Background shell ID |

**Example:**
```json
{"tool": "KillShell", "parameters": {"shell_id": "shell_abc123"}}
```

---

### SearchOutput

Search within the last command's output for specific patterns.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `pattern` | string | Yes | Search pattern (regex) |
| `context_lines` | number | No | Lines before/after match (default: 2) |
| `case_sensitive` | boolean | No | Case-sensitive search (default: false) |

**Example:**
```json
{"tool": "SearchOutput", "parameters": {"pattern": "TOTAL", "context_lines": 3}}
```

> [!TIP]
> Use this when command output is truncated and you need to find specific information like test coverage totals.

---

## Planning & Task Management Tools

### Task

Launch specialized sub-agents for complex tasks.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `subagent_type` | string | Yes | Agent type: `general-purpose`, `Explore`, `Plan`, `Implement` |
| `prompt` | string | Yes | Detailed task instructions |
| `description` | string | Yes | Short description (3-5 words) |
| `model` | string | No | Model override: `sonnet`, `opus`, `haiku` |

**Example:**
```json
{"tool": "Task", "parameters": {
  "subagent_type": "Explore",
  "prompt": "Find all Python files that import the requests library and list their dependencies",
  "description": "Explore request dependencies"
}}
```

---

### TodoWrite

Update the task list and sync to `.hcode/task.md`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `todos` | array | Yes | Array of todo objects with `content`, `status`, `activeForm` |

**Status values:** `pending`, `in_progress`, `completed`, `blocked`, `skipped`

**Example:**
```json
{"tool": "TodoWrite", "parameters": {
  "todos": [
    {"content": "Analyze existing code", "status": "completed"},
    {"content": "Implement new feature", "status": "in_progress", "activeForm": "Implementing feature"},
    {"content": "Write tests", "status": "pending"}
  ]
}}
```

---

### TodoRead

Read the current task list from `.hcode/task.md`.

No parameters required.

**Example:**
```json
{"tool": "TodoRead", "parameters": {}}
```

---

### ExitPlanMode

Exit planning mode and present the implementation plan.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan` | string | Yes | The implementation plan (markdown) |

> [!NOTE]
> Only use this for tasks requiring code implementation, not for research or exploration tasks.

---

## Web Tools

### WebFetch

Fetch URL content and convert to markdown.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `Url` | string | Yes | URL to fetch |
| `Prompt` | string | No | Focus query for content extraction |

**Example:**
```json
{"tool": "WebFetch", "parameters": {"Url": "https://docs.python.org/3/library/asyncio.html"}}
```

---

### WebSearch

Search the web and return results.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `Query` | string | Yes | Search query |
| `NumResults` | integer | No | Number of results (default: 5) |
| `AllowedDomains` | array | No | Domains to include |
| `BlockedDomains` | array | No | Domains to exclude |

**Example:**
```json
{"tool": "WebSearch", "parameters": {"Query": "Python asyncio best practices", "NumResults": 10}}
```

---

## Interactive Tools

### AskUserQuestion

Prompt the user with questions.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `questions` | array | Yes | Array of question objects |

**Example:**
```json
{"tool": "AskUserQuestion", "parameters": {
  "questions": [
    {"question": "Which testing framework do you prefer?", "options": [
      {"label": "pytest", "value": "pytest"},
      {"label": "unittest", "value": "unittest"}
    ]}
  ]
}}
```

---

## Best Practices

### Efficiency Rules

1. **Batch File Edits**: Use `MultiEdit` for multiple changes to the same file
2. **Targeted Testing**: Run specific tests first (`pytest path/to/test.py`), not full suite
3. **Read Before Edit**: Always read the file section you're editing to ensure accuracy
4. **Use Glob for Discovery**: Find files before reading/editing them

### Common Patterns

**Exploration Workflow:**
```
1. LS → Get directory structure
2. Glob → Find relevant files
3. Grep → Search for patterns
4. Read → Examine specific files
```

**Implementation Workflow:**
```
1. Read → Understand current code
2. Edit/MultiEdit → Make changes
3. Bash → Run targeted tests
4. Read → Verify changes
```

### Anti-Patterns to Avoid

- ❌ Running full test suite without user request
- ❌ Making multiple sequential Edit calls to the same file (use MultiEdit)
- ❌ Using `path` instead of `DirectoryPath` for LS tool
- ❌ Editing without first reading the file

---

## Troubleshooting

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Missing required parameter: DirectoryPath` | Using `path` instead of `DirectoryPath` | Use `DirectoryPath` for LS tool |
| `String not found in file` | Target content doesn't match exactly | Read file first, copy exact content |
| `String appears N times` | Ambiguous match | Provide more context or use `replace_all` |
| `Command timed out` | Command exceeded timeout | Increase `timeout` parameter |

### Parameter Normalization

The agent automatically normalizes:
- `/` → `.` (current directory) on Windows
- `path` → `DirectoryPath` for LS tool
- `command` → `CommandLine` for Bash tool
- `file_path` → `AbsolutePath`/`TargetFile` for file tools
