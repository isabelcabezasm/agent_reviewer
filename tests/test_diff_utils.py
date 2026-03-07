"""Tests for diff utilities module."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.diff_utils import (
    detect_language,
    get_changed_files_from_diff,
    get_staged_diff,
    read_files,
    run_git_command,
)


class TestRunGitCommand:
    """Tests for the run_git_command function."""

    @patch("src.diff_utils.subprocess.run")
    def test_runs_git_command_and_returns_stdout(
        self,
        mock_run: MagicMock,
    ) -> None:
        """Test that git command output is returned stripped."""
        mock_run.return_value = MagicMock(stdout="  output text  \n")
        result = run_git_command(["status"])
        assert result == "output text"
        mock_run.assert_called_once_with(
            ["git", "status"],
            capture_output=True,
            text=True,
            check=True,
            cwd=None,
        )

    @patch("src.diff_utils.subprocess.run")
    def test_passes_cwd_to_subprocess(
        self,
        mock_run: MagicMock,
    ) -> None:
        """Test that custom working directory is passed through."""
        mock_run.return_value = MagicMock(stdout="output")
        _ = run_git_command(["diff"], cwd="/tmp/repo")
        mock_run.assert_called_once_with(
            ["git", "diff"],
            capture_output=True,
            text=True,
            check=True,
            cwd="/tmp/repo",
        )

    @patch("src.diff_utils.subprocess.run")
    def test_raises_on_git_error(
        self,
        mock_run: MagicMock,
    ) -> None:
        """Test that CalledProcessError propagates from git."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")
        with pytest.raises(subprocess.CalledProcessError):
            _ = run_git_command(["invalid-command"])


class TestGetStagedDiff:
    """Tests for the get_staged_diff function."""

    @patch("src.diff_utils.run_git_command")
    def test_calls_git_diff_staged(
        self,
        mock_git: MagicMock,
    ) -> None:
        """Test that staged diff calls correct git command."""
        mock_git.return_value = "diff content"
        result = get_staged_diff()
        assert result == "diff content"
        mock_git.assert_called_once_with(["diff", "--staged"], cwd=None)


class TestDetectLanguage:
    """Tests for the detect_language function."""

    def test_detects_python(self) -> None:
        """Test Python language detection from .py files."""
        assert detect_language(["src/main.py", "src/utils.py"]) == "Python"

    def test_detects_typescript(self) -> None:
        """Test TypeScript detection from .ts files."""
        assert detect_language(["app.ts", "utils.ts"]) == "TypeScript"

    def test_returns_most_common_language(self) -> None:
        """Test that most common language wins with mixed files."""
        files = ["a.py", "b.py", "c.js"]
        assert detect_language(files) == "Python"

    def test_returns_auto_detect_for_unknown(self) -> None:
        """Test fallback for unknown extensions."""
        assert detect_language(["file.xyz", "other.abc"]) == "auto-detect"

    def test_returns_auto_detect_for_empty_list(self) -> None:
        """Test fallback for empty file list."""
        assert detect_language([]) == "auto-detect"


class TestGetChangedFilesFromDiff:
    """Tests for extracting file paths from diffs."""

    def test_extracts_files_from_unified_diff(self) -> None:
        """Test file path extraction from a standard unified diff."""
        diff = (
            "diff --git a/src/main.py b/src/main.py\n"
            "--- a/src/main.py\n"
            "+++ b/src/main.py\n"
            "@@ -1,3 +1,3 @@\n"
            "-old line\n"
            "+new line\n"
            "diff --git a/src/utils.py b/src/utils.py\n"
            "--- a/src/utils.py\n"
            "+++ b/src/utils.py\n"
        )
        files = get_changed_files_from_diff(diff)
        assert files == ["src/main.py", "src/utils.py"]

    def test_returns_empty_for_no_diff(self) -> None:
        """Test empty list for empty diff string."""
        assert get_changed_files_from_diff("") == []


class TestReadFiles:
    """Tests for reading file contents."""

    def test_reads_existing_file(self, tmp_path: Path) -> None:
        """Test that existing files are read with line numbers."""
        test_file = tmp_path / "test.py"
        _ = test_file.write_text("line 1\nline 2\nline 3\n")
        result = read_files([str(test_file)])
        assert "## File:" in result
        assert "   1 line 1" in result
        assert "   2 line 2" in result
        assert "   3 line 3" in result

    def test_raises_for_missing_file(self) -> None:
        """Test FileNotFoundError for non-existent files."""
        with pytest.raises(FileNotFoundError, match="File not found"):
            _ = read_files(["/nonexistent/file.py"])

    def test_reads_multiple_files(self, tmp_path: Path) -> None:
        """Test concatenation of multiple files."""
        file1 = tmp_path / "a.py"
        file2 = tmp_path / "b.py"
        _ = file1.write_text("code a\n")
        _ = file2.write_text("code b\n")
        result = read_files([str(file1), str(file2)])
        assert "a.py" in result
        assert "b.py" in result
