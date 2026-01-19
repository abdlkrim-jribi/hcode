# Hcode - Intelligent AI Coding Agent

Hcode is a powerful CLI-based AI coding assistant designed to help developers with complex tasks, code generation, and project management directly from the terminal.

## Features

- **Advanced Context Awareness**: Understands your workspace, files, and project structure.
- **Multi-Provider Support**: Compatible with major AI providers like Anthropic (Claude) and OpenAI (GPT).
- **Agentic Workflow**: Capable of planning, executing, and verifying tasks autonomously.
- **Rich CLI Interface**: Interactive terminal interface with color-coded output and progress tracking.
- **Extensive Tooling**: Built-in tools for file operations, web searching, git management, and more.

## Installation

### Prerequisites
- Python 3.10 or higher
- Git

### From Source

1. Clone the repository:
   ```bash
   git clone git@git.technica-engineering.net:hjarboui/hcode.git
   cd hcode
   ```

2. Install dependencies (using poetry or pip):
   ```bash
   # Using Poetry (Recommended)
   poetry install

   # Using pip
   pip install .
   ```

## Usage

### Running Hcode

You can run Hcode using the installed CLI command or via the helper scripts.

**CLI Command:**
```bash
hcode
```

**Helper Scripts (Windows):**
```powershell
.\scripts\run_hcode.bat
# or
.\scripts\quick_start.ps1
```

**Helper Scripts (Linux/Mac):**
```bash
./scripts/run_hcode.sh
# or
./scripts/quick_start.sh
```

### Configuration

Hcode uses a YAML-based configuration system.
- Global config: `~/.hcode/config.yaml`
- Project config: `.hcoderc` in your project root

You can also configure API keys via environment variables (see `.env.example`).

## Development

To run tests:
```bash
# Windows
.\scripts\run_tests.bat

# Linux/Mac
./scripts/run_tests.sh
```

## License

MIT License - See [LICENSE](LICENSE) for details.