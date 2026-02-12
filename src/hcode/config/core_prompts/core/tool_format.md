# Hcode Tool Call Format

**CRITICAL**: This document is the SINGLE SOURCE OF TRUTH for all tool parameter names.
All other prompt files MUST reference these exact parameter names.

## JSON Tool Call Format

When using tools, output JSON in a fenced code block with this EXACT format:

```json
{"tool": "ToolName", "arguments": {"param1": "value1", "param2": "value2"}}
```

## Canonical Parameter Reference

This table defines the ONLY valid parameter names for each tool:

| Tool | Required Parameters | Optional Parameters | Notes |
|------|---------------------|---------------------|-------|
| Read | `file_path` (string) | `start_line` (int), `end_line` (int) | Read file contents |
| Write | `file_path` (string), `content` (string) | none | Create or overwrite file |
| Edit | `file_path` (string), `old_string` (string), `new_string` (string) | `replace_all` (bool) | Replace text in file |
| Glob | `pattern` (string) | `path` (string) | Find files by pattern |
| Grep | `pattern` (string) | `path` (string), `glob` (string), `output_mode` (string) | Search file contents |
| Bash | `command` (string) | `timeout` (int), `description` (string), `run_in_background` (bool) | Run shell command |
| LS | `path` (string) | `ignore` (string) | List directory contents |

**IMPORTANT**: Use lowercase parameter names as specified above.
DO NOT use: `AbsolutePath`, `TargetFile`, `CommandLine`, `Pattern`, `Query` (uppercase variants).

## Tool Examples

### File Operations

**Read** - Read file contents
```json
{"tool": "Read", "arguments": {"file_path": "/full/path/to/file.py"}}
```

**Write** - Create or overwrite a file
```json
{"tool": "Write", "arguments": {"file_path": "/full/path/to/file.py", "content": "# Your code here\n"}}
```

**Edit** - Replace text in a file
```json
{"tool": "Edit", "arguments": {"file_path": "/path/to/file.py", "old_string": "old text to find", "new_string": "new text to use"}}
```

**LS** - List directory contents
```json
{"tool": "LS", "arguments": {"path": "."}}
```

### Search Operations

**Glob** - Find files by pattern
```json
{"tool": "Glob", "arguments": {"pattern": "**/*.py"}}
```

**Grep** - Search file contents
```json
{"tool": "Grep", "arguments": {"pattern": "search pattern", "path": "."}}
```

### Command Execution

**Bash** - Run shell command
```json
{"tool": "Bash", "arguments": {"command": "python script.py", "description": "Run the script"}}
```

## Response Format

Your response should include:
1. **Text explanation** - Describe what you're doing
2. **Tool calls** - JSON blocks for operations
3. **Summary** - Describe results

Example:
```
I'll create the script to count markdown files.

First, let me explore the project:

```json
{"tool": "LS", "arguments": {"path": "."}}
```

Good, I see the structure. Now creating the script:

```json
{"tool": "Write", "arguments": {"file_path": "count_md.py", "content": "import glob\n\ndef main():\n    files = glob.glob('**/*.md', recursive=True)\n    print(f'Found {len(files)} .md files')\n\nif __name__ == '__main__':\n    main()"}}
```

Done! The script has been created.
```

## Critical Rules

1. **Always include the "tool" key** - `{"tool": "Write", ...}` not just `{"file_path": ...}`
2. **Use "arguments", not "parameters"** - `"arguments": {...}` not `"parameters": {...}`
3. **Explain before and after** - Don't just output JSON silently
4. **Use lowercase parameter names** - Follow the canonical table above exactly
5. **Use absolute paths** - Full paths like `/home/user/project/file.py` when possible

## Parameter Aliases (Internal)

The system accepts these uppercase variants internally for backward compatibility, but you should ALWAYS use the lowercase canonical names:
- `AbsolutePath`, `TargetFile` → use `file_path`
- `CodeContent`, `Content` → use `content`
- `TargetContent` → use `old_string`
- `ReplacementContent`, `NewText` → use `new_string`
- `CommandLine` → use `command`
- `Pattern` (uppercase) → use `pattern` (lowercase)
- `Query` → use `pattern`
- `SearchPath`, `DirectoryPath` → use `path`
