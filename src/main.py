"""Agent Reviewer CLI — local AI-powered code review tool.

Provides a command-line interface to review code changes or files
using Azure OpenAI, without requiring a Pull Request.

Usage examples:
    # Review all uncommitted changes (default)
    uv run python -m src.main

    # Review staged changes only
    uv run python -m src.main --staged

    # Review specific files (can be from any location)
    uv run python -m src.main --files src/config.py /other/repo/app.py

    # Review changes compared to a branch
    uv run python -m src.main --branch main

    # Review a specific commit
    uv run python -m src.main --commit HEAD~1

    # Review another repository
    uv run python -m src.main --repo /path/to/other/repo --staged

    # Add extra review instructions
    uv run python -m src.main --instructions "Focus on error handling"
"""

import argparse
import sys

from src.config import load_config
from src.reviewer import CodeReviewer


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI.

    Returns:
        argparse.ArgumentParser: The configured argument parser.
    """
    parser = argparse.ArgumentParser(
        prog="agent-reviewer",
        description=(
            "AI-powered local code reviewer. "
            "Reviews your code changes using Azure OpenAI "
            "without needing to create a Pull Request."
        ),
    )

    # Review mode (mutually exclusive)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--staged",
        action="store_true",
        help="Review only staged (git add) changes.",
    )
    mode.add_argument(
        "--files",
        nargs="+",
        metavar="FILE",
        help="Review specific files by their full contents.",
    )
    mode.add_argument(
        "--branch",
        type=str,
        metavar="BRANCH",
        help="Review changes compared to a target branch (e.g., main).",
    )
    mode.add_argument(
        "--commit",
        type=str,
        metavar="COMMIT",
        help="Review changes from a specific commit (e.g., HEAD~1).",
    )

    # Options
    parser.add_argument(
        "--repo",
        type=str,
        default=None,
        metavar="PATH",
        help="Path to another repository to review (for git-based modes).",
    )
    parser.add_argument(
        "--instructions",
        type=str,
        default="",
        help="Extra review instructions for the AI model.",
    )
    parser.add_argument(
        "--env",
        type=str,
        default=None,
        metavar="PATH",
        help="Path to a custom .env file.",
    )

    return parser


def main() -> None:
    """Run the Agent Reviewer CLI.

    Parses command-line arguments, loads configuration, and
    executes the appropriate review mode. Outputs the AI
    review to stdout.
    """
    parser = create_parser()
    args = parser.parse_args()

    # Load configuration
    try:
        config = load_config(env_path=args.env)
    except ValueError as e:
        print(f"❌ Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    # Apply extra instructions if provided
    if args.instructions:
        # Create a new config with updated review settings
        from src.config import AppConfig, ReviewConfig

        review_config = ReviewConfig(
            extra_instructions=args.instructions,
        )
        config = AppConfig(azure=config.azure, review=review_config)

    reviewer = CodeReviewer(config)

    repo_path: str | None = args.repo
    print("🔍 Agent Reviewer — Analyzing your code...\n")
    if repo_path:
        print(f"📂 Reviewing repository: {repo_path}\n")

    try:
        if args.staged:
            result = reviewer.review_staged(cwd=repo_path)
        elif args.files:
            result = reviewer.review_files(args.files)
        elif args.branch:
            result = reviewer.review_branch(branch=args.branch, cwd=repo_path)
        elif args.commit:
            result = reviewer.review_commit(commit=args.commit, cwd=repo_path)
        else:
            # Default: review all uncommitted changes
            result = reviewer.review_uncommitted(cwd=repo_path)

        print(result)

    except ValueError as e:
        print(f"⚠️  {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

