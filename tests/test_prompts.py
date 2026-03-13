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

    def test_includes_review_principles(self) -> None:
        """Test that review principles are present in the prompt."""
        prompt = build_system_prompt()
        assert "Do No Harm" in prompt
        assert "Preserve Correctness" in prompt
        assert "Security First" in prompt
        assert "Test Coverage Is Non-Negotiable" in prompt
        assert "Be Pragmatic" in prompt

    def test_includes_all_eight_dimensions(self) -> None:
        """Test that all 8 review dimensions are present."""
        prompt = build_system_prompt()
        dimensions = [
            "Security",
            "Correctness",
            "Code Quality",
            "Testing",
            "Performance",
            "Error Handling",
            "Architecture",
            "Documentation",
        ]
        for dim in dimensions:
            assert dim in prompt, f"Dimension '{dim}' missing from prompt"

    def test_includes_verdict_in_output_format(self) -> None:
        """Test that YAML output format includes verdict."""
        prompt = build_system_prompt()
        assert "verdict:" in prompt
        assert "PASS" in prompt
        assert "NEEDS_WORK" in prompt
        assert "FAIL" in prompt

    def test_includes_dimension_scores_in_output_format(self) -> None:
        """Test that YAML output format includes dimension scores."""
        prompt = build_system_prompt()
        assert "dimension_scores:" in prompt
        assert "error_handling:" in prompt
        assert "architecture:" in prompt
        assert "documentation:" in prompt

    def test_includes_documentation_assessment(self) -> None:
        """Test that documentation assessment is in output format."""
        prompt = build_system_prompt()
        assert "documentation_assessment:" in prompt

    def test_includes_owasp_security_checks(self) -> None:
        """Test that OWASP Top 10 categories are in the security dimension."""
        prompt = build_system_prompt()
        assert "OWASP Top 10" in prompt
        assert "Broken Access Control" in prompt
        assert "Cryptographic Failures" in prompt
        assert "Injection" in prompt
        assert "Security Misconfiguration" in prompt
        assert "Authentication Failures" in prompt
        assert "Integrity Failures" in prompt
        assert "Dependency Security" in prompt
        assert "Prompt Injection" in prompt

    def test_includes_severity_merge_semantics(self) -> None:
        """Test that severity levels include merge-blocking semantics."""
        prompt = build_system_prompt()
        assert "blocks merge" in prompt
        assert "requires discussion" in prompt
        assert "non-blocking" in prompt

    def test_includes_breaking_change_and_data_loss_categories(self) -> None:
        """Test that Breaking Change and Data Loss are issue categories."""
        prompt = build_system_prompt()
        assert "Breaking Change" in prompt
        assert "Data Loss" in prompt

    def test_includes_pragmatic_grouping_guideline(self) -> None:
        """Test that pragmatic review and grouping guidelines are present."""
        prompt = build_system_prompt()
        assert "Group related comments" in prompt


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
