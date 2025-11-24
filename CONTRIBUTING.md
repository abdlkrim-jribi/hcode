# Contributing to Hcode

Thank you for your interest in contributing to Hcode! This document provides guidelines and instructions for contributing.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Poetry (for dependency management)
- Git
- API keys for Anthropic and/or OpenAI (for testing)

### Setting Up Development Environment

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/yourusername/hcode.git
   cd hcode
   ```

2. **Install Poetry**
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   # On Windows (PowerShell):
   # (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
   ```

3. **Install dependencies**
   ```bash
   # Install all dependencies including dev dependencies
   poetry install

   # Activate the virtual environment
   poetry shell
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

5. **Verify installation**
   ```bash
   # Check if hcode is available
   hcode --help

   # Run tests
   poetry run pytest
   ```

## Development Workflow

### Branch Naming Convention

- `feature/` - New features
- `bugfix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions or updates

Example: `feature/add-gemini-support`

### Making Changes

1. **Create a new branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clean, documented code
   - Follow the existing code style
   - Add tests for new functionality
   - Update documentation as needed

3. **Run tests and linting**
   ```bash
   # Run tests
   poetry run pytest

   # Format code (src layout auto-detected)
   poetry run black src/
   poetry run isort src/

   # Run linters
   poetry run pylint src/hcode/
   poetry run mypy src/hcode/
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "Add feature: description of your changes"
   ```

5. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request**
   - Go to the Hcode repository on GitHub
   - Click "New Pull Request"
   - Select your branch
   - Fill in the PR template

## Code Style Guidelines

### Python Style

- Follow PEP 8
- Use type hints where appropriate
- Maximum line length: 100 characters
- Use meaningful variable and function names
- Add docstrings to all public functions and classes

**Example:**
```python
async def execute_task(
    self,
    task_description: str,
    complexity: TaskComplexity = TaskComplexity.MODERATE,
    stream: bool = True
) -> str:
    """
    Execute a coding task autonomously.

    Args:
        task_description: Natural language task description
        complexity: Task complexity level
        stream: Stream the response

    Returns:
        Final response from the agent
    """
    pass
```

### Documentation

- Use clear, concise language
- Include code examples where helpful
- Keep README.md up to date
- Update CHANGELOG.md for significant changes

### Testing

- Write unit tests for new functionality
- Aim for >80% code coverage
- Use pytest for testing
- Test both success and failure cases

**Example:**
```python
import pytest
from hcode.core import HcodeAgent

@pytest.mark.asyncio
async def test_execute_task():
    agent = HcodeAgent(anthropic_key="test-key")
    result = await agent.execute_task("Test task", stream=False)
    assert isinstance(result, str)
```

## Areas for Contribution

### High Priority

- [ ] Additional AI provider support (Google Gemini, Cohere)
- [ ] Improved error handling and recovery
- [ ] Performance optimizations
- [ ] Enhanced testing coverage
- [ ] Documentation improvements

### Medium Priority

- [ ] VS Code extension
- [ ] Web interface
- [ ] Multi-file refactoring improvements
- [ ] Plugin system
- [ ] AST-based code analysis

### Good First Issues

Look for issues labeled `good-first-issue` in the issue tracker. These are suitable for newcomers to the project.

## Adding a New AI Provider

To add support for a new AI provider:

1. **Create provider class** in `hcode/providers/`
   ```python
   from .base import AIProvider

   class NewProvider(AIProvider):
       def __init__(self, api_key: str, model: str, **kwargs):
           super().__init__(api_key, model, **kwargs)
           # Initialize your provider client

       async def generate_completion(self, messages, stream=False, **kwargs):
           # Implement completion logic
           pass

       def count_tokens(self, text: str) -> int:
           # Implement token counting
           pass

       # Implement other required methods
   ```

2. **Add to provider selector** in `hcode/providers/provider_selector.py`

3. **Update configuration** in `hcode/utils/config.py`

4. **Add tests** in `tests/providers/`

5. **Update documentation**

## Reporting Bugs

When reporting bugs, please include:

1. **Description**: Clear description of the issue
2. **Steps to reproduce**: Detailed steps to reproduce the bug
3. **Expected behavior**: What you expected to happen
4. **Actual behavior**: What actually happened
5. **Environment**:
   - Hcode version
   - Python version
   - Operating system
   - AI provider and model used
6. **Logs**: Relevant error messages or logs

## Feature Requests

For feature requests, please:

1. Check if the feature has already been requested
2. Provide a clear description of the feature
3. Explain the use case and benefits
4. Include examples if applicable

## Code Review Process

All contributions go through code review:

1. Maintainers will review your PR
2. Address any feedback or requested changes
3. Once approved, a maintainer will merge your PR
4. Your contribution will be included in the next release

## Community Guidelines

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Provide constructive feedback
- Focus on the code, not the person
- Follow the [Code of Conduct](CODE_OF_CONDUCT.md)

## License

By contributing to Hcode, you agree that your contributions will be licensed under the MIT License.

## Questions?

If you have questions:

- Open an issue with the `question` label
- Join our community discussions
- Reach out to maintainers

Thank you for contributing to Hcode! 🚀
