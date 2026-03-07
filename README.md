# Agent Reviewer

An AI-powered local code review agent inspired by [qodo-ai/pr-agent](https://github.com/qodo-ai/pr-agent). Reviews your code directly from the command line using Azure OpenAI (`gpt-5-pro`), **without needing to create a Pull Request**.

## Purpose

The goal of this project is to build an agent that performs thorough, automated code reviews locally in VS Code. It checks for:

- **Security** — vulnerabilities, exposed secrets, authentication/authorization issues
- **Correctness** — logic errors, data corruption risks, race conditions
- **Code Quality** — SOLID principles, DRY, clean code, proper error handling
- **Testing** — adequate test coverage, well-structured tests, edge case handling
- **Performance** — N+1 queries, memory leaks, inefficient algorithms
- **Best Practices** — language-specific idioms, consistent patterns, documentation

## Architecture

Inspired by pr-agent's modular design:

```
src/
├── main.py           # CLI entry point (argparse)
├── config.py         # Configuration loading from .env
├── ai_handler.py     # Azure OpenAI API client
├── reviewer.py       # Core review orchestrator
├── prompts.py        # Review prompt templates
├── diff_utils.py     # Git diff & file utilities
├── github_utils.py   # GitHub repo cloning (public + private)
└── web/
    ├── app.py        # FastAPI web application & REST API
    └── static/
        └── index.html  # Web UI (single-page app)
```

## Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- An Azure OpenAI deployment with `gpt-5-pro`

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/isabelcabezasm/agent_reviewer.git
   cd agent_reviewer
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Configure environment variables:
   ```bash
   cp .env.template .env
   # Edit .env with your Azure OpenAI credentials
   ```

   Required variables:
   | Variable | Description |
   |---|---|
   | `AZURE_MODEL_API_ENDPOINT` | Azure OpenAI API endpoint URL |
   | `AZURE_MODEL_API_KEY` | Azure OpenAI API key |
   | `AZURE_MODEL_API_NAME` | Deployed model name (e.g., `gpt-5-pro`) |
   | `AZURE_MODEL_API_VERSION` | API version (e.g., `2024-12-01-preview`) |

### Usage

```bash
# Review all uncommitted changes (default)
uv run python -m src.main

# Review only staged changes
uv run python -m src.main --staged

# Review specific files (can be from any location)
uv run python -m src.main --files src/config.py /other/repo/app.py

# Review changes compared to a branch
uv run python -m src.main --branch main

# Review a specific commit
uv run python -m src.main --commit HEAD~1

# Add extra review instructions
uv run python -m src.main --instructions "Focus on error handling and security"
```

#### Reviewing Other Repositories

You can review code from any repository on your machine — no need to be inside it:

```bash
# Review uncommitted changes in another repo
uv run python -m src.main --repo /path/to/other/repo

# Review staged changes in another repo
uv run python -m src.main --repo /path/to/other/repo --staged

# Review branch diff in another repo
uv run python -m src.main --repo /path/to/other/repo --branch main

# Review a commit in another repo
uv run python -m src.main --repo /path/to/other/repo --commit HEAD~1
```

### Development

| Command | Description |
|---|---|
| `bin/review` | AI review of uncommitted changes |
| `bin/review --staged` | AI review of staged changes only |
| `bin/lint/all` | Run all linters |
| `bin/lint/py` | Format, lint, and type-check Python files |
| `bin/lint/md` | Lint Markdown files |
| `bin/test` | Run all unit tests |
| `uv run pytest tests/ -v` | Run tests with verbose output |

## Local Review Tools

### `bin/review` — Quick CLI

Review your code before committing, right from the terminal:

```bash
bin/review                                    # All uncommitted changes
bin/review --staged                           # Staged changes only
bin/review --files src/main.py src/config.py  # Specific files
bin/review --staged -i "Focus on security"    # With custom instructions
bin/review --repo /path/to/other/project      # Another repository
```

### Git Pre-commit Hook — Auto-review on Every Commit

Install the hook in any repository:

```bash
# Install in the current repo
bin/review-install-hook

# Install in another repo
bin/review-install-hook /path/to/other/repo
```

After installation, every `git commit` automatically runs an AI review on staged changes. If **critical issues** are found, it asks for confirmation before proceeding.

To uninstall, remove the hook file:
```bash
rm .git/hooks/pre-commit
```

### VS Code Tasks

Press `Ctrl+Shift+P` → **Tasks: Run Task** and pick:

| Task | Description |
|---|---|
| Review: Uncommitted Changes | Review all local changes |
| Review: Staged Changes | Review only staged files |
| Review: Current File | Review the file open in the editor |
| Review: Launch Web UI | Start the web interface |

## Web UI

A full web interface for reviewing any GitHub repository — including **private repos** using a Personal Access Token.

### Launch the Web UI

```bash
uv run uvicorn src.web.app:app --reload --host 0.0.0.0 --port 8000
```

Then open **http://localhost:8000** in your browser.

### Features

- **Repository URL** — paste any GitHub repo URL
- **GitHub PAT** — for private repositories (never stored, used only for cloning)
- **Review Modes** — Full repo, branch diff, or last commit
- **Custom Instructions** — tell the AI what to focus on
- **File Filters** — choose extensions and max files to review
- **Rich Results** — score badge, expandable issues by severity, code suggestions, and positive highlights
- **Raw YAML** — toggle the raw AI output

### REST API

The web app also exposes a REST API:

```bash
# Review a public repo
curl -X POST http://localhost:8000/api/review \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/owner/repo"}'

# Review a private repo
curl -X POST http://localhost:8000/api/review \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/owner/private-repo",
    "github_pat": "ghp_xxxxxxxxxxxx",
    "instructions": "Focus on security and error handling"
  }'

# Health check
curl http://localhost:8000/api/health
```

## Use from Any Project (Without Cloning This Repo)

You can review code in **any repository** without having the Agent Reviewer source code there. Three options:

### Option 1: Docker (Recommended)

One-liner install — adds the `agent-review` command globally:

```bash
curl -fsSL https://raw.githubusercontent.com/isabelcabezasm/agent_reviewer/main/bin/remote-review | bash -s -- install
```

Then use it from any project:

```bash
# Create a .env with your Azure credentials (once per project or in ~/.agent_reviewer.env)
cat > .env << EOF
AZURE_MODEL_API_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_MODEL_API_KEY=your-key
AZURE_MODEL_API_NAME=gpt-5-pro
AZURE_MODEL_API_VERSION=2024-12-01-preview
EOF

# Review your code
agent-review                        # All uncommitted changes
agent-review --staged               # Staged changes only
agent-review --files src/app.py     # Specific files
agent-review --branch main          # Compare to branch
```

Or run without installing:

```bash
docker run --rm \
  -v "$(pwd):/workspace" \
  --env-file .env \
  ghcr.io/isabelcabezasm/agent_reviewer:latest \
  --repo /workspace --staged
```

### Option 2: GitHub Action

Add to any repo's `.github/workflows/review.yml`:

```yaml
name: AI Code Review
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: isabelcabezasm/agent_reviewer@main
        with:
          azure_endpoint: ${{ secrets.AZURE_MODEL_API_ENDPOINT }}
          azure_api_key: ${{ secrets.AZURE_MODEL_API_KEY }}
          azure_model_name: "gpt-5-pro"
          instructions: "Focus on security, error handling, and test coverage"
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

This auto-reviews every PR and posts the results as a comment. Works with **private repos** via the `GITHUB_TOKEN`.

### Option 3: Web UI (Self-hosted API)

Deploy the web service and review repos from your browser:

```bash
docker run -d \
  -p 8000:8000 \
  --env-file .env \
  ghcr.io/isabelcabezasm/agent_reviewer:latest \
  uvicorn src.web.app:app --host 0.0.0.0 --port 8000
```

Then open **http://localhost:8000** — paste any repo URL + optional PAT and get a full review.

## License

MIT