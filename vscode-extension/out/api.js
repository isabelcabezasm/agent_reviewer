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
exports.reviewCode = reviewCode;
exports.reviewDiff = reviewDiff;
const https = __importStar(require("https"));
const http = __importStar(require("http"));
// ---------------------------------------------------------------------------
// API client functions
// ---------------------------------------------------------------------------
/**
 * Send code to the /api/review/code endpoint for review.
 */
async function reviewCode(baseUrl, payload, apiKey) {
    return postJson(`${baseUrl}/api/review/code`, payload, apiKey);
}
/**
 * Send a diff to the /api/review/diff endpoint for review.
 */
async function reviewDiff(baseUrl, payload, apiKey) {
    return postJson(`${baseUrl}/api/review/diff`, payload, apiKey);
}
// ---------------------------------------------------------------------------
// HTTP helper
// ---------------------------------------------------------------------------
/**
 * Makes a POST request with JSON body and returns parsed JSON response.
 * Works with both http and https URLs.
 */
function postJson(url, body, apiKey) {
    return new Promise((resolve, reject) => {
        const data = JSON.stringify(body);
        const parsed = new URL(url);
        const isHttps = parsed.protocol === "https:";
        const lib = isHttps ? https : http;
        const headers = {
            "Content-Type": "application/json",
            "Content-Length": Buffer.byteLength(data),
        };
        if (apiKey) {
            headers["X-API-Key"] = apiKey;
        }
        const req = lib.request({
            hostname: parsed.hostname,
            port: parsed.port || (isHttps ? 443 : 80),
            path: parsed.pathname,
            method: "POST",
            headers,
        }, (res) => {
            let responseData = "";
            res.on("data", (chunk) => {
                responseData += chunk.toString();
            });
            res.on("end", () => {
                const statusCode = res.statusCode ?? 0;
                if (statusCode >= 200 && statusCode < 300) {
                    try {
                        resolve(JSON.parse(responseData));
                    }
                    catch {
                        reject(new Error(`Invalid JSON response from API`));
                    }
                }
                else {
                    let detail = `API returned status ${statusCode}`;
                    try {
                        const errBody = JSON.parse(responseData);
                        if (errBody.detail)
                            detail = errBody.detail;
                    }
                    catch {
                        // Use status code message
                    }
                    reject(new Error(detail));
                }
            });
        });
        req.on("error", (err) => {
            reject(new Error(`Cannot connect to Agent Reviewer API at ${url}. ` +
                `Is the server running? (${err.message})`));
        });
        req.write(data);
        req.end();
    });
}
//# sourceMappingURL=api.js.map