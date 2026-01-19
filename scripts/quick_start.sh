#!/bin/bash

# Hcode Quick Start Script
# This script helps you get started with Hcode quickly

set -e

echo "🚀 Hcode Quick Start Script"
echo "============================"
echo ""

# Check Python version
echo "📋 Checking prerequisites..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Python not found. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
echo "✅ Python $PYTHON_VERSION found"

# Check if Poetry is installed
echo ""
echo "📦 Checking for Poetry..."
if command -v poetry &> /dev/null; then
    POETRY_VERSION=$(poetry --version 2>&1 | awk '{print $3}')
    echo "✅ Poetry $POETRY_VERSION found"
    USE_POETRY=true
else
    echo "⚠️  Poetry not found"
    echo ""
    echo "Would you like to:"
    echo "  1) Install Poetry (recommended)"
    echo "  2) Continue with pip"
    echo ""
    read -p "Enter choice (1 or 2): " choice

    if [ "$choice" = "1" ]; then
        echo ""
        echo "📥 Installing Poetry..."
        curl -sSL https://install.python-poetry.org | $PYTHON_CMD -

        # Add Poetry to PATH for this session
        export PATH="$HOME/.local/bin:$PATH"

        if command -v poetry &> /dev/null; then
            echo "✅ Poetry installed successfully"
            USE_POETRY=true
        else
            echo "❌ Poetry installation failed. Falling back to pip."
            USE_POETRY=false
        fi
    else
        USE_POETRY=false
    fi
fi

# Install Hcode
echo ""
echo "📦 Installing Hcode..."
if [ "$USE_POETRY" = true ]; then
    echo "Using Poetry..."
    poetry install
    echo "✅ Hcode installed with Poetry"
    echo ""
    echo "To activate the environment, run:"
    echo "  poetry shell"
else
    echo "Using pip..."
    $PYTHON_CMD -m venv venv

    # Activate virtual environment
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    else
        source venv/Scripts/activate
    fi

    pip install -e .
    echo "✅ Hcode installed with pip"
    echo ""
    echo "Virtual environment created in ./venv"
    echo "To activate it, run:"
    echo "  source venv/bin/activate  (Linux/macOS)"
    echo "  venv\\Scripts\\activate     (Windows)"
fi

# Check for .env file
echo ""
echo "🔑 Checking API keys..."
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found"
    echo ""
    read -p "Would you like to create .env file now? (y/n): " create_env

    if [ "$create_env" = "y" ] || [ "$create_env" = "Y" ]; then
        cp .env.example .env
        echo "✅ Created .env file from template"
        echo ""
        echo "⚠️  IMPORTANT: Edit .env and add your API keys:"
        echo "   - ANTHROPIC_API_KEY"
        echo "   - OPENAI_API_KEY"
        echo ""
        read -p "Press Enter to open .env in editor..."

        if command -v nano &> /dev/null; then
            nano .env
        elif command -v vim &> /dev/null; then
            vim .env
        else
            echo "Please edit .env manually with your preferred editor"
        fi
    else
        echo "⚠️  Remember to create .env file and add your API keys"
    fi
else
    echo "✅ .env file exists"
fi

# Verify installation
echo ""
echo "🔍 Verifying installation..."
if [ "$USE_POETRY" = true ]; then
    if poetry run hcode --version &> /dev/null; then
        echo "✅ Hcode is working correctly"
        VERSION=$(poetry run hcode --version)
        echo "   $VERSION"
    else
        echo "❌ Hcode verification failed"
        exit 1
    fi
else
    if command -v hcode &> /dev/null; then
        echo "✅ Hcode is working correctly"
        VERSION=$(hcode --version)
        echo "   $VERSION"
    else
        echo "❌ Hcode verification failed"
        echo "   Try activating the virtual environment first"
        exit 1
    fi
fi

# Success message
echo ""
echo "✅ Setup Complete!"
echo "=================="
echo ""
echo "🎉 Hcode is ready to use!"
echo ""
echo "Quick Start Commands:"
echo "  hcode --help                  # Show help"
echo "  hcode run \"your task\"         # Execute a task"
echo "  hcode chat                    # Start interactive chat"
echo "  hcode analyze <file>          # Analyze code"
echo ""
echo "📚 Documentation:"
echo "  README.md          - Main documentation"
echo "  INSTALLATION.md    - Installation guide"
echo "  TOOLS.md           - Tool reference"
echo "  SHORTCUTS.md       - Keyboard shortcuts"
echo ""
echo "💡 Examples:"
echo "  src/hcode/examples/basic_usage.py"
echo "  src/hcode/examples/advanced_features.py"
echo ""
echo "Happy coding! 🚀"
