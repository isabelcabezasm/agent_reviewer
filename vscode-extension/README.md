# Agent Reviewer — VS Code Extension

AI-powered code review directly in your editor. Reviews files, selections, or git diffs
by calling the Agent Reviewer API.

## Setup

### 1. Start the API server

```bash
# Option A: Run locally (if you have the agent_reviewer repo)
cd agent_reviewer
uv run uvicorn src.web.app:app --reload --host 0.0.0.0 --port 8000

# Option B: Run with Docker (no source code needed)
docker run -d -p 8000:8000 --env-file .env \
  ghcr.io/isabelcabezasm/agent_reviewer:latest \
  uvicorn src.web.app:app --host 0.0.0.0 --port 8000
```

### 2. Install the extension

```bash
cd vscode-extension
npm install
npm run compile
npx vsce package
code --install-extension agent-reviewer-0.1.0.vsix
```

### 3. Configure (optional)

In VS Code settings:

- `agentReviewer.apiUrl` — API server URL (default: `http://localhost:8000`)
- `agentReviewer.instructions` — Default review instructions for every review

## Commands

| Command | Description |
|---|---|
| `Agent Reviewer: Review Current File` | Reviews the entire active file |
| `Agent Reviewer: Review Selection` | Reviews only the selected code |
| `Agent Reviewer: Review Uncommitted Changes` | Reviews git staged/unstaged changes |

All commands are also available in the **editor right-click menu**.

## How It Works

1. You trigger a review command in VS Code
2. The extension sends your code/diff to the Agent Reviewer API
3. The API sends it to Azure OpenAI for analysis
4. Results appear in a styled Markdown panel beside your code

Your code is sent to **your own** API server — nothing goes to third parties except Azure OpenAI.
