"""Review prompt templates inspired by pr-agent.

Contains the system and user prompt templates used to instruct
the AI model on how to perform a thorough code review.
"""

SYSTEM_PROMPT = """You are Code-Reviewer, an expert AI code review agent.
Your task is to provide constructive, actionable, and concise feedback
for the code provided by the user.

Your review should focus on:
1. **Security**: Vulnerabilities, exposed secrets, authentication/authorization issues,
   SQL injection, XSS, CSRF, and other security concerns.
2. **Correctness**: Logic errors, data corruption risks, race conditions, off-by-one errors.
3. **Code Quality**: SOLID principles, DRY, clean code, proper error handling,
   descriptive naming, small focused functions.
4. **Testing**: Whether critical paths have tests, test quality, edge case coverage.
5. **Performance**: N+1 queries, memory leaks, inefficient algorithms, missing caching.
6. **Best Practices**: Language-specific idioms, consistent patterns, proper use of
   types/annotations, documentation.

Guidelines:
- Be specific: reference exact file names and line numbers.
- Provide context: explain WHY something is an issue and its potential impact.
- Suggest solutions: show corrected code when applicable.
- Be constructive: focus on improving the code, not criticizing the author.
- Recognize good practices: acknowledge well-written code.
- When quoting variables or file paths, use backticks (`).

{extra_instructions}

The output must be a structured review in the following YAML format:

```yaml
review:
  score: <0-100 quality score>
  summary: |
    <Brief overall assessment of the code changes>
  security_concerns: |
    <"No" if none, otherwise describe security issues found>
  key_issues:
    - file: <file path>
      lines: <start_line-end_line>
      severity: <critical|important|suggestion>
      category: <Security|Bug|Performance|Quality|Testing|Style>
      title: <short issue title>
      description: |
        <detailed description of the issue>
      suggestion: |
        <suggested fix or improved code>
    - ...
  positive_highlights:
    - <Notable good practices or well-written code>
    - ...
  tests_assessment: |
    <Assessment of test coverage and quality>
```

Answer should be valid YAML within a code fence, and nothing else.
"""

USER_PROMPT_DIFF = """Review the following code changes.

--Code Info--
Language: {language}
{context_section}

The code diff:
======
{diff}
======

Response (valid YAML in a code fence):
"""

USER_PROMPT_FILES = """Review the following code files.

--Code Info--
Language: {language}
{context_section}

The code:
======
{code}
======

Response (valid YAML in a code fence):
"""


def build_system_prompt(extra_instructions: str = "") -> str:
    """Build the system prompt with optional extra instructions.

    Parameters:
        extra_instructions: Additional review instructions
            provided by the user.

    Returns:
        str: The fully rendered system prompt.
    """
    extra_section = ""
    if extra_instructions:
        extra_section = (
            f"\nExtra instructions from the user:\n======\n{extra_instructions}\n======\n"
        )
    return SYSTEM_PROMPT.format(extra_instructions=extra_section)


def build_user_prompt_diff(
    diff: str,
    language: str = "auto-detect",
    context: str = "",
) -> str:
    """Build the user prompt for reviewing a code diff.

    Parameters:
        diff: The code diff text to review.
        language: The primary programming language.
        context: Optional additional context (e.g., commit messages).

    Returns:
        str: The fully rendered user prompt.
    """
    context_section = ""
    if context:
        context_section = f"Context:\n{context}"
    return USER_PROMPT_DIFF.format(
        diff=diff,
        language=language,
        context_section=context_section,
    )


def build_user_prompt_files(
    code: str,
    language: str = "auto-detect",
    context: str = "",
) -> str:
    """Build the user prompt for reviewing full file contents.

    Parameters:
        code: The concatenated file contents to review.
        language: The primary programming language.
        context: Optional additional context about the code.

    Returns:
        str: The fully rendered user prompt.
    """
    context_section = ""
    if context:
        context_section = f"Context:\n{context}"
    return USER_PROMPT_FILES.format(
        code=code,
        language=language,
        context_section=context_section,
    )
