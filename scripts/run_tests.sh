#!/bin/bash
# Quick Test Script for Hcode (Unix/Linux/macOS)
# Run this to verify basic functionality

set -e  # Exit on error

echo "============================================"
echo "Hcode Quick Test Suite"
echo "============================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Python is installed
echo "[1/7] Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}ERROR: Python 3 is not installed${NC}"
    exit 1
fi
python3 --version
echo ""

# Check if API keys are set
echo "[2/7] Checking environment variables..."
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo -e "${YELLOW}WARNING: ANTHROPIC_API_KEY not set${NC}"
    echo "Please set it with: export ANTHROPIC_API_KEY='your-key'"
    echo "Or create a .env file with your keys"
    exit 1
fi
echo -e "${GREEN}✓ ANTHROPIC_API_KEY is set${NC}"
echo ""

# Install dependencies if needed
echo "[3/7] Checking installation..."
if ! python3 -c "import hcode" &> /dev/null; then
    echo "Installing Hcode..."
    pip install -e . || {
        echo -e "${RED}ERROR: Installation failed${NC}"
        exit 1
    }
fi
echo -e "${GREEN}✓ Hcode is installed${NC}"
echo ""

# Run Python test script
echo "[4/7] Running comprehensive tests..."
python3 quick_test.py || {
    echo ""
    echo -e "${RED}ERROR: Tests failed${NC}"
    echo "See above for details"
    exit 1
}
echo ""

# Test CLI command
echo "[5/7] Testing CLI command..."
if ! hcode --version &> /dev/null; then
    echo -e "${RED}ERROR: hcode command not found${NC}"
    echo "Try: pip install -e ."
    exit 1
fi
hcode --version
echo -e "${GREEN}✓ CLI works${NC}"
echo ""

# Test help
echo "[6/7] Testing help command..."
if ! hcode --help &> /dev/null; then
    echo -e "${RED}ERROR: help command failed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Help command works${NC}"
echo ""

# Final message
echo "[7/7] All basic tests passed!"
echo ""
echo "============================================"
echo -e "${GREEN}✓ Hcode is ready to use!${NC}"
echo "============================================"
echo ""
echo "Next steps:"
echo "  1. hcode run \"Hello, how can you help me?\""
echo "  2. hcode chat (for interactive mode)"
echo "  3. See TESTING_GUIDE.md for more tests"
echo ""
