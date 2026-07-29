/**
 * llm.js — Local LLM interface for MCP Commander Core OS (Bay 0).
 *
 * Provides intent parsing, cognitive reasoning, and natural language understanding
 * via locally-hosted LLMs (Ollama or llama.cpp).  Data NEVER leaves the machine —
 * all requests are enforced to localhost only (RT-14).
 *
 * Supported backends:
 *   - "ollama"   : Ollama REST API  (default, port 11434)
 *   - "llamacpp"  : llama.cpp server   (default, port 8080)
 *   - "none"      : LLM disabled
 *
 * Zero external dependencies — uses only Node.js built-in http/https.
 */

"use strict";

const fs = require("fs");
const http = require("http");
const https = require("https");
const paths = require("./paths");

// ── Defaults ──────────────────────────────────────────────────────────

const DEFAULTS = {
  backend: "ollama",
  model: "llama3:8b",
  base_url: "http://localhost:11434",
  timeout_ms: 30000,
};

const HEALTH_TIMEOUT_MS = 5000;

// ── Localhost enforcement (RT-14) ────────────────────────────────────

/**
 * Validates that a URL points to localhost/127.0.0.1/::1 only.
 * Throws if the target is non-local.
 */
function assertLocalhost(targetUrl) {
  const parsed = new URL(targetUrl);
  const host = parsed.hostname.toLowerCase();
  const allowed = ["localhost", "127.0.0.1", "::1", "[::1]"];
  if (!allowed.includes(host)) {
    throw new Error(
      `RT-14 violation: LLM request targeted non-local host "${host}". ` +
      `All LLM traffic must stay on localhost.`
    );
  }
}

// ── HTTP helper ───────────────────────────────────────────────────────

/**
 * Low-level HTTP/HTTPS request helper.
 * Returns a Promise resolving to { statusCode, headers, body } where body
 * is a parsed object if Content-Type is JSON, or a raw string otherwise.
 *
 * @param {string}  targetUrl  - Absolute URL (http or https).
 * @param {object}  reqOpts   - http.request options (method, headers, …).
 * @param {number}  timeoutMs - Socket timeout in milliseconds.
 * @param {string|null} [payload] - Request body (optional).
 * @returns {Promise<{statusCode: number, headers: object, body: object|string}>}
 */
function _httpRequest(targetUrl, reqOpts, timeoutMs, payload) {
  assertLocalhost(targetUrl);

  return new Promise((resolve, reject) => {
    const parsed = new URL(targetUrl);
    const transport = parsed.protocol === "https:" ? https : http;

    const options = {
      hostname: parsed.hostname,
      port: parsed.port || (parsed.protocol === "https:" ? 443 : 80),
      path: parsed.pathname + parsed.search,
      method: reqOpts.method || "GET",
      headers: reqOpts.headers || {},
      timeout: timeoutMs,
    };

    const req = transport.request(options, (res) => {
      const chunks = [];
      res.on("data", (chunk) => chunks.push(chunk));
      res.on("end", () => {
        const raw = Buffer.concat(chunks).toString("utf-8");
        let body;
        const ct = (res.headers["content-type"] || "").toLowerCase();
        if (ct.includes("application/json")) {
          try {
            body = JSON.parse(raw);
          } catch (e) {
            body = raw;
          }
        } else {
          body = raw;
        }
        resolve({ statusCode: res.statusCode, headers: res.headers, body });
      });
    });

    req.on("timeout", () => {
      req.destroy();
      reject(new Error(`LLM request timed out after ${timeoutMs}ms`));
    });

    req.on("error", (err) => {
      reject(new Error(`LLM network error: ${err.message}`));
    });

    if (payload) {
      req.write(payload);
    }
    req.end();
  });
}

// ── Config ────────────────────────────────────────────────────────────

/**
 * Reads and returns the LLM configuration section from mcp-commander.config.json.
 * Returns built-in defaults when the config file is missing or the llm
 * section is absent.
 *
 * @returns {{ backend: string, model: string, base_url: string, timeout_ms: number }}
 */
function getConfig() {
  try {
    if (!fs.existsSync(paths.CONFIG_FILE)) {
      return { ...DEFAULTS };
    }
    const raw = fs.readFileSync(paths.CONFIG_FILE, "utf-8");
    const cfg = JSON.parse(raw);
    if (!cfg.llm || typeof cfg.llm !== "object") {
      return { ...DEFAULTS };
    }
    return {
      backend: cfg.llm.backend || DEFAULTS.backend,
      model: cfg.llm.model || DEFAULTS.model,
      base_url: cfg.llm.base_url || DEFAULTS.base_url,
      timeout_ms: cfg.llm.timeout_ms || DEFAULTS.timeout_ms,
    };
  } catch (err) {
    console.error(`[llm] Failed to read config: ${err.message}`);
    return { ...DEFAULTS };
  }
}

// ── Availability check ────────────────────────────────────────────────

/**
 * Checks whether the configured LLM backend is reachable.
 *
 * @returns {Promise<{ available: boolean, backend: string, model: string, error?: string }>}
 */
async function isAvailable() {
  const cfg = getConfig();
  const { backend, model, base_url } = cfg;

  if (backend === "none") {
    return { available: false, backend, model, error: 'LLM backend is disabled ("none")' };
  }

  let healthUrl;
  if (backend === "ollama") {
    healthUrl = `${base_url}/api/tags`;
  } else if (backend === "llamacpp") {
    healthUrl = `${base_url}/health`;
  } else {
    return { available: false, backend, model, error: `Unknown backend: "${backend}"` };
  }

  try {
    const res = await _httpRequest(
      healthUrl,
      { method: "GET" },
      HEALTH_TIMEOUT_MS
    );
    if (res.statusCode === 200) {
      return { available: true, backend, model };
    }
    return {
      available: false,
      backend,
      model,
      error: `Health check returned HTTP ${res.statusCode}`,
    };
  } catch (err) {
    console.error(`[llm] Availability check failed: ${err.message}`);
    return { available: false, backend, model, error: err.message };
  }
}

// ── Generate (single prompt) ──────────────────────────────────────────

/**
 * Sends a text-generation request to the local LLM.
 *
 * @param {string} prompt  - The user prompt to send.
 * @param {object} [options] - Optional overrides.
 * @param {string} [options.model]       - Model name override.
 * @param {number} [options.temperature]  - Sampling temperature (default 0.7).
 * @param {number} [options.maxTokens]    - Max tokens to generate (default 2048).
 * @param {string} [options.system]       - System prompt.
 * @param {number} [options.timeout]      - Request timeout override (ms).
 * @returns {Promise<{ text: string, model: string, tokensUsed?: number, durationMs: number }>}
 */
async function generate(prompt, options) {
  const cfg = getConfig();
  const {
    model = cfg.model,
    temperature = 0.7,
    maxTokens = 2048,
    system,
    timeout = cfg.timeout_ms,
  } = options || {};

  const startTime = Date.now();
  let endpoint;
  let body;

  if (cfg.backend === "ollama") {
    endpoint = `${cfg.base_url}/api/generate`;
    body = {
      model,
      prompt,
      stream: false,
      options: {
        temperature,
        num_predict: maxTokens,
      },
    };
    if (system) body.system = system;
  } else if (cfg.backend === "llamacpp") {
    endpoint = `${cfg.base_url}/completion`;
    body = {
      prompt,
      n_predict: maxTokens,
      temperature,
    };
    if (system) body.system_prompt = system;
  } else {
    throw new Error(`Cannot generate: unsupported backend "${cfg.backend}"`);
  }

  const payload = JSON.stringify(body);
  let res;
  try {
    res = await _httpRequest(
      endpoint,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Content-Length": Buffer.byteLength(payload),
        },
      },
      timeout,
      payload
    );
  } catch (err) {
    throw new Error(`LLM generate request failed: ${err.message}`);
  }

  if (res.statusCode !== 200) {
    const detail =
      typeof res.body === "object" ? JSON.stringify(res.body) : String(res.body);
    throw new Error(`LLM generate returned HTTP ${res.statusCode}: ${detail}`);
  }

  const durationMs = Date.now() - startTime;

  // Parse backend-specific response shapes
  if (cfg.backend === "ollama") {
    const data = res.body;
    return {
      text: data.response || "",
      model: data.model || model,
      tokensUsed: data.eval_count || undefined,
      durationMs,
    };
  } else {
    const data = res.body;
    return {
      text: data.content || "",
      model: data.model || model,
      tokensUsed: data.tokens_predicted || data.eval_count || undefined,
      durationMs,
    };
  }
}

// ── Chat (multi-turn) ─────────────────────────────────────────────────

/**
 * Sends a chat-completion request with message history.
 *
 * @param {Array<{ role: "system"|"user"|"assistant", content: string }>} messages
 * @param {object} [options] - Optional overrides.
 * @param {string} [options.model]       - Model name override.
 * @param {number} [options.temperature]  - Sampling temperature (default 0.7).
 * @param {number} [options.maxTokens]    - Max tokens to generate (default 2048).
 * @param {number} [options.timeout]      - Request timeout override (ms).
 * @returns {Promise<{ text: string, model: string, durationMs: number }>}
 */
async function chat(messages, options) {
  if (!Array.isArray(messages) || messages.length === 0) {
    throw new Error("chat() requires a non-empty messages array");
  }

  const cfg = getConfig();
  const {
    model = cfg.model,
    temperature = 0.7,
    maxTokens = 2048,
    timeout = cfg.timeout_ms,
  } = options || {};

  const startTime = Date.now();
  let endpoint;
  let body;

  if (cfg.backend === "ollama") {
    endpoint = `${cfg.base_url}/api/chat`;
    body = {
      model,
      messages,
      stream: false,
      options: {
        temperature,
        num_predict: maxTokens,
      },
    };
  } else if (cfg.backend === "llamacpp") {
    endpoint = `${cfg.base_url}/v1/chat/completions`;
    body = {
      model,
      messages,
      temperature,
      max_tokens: maxTokens,
      stream: false,
    };
  } else {
    throw new Error(`Cannot chat: unsupported backend "${cfg.backend}"`);
  }

  const payload = JSON.stringify(body);
  let res;
  try {
    res = await _httpRequest(
      endpoint,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Content-Length": Buffer.byteLength(payload),
        },
      },
      timeout,
      payload
    );
  } catch (err) {
    throw new Error(`LLM chat request failed: ${err.message}`);
  }

  if (res.statusCode !== 200) {
    const detail =
      typeof res.body === "object" ? JSON.stringify(res.body) : String(res.body);
    throw new Error(`LLM chat returned HTTP ${res.statusCode}: ${detail}`);
  }

  const durationMs = Date.now() - startTime;

  // Parse backend-specific response shapes
  if (cfg.backend === "ollama") {
    const data = res.body;
    return {
      text: (data.message && data.message.content) || "",
      model: data.model || model,
      durationMs,
    };
  } else {
    const data = res.body;
    const content =
      data.choices &&
      data.choices[0] &&
      data.choices[0].message &&
      data.choices[0].message.content
        ? data.choices[0].message.content
        : "";
    return {
      text: content,
      model: data.model || model,
      durationMs,
    };
  }
}

// ── Embeddings ────────────────────────────────────────────────────────

/**
 * Generates a text embedding vector.  Only supported with the Ollama backend.
 *
 * Attempts /api/embed first (Ollama >= 0.5), falls back to /api/embeddings.
 *
 * @param {string} text - The text to embed.
 * @returns {Promise<{ embedding: number[], model: string }>}
 */
async function embed(text) {
  const cfg = getConfig();

  if (cfg.backend !== "ollama") {
    throw new Error(
      `Embeddings are only supported with the "ollama" backend. ` +
      `Current backend: "${cfg.backend}"`
    );
  }

  if (typeof text !== "string" || text.trim().length === 0) {
    throw new Error("embed() requires a non-empty string");
  }

  const model = cfg.model;

  // Try the newer /api/embed endpoint first, fall back to /api/embeddings
  const endpoints = [
    `${cfg.base_url}/api/embed`,
    `${cfg.base_url}/api/embeddings`,
  ];

  let lastError;
  for (const endpoint of endpoints) {
    const body = JSON.stringify({ model, input: text });
    try {
      const res = await _httpRequest(
        endpoint,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Content-Length": Buffer.byteLength(body),
          },
        },
        cfg.timeout_ms,
        body
      );

      if (res.statusCode === 200) {
        const data = res.body;
        // /api/embed returns { embeddings: [[...]] }
        // /api/embeddings returns { embedding: [...] }
        let embedding;
        if (Array.isArray(data.embeddings) && data.embeddings.length > 0) {
          embedding = data.embeddings[0];
        } else if (Array.isArray(data.embedding)) {
          embedding = data.embedding;
        }
        if (!embedding) {
          throw new Error("No embedding vector found in response");
        }
        return { embedding, model: data.model || model };
      }

      // Non-200 — try next endpoint
      lastError = `HTTP ${res.statusCode}`;
    } catch (err) {
      // Network or parse error — try next endpoint
      lastError = err.message;
    }
  }

  console.error(`[llm] Embedding failed on all endpoints: ${lastError}`);
  throw new Error(`Failed to generate embedding: ${lastError}`);
}

// ── List models ───────────────────────────────────────────────────────

/**
 * Lists models available on the configured LLM backend.
 *
 * @returns {Promise<Array<{ name: string, size?: string, modified?: string }>>}
 */
async function listModels() {
  const cfg = getConfig();

  if (cfg.backend === "none") {
    return [];
  }

  if (cfg.backend === "ollama") {
    const endpoint = `${cfg.base_url}/api/tags`;
    try {
      const res = await _httpRequest(
        endpoint,
        { method: "GET" },
        HEALTH_TIMEOUT_MS
      );

      if (res.statusCode !== 200) {
        console.error(`[llm] listModels: HTTP ${res.statusCode}`);
        return [];
      }

      const data = res.body;
      if (!Array.isArray(data.models)) return [];

      return data.models.map((m) => ({
        name: m.name || m.model || "unknown",
        size: m.size != null ? String(m.size) : undefined,
        modified: m.modified_at || m.modified || undefined,
      }));
    } catch (err) {
      console.error(`[llm] listModels failed: ${err.message}`);
      return [];
    }
  }

  if (cfg.backend === "llamacpp") {
    // llama.cpp does not expose a model-listing endpoint
    return [];
  }

  console.error(`[llm] listModels: unknown backend "${cfg.backend}"`);
  return [];
}

// ── Export ─────────────────────────────────────────────────────────────

module.exports = {
  getConfig,
  isAvailable,
  generate,
  chat,
  embed,
  listModels,
};
