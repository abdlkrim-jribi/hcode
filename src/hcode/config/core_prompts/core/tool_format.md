# Hcode Tool Call Format

## JSON Tool Call Format

When using tools, output JSON in a fenced code block with this EXACT format:

```json
{"tool": "ToolName", "arguments": {"param1": "value1", "param2": "value2"}}
```

## Available Tools

### File Operations

**LS** - List directory contents
```json
{"tool": "LS", "arguments": {"DirectoryPath": "."}}
```

**Read** - Read file contents
```json
{"tool": "Read", "arguments": {"AbsolutePath": "/full/path/to/file.py"}}
```

**Write** - Create or overwrite a file
```json
{"tool": "Write", "arguments": {"TargetFile": "/full/path/to/file.py", "CodeContent": "# Your code here\n"}}
```

**Edit** - Replace text in a file
```json
{"tool": "Edit", "arguments": {"TargetFile": "/path/to/file.py", "TargetContent": "old text to find", "ReplacementContent": "new text to use"}}
```

### Search Operations

**Glob** - Find files by pattern
```json
{"tool": "Glob", "arguments": {"Pattern": "**/*.py"}}
```

**Grep** - Search file contents
```json
{"tool": "Grep", "arguments": {"Query": "search pattern", "SearchPath": "."}}
```

### Command Execution

**Bash** - Run shell command
```json
{"tool": "Bash", "arguments": {"CommandLine": "python script.py", "description": "Run the script"}}
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

{"tool": "LS", "arguments": {"DirectoryPath": "."}}

Good, I see the structure. Now creating the script:

{"tool": "Write", "arguments": {"TargetFile": "count_md.py", "CodeContent": "import glob\n\ndef main():\n    files = glob.glob('**/*.md', recursive=True)\n    print(f'Found {len(files)} .md files')\n\nif __name__ == '__main__':\n    main()"}}

Done! The script has been created.
```

## Critical Rules

1. **Always include the "tool" key** - `{"tool": "Write", ...}` not just `{"TargetFile": ...}`
2. **Use arguments, not parameters** - `"arguments": {...}` not `"parameters": {...}`
3. **Explain before and after** - Don't just output JSON silently
4. **Use absolute paths** - Full paths like `/home/user/project/file.py`
