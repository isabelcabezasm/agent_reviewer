import * as https from "https";
import * as http from "http";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ReviewResponse {
  raw_review: string;
  parsed_review: ParsedReview | null;
  files_reviewed: number;
  repo_url: string;
}

export interface ParsedReview {
  score?: number;
  summary?: string;
  security_concerns?: string;
  tests_assessment?: string;
  key_issues?: ReviewIssue[];
  positive_highlights?: string[];
  [key: string]: unknown;
}

export interface ReviewIssue {
  file?: string;
  lines?: string;
  severity?: string;
  category?: string;
  title?: string;
  description?: string;
  suggestion?: string;
}

interface CodePayload {
  code: string;
  language: string;
  filename: string;
  instructions: string;
}

interface DiffPayload {
  diff: string;
  instructions: string;
}

// ---------------------------------------------------------------------------
// API client functions
// ---------------------------------------------------------------------------

/**
 * Send code to the /api/review/code endpoint for review.
 */
export async function reviewCode(
  baseUrl: string,
  payload: CodePayload,
  apiKey?: string
): Promise<ReviewResponse> {
  return postJson<ReviewResponse>(`${baseUrl}/api/review/code`, payload, apiKey);
}

/**
 * Send a diff to the /api/review/diff endpoint for review.
 */
export async function reviewDiff(
  baseUrl: string,
  payload: DiffPayload,
  apiKey?: string
): Promise<ReviewResponse> {
  return postJson<ReviewResponse>(`${baseUrl}/api/review/diff`, payload, apiKey);
}

// ---------------------------------------------------------------------------
// HTTP helper
// ---------------------------------------------------------------------------

/**
 * Makes a POST request with JSON body and returns parsed JSON response.
 * Works with both http and https URLs.
 */
function postJson<T>(url: string, body: unknown, apiKey?: string): Promise<T> {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const parsed = new URL(url);
    const isHttps = parsed.protocol === "https:";
    const lib = isHttps ? https : http;

    const headers: Record<string, string | number> = {
      "Content-Type": "application/json",
      "Content-Length": Buffer.byteLength(data),
    };
    if (apiKey) {
      headers["X-API-Key"] = apiKey;
    }

    const req = lib.request(
      {
        hostname: parsed.hostname,
        port: parsed.port || (isHttps ? 443 : 80),
        path: parsed.pathname,
        method: "POST",
        headers,
      },
      (res) => {
        let responseData = "";
        res.on("data", (chunk: Buffer) => {
          responseData += chunk.toString();
        });
        res.on("end", () => {
          const statusCode = res.statusCode ?? 0;
          if (statusCode >= 200 && statusCode < 300) {
            try {
              resolve(JSON.parse(responseData) as T);
            } catch {
              reject(new Error(`Invalid JSON response from API`));
            }
          } else {
            let detail = `API returned status ${statusCode}`;
            try {
              const errBody = JSON.parse(responseData) as { detail?: string };
              if (errBody.detail) detail = errBody.detail;
            } catch {
              // Use status code message
            }
            reject(new Error(detail));
          }
        });
      }
    );

    req.on("error", (err: Error) => {
      reject(
        new Error(
          `Cannot connect to Agent Reviewer API at ${url}. ` +
            `Is the server running? (${err.message})`
        )
      );
    });

    req.write(data);
    req.end();
  });
}
