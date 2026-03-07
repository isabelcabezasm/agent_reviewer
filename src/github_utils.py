"""GitHub repository utilities for cloning and reading remote repos.

Provides functions to clone repositories (including private ones
via PAT) into temporary directories and extract code for review.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path


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

    cmd = ["git", "clone", "--depth", "1"]
    if branch:
        cmd.extend(["--branch", branch])
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


def get_default_branch_diff(
    repo_path: str,
    base_branch: str = "main",
) -> str:
    """Get the diff of the default branch's latest commit.

    Parameters:
        repo_path: Path to the cloned repository.
        base_branch: The base branch name.

    Returns:
        str: The diff of the latest commit, or empty string
            if no commits exist.
    """
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo_path,
        )
        if not result.stdout.strip():
            return ""

        diff_result = subprocess.run(
            ["git", "diff", "HEAD~1..HEAD"],
            capture_output=True,
            text=True,
            check=False,
            cwd=repo_path,
        )
        return diff_result.stdout.strip()
    except subprocess.CalledProcessError:
        return ""
