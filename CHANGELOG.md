# Changelog

All notable changes to Hcode will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-11-10

### Added
- Initial release of Hcode
- **Dual AI provider support** (Anthropic Claude and OpenAI GPT)
- **Poetry package manager** integration for dependency management
- Intelligent provider selection based on task complexity
- Automatic fallback mechanism between providers
- Cost optimization across providers

#### Core Features
- Comprehensive **tool system** with 20+ built-in tools
  - File operations (Read, Write, Edit, Glob, Grep)
  - Web capabilities (WebFetch, WebSearch, WebScrape)
  - Interactive tools (AskUserQuestion, TodoWrite, Confirm, DisplayPanel, Progress)
  - Notebook support (NotebookEdit, NotebookRead, NotebookExecute)
  - Custom commands (SlashCommand, Skill, Hooks)
- **Sub-agent system** for specialized tasks
  - ExploreAgent: Fast codebase exploration
  - PlanAgent: Implementation planning
  - ImplementAgent: Code implementation
  - AgentOrchestrator: Parallel/sequential execution
- **Enhanced CLI** with beautiful terminal UI
  - Rich formatting with colors and styles
  - Progress indicators and spinners
  - Interactive panels and tables
  - Markdown rendering
  - Command aliases and shortcuts
- **Enterprise-grade safety system**
  - Automatic backups before modifications
  - Transaction system with commit/rollback
  - Checkpoint system for manual saves
  - Dry-run mode for previewing changes
- **Advanced context management**
  - SQLite persistence for long conversations
  - Smart truncation with importance scoring
  - Session import/export
  - Provider-specific optimization
- **Custom OpenAI base URL support**
  - Azure OpenAI integration
  - Proxy and middleware support
  - OpenAI-compatible APIs (Ollama, LM Studio, vLLM)

#### Infrastructure
- File system operations (read, write, search, watch)
- Git integration (status, diff, commit)
- Configuration system (.hcoderc support)
- Project analysis capabilities
- Interactive chat mode
- Code analysis and debugging features
- Provider comparison mode
- Tool executor for external commands (linters, formatters, test runners)

### Supported Models
- Anthropic: Claude 3 Opus, Claude 3.5 Sonnet, Claude 3 Haiku
- OpenAI: GPT-4, GPT-4-Turbo, GPT-4o, GPT-4o-mini, GPT-3.5-Turbo

### Features
- Autonomous task execution
- Task planning and breakdown
- Code generation and refactoring
- Bug detection and security analysis
- Testing integration
- Real-time streaming responses
- Context window management
- Token counting and cost tracking

## [Unreleased]

### Planned
- Support for additional AI providers (Google Gemini, Cohere)
- Web interface
- VS Code extension
- Team collaboration features
- Custom plugin system
- Enhanced multi-file refactoring
- AST-based code analysis
- Docker integration improvements
- Performance optimizations
