"""GitHub repository utilities for cloning and reading remote repos.

Provides functions to clone repositories (including private ones
via PAT) into temporary directories and extract code for review.
"""

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def clone_repo(
    repo_url: str,
    github_pat: str | None = None,
    branch: str | None = None,
) -> str:
    """Clone a GitHub repository into a temporary directory.

    Supports both public and private repos. For private repos,
    a GitHub Personal Access Token (PAT) is injected into the
    clone URL.

    Parameters:
        repo_url: The GitHub repository URL
            (e.g., https://github.com/owner/repo).
        github_pat: Optional GitHub Personal Access Token for
            private repository access.
        branch: Optional branch name to clone. Defaults to the
            repo's default branch.

    Returns:
        str: Path to the temporary directory containing the clone.

    Raises:
        subprocess.CalledProcessError: If git clone fails.
        ValueError: If the repo URL is invalid.
    """
    if not repo_url:
        raise ValueError("Repository URL is required.")

    logger.info("Cloning repository: %s", repo_url)

    # Normalize URL: remove trailing .git and slashes
    clean_url = repo_url.rstrip("/")
    if not clean_url.endswith(".git"):
        clean_url += ".git"

    # Inject PAT for authentication if provided
    auth_url = clean_url
    if github_pat:
        # https://github.com/owner/repo.git -> https://PAT@github.com/owner/repo.git
        auth_url = clean_url.replace("https://", f"https://{github_pat}@")

    tmp_dir = tempfile.mkdtemp(prefix="agent_reviewer_")

    cmd = ["git", "clone"]
    if branch:
        cmd.extend(["--branch", branch])
    else:
        cmd.extend(["--depth", "1"])
    cmd.extend([auth_url, tmp_dir])

    try:
        _ = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        # Clean up on failure
        cleanup_repo(tmp_dir)
        # Sanitize error message to not leak PAT
        error_msg = e.stderr or e.stdout or "Unknown error"
        if github_pat:
            error_msg = error_msg.replace(github_pat, "***")
        raise ValueError(f"Failed to clone repository: {error_msg}") from e

    return tmp_dir


def cleanup_repo(repo_path: str) -> None:
    """Remove a cloned repository temporary directory.

    Parameters:
        repo_path: Path to the temporary directory to remove.
    """
    if repo_path and Path(repo_path).exists():
        shutil.rmtree(repo_path, ignore_errors=True)


def get_repo_files(
    repo_path: str,
    extensions: list[str] | None = None,
    max_files: int = 50,
) -> list[str]:
    """List code files in a cloned repository.

    Filters out common non-code directories and files.

    Parameters:
        repo_path: Path to the cloned repository.
        extensions: Optional list of file extensions to include
            (e.g., ['.py', '.js']). If None, uses a default set.
        max_files: Maximum number of files to return.

    Returns:
        list[str]: List of file paths relative to repo root.
    """
    if extensions is None:
        extensions = [
            ".py",
            ".js",
            ".ts",
            ".tsx",
            ".jsx",
            ".java",
            ".cs",
            ".go",
            ".rs",
            ".rb",
            ".cpp",
            ".c",
            ".h",
            ".swift",
            ".kt",
            ".sh",
            ".sql",
        ]

    skip_dirs = {
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        "dist",
        "build",
        ".next",
        "vendor",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        "coverage",
        ".coverage",
        "htmlcov",
    }

    repo = Path(repo_path)
    files: list[str] = []

    for path in sorted(repo.rglob("*")):
        if len(files) >= max_files:
            break

        # Skip excluded directories
        if any(skip in path.parts for skip in skip_dirs):
            continue

        if path.is_file() and path.suffix.lower() in extensions:
            files.append(str(path))

    return files


def _detect_default_branch(repo_path: str) -> str:
    """Detect the default branch name from origin/HEAD."""
    try:
        result = subprocess.run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
            capture_output=True, text=True, check=True, cwd=repo_path,
        )
        # refs/remotes/origin/develop -> develop
        return result.stdout.strip().split("/")[-1]
    except subprocess.CalledProcessError:
        return "main"


def get_default_branch_diff(
    repo_path: str,
    base_branch: str = "auto",
) -> str:
    """Get the diff between the current branch and a base branch.

    For branch reviews, diffs the current HEAD against the
    merge-base with the base branch. Auto-detects the default
    branch (main, master, develop, etc.) from origin/HEAD.

    Parameters:
        repo_path: Path to the cloned repository.
        base_branch: The base branch to diff against.
            Use 'auto' to auto-detect from origin/HEAD.

    Returns:
        str: The unified diff, or empty string if unavailable.
    """
    if base_branch == "auto":
        base_branch = _detect_default_branch(repo_path)
    logger.info("Diffing against base branch: %s", base_branch)

    try:
        merge_base = subprocess.run(
            ["git", "merge-base", f"origin/{base_branch}", "HEAD"],
            capture_output=True, text=True, check=True, cwd=repo_path,
        )
        base_commit = merge_base.stdout.strip()
        if not base_commit:
            return ""

        diff_result = subprocess.run(
            ["git", "diff", base_commit, "HEAD"],
            capture_output=True, text=True, check=True, cwd=repo_path,
        )
        return diff_result.stdout.strip()
    except subprocess.CalledProcessError:
        # Fallback: diff last commit only
        try:
            diff_result = subprocess.run(
                ["git", "diff", "HEAD~1..HEAD"],
                capture_output=True, text=True, check=False, cwd=repo_path,
            )
            return diff_result.stdout.strip()
        except subprocess.CalledProcessError:
            return ""
