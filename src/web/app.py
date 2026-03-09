"""FastAPI web application for the Agent Reviewer.

Provides a web UI and REST API to review GitHub repositories
(including private ones) and raw code/diffs using Azure OpenAI
or GitHub Copilot. Designed to be called from VS Code extensions,
CI pipelines, or any HTTP client.
"""

import re
from pathlib import Path
from typing import Annotated, Any, cast

import yaml
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.config import AppConfig, ReviewConfig, load_config
from src.diff_utils import detect_language, read_files
from src.github_utils import cleanup_repo, clone_repo, get_default_branch_diff, get_repo_files
from src.handler_factory import create_handler
from src.prompts import build_system_prompt, build_user_prompt_diff, build_user_prompt_files
from src.web.auth import (
    create_session,
    get_api_key,
    invalidate_session,
    is_auth_enabled,
    validate_session,
    verify_api_key,
)

# ---------------------------------------------------------------------------
# Pydantic models for the API
# ---------------------------------------------------------------------------


class ReviewRequest(BaseModel):
    """Request body for the /api/review endpoint.

    Attributes:
        repo_url: GitHub repository URL to review.
        github_pat: Optional Personal Access Token for private repos.
        mode: Review mode — 'full', 'branch', or 'commit'.
        branch: Branch name (used when mode is 'branch').
        instructions: Extra review instructions for the AI.
        file_extensions: Optional file extensions filter.
        max_files: Maximum number of files to include.
    """

    repo_url: str
    github_pat: str | None = None
    mode: str = "full"
    branch: str | None = None
    instructions: str = ""
    file_extensions: list[str] | None = None
    max_files: int = Field(default=30, ge=1, le=100)


class ReviewResponse(BaseModel):
    """Response body for the /api/review endpoint.

    Attributes:
        raw_review: The raw AI response text.
        parsed_review: The parsed review as a dict (if YAML).
        files_reviewed: Number of files included in the review.
        repo_url: The repository that was reviewed.
    """

    raw_review: str
    parsed_review: dict[str, Any] | None = None
    files_reviewed: int = 0
    repo_url: str = ""


class CodeReviewRequest(BaseModel):
    """Request body for the /api/review/code endpoint.

    Lightweight endpoint — send code directly without a repo URL.
    Designed for VS Code extensions and other editor integrations.

    Attributes:
        code: The source code to review.
        language: Programming language (e.g., 'Python', 'TypeScript').
        filename: Optional filename for context.
        instructions: Extra review instructions for the AI.
    """

    code: str
    language: str = "auto-detect"
    filename: str = ""
    instructions: str = ""


class DiffReviewRequest(BaseModel):
    """Request body for the /api/review/diff endpoint.

    Send a git diff directly for review.

    Attributes:
        diff: The unified diff text.
        instructions: Extra review instructions for the AI.
    """

    diff: str
    instructions: str = ""


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Agent Reviewer",
    description="AI-powered code review web service",
    version="0.1.0",
)

# CORS — allow VS Code extensions and other clients to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (HTML/CSS/JS)
STATIC_DIR = Path(__file__).parent / "static"
app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static",
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/", response_model=None)
def serve_ui(request: Request) -> FileResponse | RedirectResponse:
    """Serve the main web UI or redirect to login."""
    if is_auth_enabled():
        token = request.cookies.get("session_token", "")
        if not validate_session(token):
            return RedirectResponse(url="/login")
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/login", response_model=None)
def serve_login() -> FileResponse | RedirectResponse:
    """Serve the login page, or redirect to UI if auth is disabled."""
    if not is_auth_enabled():
        return RedirectResponse(url="/")
    return FileResponse(str(STATIC_DIR / "login.html"))


class LoginRequest(BaseModel):
    """Login request body.

    Attributes:
        api_key: The API key to authenticate with.
    """

    api_key: str


@app.post("/auth/login")
def login(body: LoginRequest) -> JSONResponse:
    """Authenticate with API key and set session cookie."""
    import hmac as _hmac

    expected = get_api_key()
    if not expected:
        return JSONResponse({"error": "Auth not configured"}, status_code=500)

    if not _hmac.compare_digest(body.api_key.encode(), expected.encode()):
        return JSONResponse({"error": "Invalid API key"}, status_code=401)

    token = create_session()
    response = JSONResponse({"status": "ok"})
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=86400,  # 24 hours
    )
    return response


@app.post("/auth/logout")
def logout(request: Request) -> JSONResponse:
    """Invalidate session and clear cookie."""
    token = request.cookies.get("session_token", "")
    if token:
        invalidate_session(token)
    response = JSONResponse({"status": "logged_out"})
    response.delete_cookie("session_token")
    return response


@app.post("/api/review", response_model=ReviewResponse)
def review_repo(
    request: ReviewRequest,
    _key: Annotated[str | None, Depends(verify_api_key)] = None,
) -> ReviewResponse:
    """Review a GitHub repository.

    Clones the repository, collects code based on the selected mode,
    sends it to Azure OpenAI for review, and returns the results.

    Parameters:
        request: The review request with repo URL, PAT, mode, etc.

    Returns:
        ReviewResponse: The AI review with raw and parsed output.

    Raises:
        HTTPException: On clone failure, config error, or AI error.
    """
    # Load Azure config
    try:
        config = load_config()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Server config error: {e}") from e

    if request.instructions:
        review_cfg = ReviewConfig(extra_instructions=request.instructions)
        config = AppConfig(
            provider=config.provider,
            azure=config.azure,
            copilot=config.copilot,
            review=review_cfg,
        )

    # Clone the repository
    repo_path: str | None = None
    try:
        repo_path = clone_repo(
            repo_url=request.repo_url,
            github_pat=request.github_pat,
            branch=request.branch if request.mode == "branch" else None,
        )

        # Collect code based on mode
        if request.mode == "commit":
            diff = get_default_branch_diff(repo_path)
            if not diff:
                raise HTTPException(
                    status_code=400,
                    detail="No commit diff found in the repository.",
                )
            files_count = len(diff.splitlines())
            review_text = _review_with_diff(config, diff)

        elif request.mode == "branch":
            diff = get_default_branch_diff(repo_path, base_branch=request.branch or "main")
            if diff:
                files_count = len(diff.splitlines())
                review_text = _review_with_diff(config, diff)
            else:
                # Fall back to full file review
                review_text, files_count = _review_with_files(
                    config, repo_path, request.file_extensions, request.max_files
                )

        else:
            # Full repo review
            review_text, files_count = _review_with_files(
                config, repo_path, request.file_extensions, request.max_files
            )

        # Parse YAML from response
        parsed = _parse_review_yaml(review_text)

        return ReviewResponse(
            raw_review=review_text,
            parsed_review=parsed,
            files_reviewed=files_count,
            repo_url=request.repo_url,
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Review failed: {e}",
        ) from e
    finally:
        if repo_path:
            cleanup_repo(repo_path)


@app.get("/api/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Lightweight endpoints for VS Code / editor integrations
# ---------------------------------------------------------------------------


@app.post("/api/review/code", response_model=ReviewResponse)
def review_code(
    request: CodeReviewRequest,
    _key: Annotated[str | None, Depends(verify_api_key)] = None,
) -> ReviewResponse:
    """Review raw source code directly.

    Lightweight endpoint designed for VS Code extensions and
    other editor integrations. No repo cloning needed — just send
    the code as a string.

    Parameters:
        request: The code review request with source code,
            language, and optional instructions.

    Returns:
        ReviewResponse: The AI review with raw and parsed output.
    """
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="No code provided.")

    try:
        config = load_config()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Server config error: {e}") from e

    if request.instructions:
        review_cfg = ReviewConfig(extra_instructions=request.instructions)
        config = AppConfig(
            provider=config.provider,
            azure=config.azure,
            copilot=config.copilot,
            review=review_cfg,
        )

    ai = create_handler(config)

    # Build the code with line numbers and file header
    lines = request.code.splitlines()
    numbered = "\n".join(f"{i:4d} {line}" for i, line in enumerate(lines, 1))
    header = f"## File: '{request.filename}'" if request.filename else "## Code"
    formatted_code = f"{header}\n{numbered}"

    system_prompt = build_system_prompt(
        extra_instructions=config.review.extra_instructions,
    )
    user_prompt = build_user_prompt_files(
        code=formatted_code,
        language=request.language,
    )

    try:
        review_text = ai.chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        parsed = _parse_review_yaml(review_text)

        return ReviewResponse(
            raw_review=review_text,
            parsed_review=parsed,
            files_reviewed=1,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Review failed: {e}") from e


@app.post("/api/review/diff", response_model=ReviewResponse)
def review_diff(
    request: DiffReviewRequest,
    _key: Annotated[str | None, Depends(verify_api_key)] = None,
) -> ReviewResponse:
    """Review a git diff directly.

    Send a unified diff and get back a structured review.
    Ideal for pre-commit hooks and CI pipelines.

    Parameters:
        request: The diff review request.

    Returns:
        ReviewResponse: The AI review with raw and parsed output.
    """
    if not request.diff.strip():
        raise HTTPException(status_code=400, detail="No diff provided.")

    try:
        config = load_config()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Server config error: {e}") from e

    if request.instructions:
        review_cfg = ReviewConfig(extra_instructions=request.instructions)
        config = AppConfig(
            provider=config.provider,
            azure=config.azure,
            copilot=config.copilot,
            review=review_cfg,
        )

    try:
        review_text = _review_with_diff(config, request.diff)
        parsed = _parse_review_yaml(review_text)

        return ReviewResponse(
            raw_review=review_text,
            parsed_review=parsed,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Review failed: {e}") from e


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _review_with_diff(config: AppConfig, diff: str) -> str:
    """Send a diff to the AI for review.

    Parameters:
        config: Application configuration.
        diff: Unified diff string.

    Returns:
        str: The AI review response.
    """
    from src.diff_utils import get_changed_files_from_diff

    ai = create_handler(config)
    changed_files = get_changed_files_from_diff(diff)
    language = detect_language(changed_files)

    system_prompt = build_system_prompt(
        extra_instructions=config.review.extra_instructions,
    )
    user_prompt = build_user_prompt_diff(diff=diff, language=language)

    return ai.chat_completion(system_prompt=system_prompt, user_prompt=user_prompt)


def _review_with_files(
    config: AppConfig,
    repo_path: str,
    extensions: list[str] | None,
    max_files: int,
) -> tuple[str, int]:
    """Read repo files and send to the AI for review.

    Parameters:
        config: Application configuration.
        repo_path: Path to the cloned repository.
        extensions: File extensions to include.
        max_files: Maximum number of files.

    Returns:
        tuple: (review_text, files_count)
    """
    ai = create_handler(config)
    file_paths = get_repo_files(repo_path, extensions=extensions, max_files=max_files)

    if not file_paths:
        raise ValueError("No matching code files found in the repository.")

    code = read_files(file_paths)
    language = detect_language(file_paths)

    system_prompt = build_system_prompt(
        extra_instructions=config.review.extra_instructions,
    )
    user_prompt = build_user_prompt_files(code=code, language=language)

    review_text = ai.chat_completion(system_prompt=system_prompt, user_prompt=user_prompt)
    return review_text, len(file_paths)


def _parse_review_yaml(raw_text: str) -> dict[str, Any] | None:
    """Extract and parse YAML from the AI response.

    The AI response may contain YAML inside a code fence.
    This function extracts and parses it.

    Parameters:
        raw_text: The raw AI response text.

    Returns:
        The parsed review dict, or None if parsing fails.
    """
    # Try to extract YAML from code fence
    yaml_match = re.search(r"```ya?ml\s*\n(.*?)```", raw_text, re.DOTALL)
    yaml_text = yaml_match.group(1) if yaml_match else raw_text

    try:
        parsed_data: object = yaml.safe_load(yaml_text)
        if not isinstance(parsed_data, dict):
            return None
        data = cast(dict[str, Any], parsed_data)
        return data.get("review", data)
    except yaml.YAMLError:
        return None
