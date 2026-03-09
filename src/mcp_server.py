"""MCP server for the Agent Reviewer.

Exposes the code-review capabilities of Agent Reviewer as
Model Context Protocol (MCP) tools so that GitHub Copilot
(or any MCP-compatible client) can request AI code reviews.

Start with:
    uv run python -m src.mcp_server          # stdio (VS Code)
    uv run python -m src.mcp_server --sse     # SSE  (HTTP)
"""

from __future__ import annotations

import logging
import sys

from mcp.server.fastmcp import FastMCP

from src.config import AppConfig, ReviewConfig
from src.diff_utils import (
    detect_language,
    get_all_uncommitted_diff,
    get_branch_diff,
    get_changed_files_from_diff,
    get_commit_diff,
    get_staged_diff,
    read_files,
)
from src.github_utils import get_repo_files
from src.handler_factory import create_handler
from src.prompts import (
    build_system_prompt,
    build_user_prompt_diff,
    build_user_prompt_files,
)

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# MCP server instance
# -------------------------------------------------------------------


def _build_mcp() -> FastMCP:
    """Create the FastMCP server instance.

    When ``MCP_ALLOWED_HOSTS`` is set (comma-separated), those
    hosts are added to the transport security allow list. This is
    required when the server runs behind a reverse proxy (e.g.,
    Azure Container Apps) whose external hostname differs from
    the internal bind address.

    If the env var is set to ``*``, DNS rebinding protection is
    disabled entirely (convenient for development / trusted
    networks).

    Returns:
        FastMCP: The configured MCP server instance.
    """
    import os

    from mcp.server.transport_security import TransportSecuritySettings

    allowed_raw = os.getenv("MCP_ALLOWED_HOSTS", "")

    transport_security: TransportSecuritySettings | None = None
    if allowed_raw == "*":
        transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=False,
        )
    elif allowed_raw:
        hosts = [h.strip() for h in allowed_raw.split(",") if h.strip()]
        transport_security = TransportSecuritySettings(
            allowed_hosts=hosts,
        )

    return FastMCP(
        "Agent Reviewer",
        instructions=(
            "AI-powered code review tools. Reviews code changes, "
            "diffs, files, and git history using Azure OpenAI "
            "or GitHub Copilot."
        ),
        transport_security=transport_security,
    )


mcp = _build_mcp()

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------


def _load_config(
    extra_instructions: str = "",
) -> AppConfig:
    """Build an AppConfig from environment variables.

    Auto-detects the AI provider (Azure or Copilot) from
    available environment variables.

    Parameters:
        extra_instructions: Additional review instructions
            provided by the caller.

    Returns:
        AppConfig: The fully populated application config.

    Raises:
        ValueError: If required env vars are missing.
    """
    from dotenv import load_dotenv

    from src.config import load_config

    _ = load_dotenv()
    config = load_config()

    if extra_instructions:
        review = ReviewConfig(extra_instructions=extra_instructions)
        config = AppConfig(
            provider=config.provider,
            azure=config.azure,
            copilot=config.copilot,
            review=review,
        )
    return config


def _do_review_diff(
    diff: str,
    extra_instructions: str = "",
) -> str:
    """Review a unified diff string through the AI model.

    Parameters:
        diff: The unified diff text.
        extra_instructions: Optional extra review instructions.

    Returns:
        str: The AI-generated review in YAML format.
    """
    config = _load_config(extra_instructions)
    handler = create_handler(config)

    changed_files = get_changed_files_from_diff(diff)
    language = detect_language(changed_files)

    system_prompt = build_system_prompt(
        extra_instructions=config.review.extra_instructions,
    )
    user_prompt = build_user_prompt_diff(
        diff=diff,
        language=language,
    )
    return handler.chat_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )


def _do_review_files(
    file_paths: list[str],
    extra_instructions: str = "",
) -> str:
    """Review specific files through the AI model.

    Parameters:
        file_paths: List of absolute file paths to review.
        extra_instructions: Optional extra review instructions.

    Returns:
        str: The AI-generated review in YAML format.
    """
    config = _load_config(extra_instructions)
    handler = create_handler(config)

    code = read_files(file_paths)
    language = detect_language(file_paths)

    system_prompt = build_system_prompt(
        extra_instructions=config.review.extra_instructions,
    )
    user_prompt = build_user_prompt_files(
        code=code,
        language=language,
    )
    return handler.chat_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )


# -------------------------------------------------------------------
# MCP Tools
# -------------------------------------------------------------------


@mcp.tool()
def review_staged_changes(
    repo_path: str = ".",
    instructions: str = "",
) -> str:
    """Review staged (git add) changes in a repository.

    Analyzes only the changes that have been staged with
    ``git add`` and returns a structured code review.

    Parameters:
        repo_path: Path to the git repository. Defaults to
            the current directory.
        instructions: Extra review instructions for the AI
            (e.g., "Focus on error handling").

    Returns:
        str: A structured code review in YAML format.
    """
    diff = get_staged_diff(cwd=repo_path)
    if not diff:
        return "No staged changes found. Stage files with `git add` first."
    return _do_review_diff(diff, extra_instructions=instructions)


@mcp.tool()
def review_uncommitted_changes(
    repo_path: str = ".",
    instructions: str = "",
) -> str:
    """Review all uncommitted changes (staged + unstaged).

    Compares HEAD to the working tree and returns a structured
    code review covering every pending change.

    Parameters:
        repo_path: Path to the git repository. Defaults to
            the current directory.
        instructions: Extra review instructions for the AI.

    Returns:
        str: A structured code review in YAML format.
    """
    diff = get_all_uncommitted_diff(cwd=repo_path)
    if not diff:
        return "No uncommitted changes found."
    return _do_review_diff(diff, extra_instructions=instructions)


@mcp.tool()
def review_branch_changes(
    branch: str = "main",
    repo_path: str = ".",
    instructions: str = "",
) -> str:
    """Review changes compared to a target branch.

    Shows a structured review of everything that differs
    between the current HEAD and the specified branch.

    Parameters:
        branch: Branch to compare against (e.g., ``main``).
        repo_path: Path to the git repository.
        instructions: Extra review instructions for the AI.

    Returns:
        str: A structured code review in YAML format.
    """
    diff = get_branch_diff(branch=branch, cwd=repo_path)
    if not diff:
        return f"No changes found compared to branch '{branch}'."
    return _do_review_diff(diff, extra_instructions=instructions)


@mcp.tool()
def review_commit(
    commit: str = "HEAD~1",
    repo_path: str = ".",
    instructions: str = "",
) -> str:
    """Review changes introduced by a specific commit.

    Compares the given commit reference to HEAD and returns
    a structured code review.

    Parameters:
        commit: Commit reference (e.g., ``HEAD~1``, a SHA).
        repo_path: Path to the git repository.
        instructions: Extra review instructions for the AI.

    Returns:
        str: A structured code review in YAML format.
    """
    diff = get_commit_diff(commit=commit, cwd=repo_path)
    if not diff:
        return f"No changes found for commit '{commit}'."
    return _do_review_diff(diff, extra_instructions=instructions)


@mcp.tool()
def review_files(
    file_paths: list[str],
    instructions: str = "",
) -> str:
    """Review specific files by their full contents.

    Reads each file, sends the contents to the AI model,
    and returns a structured code review.

    Parameters:
        file_paths: List of absolute or relative file paths
            to review.
        instructions: Extra review instructions for the AI.

    Returns:
        str: A structured code review in YAML format.
    """
    if not file_paths:
        return "No file paths provided."
    return _do_review_files(file_paths, extra_instructions=instructions)


@mcp.tool()
def review_repository(
    repo_path: str = ".",
    file_extensions: list[str] | None = None,
    max_files: int = 30,
    instructions: str = "",
) -> str:
    """Review an entire repository by scanning its code files.

    Collects all code files (filtered by extension) from the
    repository directory, reads their contents, and sends them
    to the AI model for a comprehensive review.

    Parameters:
        repo_path: Path to the repository root. Defaults to
            the current directory.
        file_extensions: Optional list of extensions to include
            (e.g., ``[".py", ".ts"]``). Defaults to common
            code extensions.
        max_files: Maximum number of files to review (1-100).
            Keeps cost and latency manageable.
        instructions: Extra review instructions for the AI.

    Returns:
        str: A structured code review in YAML format.
    """
    files = get_repo_files(
        repo_path=repo_path,
        extensions=file_extensions,
        max_files=max_files,
    )
    if not files:
        return (
            "No code files found in the repository. "
            "Check the path or adjust file_extensions."
        )
    return _do_review_files(files, extra_instructions=instructions)


@mcp.tool()
def review_current_branch(
    base_branch: str = "main",
    repo_path: str = ".",
    instructions: str = "",
) -> str:
    """Review all changes on the current branch vs a base branch.

    Computes the diff between the current HEAD and the base
    branch (e.g., ``main``) and returns a structured review
    of every change introduced on this branch.

    This is the recommended tool when the user asks to
    "review my branch" or "review what I changed".

    Parameters:
        base_branch: The branch to compare against.
            Defaults to ``main``.
        repo_path: Path to the git repository.
        instructions: Extra review instructions for the AI.

    Returns:
        str: A structured code review in YAML format.
    """
    diff = get_branch_diff(branch=base_branch, cwd=repo_path)
    if not diff:
        return (
            f"No changes found on the current branch "
            f"compared to '{base_branch}'."
        )
    return _do_review_diff(diff, extra_instructions=instructions)


@mcp.tool()
def review_code_snippet(
    code: str,
    language: str = "auto-detect",
    instructions: str = "",
) -> str:
    """Review a raw code snippet (no git/files needed).

    Accepts code directly and returns a structured review.
    Ideal for reviewing code pasted by the user or extracted
    from an editor selection.

    Parameters:
        code: The source code to review.
        language: Programming language (e.g., ``Python``).
        instructions: Extra review instructions for the AI.

    Returns:
        str: A structured code review in YAML format.
    """
    config = _load_config(instructions)
    handler = create_handler(config)

    system_prompt = build_system_prompt(
        extra_instructions=config.review.extra_instructions,
    )
    user_prompt = build_user_prompt_files(
        code=code,
        language=language,
    )
    return handler.chat_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )


@mcp.tool()
def review_diff(
    diff: str,
    instructions: str = "",
) -> str:
    """Review a raw unified diff (no git repo needed).

    Accepts a diff string directly and returns a structured
    review. Useful when the diff is already available (e.g.,
    from a CI pipeline or PR webhook).

    Parameters:
        diff: The unified diff text to review.
        instructions: Extra review instructions for the AI.

    Returns:
        str: A structured code review in YAML format.
    """
    if not diff.strip():
        return "Empty diff provided — nothing to review."
    return _do_review_diff(diff, extra_instructions=instructions)


# -------------------------------------------------------------------
# Entry point
# -------------------------------------------------------------------


def _parse_transport() -> str:
    """Detect the requested transport from CLI arguments.

    Supports ``--sse``, ``--streamable-http``, and ``--stdio``
    (the default).

    Returns:
        str: One of ``stdio``, ``sse``, or ``streamable-http``.
    """
    for arg in sys.argv[1:]:
        if arg in ("--sse", "--streamable-http"):
            return arg.lstrip("-")
    return "stdio"


def _build_http_app() -> object:
    """Build a Starlette ASGI app with optional bearer-token auth.

    If ``AGENT_REVIEWER_API_KEY`` is set, requests must include
    an ``Authorization: Bearer <key>`` header. This secures the
    MCP server when deployed as a remote HTTP service.

    Returns:
        The ASGI application ready for ``uvicorn``.
    """
    import os

    from starlette.requests import Request as StarletteRequest
    from starlette.responses import JSONResponse
    from starlette.types import ASGIApp, Receive, Scope, Send

    api_key = os.getenv("AGENT_REVIEWER_API_KEY", "")
    transport = _parse_transport()

    if transport == "sse":
        inner_app: ASGIApp = mcp.sse_app()
    else:
        inner_app = mcp.streamable_http_app()

    if not api_key:
        return inner_app

    # Wrap with bearer-token authentication
    class BearerAuthMiddleware:
        """ASGI middleware that validates Bearer tokens.

        Wraps the MCP app and rejects requests that do not
        carry a valid ``Authorization: Bearer <key>`` header.
        The ``/health`` path is always allowed without auth.
        """

        def __init__(self, app: ASGIApp) -> None:
            self.app = app

        async def __call__(
            self,
            scope: Scope,
            receive: Receive,
            send: Send,
        ) -> None:
            """Validate the Authorization header on HTTP requests."""
            if scope["type"] != "http":
                await self.app(scope, receive, send)
                return

            request = StarletteRequest(scope)
            path = request.url.path

            # Allow health checks without auth
            if path == "/health":
                response = JSONResponse({"status": "ok"})
                await response(scope, receive, send)
                return

            auth_header = request.headers.get("authorization", "")
            if not auth_header.startswith("Bearer "):
                response = JSONResponse(
                    {"error": "Missing or invalid Authorization header"},
                    status_code=401,
                )
                await response(scope, receive, send)
                return

            token = auth_header[7:]
            if token != api_key:
                response = JSONResponse(
                    {"error": "Invalid API key"},
                    status_code=403,
                )
                await response(scope, receive, send)
                return

            await self.app(scope, receive, send)

    return BearerAuthMiddleware(inner_app)


def main() -> None:
    """Run the MCP server.

    Transport modes:
        - ``stdio``  (default) — for local VS Code / Copilot
        - ``--sse``  — HTTP Server-Sent Events
        - ``--streamable-http`` — HTTP streamable transport

    For HTTP modes, set ``AGENT_REVIEWER_API_KEY`` to require
    bearer-token authentication.

    Environment variables for HTTP mode:
        - ``MCP_HOST`` — bind address (default: ``0.0.0.0``)
        - ``MCP_PORT`` — port number (default: ``8080``)
    """
    import os

    transport = _parse_transport()

    if transport == "stdio":
        logger.info("Starting Agent Reviewer MCP server (stdio)")
        mcp.run(transport="stdio")
    else:
        import uvicorn

        app = _build_http_app()
        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_PORT", "8080"))
        logger.info(
            "Starting Agent Reviewer MCP server (%s) on %s:%s",
            transport,
            host,
            port,
        )
        uvicorn.run(
            app,  # type: ignore[arg-type]
            host=host,
            port=port,
        )


if __name__ == "__main__":
    main()
