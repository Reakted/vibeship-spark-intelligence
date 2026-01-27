#!/bin/bash
# Spark Installation Script
# One-command setup for the self-evolving intelligence layer

set -e

SPARK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLAUDE_CONFIG_DIR="$HOME/.claude"

echo "========================================"
echo "  SPARK - Self-Evolving Intelligence"
echo "========================================"
echo ""

# Check Python version
echo "Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.10+"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✓ Python $PYTHON_VERSION found"

# Enforce Python >= 3.10 (matches pyproject.toml)
python3 - <<'PY'
import sys
if sys.version_info < (3,10):
    raise SystemExit('❌ Python 3.10+ required')
PY

# Install dependencies
echo ""
echo "Installing dependencies..."
# Install in editable mode when running from the repo (recommended)
if [ -f "$SPARK_DIR/pyproject.toml" ]; then
  pip3 install -e "$SPARK_DIR" --quiet 2>/dev/null || pip3 install -e "$SPARK_DIR" --user --quiet
else
  pip3 install requests --quiet 2>/dev/null || pip3 install requests --user --quiet
fi
echo "✓ Core dependencies installed"

# Optional: Install sentence-transformers for semantic search
echo ""
read -p "Install semantic search support? (requires ~500MB, recommended) [y/N]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Installing sentence-transformers (this may take a few minutes)..."
    pip3 install sentence-transformers --quiet 2>/dev/null || pip3 install sentence-transformers --user --quiet
    echo "✓ Semantic search enabled"
fi

# Create Spark config directory
echo ""
echo "Setting up Spark config..."
mkdir -p "$HOME/.spark"
echo "✓ Config directory: ~/.spark"

# Set up Claude Code hooks (if Claude Code is installed)
if [ -d "$CLAUDE_CONFIG_DIR" ]; then
    echo ""
    read -p "Set up Claude Code hooks for auto-capture? [Y/n]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        # Create hooks config
        cat > "$CLAUDE_CONFIG_DIR/spark-hooks.json" << HOOKS
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "python3 $SPARK_DIR/hooks/observe.py"
      }]
    }],
    "PostToolUseFailure": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "python3 $SPARK_DIR/hooks/observe.py"
      }]
    }]
  }
}
HOOKS
        echo "✓ Claude Code hooks configured"
        echo "  Note: Merge with your existing settings.json if you have custom hooks"
    fi
fi

# Test installation
echo ""
echo "Testing installation..."
cd "$SPARK_DIR"
if python3 cli.py health > /dev/null 2>&1; then
    echo "✓ Spark is working!"
else
    echo "⚠ Some components may need configuration"
fi

# Print summary
echo ""
echo "========================================"
echo "  Installation Complete!"
echo "========================================"
echo ""
echo "Spark directory: $SPARK_DIR"
echo ""
echo "Quick start:"
echo "  cd $SPARK_DIR"
echo "  python3 cli.py status    # Check status"
echo "  python3 cli.py health    # Health check"
echo "  python3 cli.py learnings # View learnings"
echo ""
echo "For Mind integration (recommended):"
echo "  pip3 install vibeship-mind"
echo "  python3 -m mind.lite_tier  # Start Mind server"
echo "  python3 cli.py sync        # Sync learnings"
echo ""
echo "Documentation: $SPARK_DIR/README.md"
echo ""
