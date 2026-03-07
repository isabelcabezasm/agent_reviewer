import * as vscode from "vscode";
import { reviewCode, reviewDiff, ReviewResponse } from "./api";

/**
 * Activates the Agent Reviewer extension.
 * Registers three commands: review file, review selection, review diff.
 */
export function activate(context: vscode.ExtensionContext): void {
  context.subscriptions.push(
    vscode.commands.registerCommand("agentReviewer.reviewFile", handleReviewFile),
    vscode.commands.registerCommand("agentReviewer.reviewSelection", handleReviewSelection),
    vscode.commands.registerCommand("agentReviewer.reviewDiff", handleReviewDiff)
  );
}

export function deactivate(): void {
  // Nothing to clean up
}

// ---------------------------------------------------------------------------
// Command handlers
// ---------------------------------------------------------------------------

async function handleReviewFile(): Promise<void> {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showWarningMessage("No active file to review.");
    return;
  }

  const code = editor.document.getText();
  const language = editor.document.languageId;
  const filename = editor.document.fileName;
  const instructions = getInstructions();
  const apiKey = getApiKey();

  await runReview("Reviewing file...", () =>
    reviewCode(getApiUrl(), { code, language, filename, instructions }, apiKey)
  );
}

async function handleReviewSelection(): Promise<void> {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showWarningMessage("No active editor.");
    return;
  }

  const selection = editor.selection;
  if (selection.isEmpty) {
    vscode.window.showWarningMessage("No text selected. Select code to review.");
    return;
  }

  const code = editor.document.getText(selection);
  const language = editor.document.languageId;
  const filename = editor.document.fileName;
  const instructions = getInstructions();
  const apiKey = getApiKey();

  await runReview("Reviewing selection...", () =>
    reviewCode(getApiUrl(), { code, language, filename, instructions }, apiKey)
  );
}

async function handleReviewDiff(): Promise<void> {
  const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
  if (!workspaceFolder) {
    vscode.window.showWarningMessage("No workspace folder open.");
    return;
  }

  const cwd = workspaceFolder.uri.fsPath;
  const instructions = getInstructions();
  const apiKey = getApiKey();

  // Get staged diff first, fall back to all uncommitted
  let diff = await runGitCommand(["diff", "--staged"], cwd);
  if (!diff.trim()) {
    diff = await runGitCommand(["diff", "HEAD"], cwd);
  }

  if (!diff.trim()) {
    vscode.window.showInformationMessage("No uncommitted changes found.");
    return;
  }

  await runReview("Reviewing uncommitted changes...", () =>
    reviewDiff(getApiUrl(), { diff, instructions }, apiKey)
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getApiUrl(): string {
  return vscode.workspace.getConfiguration("agentReviewer").get("apiUrl", "http://localhost:8000");
}

function getInstructions(): string {
  return vscode.workspace.getConfiguration("agentReviewer").get("instructions", "");
}

function getApiKey(): string | undefined {
  const key = vscode.workspace.getConfiguration("agentReviewer").get<string>("apiKey", "");
  return key || undefined;
}

/**
 * Runs a review with a progress indicator, then shows results in a panel.
 */
async function runReview(
  title: string,
  reviewFn: () => Promise<ReviewResponse>
): Promise<void> {
  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: `🔍 Agent Reviewer: ${title}`,
      cancellable: false,
    },
    async () => {
      try {
        const result = await reviewFn();
        showReviewPanel(result);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : String(err);
        vscode.window.showErrorMessage(`Agent Reviewer: ${message}`);
      }
    }
  );
}

/**
 * Renders the review result as a Markdown document in a new editor panel.
 */
function showReviewPanel(result: ReviewResponse): void {
  const markdown = formatReviewAsMarkdown(result);

  const panel = vscode.window.createWebviewPanel(
    "agentReviewerResult",
    "🔍 Code Review",
    vscode.ViewColumn.Beside,
    { enableScripts: false }
  );

  panel.webview.html = renderMarkdownHtml(markdown);
}

/**
 * Converts a ReviewResponse into a readable Markdown string.
 */
function formatReviewAsMarkdown(result: ReviewResponse): string {
  const r = result.parsed_review;
  if (!r) {
    return `# 🔍 Code Review\n\n\`\`\`\n${result.raw_review}\n\`\`\``;
  }

  let md = "# 🔍 Agent Reviewer — Code Review\n\n";

  // Score
  if (r.score !== undefined) {
    const score = Number(r.score);
    const emoji = score >= 75 ? "🟢" : score >= 50 ? "🟡" : "🔴";
    md += `## ${emoji} Score: ${score}/100\n\n`;
  }

  // Summary
  if (r.summary) {
    md += `## Summary\n\n${r.summary}\n\n`;
  }

  // Security
  if (r.security_concerns && String(r.security_concerns).toLowerCase() !== "no") {
    md += `## 🔒 Security Concerns\n\n${r.security_concerns}\n\n`;
  }

  // Key Issues
  const issues = r.key_issues;
  if (Array.isArray(issues) && issues.length > 0) {
    md += `## 🚩 Key Issues (${issues.length})\n\n`;
    for (const issue of issues) {
      const sev = issue.severity || "suggestion";
      const icon =
        sev === "critical" ? "🔴" : sev === "important" ? "🟡" : "🟢";
      md += `### ${icon} ${issue.title || "Issue"}\n\n`;
      if (issue.file) {
        md += `**File:** \`${issue.file}\``;
        if (issue.lines) md += ` (lines ${issue.lines})`;
        md += "\n\n";
      }
      if (issue.category) {
        md += `**Category:** ${issue.category} · **Severity:** ${sev}\n\n`;
      }
      if (issue.description) {
        md += `${issue.description}\n\n`;
      }
      if (issue.suggestion) {
        md += `**💡 Suggestion:**\n\n\`\`\`\n${issue.suggestion}\n\`\`\`\n\n`;
      }
      md += "---\n\n";
    }
  }

  // Tests
  if (r.tests_assessment) {
    md += `## 🧪 Tests Assessment\n\n${r.tests_assessment}\n\n`;
  }

  // Highlights
  const highlights = r.positive_highlights;
  if (Array.isArray(highlights) && highlights.length > 0) {
    md += `## ✨ Positive Highlights\n\n`;
    for (const h of highlights) {
      md += `- ✓ ${h}\n`;
    }
    md += "\n";
  }

  return md;
}

/**
 * Wraps markdown in a simple HTML page for the webview panel.
 * Uses a lightweight Markdown→HTML conversion.
 */
function renderMarkdownHtml(markdown: string): string {
  // Simple markdown to HTML (code blocks, headers, bold, lists, hr)
  let html = escapeHtml(markdown);

  // Code blocks
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="$1">$2</code></pre>');
  // Inline code
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  // Headers
  html = html.replace(/^### (.+)$/gm, "<h3>$1</h3>");
  html = html.replace(/^## (.+)$/gm, "<h2>$1</h2>");
  html = html.replace(/^# (.+)$/gm, "<h1>$1</h1>");
  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  // List items
  html = html.replace(/^- (.+)$/gm, "<li>$1</li>");
  // Horizontal rules
  html = html.replace(/^---$/gm, "<hr>");
  // Paragraphs (double newlines)
  html = html.replace(/\n\n/g, "</p><p>");
  // Single newlines in paragraphs
  html = html.replace(/\n/g, "<br>");

  return `<!DOCTYPE html>
<html>
<head>
<style>
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    padding: 16px 24px;
    line-height: 1.6;
    color: var(--vscode-foreground);
    background: var(--vscode-editor-background);
  }
  h1, h2, h3 { margin-top: 24px; }
  h1 { font-size: 1.5em; border-bottom: 1px solid var(--vscode-panel-border); padding-bottom: 8px; }
  h2 { font-size: 1.25em; }
  h3 { font-size: 1.1em; }
  code {
    background: var(--vscode-textCodeBlock-background);
    padding: 2px 6px;
    border-radius: 3px;
    font-family: var(--vscode-editor-font-family);
    font-size: 0.9em;
  }
  pre {
    background: var(--vscode-textCodeBlock-background);
    padding: 12px 16px;
    border-radius: 6px;
    overflow-x: auto;
  }
  pre code { background: none; padding: 0; }
  hr { border: none; border-top: 1px solid var(--vscode-panel-border); margin: 16px 0; }
  li { margin: 4px 0; list-style: none; }
  strong { font-weight: 600; }
</style>
</head>
<body><p>${html}</p></body>
</html>`;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

/**
 * Runs a git command and returns stdout.
 */
async function runGitCommand(args: string[], cwd: string): Promise<string> {
  const cp = await import("child_process");
  return new Promise((resolve) => {
    cp.execFile("git", args, { cwd }, (err, stdout) => {
      resolve(err ? "" : stdout);
    });
  });
}
