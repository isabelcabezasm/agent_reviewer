"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const api_1 = require("./api");
/**
 * Activates the Agent Reviewer extension.
 * Registers three commands: review file, review selection, review diff.
 */
function activate(context) {
    context.subscriptions.push(vscode.commands.registerCommand("agentReviewer.reviewFile", handleReviewFile), vscode.commands.registerCommand("agentReviewer.reviewSelection", handleReviewSelection), vscode.commands.registerCommand("agentReviewer.reviewDiff", handleReviewDiff), vscode.commands.registerCommand("agentReviewer.reviewBranch", handleReviewBranch), vscode.commands.registerCommand("agentReviewer.reviewRepo", handleReviewRepo), vscode.commands.registerCommand("agentReviewer.testConnection", handleTestConnection));
}
function deactivate() {
    // Nothing to clean up
}
// ---------------------------------------------------------------------------
// Command handlers
// ---------------------------------------------------------------------------
async function handleReviewFile() {
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
    await runReview("Reviewing file...", () => (0, api_1.reviewCode)(getApiUrl(), { code, language, filename, instructions }, apiKey));
}
async function handleReviewSelection() {
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
    await runReview("Reviewing selection...", () => (0, api_1.reviewCode)(getApiUrl(), { code, language, filename, instructions }, apiKey));
}
async function handleReviewDiff() {
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
    await runReview("Reviewing uncommitted changes...", () => (0, api_1.reviewDiff)(getApiUrl(), { diff, instructions }, apiKey));
}
async function handleReviewBranch() {
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    if (!workspaceFolder) {
        vscode.window.showWarningMessage("No workspace folder open.");
        return;
    }
    const cwd = workspaceFolder.uri.fsPath;
    const instructions = getInstructions();
    const apiKey = getApiKey();
    // Detect the default branch from origin/HEAD
    let defaultBranch = "main";
    const originHead = await runGitCommand(["symbolic-ref", "refs/remotes/origin/HEAD"], cwd);
    if (originHead.trim()) {
        defaultBranch = originHead.trim().split("/").pop() || "main";
    }
    else {
        // Try common default branches
        for (const candidate of ["main", "master", "develop"]) {
            const check = await runGitCommand(["rev-parse", "--verify", `origin/${candidate}`], cwd);
            if (check.trim()) {
                defaultBranch = candidate;
                break;
            }
        }
    }
    // Find merge-base between default branch and current HEAD
    const mergeBase = await runGitCommand(["merge-base", `origin/${defaultBranch}`, "HEAD"], cwd);
    if (!mergeBase.trim()) {
        vscode.window.showWarningMessage(`Could not find merge-base with origin/${defaultBranch}. Are you on a feature branch?`);
        return;
    }
    // Diff from merge-base to working tree (committed + uncommitted)
    const diff = await runGitCommand(["diff", mergeBase.trim()], cwd);
    if (!diff.trim()) {
        vscode.window.showInformationMessage(`No changes found compared to origin/${defaultBranch}.`);
        return;
    }
    const currentBranch = await runGitCommand(["branch", "--show-current"], cwd);
    const branchName = currentBranch.trim() || "current branch";
    await runReview(`Reviewing branch '${branchName}' vs '${defaultBranch}' (committed + uncommitted)...`, () => (0, api_1.reviewDiff)(getApiUrl(), { diff, instructions }, apiKey));
}
async function handleReviewRepo() {
    const repoUrl = await vscode.window.showInputBox({
        prompt: "Enter the GitHub repository URL to review",
        placeHolder: "https://github.com/owner/repo",
        validateInput: (value) => {
            if (!value.trim())
                return "Repository URL is required";
            if (!/^https?:\/\/.+/.test(value))
                return "Must be a valid URL";
            return null;
        },
    });
    if (!repoUrl)
        return;
    const mode = await vscode.window.showQuickPick([
        { label: "Full Review", description: "Review all files in the repository", value: "full" },
        { label: "Branch Diff", description: "Review changes from a specific branch", value: "branch" },
        { label: "Latest Commit", description: "Review the latest commit diff", value: "commit" },
    ], { placeHolder: "Select review mode" });
    if (!mode)
        return;
    let branch;
    if (mode.value === "branch") {
        branch =
            (await vscode.window.showInputBox({
                prompt: "Enter the branch name",
                placeHolder: "main",
            })) || undefined;
        if (!branch)
            return;
    }
    const githubPat = (await vscode.window.showInputBox({
        prompt: "GitHub PAT for private repos (leave empty for public repos)",
        password: true,
    })) || undefined;
    const instructions = getInstructions();
    const apiKey = getApiKey();
    await runReview("Reviewing repository...", () => (0, api_1.reviewRepo)(getApiUrl(), {
        repo_url: repoUrl,
        github_pat: githubPat,
        mode: mode.value,
        branch,
        instructions,
        max_files: 30,
    }, apiKey));
}
async function handleTestConnection() {
    const apiUrl = getApiUrl();
    const apiKey = getApiKey();
    try {
        const result = await (0, api_1.healthCheck)(apiUrl, apiKey);
        if (result.status === "ok") {
            vscode.window.showInformationMessage(`Agent Reviewer: Connected to ${apiUrl} successfully!`);
        }
        else {
            vscode.window.showWarningMessage(`Agent Reviewer: API responded but status is '${result.status}'.`);
        }
    }
    catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        vscode.window.showErrorMessage(`Agent Reviewer: ${message}`);
    }
}
// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function getApiUrl() {
    return vscode.workspace.getConfiguration("agentReviewer").get("apiUrl", "http://localhost:8000");
}
function getInstructions() {
    return vscode.workspace.getConfiguration("agentReviewer").get("instructions", "");
}
function getApiKey() {
    const key = vscode.workspace.getConfiguration("agentReviewer").get("apiKey", "");
    return key || undefined;
}
/**
 * Runs a review with a progress indicator, then shows results in a panel.
 */
async function runReview(title, reviewFn) {
    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: `🔍 Agent Reviewer: ${title}`,
        cancellable: false,
    }, async () => {
        try {
            const result = await reviewFn();
            showReviewPanel(result);
        }
        catch (err) {
            const message = err instanceof Error ? err.message : String(err);
            vscode.window.showErrorMessage(`Agent Reviewer: ${message}`);
        }
    });
}
/**
 * Renders the review result as a Markdown document in a new editor panel.
 */
function showReviewPanel(result) {
    const markdown = formatReviewAsMarkdown(result);
    const panel = vscode.window.createWebviewPanel("agentReviewerResult", "🔍 Code Review", vscode.ViewColumn.Beside, { enableScripts: false });
    panel.webview.html = renderMarkdownHtml(markdown);
}
/**
 * Converts a ReviewResponse into a readable Markdown string.
 */
function formatReviewAsMarkdown(result) {
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
            const icon = sev === "critical" ? "🔴" : sev === "important" ? "🟡" : "🟢";
            md += `### ${icon} ${issue.title || "Issue"}\n\n`;
            if (issue.file) {
                md += `**File:** \`${issue.file}\``;
                if (issue.lines)
                    md += ` (lines ${issue.lines})`;
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
function renderMarkdownHtml(markdown) {
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
function escapeHtml(text) {
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}
/**
 * Runs a git command and returns stdout.
 */
async function runGitCommand(args, cwd) {
    const cp = await Promise.resolve().then(() => __importStar(require("child_process")));
    return new Promise((resolve) => {
        cp.execFile("git", args, { cwd }, (err, stdout) => {
            resolve(err ? "" : stdout);
        });
    });
}
//# sourceMappingURL=extension.js.map