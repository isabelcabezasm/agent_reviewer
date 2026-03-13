# Agent Reviewer

An AI-powered local code review agent inspired by
[qodo-ai/pr-agent](https://github.com/qodo-ai/pr-agent). Reviews your code directly from the
command line, web UI, or **GitHub Copilot (via MCP)** using Azure OpenAI or GitHub Copilot as the
AI backend — **without needing to create a Pull Request**.

## Purpose

The goal of this project is to build an agent that performs thorough, automated code reviews
locally in VS Code. It checks for:

- **Security** — vulnerabilities, exposed secrets, authentication/authorization issues
- **Correctness** — logic errors, data corruption risks, race conditions
- **Code Quality** — SOLID principles, DRY, clean code, proper error handling
- **Testing** — adequate test coverage, well-structured tests, edge case handling
- **Performance** — N+1 queries, memory leaks, inefficient algorithms
- **Best Practices** — language-specific idioms, consistent patterns, documentation

## AI Provider Support

Agent Reviewer supports two AI backends:

| Provider | Description | Auth |
|---|---|---|
| **Azure OpenAI** | Azure-hosted models (e.g., `gpt-5.4-pro`) | API key or Entra ID |
| **GitHub Copilot** | GitHub Copilot Chat API (e.g., `gpt-4.1`, `claude-sonnet-4`) | GitHub token or `gh` CLI |

The provider is auto-detected from environment variables, or set explicitly with `AI_PROVIDER`.

## Architecture

Inspired by pr-agent's modular design:

```text
src/
├── main.py              # CLI entry point (argparse)
├── config.py            # Configuration loading from .env
├── ai_handler.py        # Azure OpenAI API client (Chat Completions + Responses API)
├── copilot_handler.py   # GitHub Copilot API client
├── handler_factory.py   # Factory to create the right AI handler (cached)
├── reviewer.py          # Core review orchestrator
├── prompts.py           # Review prompt templates
├── diff_utils.py        # Git diff & file utilities
├── github_utils.py      # GitHub repo cloning & branch diffing
├── ssl_utils.py         # SSL/TLS certificate configuration
├── mcp_server.py        # MCP server for GitHub Copilot integration
└── web/
    ├── app.py           # FastAPI web application & REST API
    ├── auth.py          # Authentication (API key + sessions)
    └── static/
        ├── index.html   # Web UI (single-page app)
        └── login.html   # Login page
```

## Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- One of the following AI backends:
  - **Azure OpenAI** — a deployed model (e.g., `gpt-5-pro`)
  - **GitHub Copilot** — a Copilot subscription + GitHub token

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
   # Edit .env with your AI provider credentials
   ```

#### Azure OpenAI Configuration

   | Variable | Description |
   |---|---|
   | `AI_PROVIDER` | Set to `azure` (or leave empty — Azure is the default) |
   | `AZURE_MODEL_API_ENDPOINT` | Azure OpenAI API endpoint URL |
   | `AZURE_MODEL_API_KEY` | Azure OpenAI API key (or leave empty for Entra ID auth) |
   | `AZURE_MODEL_API_NAME` | Deployed model name (e.g., `gpt-5-pro`) |
   | `AZURE_MODEL_API_VERSION` | API version (e.g., `2024-12-01-preview`) |

#### GitHub Copilot Configuration

   | Variable | Description |
   |---|---|
   | `AI_PROVIDER` | Set to `copilot` |
   | `GITHUB_TOKEN` | GitHub token (PAT or Copilot token). If omitted, falls back to `gh auth token` |
   | `COPILOT_MODEL_NAME` | Model to use (default: `gpt-4.1`). Other options: `gpt-4o`, `o3-mini`, `claude-sonnet-4` |

> **Auto-detection:** If `AI_PROVIDER` is not set, the provider is auto-detected. If Azure env
> vars are present, Azure is used. If only `GITHUB_TOKEN` is set, Copilot is used.

#### Other Configuration

   | Variable | Description |
   |---|---|
   | `AGENT_REVIEWER_API_KEY` | API key for web UI/API authentication (leave empty to disable) |
   | `USE_CERTS` | Set to `true` to use a custom CA bundle for SSL (default: `false`) |
   | `CERTS_PATH` | Path to CA certificate bundle (default: `/etc/ssl/certs/ca-certificates.crt`) |
   | `LOG_LEVEL` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`) |

## Authentication

Authentication is controlled by the `AGENT_REVIEWER_API_KEY` environment variable:

- **Set it** → all API endpoints and the Web UI require
  authentication
- **Leave it empty** → authentication is disabled (open access)

### Web UI Authentication

When auth is enabled, the Web UI shows a **login page** where users enter the API key.
A secure session cookie is set for 24 hours.

### REST API Authentication

API clients authenticate via the `X-API-Key` header:

```bash
curl -X POST https://your-api/api/review/code \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"code": "def hello(): pass"}'
```

Or via query parameter: `?api_key=your-api-key`

### VS Code Extension Authentication

Set the API key in VS Code Settings:

- `agentReviewer.apiKey` — your API key (sent as `X-API-Key` header)

### Health Endpoint

`/api/health` is always public (no auth required) for monitoring and probes.

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

After installation, every `git commit` automatically runs an AI review on staged changes.
If **critical issues** are found, it asks for confirmation before proceeding.

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

## MCP Server (GitHub Copilot Integration)

Agent Reviewer includes an **MCP (Model Context Protocol) server** that exposes code review tools
directly to GitHub Copilot in VS Code. This means you can ask Copilot to review your code and it
will use Agent Reviewer's tools automatically.

### Available MCP Tools

| Tool | Description |
|---|---|
| `review_staged_changes` | Review staged (`git add`) changes |
| `review_uncommitted_changes` | Review all pending changes (staged + unstaged) |
| `review_branch_changes` | Review diff between current HEAD and a target branch |
| `review_current_branch` | Review all changes on the current branch vs `main` |
| `review_commit` | Review changes from a specific commit |
| `review_files` | Review specific files by path |
| `review_repository` | Scan and review all code files in a repository |
| `review_code_snippet` | Review a raw code snippet (no git needed) |
| `review_diff` | Review a raw unified diff (no git needed) |

### Setup (VS Code)

The MCP server configuration is already included in `.vscode/mcp.json`:

```json
{
  "servers": {
    "agent-reviewer": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "python", "-m", "src.mcp_server"]
    }
  }
}
```

No extra setup needed — open the workspace in VS Code and the MCP server is available to Copilot.

### Usage with Copilot

Once the MCP server is running, ask Copilot things like:

- *"Review my staged changes"*
- *"Review the current branch against main"*
- *"Review the file src/config.py"*
- *"Review this code snippet for security issues"*
- *"Review the whole repository, focus on error handling"*

Copilot will automatically select the appropriate MCP tool and return a structured YAML review.

### Running Manually

```bash
# stdio mode (default, used by VS Code)
uv run python -m src.mcp_server

# SSE mode (HTTP)
uv run python -m src.mcp_server --sse

# Streamable HTTP mode (recommended for remote deployment)
uv run python -m src.mcp_server --streamable-http
```

### Using MCP from Another VS Code (Remote)

You can deploy the MCP server as an HTTP service and connect to it from **any VS Code instance**
— no need to clone the repo or install dependencies on the remote machine.

#### Option 1: Deploy to Azure Container Apps

```bash
# One command deploys the MCP server with bearer-token auth
bin/deploy-mcp

# Update after code changes
bin/deploy-mcp --update

# Tear down
bin/deploy-mcp --destroy
```

The script requires `AGENT_REVIEWER_API_KEY` in your `.env` (used as the bearer token).
After deployment, it prints the URL and the `mcp.json` config to copy.

#### Option 2: Run with Docker

```bash
docker run -d \
  -p 8080:8080 \
  --env-file .env \
  -e MCP_PORT=8080 \
  ghcr.io/isabelcabezasm/agent_reviewer:latest \
  python -m src.mcp_server --streamable-http
```

#### Option 3: Run Directly

```bash
# On the server machine
AGENT_REVIEWER_API_KEY=your-secret-key \
MCP_HOST=0.0.0.0 \
MCP_PORT=8080 \
uv run python -m src.mcp_server --streamable-http
```

#### Connect from VS Code

On the **client** VS Code, create `.vscode/mcp.json` in your project:

```json
{
  "servers": {
    "agent-reviewer": {
      "type": "http",
      "url": "https://YOUR-MCP-SERVER-URL/mcp",
      "headers": {
        "Authorization": "Bearer YOUR-API-KEY"
      }
    }
  }
}
```

Replace `YOUR-MCP-SERVER-URL` and `YOUR-API-KEY` with your deployment values.
An example config is provided in `.vscode/mcp.json.remote-example`.

> **Security:** When `AGENT_REVIEWER_API_KEY` is set, all MCP HTTP requests require
> `Authorization: Bearer <key>`. The `/health` endpoint is always public.

## Web UI

A full web interface for reviewing any GitHub repository — including **private repos**
using a Personal Access Token.

### Launch the Web UI

```bash
uv run uvicorn src.web.app:app --reload --host 0.0.0.0 --port 8000
```

Then open **<http://localhost:8000>** in your browser.

### Features

- **Repository URL** — paste any GitHub repo URL
- **GitHub PAT** — for private repositories (never stored, used only for cloning)
- **Review Modes** — Full repo, branch diff, or last commit
- **Custom Instructions** — tell the AI what to focus on
- **File Filters** — choose extensions and max files to review
- **Rich Results** — score badge, expandable issues by severity, code suggestions, and positive highlights
- **Raw YAML** — toggle the raw AI output

### REST API Reference

The web app exposes a REST API with three endpoints:

```bash
# Review a GitHub repo (clones it server-side)
curl -X POST http://localhost:8000/api/review \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/owner/repo"}'

# Review raw code directly (used by VS Code extension)
curl -X POST http://localhost:8000/api/review/code \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def hello(): return 42",
    "language": "python",
    "filename": "app.py",
    "instructions": "Check for type hints"
  }'

# Review a git diff directly (used by pre-commit hooks)
curl -X POST http://localhost:8000/api/review/diff \
  -H "Content-Type: application/json" \
  -d '{
    "diff": "+new line\n-old line",
    "instructions": "Focus on security"
  }'

# Health check
curl http://localhost:8000/api/health
```

| Endpoint | Input | Use Case |
|---|---|---|
| `POST /api/review` | Repo URL + optional PAT | Web UI, CI pipelines |
| `POST /api/review/code` | Raw source code | VS Code extension, editor plugins |
| `POST /api/review/diff` | Git diff text | Pre-commit hooks, CI pipelines |
| `GET /api/health` | — | Monitoring |

## VS Code Extension (Remote)

A VS Code extension that calls the published API to review code directly from your editor,
with results shown in a Markdown panel.

### Extension Setup

1. **Start the API** (locally or on Azure):

   ```bash
   # Local
   uv run uvicorn src.web.app:app --reload --host 0.0.0.0 --port 8000

   # Or with Docker (no source code needed)
   docker run -d -p 8000:8000 --env-file .env \
     ghcr.io/isabelcabezasm/agent_reviewer:latest \
     uvicorn src.web.app:app --host 0.0.0.0 --port 8000
   ```

2. **Install the extension**:

   ```bash
   cd vscode-extension
   npm install && npm run compile
   npx vsce package
   code --install-extension isa-improvement-system-agent-0.3.0.vsix
   ```

3. **Configure** (VS Code Settings):
   - `agentReviewer.apiUrl` — API URL (default: `http://localhost:8000`)
   - `agentReviewer.instructions` — Default review instructions

### Commands

| Command | What It Does |
|---|---|
| **ISA: Review Current File** | Sends the full file to the API |
| **ISA: Review Selection** | Sends only selected code |
| **ISA: Review Uncommitted Changes** | Sends git diff of uncommitted changes |
| **ISA: Review Commited and Uncommited changes** | Diffs all branch changes (committed + uncommitted) against the default branch |
| **ISA: Review GitHub Repository** | Reviews a remote GitHub repo by URL |
| **ISA: Test API Connection** | Verifies the API server is reachable |

All commands are also in the **right-click context menu**.

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

# Or use GitHub Copilot instead:
cat > .env << EOF
AI_PROVIDER=copilot
GITHUB_TOKEN=ghp_your_token
COPILOT_MODEL_NAME=gpt-4.1
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

Then open **<http://localhost:8000>** — paste any repo URL + optional PAT and get a full review.

## Deploy to Azure

Deploy the API as an Azure Container App with a single command:

```bash
bin/deploy           # Full deploy (build + push + create Container App)
bin/deploy --update  # Update after code changes (rebuild image only)
bin/deploy --destroy # Tear down the Container App
```

This creates:

- An **Azure Container Registry** (`agentrevieweracr`) in resource group `my-tests`
- A **Container Apps Environment** with a public HTTPS endpoint
- A **Container App** running the API (scales to 0 when idle)

After deploy, the script prints the URL. Set it in the VS Code extension:

```text
agentReviewer.apiUrl = https://agent-reviewer.<region>.azurecontainerapps.io
```

## License

MIT
