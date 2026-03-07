"""Git diff and file utilities for collecting code to review.

Provides functions to retrieve git diffs (staged, unstaged,
branch comparisons) and read file contents for review.
"""

import subprocess
from pathlib import Path


def run_git_command(args: list[str], cwd: str | None = None) -> str:
    """Execute a git command and return its stdout.

    Parameters:
        args: The git command arguments (without 'git' prefix).
        cwd: The working directory for the git command.
            Defaults to the current directory.

    Returns:
        str: The command's standard output, stripped of
            trailing whitespace.

    Raises:
        subprocess.CalledProcessError: If the git command
            exits with a non-zero return code.
    """
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=True,
        cwd=cwd,
    )
    return result.stdout.strip()


def get_staged_diff(cwd: str | None = None) -> str:
    """Get the diff of staged (indexed) changes.

    Parameters:
        cwd: The working directory for the git command.

    Returns:
        str: The unified diff of staged changes.
    """
    return run_git_command(["diff", "--staged"], cwd=cwd)


def get_unstaged_diff(cwd: str | None = None) -> str:
    """Get the diff of unstaged working tree changes.

    Parameters:
        cwd: The working directory for the git command.

    Returns:
        str: The unified diff of unstaged changes.
    """
    return run_git_command(["diff"], cwd=cwd)


def get_all_uncommitted_diff(cwd: str | None = None) -> str:
    """Get the combined diff of all uncommitted changes.

    Includes both staged and unstaged changes by comparing
    HEAD to the working tree.

    Parameters:
        cwd: The working directory for the git command.

    Returns:
        str: The unified diff of all uncommitted changes.
    """
    return run_git_command(["diff", "HEAD"], cwd=cwd)


def get_branch_diff(
    branch: str = "main",
    cwd: str | None = None,
) -> str:
    """Get the diff between current HEAD and a target branch.

    Parameters:
        branch: The branch to compare against. Defaults to 'main'.
        cwd: The working directory for the git command.

    Returns:
        str: The unified diff between the branch and HEAD.
    """
    return run_git_command(["diff", f"{branch}...HEAD"], cwd=cwd)


def get_commit_diff(
    commit: str = "HEAD~1",
    cwd: str | None = None,
) -> str:
    """Get the diff for a specific commit or commit range.

    Parameters:
        commit: The commit reference (e.g., 'HEAD~1', 'abc123').
            Defaults to the last commit.
        cwd: The working directory for the git command.

    Returns:
        str: The unified diff for the specified commit.
    """
    return run_git_command(["diff", f"{commit}..HEAD"], cwd=cwd)


def read_files(file_paths: list[str]) -> str:
    """Read and concatenate the contents of multiple files.

    Each file's content is prefixed with a header showing the
    file path, similar to pr-agent's diff format.

    Parameters:
        file_paths: List of file paths to read.

    Returns:
        str: The concatenated file contents with headers.

    Raises:
        FileNotFoundError: If any specified file does not exist.
    """
    sections: list[str] = []
    for file_path in file_paths:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content = path.read_text(encoding="utf-8")
        # Add line numbers to each line for precise review references
        numbered_lines: list[str] = []
        for i, line in enumerate(content.splitlines(), start=1):
            numbered_lines.append(f"{i:4d} {line}")
        numbered_content = "\n".join(numbered_lines)

        sections.append(f"## File: '{file_path}'\n{numbered_content}")
    return "\n\n".join(sections)


def detect_language(file_paths: list[str]) -> str:
    """Detect the primary programming language from file extensions.

    Parameters:
        file_paths: List of file paths to analyze.

    Returns:
        str: The detected primary language name, or
            'auto-detect' if no known extension is found.
    """
    extension_map: dict[str, str] = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".tsx": "TypeScript (React)",
        ".jsx": "JavaScript (React)",
        ".java": "Java",
        ".cs": "C#",
        ".rb": "Ruby",
        ".go": "Go",
        ".rs": "Rust",
        ".cpp": "C++",
        ".c": "C",
        ".swift": "Swift",
        ".kt": "Kotlin",
        ".sh": "Shell",
        ".yaml": "YAML",
        ".yml": "YAML",
        ".json": "JSON",
        ".md": "Markdown",
        ".sql": "SQL",
    }

    # Count occurrences of each language
    lang_counts: dict[str, int] = {}
    for fp in file_paths:
        ext = Path(fp).suffix.lower()
        lang = extension_map.get(ext)
        if lang:
            lang_counts[lang] = lang_counts.get(lang, 0) + 1

    if not lang_counts:
        return "auto-detect"

    # Return the most common language
    return max(lang_counts, key=lambda k: lang_counts[k])


def get_changed_files_from_diff(diff: str) -> list[str]:
    """Extract file paths from a unified diff.

    Parameters:
        diff: A unified diff string.

    Returns:
        list[str]: List of file paths found in the diff.
    """
    files: list[str] = []
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            files.append(line[6:])
    return files
