#!/usr/bin/env bash
# Entrypoint for the GitHub Action.
# Runs the reviewer and posts results as a PR comment.

set -eo pipefail

cd /app

# Build CLI args based on environment
ARGS=()

case "${REVIEW_MODE}" in
    staged)
        ARGS+=("--staged")
        ;;
    commit)
        ARGS+=("--commit" "HEAD~1")
        ;;
    files)
        if [ -n "${REVIEW_FILES}" ]; then
            ARGS+=("--files" ${REVIEW_FILES})
        fi
        ;;
    branch|*)
        ARGS+=("--branch" "${REVIEW_BRANCH:-main}")
        ;;
esac

if [ -n "${REVIEW_INSTRUCTIONS}" ]; then
    ARGS+=("--instructions" "${REVIEW_INSTRUCTIONS}")
fi

# Point at the checked-out repo
ARGS+=("--repo" "${GITHUB_WORKSPACE}")

echo "🔍 Agent Reviewer — GitHub Action"
echo "Mode: ${REVIEW_MODE}"
echo ""

# Run the review
REVIEW_OUTPUT=$(python -m src.main "${ARGS[@]}" 2>&1) || true

echo "${REVIEW_OUTPUT}"

# If running in a PR context, post as a comment
if [ -n "${GITHUB_TOKEN}" ] && [ -n "${GITHUB_EVENT_PATH}" ]; then
    PR_NUMBER=$(jq -r '.pull_request.number // empty' "${GITHUB_EVENT_PATH}" 2>/dev/null || true)

    if [ -n "${PR_NUMBER}" ]; then
        COMMENT_BODY="## 🔍 Agent Reviewer — AI Code Review

${REVIEW_OUTPUT}"

        # Post comment via GitHub API
        gh api \
            -X POST \
            "/repos/${GITHUB_REPOSITORY}/issues/${PR_NUMBER}/comments" \
            -f body="${COMMENT_BODY}" \
            2>/dev/null || echo "⚠️ Could not post PR comment (missing GITHUB_TOKEN permissions?)"
    fi
fi
