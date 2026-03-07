#!/bin/bash

# Development container setup script for agent_reviewer project
set -e

echo "🚀 Setting up agent_reviewer development environment..."

# Ensure uv is in PATH
export PATH="$HOME/.cargo/bin:$PATH"

# Install project dependencies
echo "📦 Installing Python dependencies..."
cd /workspaces/agent_reviewer

# Check if uv is available, if not install it
if ! command -v uv &> /dev/null; then
    echo "🐍 Installing uv (Python package manager)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

export UV_LINK_MODE=copy
# Sync dependencies
uv sync

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p .vscode

# Set proper permissions
echo "🔒 Setting permissions..."
chmod +x /workspaces/agent_reviewer/.devcontainer/post_create.sh
chmod +x /workspaces/agent_reviewer/bin/env
chmod +x /workspaces/agent_reviewer/bin/help
chmod +x /workspaces/agent_reviewer/bin/test
chmod +x /workspaces/agent_reviewer/bin/lint/all
chmod +x /workspaces/agent_reviewer/bin/lint/py
chmod +x /workspaces/agent_reviewer/bin/lint/md

# Create a sample .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "🔐 Creating .env file from template..."
    cp .env.template .env
fi

echo "✅ Developer environment setup complete!"
echo ""
echo "🎯 Next steps:"
echo "1. Configure your .env file with actual credentials"
echo "2. Run 'uv run python -m src.main --help' to see available commands"
echo "3. Start coding! 🚀"
echo ""

echo "📝 Available commands:"
echo "  - bin/help                    # Shows help options"
echo "  - bin/env                     # Exports variables from an environment file"

echo "  - bin/lint/all                # Run all linting"
echo "  - bin/lint/md                 # Lint all Markdown files"
echo "  - bin/lint/py                 # Format, line and type check all Python files"
echo "  - bin/test                    # Run all unit tests"

echo "  - uv sync                     # Install/update dependencies"
echo "  - uv run ruff check           # Lint code"
echo "  - uv run ruff format          # Format code"
echo "  - uv run pyright              # Type checking"
echo "  - uv run python -m src.main   # Run main application"