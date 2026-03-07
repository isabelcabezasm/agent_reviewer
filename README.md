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
├── main.py          # CLI entry point (argparse)
├── config.py        # Configuration loading from .env
├── ai_handler.py    # Azure OpenAI API client
├── reviewer.py      # Core review orchestrator
├── prompts.py       # Review prompt templates
└── diff_utils.py    # Git diff & file utilities
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
| `bin/lint/all` | Run all linters |
| `bin/lint/py` | Format, lint, and type-check Python files |
| `bin/lint/md` | Lint Markdown files |
| `bin/test` | Run all unit tests |
| `uv run pytest tests/ -v` | Run tests with verbose output |

## License

MIT