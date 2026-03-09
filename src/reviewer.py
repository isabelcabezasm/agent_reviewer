"""Core code reviewer module.

Orchestrates the review process by collecting code (diffs or files),
building prompts, and sending them to the AI model for analysis.
Inspired by qodo-ai/pr-agent's PRReviewer pattern.
"""

from src.config import AppConfig
from src.diff_utils import (
    detect_language,
    get_all_uncommitted_diff,
    get_branch_diff,
    get_changed_files_from_diff,
    get_commit_diff,
    get_staged_diff,
    read_files,
)
from src.handler_factory import create_handler
from src.prompts import (
    build_system_prompt,
    build_user_prompt_diff,
    build_user_prompt_files,
)


class CodeReviewer:
    """AI-powered local code reviewer.

    Reviews code changes or files using Azure OpenAI, without
    requiring a Pull Request to be created. Works entirely
    locally using git diffs or direct file reading.

    Attributes:
        config: The application configuration.
        ai_handler: The AI handler for model communication.
    """

    def __init__(self, config: AppConfig) -> None:
        """Initialize the code reviewer.

        Parameters:
            config: Application configuration including AI
                provider credentials and review settings.
        """
        self.config = config
        self.ai_handler = create_handler(config)

    def review_staged(
        self,
        cwd: str | None = None,
    ) -> str:
        """Review only staged (git add) changes.

        Parameters:
            cwd: Working directory for git commands.

        Returns:
            str: The AI-generated review in YAML format.

        Raises:
            ValueError: If there are no staged changes.
        """
        diff = get_staged_diff(cwd=cwd)
        if not diff:
            raise ValueError("No staged changes found. Use 'git add' to stage changes first.")
        return self._review_diff(diff)

    def review_uncommitted(
        self,
        cwd: str | None = None,
    ) -> str:
        """Review all uncommitted changes (staged + unstaged).

        Parameters:
            cwd: Working directory for git commands.

        Returns:
            str: The AI-generated review in YAML format.

        Raises:
            ValueError: If there are no uncommitted changes.
        """
        diff = get_all_uncommitted_diff(cwd=cwd)
        if not diff:
            raise ValueError("No uncommitted changes found.")
        return self._review_diff(diff)

    def review_branch(
        self,
        branch: str = "main",
        cwd: str | None = None,
    ) -> str:
        """Review changes compared to a target branch.

        Parameters:
            branch: The branch to compare against.
            cwd: Working directory for git commands.

        Returns:
            str: The AI-generated review in YAML format.

        Raises:
            ValueError: If there are no changes vs the branch.
        """
        diff = get_branch_diff(branch=branch, cwd=cwd)
        if not diff:
            raise ValueError(f"No changes found compared to branch '{branch}'.")
        return self._review_diff(diff)

    def review_commit(
        self,
        commit: str = "HEAD~1",
        cwd: str | None = None,
    ) -> str:
        """Review changes from a specific commit.

        Parameters:
            commit: The commit reference to compare from.
            cwd: Working directory for git commands.

        Returns:
            str: The AI-generated review in YAML format.

        Raises:
            ValueError: If there are no changes for the commit.
        """
        diff = get_commit_diff(commit=commit, cwd=cwd)
        if not diff:
            raise ValueError(f"No changes found for commit '{commit}'.")
        return self._review_diff(diff)

    def review_files(self, file_paths: list[str]) -> str:
        """Review specific files by reading their full contents.

        Parameters:
            file_paths: List of file paths to review.

        Returns:
            str: The AI-generated review in YAML format.

        Raises:
            FileNotFoundError: If any file does not exist.
            ValueError: If the file list is empty.
        """
        if not file_paths:
            raise ValueError("No files specified for review.")

        code = read_files(file_paths)
        language = detect_language(file_paths)

        system_prompt = build_system_prompt(
            extra_instructions=self.config.review.extra_instructions,
        )
        user_prompt = build_user_prompt_files(
            code=code,
            language=language,
        )

        return self.ai_handler.chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

    def _review_diff(self, diff: str) -> str:
        """Internal method to review a code diff.

        Detects the language from changed files and sends
        the diff to the AI model for review.

        Parameters:
            diff: The unified diff string to review.

        Returns:
            str: The AI-generated review in YAML format.
        """
        changed_files = get_changed_files_from_diff(diff)
        language = detect_language(changed_files)

        system_prompt = build_system_prompt(
            extra_instructions=self.config.review.extra_instructions,
        )
        user_prompt = build_user_prompt_diff(
            diff=diff,
            language=language,
        )

        return self.ai_handler.chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
