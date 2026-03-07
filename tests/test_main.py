"""Tests for the main CLI module."""

from src.main import create_parser


class TestCreateParser:
    """Tests for the argument parser."""

    def test_parser_defaults_to_no_mode(self) -> None:
        """Test that parser with no args has all modes as None/False."""
        parser = create_parser()
        args = parser.parse_args([])
        assert args.staged is False
        assert args.files is None
        assert args.branch is None
        assert args.commit is None

    def test_parser_staged_flag(self) -> None:
        """Test --staged flag is recognized."""
        parser = create_parser()
        args = parser.parse_args(["--staged"])
        assert args.staged is True

    def test_parser_files_argument(self) -> None:
        """Test --files accepts multiple file paths."""
        parser = create_parser()
        args = parser.parse_args(["--files", "a.py", "b.py"])
        assert args.files == ["a.py", "b.py"]

    def test_parser_branch_argument(self) -> None:
        """Test --branch accepts a branch name."""
        parser = create_parser()
        args = parser.parse_args(["--branch", "develop"])
        assert args.branch == "develop"

    def test_parser_commit_argument(self) -> None:
        """Test --commit accepts a commit reference."""
        parser = create_parser()
        args = parser.parse_args(["--commit", "HEAD~3"])
        assert args.commit == "HEAD~3"

    def test_parser_instructions_argument(self) -> None:
        """Test --instructions accepts review instructions."""
        parser = create_parser()
        args = parser.parse_args(["--instructions", "Focus on security"])
        assert args.instructions == "Focus on security"

    def test_parser_env_argument(self) -> None:
        """Test --env accepts a custom .env path."""
        parser = create_parser()
        args = parser.parse_args(["--env", "/custom/.env"])
        assert args.env == "/custom/.env"

    def test_parser_repo_argument(self) -> None:
        """Test --repo accepts a path to another repository."""
        parser = create_parser()
        args = parser.parse_args(["--repo", "/other/repo", "--staged"])
        assert args.repo == "/other/repo"
        assert args.staged is True

    def test_parser_repo_defaults_to_none(self) -> None:
        """Test --repo defaults to None when not provided."""
        parser = create_parser()
        args = parser.parse_args([])
        assert args.repo is None
