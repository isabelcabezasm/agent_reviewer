"""Tests for the review prompts module."""

from src.prompts import (
    build_system_prompt,
    build_user_prompt_diff,
    build_user_prompt_files,
)


class TestBuildSystemPrompt:
    """Tests for the build_system_prompt function."""

    def test_builds_prompt_without_extra_instructions(self) -> None:
        """Test that base prompt is generated without extras."""
        prompt = build_system_prompt()
        assert "Code-Reviewer" in prompt
        assert "Security" in prompt
        assert "YAML" in prompt

    def test_includes_extra_instructions(self) -> None:
        """Test that extra instructions are included in prompt."""
        prompt = build_system_prompt(
            extra_instructions="Focus on error handling"
        )
        assert "Focus on error handling" in prompt
        assert "Extra instructions from the user" in prompt


class TestBuildUserPromptDiff:
    """Tests for the build_user_prompt_diff function."""

    def test_builds_diff_prompt(self) -> None:
        """Test that diff content is embedded in prompt."""
        prompt = build_user_prompt_diff(
            diff="+ new line\n- old line",
            language="Python",
        )
        assert "+ new line" in prompt
        assert "Python" in prompt

    def test_includes_context_when_provided(self) -> None:
        """Test that context section is included."""
        prompt = build_user_prompt_diff(
            diff="some diff",
            context="Fix: resolved login bug",
        )
        assert "Fix: resolved login bug" in prompt

    def test_excludes_context_when_empty(self) -> None:
        """Test that context section is omitted if empty."""
        prompt = build_user_prompt_diff(diff="some diff")
        assert "Context:" not in prompt


class TestBuildUserPromptFiles:
    """Tests for the build_user_prompt_files function."""

    def test_builds_files_prompt(self) -> None:
        """Test that code content is embedded in prompt."""
        prompt = build_user_prompt_files(
            code="def hello(): pass",
            language="Python",
        )
        assert "def hello(): pass" in prompt
        assert "Python" in prompt

    def test_includes_context_when_provided(self) -> None:
        """Test that context section is included."""
        prompt = build_user_prompt_files(
            code="some code",
            context="Authentication module",
        )
        assert "Authentication module" in prompt
