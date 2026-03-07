"""Tests for the GitHub repository utilities."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.github_utils import (
    cleanup_repo,
    clone_repo,
    get_repo_files,
)


class TestCloneRepo:
    """Tests for the clone_repo function."""

    def test_raises_on_empty_url(self) -> None:
        """Test that empty URL raises ValueError."""
        with pytest.raises(ValueError, match="Repository URL is required"):
            _ = clone_repo("")

    @patch("src.github_utils.subprocess.run")
    @patch("src.github_utils.tempfile.mkdtemp")
    def test_clones_public_repo(
        self,
        mock_mkdtemp: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """Test that public repo clone calls git correctly."""
        mock_mkdtemp.return_value = "/tmp/test_clone"
        mock_run.return_value = MagicMock(returncode=0)

        result = clone_repo("https://github.com/owner/repo")

        assert result == "/tmp/test_clone"
        call_args = mock_run.call_args[0][0]
        assert "git" in call_args
        assert "clone" in call_args
        assert "https://github.com/owner/repo.git" in call_args

    @patch("src.github_utils.subprocess.run")
    @patch("src.github_utils.tempfile.mkdtemp")
    def test_injects_pat_for_private_repos(
        self,
        mock_mkdtemp: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """Test that PAT is injected into the clone URL."""
        mock_mkdtemp.return_value = "/tmp/test_clone"
        mock_run.return_value = MagicMock(returncode=0)

        _ = clone_repo(
            "https://github.com/owner/private-repo",
            github_pat="ghp_test123",
        )

        call_args = mock_run.call_args[0][0]
        assert "https://ghp_test123@github.com/owner/private-repo.git" in call_args

    @patch("src.github_utils.subprocess.run")
    @patch("src.github_utils.tempfile.mkdtemp")
    @patch("src.github_utils.cleanup_repo")
    def test_sanitizes_pat_in_error(
        self,
        mock_cleanup: MagicMock,
        mock_mkdtemp: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """Test that PAT is not leaked in error messages."""
        mock_mkdtemp.return_value = "/tmp/test_clone"
        mock_run.side_effect = subprocess.CalledProcessError(
            128, "git", stderr="fatal: auth failed with ghp_secret123"
        )

        with pytest.raises(ValueError) as exc_info:
            _ = clone_repo(
                "https://github.com/owner/repo",
                github_pat="ghp_secret123",
            )

        assert "ghp_secret123" not in str(exc_info.value)
        assert "***" in str(exc_info.value)

    @patch("src.github_utils.subprocess.run")
    @patch("src.github_utils.tempfile.mkdtemp")
    def test_clones_specific_branch(
        self,
        mock_mkdtemp: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """Test that branch parameter is passed to git."""
        mock_mkdtemp.return_value = "/tmp/test_clone"
        mock_run.return_value = MagicMock(returncode=0)

        _ = clone_repo(
            "https://github.com/owner/repo",
            branch="develop",
        )

        call_args = mock_run.call_args[0][0]
        assert "--branch" in call_args
        assert "develop" in call_args


class TestCleanupRepo:
    """Tests for the cleanup_repo function."""

    def test_removes_existing_directory(self, tmp_path: Path) -> None:
        """Test that existing directory is removed."""
        test_dir = tmp_path / "to_remove"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("test")

        cleanup_repo(str(test_dir))

        assert not test_dir.exists()

    def test_handles_nonexistent_path(self) -> None:
        """Test that nonexistent path does not raise."""
        cleanup_repo("/nonexistent/path/xyz")


class TestGetRepoFiles:
    """Tests for the get_repo_files function."""

    def test_finds_python_files(self, tmp_path: Path) -> None:
        """Test that Python files are discovered."""
        (tmp_path / "app.py").write_text("print('hello')")
        (tmp_path / "utils.py").write_text("x = 1")
        (tmp_path / "readme.txt").write_text("docs")

        files = get_repo_files(str(tmp_path), extensions=[".py"])

        assert len(files) == 2
        assert all(f.endswith(".py") for f in files)

    def test_skips_git_directory(self, tmp_path: Path) -> None:
        """Test that .git directory is excluded."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config.py").write_text("git stuff")
        (tmp_path / "app.py").write_text("code")

        files = get_repo_files(str(tmp_path), extensions=[".py"])

        assert len(files) == 1
        assert all(".git" not in f for f in files)

    def test_respects_max_files(self, tmp_path: Path) -> None:
        """Test that max_files limit is enforced."""
        for i in range(10):
            (tmp_path / f"file{i}.py").write_text(f"x = {i}")

        files = get_repo_files(str(tmp_path), extensions=[".py"], max_files=3)

        assert len(files) == 3

    def test_skips_node_modules(self, tmp_path: Path) -> None:
        """Test that node_modules directory is excluded."""
        nm = tmp_path / "node_modules"
        nm.mkdir()
        (nm / "lib.js").write_text("module code")
        (tmp_path / "app.js").write_text("app code")

        files = get_repo_files(str(tmp_path), extensions=[".js"])

        assert len(files) == 1
