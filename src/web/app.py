"""FastAPI web application for the Agent Reviewer.

Provides a web UI and REST API to review GitHub repositories
(including private ones) using Azure OpenAI.
"""

import re
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles  # pyright: ignore[reportUnknownVariableType]
from pydantic import BaseModel, Field

from src.config import AppConfig, ReviewConfig, load_config
from src.diff_utils import detect_language, read_files
from src.github_utils import cleanup_repo, clone_repo, get_default_branch_diff, get_repo_files
from src.prompts import build_system_prompt, build_user_prompt_diff, build_user_prompt_files
from src.ai_handler import AIHandler


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


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Agent Reviewer",
    description="AI-powered code review web service",
    version="0.1.0",
)

# Serve static files (HTML/CSS/JS)
STATIC_DIR = Path(__file__).parent / "static"
app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),  # pyright: ignore[reportUnknownArgumentType]
    name="static",
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
def serve_ui() -> FileResponse:
    """Serve the main web UI."""
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.post("/api/review", response_model=ReviewResponse)
def review_repo(request: ReviewRequest) -> ReviewResponse:
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
        config = AppConfig(azure=config.azure, review=review_cfg)

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

    ai = AIHandler(config.azure)
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
    ai = AIHandler(config.azure)
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
        data: dict[str, Any] = yaml.safe_load(yaml_text)  # pyright: ignore[reportUnknownMemberType]
        if isinstance(data, dict):
            # Flatten if wrapped in 'review' key
            return data.get("review", data)
        return None
    except yaml.YAMLError:  # pyright: ignore[reportUnknownMemberType]
        return None
