# Hcode - Universal AI Coding Assistant

**The most powerful AI coding assistant supporting both Anthropic Claude and OpenAI GPT with 100% Claude Code feature parity.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-0.1.0-green.svg)](https://github.com/yourusername/hcode)

---

## Table of Contents

- [What is Hcode?](#what-is-hcode)
- [Key Features](#key-features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Complete Feature Guide](#complete-feature-guide)
- [Usage Examples](#usage-examples)
- [CLI Commands Reference](#cli-commands-reference)
- [Configuration](#configuration)
- [Advanced Features](#advanced-features)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## What is Hcode?

Hcode is a **universal AI coding assistant** that combines the best of both worlds: **Anthropic's Claude** for complex reasoning and **OpenAI's GPT** for versatility. With **26+ comprehensive tools** and **100% feature parity with Claude Code**, Hcode provides everything you need for AI-assisted software development.

### Why Choose Hcode?

- **Dual AI Provider Support** - Use Claude OR GPT, switch seamlessly
- **100% Claude Code Parity** - All features from Claude Code extension
- **26+ Professional Tools** - File operations, bash execution, web capabilities, and more
- **Beautiful Terminal UI** - Rich formatting with progress indicators
- **Cross-Platform** - Works on Windows, macOS, and Linux
- **Open Source** - MIT licensed, fully customizable
- **Production Ready** - Enterprise-grade safety and backup system
- **Cost Optimized** - Intelligent provider routing to minimize costs

---

## Key Features

### AI Providers

| Provider | Models Supported | Best For |
|----------|------------------|----------|
| **Anthropic Claude** | claude-3-opus, claude-3-sonnet, claude-3-haiku | Complex reasoning, code analysis, architecture |
| **OpenAI GPT** | gpt-4, gpt-4-turbo, gpt-4o, gpt-3.5-turbo | Fast iteration, general tasks, code generation |
| **Cerebras** | llama3.1-8b, llama3.1-70b | Cost-effective, high-speed inference |
| **Azure OpenAI** | All Azure models | Enterprise deployments |
| **Local Models** | Ollama, LM Studio, vLLM | Privacy, offline usage |

### 26+ Comprehensive Tools

#### File Operations (7 tools)
- **Read** - Read files with line numbers, ranges, and offsets
- **Write** - Create new files with content
- **Edit** - Make precise string-based edits to existing files
- **MultiEdit** - Apply multiple edits to a file in one operation
- **Glob** - Find files using glob patterns (`**/*.py`)
- **Grep** - Search file contents with regex (ripgrep-style)
- **LS** - List directory contents with ignore patterns

#### Execution & Shell (4 tools)
- **Bash** - Execute shell commands with timeout and background support
- **BashOutput** - Retrieve output from background shell processes
- **KillShell** - Terminate background shell processes
- **NotebookExecute** - Execute Jupyter notebooks

#### Web Capabilities (3 tools)
- **WebSearch** - Search the web (Brave/Google integration)
- **WebFetch** - Fetch and process web content with AI
- **WebScrape** - Extract structured data from websites

#### Interactive Tools (6 tools)
- **AskUserQuestion** - Ask multi-choice questions with rich UI
- **Confirm** - Get user confirmations for critical operations
- **TodoWrite** - Create and manage task lists with progress tracking
- **TodoRead** - Read current task list state
- **DisplayPanel** - Show formatted information panels
- **Progress** - Display progress bars and spinners

#### Agent & Planning (2 tools)
- **Task** - Launch specialized sub-agents for complex tasks
- **ExitPlanMode** - Signal transition from planning to implementation

#### Notebook Tools (2 tools)
- **NotebookEdit** - Edit Jupyter notebook cells
- **NotebookRead** - Read notebooks with outputs and metadata

#### System Tools (2 tools)
- **SlashCommand** - Execute custom slash commands
- **Skill** - Run reusable skills from skills library

---

## Installation

### Prerequisites

- Python 3.8 or higher
- pip or Poetry package manager
- API key from Anthropic or OpenAI (or both)

### Method 1: Quick Install (Recommended)

**Linux/macOS:**
```bash
git clone https://github.com/yourusername/hcode.git
cd hcode
chmod +x quick_start.sh
./quick_start.sh
```

**Windows (PowerShell):**
```powershell
git clone https://github.com/yourusername/hcode.git
cd hcode
.\quick_start.ps1
```

The quick start scripts will:
- Check system prerequisites
- Install dependencies
- Set up configuration files
- Verify installation
- Run a test query

### Method 2: Manual Installation with pip

```bash
# Clone the repository
git clone https://github.com/yourusername/hcode.git
cd hcode

# Install in development mode
pip install -e .

# Verify installation
hcode --version
```

### Method 3: Using Poetry

```bash
# Clone repository
git clone https://github.com/yourusername/hcode.git
cd hcode

# Install Poetry if needed
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Activate virtual environment
poetry shell

# Verify installation
hcode --version
```

---

## Quick Start

### 1. Set Up API Keys

Create a `.env` file in your project directory:

```bash
# Anthropic Claude API
ANTHROPIC_API_KEY=sk-ant-your-key-here

# OpenAI GPT API
OPENAI_API_KEY=sk-your-key-here

# Optional: Custom OpenAI base URL (for Azure, Cerebras, local models)
OPENAI_BASE_URL=https://api.cerebras.ai/v1

# Optional: Set default provider
CODE_PROVIDER=auto  # Options: auto, anthropic, openai

# Optional: Cost optimization
HCODE_OPTIMIZE_COST=aggressive  # Options: balanced, aggressive
```

### 2. Test the Installation

```bash
# Simple test
hcode run "What is 2 + 2? Answer in one word."

# Test with specific provider
hcode run "What is Python?" --provider=openai --model=gpt-4o

# Test with Cerebras (cost-effective)
hcode run "Hello, how are you?" --provider=openai --model=llama3.1-8b
```

### 3. Start Using Hcode

```bash
# Interactive chat mode
hcode chat

# Execute a coding task
hcode run "Create a Python function to calculate fibonacci numbers"

# Analyze a codebase
hcode analyze src/

# Get help
hcode --help
```

---

## Complete Feature Guide

### File Operations

#### Reading Files

```bash
# Read entire file
hcode run "Read and summarize main.py"

# Read specific lines
hcode run "Show me lines 100-150 of main.py"

# Read multiple files
hcode run "Compare user.py and admin.py implementations"
```

**Programmatic Usage:**
```python
from hcode.tools import ReadTool

read_tool = ReadTool()
content = await read_tool.execute(
    file_path="/path/to/file.py",
    offset=100,  # Start at line 100
    limit=50     # Read 50 lines
)
```

#### Writing Files

```bash
# Create new file
hcode run "Create a config.yaml file with database settings"

# Generate code file
hcode run "Create a REST API endpoint for user authentication in api.py"
```

**Programmatic Usage:**
```python
from hcode.tools import WriteTool

write_tool = WriteTool()
await write_tool.execute(
    file_path="/path/to/new_file.py",
    content="def hello():\n    print('Hello, World!')"
)
```

#### Editing Files

```bash
# Make precise edits
hcode run "In main.py, replace 'localhost' with '0.0.0.0'"

# Refactor code
hcode run "Add type hints to all functions in utils.py"

# Fix bugs
hcode run "Fix the NullPointerException on line 42 in handler.py"
```

**Programmatic Usage:**
```python
from hcode.tools import EditTool

edit_tool = EditTool()
await edit_tool.execute(
    file_path="/path/to/file.py",
    old_string="def old_function():",
    new_string="def new_function():",
    replace_all=False  # Set True to replace all occurrences
)
```

#### Multiple Edits (MultiEdit)

```bash
# Make multiple changes at once
hcode run "In config.py: 1) Update version to 2.0, 2) Change port to 8080, 3) Enable debug mode"
```

**Programmatic Usage:**
```python
from hcode.tools import MultiEditTool

multi_edit = MultiEditTool()
await multi_edit.execute(
    file_path="/path/to/file.py",
    edits=[
        {"old_string": "VERSION = '1.0'", "new_string": "VERSION = '2.0'"},
        {"old_string": "PORT = 3000", "new_string": "PORT = 8080"},
        {"old_string": "DEBUG = False", "new_string": "DEBUG = True"}
    ]
)
```

#### Finding Files (Glob)

```bash
# Find Python files
hcode run "List all Python files in the project"

# Find test files
hcode run "Show me all test files in the tests directory"

# Find by pattern
hcode run "Find all React component files (*.tsx)"
```

**Programmatic Usage:**
```python
from hcode.tools import GlobTool

glob_tool = GlobTool()
files = await glob_tool.execute(
    pattern="**/*.py",  # Find all Python files
    path="/project/root"
)
```

#### Searching Code (Grep)

```bash
# Search for text
hcode run "Find all TODO comments in the codebase"

# Search with regex
hcode run "Find all API endpoints defined in the code"

# Search in specific files
hcode run "Search for 'database' in all Python files"
```

**Programmatic Usage:**
```python
from hcode.tools import GrepTool

grep_tool = GrepTool()
results = await grep_tool.execute(
    pattern="TODO|FIXME",  # Regex pattern
    path="/project/root",
    type="py",  # Search only Python files
    output_mode="content",  # Show matching lines
    head_limit=20  # Limit results
)
```

#### Listing Directories (LS)

```bash
# List directory contents
hcode run "What files are in the src directory?"

# List with filters
hcode run "Show Python files in src, excluding tests"
```

**Programmatic Usage:**
```python
from hcode.tools import LSTool

ls_tool = LSTool()
listing = await ls_tool.execute(
    path="/path/to/directory",
    ignore="*.pyc,__pycache__,*.egg-info"  # Ignore patterns
)
```

---

### Bash & Command Execution

#### Running Commands

```bash
# Execute simple command
hcode run "Run pytest on the test suite"

# Run with output
hcode run "Check git status and tell me what files changed"

# Build and test
hcode run "Build the project and run all tests"
```

**Programmatic Usage:**
```python
from hcode.tools import BashTool

bash_tool = BashTool()

# Simple command
result = await bash_tool.execute(
    command="ls -la",
    timeout=5000  # 5 seconds
)

# Background command
result = await bash_tool.execute(
    command="npm run dev",
    run_in_background=True
)
shell_id = result.shell_id  # Save for later
```

#### Background Processes

```bash
# Start server in background
hcode run "Start the development server in the background"

# Monitor background process
hcode run "Check the output of the dev server"

# Stop background process
hcode run "Stop the development server"
```

**Programmatic Usage:**
```python
from hcode.tools import BashTool, BashOutputTool, KillShellTool

# Start background process
bash = BashTool()
result = await bash.execute(
    command="python server.py",
    run_in_background=True
)
shell_id = result.shell_id

# Check output
output_tool = BashOutputTool()
output = await output_tool.execute(bash_id=shell_id)
print(output.stdout)

# Kill process
kill_tool = KillShellTool()
await kill_tool.execute(shell_id=shell_id)
```

---

### Web Capabilities

#### Web Search

```bash
# Search for information
hcode run "Search for 'Python asyncio best practices 2024' and summarize"

# Research topic
hcode run "Search for recent security vulnerabilities in Node.js"
```

**Programmatic Usage:**
```python
from hcode.tools import WebSearchTool

web_search = WebSearchTool()
results = await web_search.execute(
    query="Python asyncio tutorial",
    allowed_domains=["python.org", "realpython.com"],  # Optional
    blocked_domains=["spam.com"]  # Optional
)
```

#### Web Fetch

```bash
# Fetch and analyze webpage
hcode run "Fetch https://python.org and summarize the main features"

# Extract specific information
hcode run "Get the latest Python version from python.org"
```

**Programmatic Usage:**
```python
from hcode.tools import WebFetchTool

web_fetch = WebFetchTool()
content = await web_fetch.execute(
    url="https://docs.python.org/3/library/asyncio.html",
    prompt="Summarize key concepts of asyncio"
)
```

#### Web Scrape

```bash
# Scrape structured data
hcode run "Scrape product prices from example.com/products"

# Extract content
hcode run "Get all article titles from news.example.com"
```

**Programmatic Usage:**
```python
from hcode.tools import WebScrapeTool

scraper = WebScrapeTool()
data = await scraper.execute(
    url="https://example.com",
    selector=".product-price",  # CSS selector
    extract_type="text"  # or "html", "attr"
)
```

---

### Interactive Features

#### Asking Questions

```bash
# AI asks user for input during execution
hcode run "Create a new API endpoint (ask me for details)"
```

**Programmatic Usage:**
```python
from hcode.tools import AskUserQuestionTool

question_tool = AskUserQuestionTool()
answers = await question_tool.execute(
    questions=[
        {
            "question": "Which database do you want to use?",
            "header": "Database",
            "options": [
                {"label": "PostgreSQL", "description": "Robust SQL database"},
                {"label": "MongoDB", "description": "Flexible NoSQL database"},
                {"label": "Redis", "description": "In-memory data store"}
            ],
            "multiSelect": False
        }
    ]
)
```

#### Task Management (Todos)

```bash
# AI automatically creates and manages todos for complex tasks
hcode run "Implement user authentication system with JWT"
```

**Programmatic Usage:**
```python
from hcode.tools import TodoWriteTool, TodoReadTool

# Create todos
todo_write = TodoWriteTool()
await todo_write.execute(
    todos=[
        {"content": "Set up database", "status": "in_progress", "activeForm": "Setting up database"},
        {"content": "Create models", "status": "pending", "activeForm": "Creating models"},
        {"content": "Write tests", "status": "pending", "activeForm": "Writing tests"}
    ]
)

# Read current todos
todo_read = TodoReadTool()
current_todos = await todo_read.execute()
```

#### Confirmations

```bash
# AI asks for confirmation before destructive operations
hcode run "Delete all test files older than 30 days"
```

**Programmatic Usage:**
```python
from hcode.tools import ConfirmTool

confirm = ConfirmTool()
approved = await confirm.execute(
    message="This will delete 42 files. Continue?",
    default=False  # Default to No
)
```

---

### Jupyter Notebook Support

#### Reading Notebooks

```bash
# Read notebook
hcode run "Summarize what analysis.ipynb does"

# Check specific cells
hcode run "Show me the data processing code in notebook.ipynb"
```

**Programmatic Usage:**
```python
from hcode.tools import NotebookReadTool

notebook_read = NotebookReadTool()
content = await notebook_read.execute(
    notebook_path="/path/to/notebook.ipynb"
)
```

#### Editing Notebooks

```bash
# Edit notebook cell
hcode run "In analysis.ipynb, update cell 3 to use pandas 2.0 syntax"

# Add new cell
hcode run "Add a visualization cell after cell 5 in notebook.ipynb"
```

**Programmatic Usage:**
```python
from hcode.tools import NotebookEditTool

notebook_edit = NotebookEditTool()
await notebook_edit.execute(
    notebook_path="/path/to/notebook.ipynb",
    cell_id="cell-123",
    new_source="import pandas as pd\ndf = pd.read_csv('data.csv')",
    cell_type="code",
    edit_mode="replace"  # or "insert", "delete"
)
```

#### Executing Notebooks

```bash
# Run notebook
hcode run "Execute the data-analysis.ipynb notebook"

# Run and check results
hcode run "Run notebook.ipynb and tell me if there are any errors"
```

**Programmatic Usage:**
```python
from hcode.tools import NotebookExecuteTool

notebook_exec = NotebookExecuteTool()
result = await notebook_exec.execute(
    notebook_path="/path/to/notebook.ipynb",
    timeout=300  # 5 minutes
)
```

---

### Agent System & Sub-Agents

Hcode includes specialized sub-agents for complex tasks:

#### Task Agent

Launch specialized sub-agents for specific tasks:

```bash
# The AI automatically decides when to use sub-agents
hcode run "Analyze the entire codebase and create a comprehensive architecture document"
```

**Programmatic Usage:**
```python
from hcode.tools import TaskTool

task_tool = TaskTool()
result = await task_tool.execute(
    task="Explore the codebase and find all API endpoints",
    subagent_type="Explore",  # or "Plan", "general-purpose"
    thoroughness="medium"  # quick, medium, very thorough
)
```

#### Planning Mode

```bash
# Create implementation plan
hcode run "Plan how to add rate limiting to the API"

# AI creates detailed step-by-step plan, then asks to proceed
```

**Programmatic Usage:**
```python
from hcode.tools import ExitPlanModeTool

# AI uses this internally to signal plan completion
exit_plan = ExitPlanModeTool()
await exit_plan.execute(
    plan="1. Add rate limiting middleware\n2. Configure Redis\n3. Add tests"
)
```

---

## Usage Examples

### Example 1: Create a REST API

```bash
hcode run "Create a FastAPI REST API for a todo application with CRUD operations"
```

**What Hcode does:**
1. Creates project structure
2. Writes FastAPI code with routes
3. Adds models and schemas
4. Includes error handling
5. Generates tests
6. Creates requirements.txt

### Example 2: Debug and Fix Issue

```bash
hcode run "There's a TypeError on line 42 of handlers.py. Find and fix it."
```

**What Hcode does:**
1. Reads the file around line 42
2. Identifies the TypeError
3. Analyzes the root cause
4. Fixes the issue
5. Explains the fix

### Example 3: Refactor Code

```bash
hcode run "Refactor database.py to use async/await instead of callbacks"
```

**What Hcode does:**
1. Reads database.py
2. Identifies callback patterns
3. Converts to async/await
4. Updates function signatures
5. Updates all callers
6. Preserves functionality

### Example 4: Add Tests

```bash
hcode run "Add pytest tests for all functions in utils.py"
```

**What Hcode does:**
1. Reads utils.py
2. Identifies all functions
3. Creates test_utils.py
4. Writes comprehensive tests
5. Includes edge cases
6. Runs tests to verify

### Example 5: Code Review

```bash
hcode run "Review api.py for security vulnerabilities and best practices"
```

**What Hcode does:**
1. Reads api.py
2. Analyzes for security issues
3. Checks for best practices
4. Provides detailed feedback
5. Suggests improvements
6. Can apply fixes if requested

### Example 6: Documentation

```bash
hcode run "Add detailed docstrings to all functions in main.py"
```

**What Hcode does:**
1. Reads main.py
2. Analyzes each function
3. Adds comprehensive docstrings
4. Includes parameter descriptions
5. Adds return type documentation
6. Includes usage examples

### Example 7: Database Migration

```bash
hcode run "Create an Alembic migration to add email field to User model"
```

**What Hcode does:**
1. Reads current User model
2. Creates migration file
3. Adds upgrade() and downgrade()
4. Tests migration
5. Updates model documentation

### Example 8: Frontend Component

```bash
hcode run "Create a React component for user profile with avatar, name, and bio"
```

**What Hcode does:**
1. Creates component file
2. Writes TypeScript/JSX
3. Adds props interface
4. Includes styling
5. Adds PropTypes validation
6. Creates example usage

---

## CLI Commands Reference

### Basic Commands

#### `hcode run`
Execute a single task.

```bash
# Basic usage
hcode run "your task here"

# With options
hcode run "your task" --provider=openai --model=gpt-4o --complexity=complex

# Options:
#   --provider: auto, anthropic, openai, claude, gpt
#   --model: specific model name (e.g., claude-3-opus, gpt-4o)
#   --complexity: simple, moderate, complex
#   --cost: optimize for cost
#   --session: session ID to resume
#   --stream / --no-stream: enable/disable streaming
#   --agents / --no-agents: use sub-agents
```

#### `hcode chat`
Start interactive chat session.

```bash
# Basic chat
hcode chat

# With options
hcode chat --provider=anthropic --model=claude-3-opus

# In chat, use commands:
#   /help     - Show help
#   /clear    - Clear conversation
#   /tasks    - Show todo list
#   /exit     - Exit chat
```

#### `hcode analyze`
Analyze code files or directories.

```bash
# Analyze file
hcode analyze src/main.py

# Analyze directory
hcode analyze src/

# With complexity
hcode analyze src/ --complexity=complex
```

#### `hcode explore`
Explore codebase structure.

```bash
# Basic exploration
hcode explore

# With query
hcode explore "Find all database models"

# Options:
#   --thoroughness: quick, medium, very thorough
```

### Advanced Commands

#### `hcode --version`
Show version information.

```bash
hcode --version
```

#### `hcode --help`
Show help message.

```bash
hcode --help
hcode run --help
hcode chat --help
```

### Global Options

```bash
--provider       # AI provider (auto, anthropic, openai)
--model          # Specific model name
--complexity     # Task complexity (simple, moderate, complex)
--cost           # Enable cost optimization
--session        # Session ID
--stream         # Enable streaming (default: true)
--no-stream      # Disable streaming
--agents         # Enable sub-agents
--no-agents      # Disable sub-agents (default)
--debug          # Enable debug mode
```

---

## Configuration

### Environment Variables (.env)

Create `.env` file in your project root:

```bash
# API Keys
ANTHROPIC_API_KEY=sk-ant-your-key-here
OPENAI_API_KEY=sk-your-key-here

# Custom OpenAI Base URL (optional)
OPENAI_BASE_URL=https://api.cerebras.ai/v1

# Default Provider
CODE_PROVIDER=auto  # auto, anthropic, openai

# Cost Optimization
HCODE_OPTIMIZE_COST=balanced  # balanced, aggressive

# Model Preferences
ANTHROPIC_DEFAULT_MODEL=claude-3-sonnet
OPENAI_DEFAULT_MODEL=gpt-4o

# Temperature (creativity)
ANTHROPIC_TEMPERATURE=0.3
OPENAI_TEMPERATURE=0.3

# Max Tokens
ANTHROPIC_MAX_TOKENS=4000
OPENAI_MAX_TOKENS=4000
```

### Configuration File (.hcoderc)

Create `.hcoderc` YAML file in your project:

```yaml
# Provider Configuration
providers:
  anthropic:
    api_key_env: ANTHROPIC_API_KEY
    default_model: claude-3-5-sonnet-20241022
    max_tokens: 4000
    temperature: 0.3

  openai:
    api_key_env: OPENAI_API_KEY
    base_url_env: OPENAI_BASE_URL  # Optional
    default_model: gpt-4o
    max_tokens: 4000
    temperature: 0.3

# Preferences
preferences:
  primary_provider: auto  # auto, anthropic, openai
  fallback_enabled: true
  cost_optimization: balanced  # balanced, aggressive
  prefer_streaming: true
  max_cost_per_request: 1.0

# Tool Configuration
tools:
  linter: auto  # auto, pylint, eslint, etc.
  formatter: auto  # auto, black, prettier, etc.
  test_runner: auto  # auto, pytest, jest, etc.

# Safety Settings
safety:
  confirm_destructive: true
  auto_backup: true
  backup_retention_days: 7

# Custom Commands Directory
commands_dir: .hcode/commands

# Skills Directory
skills_dir: .hcode/skills
```

### Custom Commands

Create custom slash commands in `.hcode/commands/`:

**Example: `.hcode/commands/review-pr.md`**
```markdown
---
description: Review a pull request
---

Review pull request #{args} for:
- Code quality
- Security vulnerabilities
- Best practices
- Test coverage
- Documentation

Provide detailed feedback with specific recommendations.
```

**Usage:**
```bash
hcode /review-pr 123
```

### Custom Skills

Create reusable skills in `.hcode/skills/`:

**Example: `.hcode/skills/security-audit.md`**
```markdown
---
name: security-audit
description: Perform security audit
---

Perform comprehensive security audit:
1. Check for SQL injection vulnerabilities
2. Verify input validation
3. Check authentication/authorization
4. Review password handling
5. Check for XSS vulnerabilities
6. Verify CSRF protection
7. Review dependency vulnerabilities
8. Check for sensitive data exposure
```

---

## Advanced Features

### Multi-Provider Strategy

Hcode intelligently routes tasks to the best provider:

```python
from hcode.core import EnhancedHcodeAgent
from hcode.providers import TaskComplexity, TaskType

agent = EnhancedHcodeAgent(
    anthropic_key="your-key",
    openai_key="your-key"
)

# Simple task -> uses faster/cheaper model
result = await agent.execute_task(
    task="Add a comment to function",
    complexity=TaskComplexity.SIMPLE
)

# Complex task -> uses more powerful model
result = await agent.execute_task(
    task="Refactor entire authentication system",
    complexity=TaskComplexity.COMPLEX
)
```

### Cost Optimization

```python
# Enable aggressive cost optimization
agent = EnhancedHcodeAgent(
    anthropic_key="your-key",
    openai_key="your-key",
    cost_optimization="aggressive"
)

# Get cost statistics
stats = agent.get_session_stats()
print(f"Total cost: ${stats['total_cost']:.4f}")
print(f"Provider used: {stats['provider']}")
```

### Background Tasks

```python
from hcode.tools import BashTool

bash = BashTool()

# Start long-running process
result = await bash.execute(
    command="python train_model.py",
    run_in_background=True,
    timeout=3600000  # 1 hour
)

# Continue working on other tasks...

# Check progress later
from hcode.tools import BashOutputTool
output_tool = BashOutputTool()
output = await output_tool.execute(bash_id=result.shell_id)
print(output.stdout)
```

### Session Management

```python
# Create named session
agent = EnhancedHcodeAgent(
    anthropic_key="your-key",
    session_id="feature-auth"
)

# Work on task...
await agent.execute_task("Implement JWT auth")

# Later, resume the same session
agent2 = EnhancedHcodeAgent(
    anthropic_key="your-key",
    session_id="feature-auth"  # Same ID
)
# Context is preserved!
```

### Safety & Backups

```python
# Start a transaction
tx_id = agent.safety_guard.start_transaction("Refactor database layer")

try:
    # Make changes
    await agent.execute_task("Refactor database.py")

    # Commit if successful
    agent.safety_guard.commit_transaction()
except Exception as e:
    # Rollback on error
    agent.safety_guard.rollback_transaction()
    print(f"Rolled back: {e}")
```

---

## Troubleshooting

### Common Issues

#### 1. "No module named 'hcode'"

**Solution:**
```bash
# Make sure you installed the package
pip install -e .

# Or activate virtual environment
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
```

#### 2. "API key not found"

**Solution:**
```bash
# Make sure .env file exists with keys
cat .env  # Check file exists

# Or set environment variables
export ANTHROPIC_API_KEY="your-key"
export OPENAI_API_KEY="your-key"
```

#### 3. "Module not found" for models

**Solution:**
```bash
# Install missing dependencies
pip install -r requirements.txt

# Or specific packages
pip install anthropic openai rich click
```

#### 4. Unicode/Emoji errors on Windows

**Solution:**
The application automatically handles this! Windows console encoding is detected and safe alternatives are used.

If issues persist:
```bash
# Use Windows Terminal instead of cmd.exe
# Or set console to UTF-8
chcp 65001
```

#### 5. "Model does not exist" with Cerebras

**Solution:**
```bash
# Use Cerebras-compatible models
hcode run "task" --provider=openai --model=llama3.1-8b

# Available models: llama3.1-8b, llama3.1-70b
```

#### 6. "Connection timeout"

**Solution:**
```bash
# Increase timeout
hcode run "task" --timeout=60

# Or check network/proxy settings
export HTTP_PROXY=http://proxy:port
export HTTPS_PROXY=http://proxy:port
```

#### 7. Permission errors on Linux/macOS

**Solution:**
```bash
# Make scripts executable
chmod +x quick_start.sh
chmod +x run_tests.sh

# Or run with python
python -m hcode.cli_enhanced run "task"
```

### Getting Help

#### Debug Mode

```bash
# Enable debug output
hcode run "task" --debug

# This shows:
# - API requests/responses
# - Tool executions
# - Internal state
# - Error tracebacks
```

#### Verbose Logging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Run your code
agent = EnhancedHcodeAgent(...)
```

#### Check Logs

```bash
# View session logs
ls -la ~/.hcode/sessions/

# View specific session
cat ~/.hcode/sessions/session_20251122_155540.json
```

### Known Limitations

1. **Windows Console** - Some Unicode characters may not display correctly in cmd.exe (use Windows Terminal)
2. **Token Limits** - Very large codebases may hit context limits (use sub-agents for exploration)
3. **API Rate Limits** - Respect provider rate limits (automatic backoff included)
4. **Background Processes** - Limited to platform's shell capabilities

---

## Performance Tips

### 1. Use Cost Optimization

```bash
# Set in .env
HCODE_OPTIMIZE_COST=aggressive
```

### 2. Choose Right Complexity

```bash
# Simple tasks
hcode run "Add a comment" --complexity=simple

# Complex tasks
hcode run "Refactor entire module" --complexity=complex
```

### 3. Use Sub-Agents for Large Codebases

```bash
# Enable agents for exploration
hcode run "Find all API endpoints" --agents
```

### 4. Reuse Sessions

```bash
# Continue previous work
hcode run "task" --session=session_123
```

### 5. Stream Responses

```bash
# Default is streaming (faster perceived performance)
hcode run "task" --stream
```

---

## Architecture

```
hcode/
├── src/hcode/              # Main package
│   ├── providers/          # AI provider implementations
│   │   ├── anthropic_provider.py
│   │   ├── openai_provider.py
│   │   └── provider_selector.py
│   ├── core/               # Core components
│   │   ├── agent.py
│   │   ├── enhanced_agent.py
│   │   ├── context.py
│   │   ├── filesystem.py
│   │   └── safety.py
│   ├── tools/              # Tool system (26+ tools)
│   │   ├── file_tools.py
│   │   ├── bash_tools.py
│   │   ├── web_tools.py
│   │   ├── interactive_tools.py
│   │   ├── notebook_tools.py
│   │   ├── agent_tools.py
│   │   ├── command_system.py
│   │   └── tool_manager.py
│   ├── agents/             # Sub-agent system
│   │   └── sub_agent.py
│   ├── utils/              # Utilities
│   │   ├── config.py
│   │   └── project_analyzer.py
│   ├── cli.py              # Basic CLI
│   └── cli_enhanced.py     # Enhanced CLI (main entry)
├── tests/                  # Test suite
├── examples/               # Example scripts
├── docs/                   # Documentation
├── .env.example            # Environment template
├── .hcoderc.example        # Config template
├── pyproject.toml          # Poetry config
├── setup.py                # Setup config
├── requirements.txt        # Pip requirements
└── README.md               # This file
```

---

## Testing

### Run Automated Tests

```bash
# Linux/macOS
./run_tests.sh

# Windows
run_tests.bat

# Or manually
python quick_test.py
```

### Manual Testing

```bash
# Test basic functionality
hcode run "What is 2 + 2?"

# Test file operations
hcode run "List all Python files in src/"

# Test provider
hcode run "Hello" --provider=openai --model=gpt-4o

# Test Cerebras
hcode run "Hello" --provider=openai --model=llama3.1-8b
```

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Contribution Guide

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Make changes and test: `python quick_test.py`
4. Commit: `git commit -m 'Add amazing feature'`
5. Push: `git push origin feature/amazing-feature`
6. Open Pull Request

---

## Documentation

- **[QUICK_START.md](QUICK_START.md)** - Quick start guide
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Testing instructions
- **[FEATURE_COMPARISON.md](FEATURE_COMPARISON.md)** - Feature parity analysis
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Implementation details
- **[APPLICATION_STATUS.md](APPLICATION_STATUS.md)** - Current status report
- **[CHANGELOG.md](CHANGELOG.md)** - Version history
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines

---

## Comparison with Other Tools

| Feature | Hcode | Claude Code | Cursor | GitHub Copilot |
|---------|-------|-------------|--------|----------------|
| **Dual AI Providers** | ✅ Both | ❌ Claude only | ❌ Proprietary | ❌ GPT only |
| **Open Source** | ✅ MIT | ❌ Closed | ❌ Closed | ❌ Closed |
| **CLI Tool** | ✅ Full | ❌ Extension only | ❌ Editor only | ❌ Editor only |
| **26+ Tools** | ✅ Yes | ✅ Yes | ⚠️ Limited | ⚠️ Limited |
| **Sub-Agents** | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| **Web Search** | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| **Jupyter Support** | ✅ Yes | ✅ Yes | ⚠️ Limited | ⚠️ Limited |
| **Custom Commands** | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| **Background Shells** | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| **Safety System** | ✅ Full | ✅ Full | ⚠️ Basic | ❌ None |
| **Cost Optimization** | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Self-Hosted** | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Custom Base URLs** | ✅ Yes | ❌ No | ❌ No | ❌ No |

---

## Pricing & Cost Optimization

### API Costs (Approximate)

| Provider | Model | Cost per 1M tokens | Best For |
|----------|-------|-------------------|----------|
| Anthropic | claude-3-opus | $15-$75 | Complex reasoning |
| Anthropic | claude-3-sonnet | $3-$15 | General use |
| Anthropic | claude-3-haiku | $0.25-$1.25 | Simple tasks |
| OpenAI | gpt-4 | $30-$60 | High quality |
| OpenAI | gpt-4-turbo | $10-$30 | Balance |
| OpenAI | gpt-3.5-turbo | $0.5-$1.5 | Fast & cheap |
| Cerebras | llama3.1-8b | $0.60-$1.60 | Cost-effective |

### Cost Optimization Tips

1. **Use aggressive mode:** Set `HCODE_OPTIMIZE_COST=aggressive`
2. **Choose right complexity:** Don't use `complex` for simple tasks
3. **Use Cerebras for testing:** `--model=llama3.1-8b`
4. **Reuse sessions:** Avoid re-sending context
5. **Use sub-agents:** Only explore when needed

**Example savings:**
- Simple task with aggressive mode: ~$0.02 (vs $0.10 without)
- Using Cerebras: ~$0.02 (vs $0.15 with GPT-4)
- **Potential savings: 80-90%**

---

## FAQ

### Q: Do I need both API keys?

**A:** No! You only need one. Hcode works with either Anthropic OR OpenAI. Having both enables cost optimization and fallback.

### Q: Can I use local models?

**A:** Yes! Use any OpenAI-compatible endpoint:
```bash
export OPENAI_BASE_URL=http://localhost:8000/v1
```
Works with Ollama, LM Studio, vLLM, etc.

### Q: How much does it cost to use?

**A:** Depends on usage. Simple tasks: ~$0.02. Complex tasks: ~$0.15. Use aggressive mode and Cerebras for 80% savings.

### Q: Is my code sent to AI providers?

**A:** Only the code you're actively working on is sent to the AI provider for processing. The entire codebase is not uploaded.

### Q: Can I use it offline?

**A:** Partially. With local models (Ollama, etc.) you can work offline. Web search and online AI providers require internet.

### Q: What languages are supported?

**A:** All major languages! Python, JavaScript, TypeScript, Java, C++, Go, Rust, Ruby, PHP, and 20+ more.

### Q: Does it work with monorepos?

**A:** Yes! Hcode handles projects of any size. Use sub-agents for efficient exploration of large codebases.

### Q: Can I customize the AI behavior?

**A:** Yes! Configure temperature, max tokens, system prompts, and more in `.hcoderc`.

### Q: Is it safe for production code?

**A:** Yes! Hcode includes enterprise-grade safety features: automatic backups, transaction system, dry-run mode, and rollback capabilities.

### Q: How does it compare to GitHub Copilot?

**A:** Hcode is a CLI tool with 26+ professional tools, while Copilot is an editor extension focused on code completion. Hcode offers more comprehensive features for complete software development workflows.

---

## Roadmap

### Phase 1 (Current - v0.1.0) ✅
- ✅ Dual provider support (Anthropic + OpenAI)
- ✅ 26+ comprehensive tools
- ✅ 100% Claude Code feature parity
- ✅ Cross-platform support (Windows, macOS, Linux)
- ✅ Beautiful terminal UI
- ✅ Cost optimization

### Phase 2 (Coming Soon - v0.2.0)
- 🔄 VS Code Extension
- 🔄 JetBrains Plugin
- 🔄 Enhanced web scraping
- 🔄 Database integration tools
- 🔄 Git workflow automation
- 🔄 Docker/Kubernetes support

### Phase 3 (Future - v0.3.0)
- 📋 Plugin system
- 📋 Complete hooks system
- 📋 Checkpoint system
- 📋 Team collaboration features
- 📋 Cloud synchronization
- 📋 Web dashboard

---

## License

MIT License - see [LICENSE](LICENSE) for details.

**You are free to:**
- ✅ Use commercially
- ✅ Modify
- ✅ Distribute
- ✅ Private use

**Under the condition that:**
- Include copyright notice
- Include license text

---

## Acknowledgments

- **Anthropic** - For Claude API and inspiration from Claude Code
- **OpenAI** - For GPT API
- **Rich** - For beautiful terminal output
- **Click** - For CLI framework
- **Community** - For feedback and contributions

---

## Support & Community

### Get Help

- **Documentation:** [docs/](docs/)
- **Issues:** [GitHub Issues](https://github.com/yourusername/hcode/issues)
- **Discussions:** [GitHub Discussions](https://github.com/yourusername/hcode/discussions)

### Stay Updated

- **GitHub:** [github.com/yourusername/hcode](https://github.com/yourusername/hcode)
- **Changelog:** [CHANGELOG.md](CHANGELOG.md)
- **Releases:** [GitHub Releases](https://github.com/yourusername/hcode/releases)

### Report Issues

Found a bug? [Open an issue](https://github.com/yourusername/hcode/issues/new)

Include:
- Hcode version (`hcode --version`)
- Python version
- Operating system
- Error message/traceback
- Steps to reproduce

---

## Quick Links

- **[Installation](#installation)** - Get started in 5 minutes
- **[Quick Start](#quick-start)** - First steps
- **[Features](#complete-feature-guide)** - Complete feature guide
- **[Examples](#usage-examples)** - Real-world examples
- **[CLI Reference](#cli-commands-reference)** - Command reference
- **[Configuration](#configuration)** - Configuration guide
- **[Troubleshooting](#troubleshooting)** - Common issues
- **[Contributing](#contributing)** - Contribution guide

---

<div align="center">

**Built with ❤️ by the Hcode team**

*Making AI coding assistants accessible, powerful, and beautiful.*

**[Get Started](#installation)** | **[Documentation](docs/)** | **[GitHub](https://github.com/yourusername/hcode)**

</div>
