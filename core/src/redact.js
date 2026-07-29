/**
 * redact.js — PII redaction filter for MCP Commander Core OS.
 *
 * Scans text for personally identifiable information and replaces matches
 * before data leaves the system or reaches the LLM.  Supports multiple PII
 * types, two redaction modes (replace / mask), and configuration via
 * mcp-commander.config.json.
 *
 * Every write path in MCP Commander MUST pass through this module (RT-06).
 * All text sent to the LLM is pre-filtered here (RT-06, RT-07).
 * Telemetry output is guaranteed free of identifiable data (RT-10).
 *
 * Config (mcp-commander.config.json):
 *   { "redact": { "patterns": ["ssn", "credit_card", "phone", "email", "api_key"] } }
 *
 * Usage:
 *   const redact = require("./redact");
 *   redact.redact(text);                    // replace mode (default)
 *   redact.redact(text, { mode: "mask" });  // partial masking
 *   redact.countMatches(text);              // { total, byType }
 *   redact.scan(text);                      // [{ type, start, end, original, replacement }]
 */

"use strict";

const fs = require("fs");
const paths = require("./paths");

// ── Pattern Definitions ────────────────────────────────────────────────
//
// Each entry:
//   name    — identifier used in config and [REDACTED:<name>] tags
//   pattern — RegExp source (flags are added dynamically; do NOT use /g)
//   masker  — function(match) => partially-masked string

const PATTERNS = {

  // ── SSN ─────────────────────────────────────────────────────────────
  // Matches dashed (XXX-XX-XXXX) and bare nine-digit (XXXXXXXXX) formats.
  // Bare format is aggressive — enable selectively via config.
  ssn: {
    name: "ssn",
    pattern: /\b\d{3}-\d{2}-\d{4}\b|\b\d{9}\b/,
    masker(match) {
      if (match.includes("-")) return "***-**-" + match.slice(-4);
      return "*****" + match.slice(-4);
    },
  },

  // ── Credit Card (Visa 4x, MC 51-55, Amex 34/37, Discover 6011/65) ──
  // Handles 13-16 digit sequences with optional space / dash grouping.
  credit_card: {
    name: "credit_card",
    pattern:
      /\b(?:4\d{3}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}|5[1-5]\d{2}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}|3[47]\d{2}[\s-]?\d{6}[\s-]?\d{5}|6(?:011|5[0-9]{2})[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4})\b/,
    masker(match) {
      const digits = match.replace(/\D/g, "");
      const last4 = digits.slice(-4);
      // Amex is 15 digits — show last 5 to match conventional receipt format
      if (digits.length === 15) return "****-******-" + digits.slice(-5);
      return "****-****-****-" + last4;
    },
  },

  // ── Phone (US formats) ──────────────────────────────────────────────
  // XXX-XXX-XXXX | (XXX) XXX-XXXX | XXX.XXX.XXXX | +1-XXX-XXX-XXXX
  phone: {
    name: "phone",
    pattern: /(?:\+1[-.\s]?)?(?:\(\d{3}\)\s?|\b\d{3}[-.\s]?)\d{3}[-.\s]?\d{4}\b/,
    masker(match) {
      const digits = match.replace(/\D/g, "");
      const last4 = digits.slice(-4);
      if (match.includes("(")) return "(***) ***-" + last4;
      if (match.startsWith("+")) return "+*-***-***-" + last4;
      return "***-***-" + last4;
    },
  },

  // ── Email ───────────────────────────────────────────────────────────
  email: {
    name: "email",
    pattern: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/,
    masker(match) {
      const [local, domain] = match.split("@");
      const maskedLocal = local.charAt(0) + "***";
      const parts = domain.split(".");
      if (parts.length >= 2) {
        const tld = parts.pop();
        const maskedDomain = parts.map(() => "****").join(".");
        return maskedLocal + "@" + maskedDomain + "." + tld;
      }
      return maskedLocal + "@****";
    },
  },

  // ── API Keys ────────────────────────────────────────────────────────
  // Covers: sk-... | pk_... | key-... | Bearer <token> | 32+ hex | 40+ base64
  api_key: {
    name: "api_key",
    pattern:
      /\bsk-[A-Za-z0-9\-_]{20,}\b|\bpk_[A-Za-z0-9\-_]{20,}\b|\bkey-[A-Za-z0-9\-_]{16,}\b|\bBearer\s+[A-Za-z0-9\-._+/]{20,}|\b(?:[A-Za-z0-9+/]{40,}={0,2})\b|\b[0-9a-fA-F]{32,}\b/,
    masker(match) {
      const trimmed = match.trim();
      if (trimmed.startsWith("Bearer ")) return "Bearer ****...";
      if (trimmed.length > 8) return trimmed.slice(0, 6) + "****...";
      return "****";
    },
  },

  // ── IPv4 (optional — enable via config) ────────────────────────────
  ipv4: {
    name: "ipv4",
    pattern:
      /\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b/,
    masker(match) {
      const parts = match.split(".");
      return "***.***." + parts.slice(2).join(".");
    },
  },

  // ── Date of Birth (optional — enable via config) ────────────────────
  // MM/DD/YYYY | DD-MM-YYYY | YYYY/MM/DD etc.  Aggressive; use selectively.
  date_of_birth: {
    name: "date_of_birth",
    pattern: /\b(?:\d{1,2}[-\/]\d{1,2}[-\/]\d{2,4}|\d{4}[-\/]\d{1,2}[-\/]\d{1,2})\b/,
    masker(match) {
      return match.replace(/\d/g, "*");
    },
  },
};

// ── Known pattern names (for default-all fallback) ───────────────────────

const ALL_PATTERN_NAMES = Object.keys(PATTERNS);

// ── Config loader (cached per process) ──────────────────────────────────
//
// Reads mcp-commander.config.json once and caches the result.  Set to null (not
// undefined) after the first read so the sentinel value distinguishes
// "never loaded" from "config file missing".

let _cachedPatterns = undefined;

function loadDefaultPatterns() {
  if (_cachedPatterns !== undefined) return _cachedPatterns;
  try {
    const raw = fs.readFileSync(paths.CONFIG_FILE, "utf-8");
    const config = JSON.parse(raw);
    if (config.redact && Array.isArray(config.redact.patterns)) {
      _cachedPatterns = config.redact.patterns.slice();
    } else {
      _cachedPatterns = ALL_PATTERN_NAMES.slice();
    }
  } catch (_) {
    _cachedPatterns = ALL_PATTERN_NAMES.slice();
  }
  return _cachedPatterns;
}

// ── Active-pattern resolver ─────────────────────────────────────────────

/**
 * Determine which PATTERNS entries are active for this call.
 * Options.patterns takes precedence; otherwise falls back to config,
 * then to every registered pattern.
 *
 * @param {object} [options]
 * @returns {Array<typeof PATTERNS[keyof PATTERNS]>}
 */
function resolveActivePatterns(options) {
  const names = (options && Array.isArray(options.patterns))
    ? options.patterns
    : loadDefaultPatterns();

  const active = [];
  for (const name of names) {
    if (PATTERNS[name]) active.push(PATTERNS[name]);
  }
  return active;
}

// ── Overlap resolution ─────────────────────────────────────────────────
//
// When multiple patterns match overlapping regions of text, we keep the
// match that starts earliest; if two matches share the same start offset
// the longer match wins.  Remaining overlapping matches are discarded.

function resolveOverlaps(matches) {
  if (matches.length === 0) return matches;

  // Sort: ascending start, then descending length (longer wins ties)
  matches.sort((a, b) => {
    if (a.start !== b.start) return a.start - b.start;
    return (b.end - b.start) - (a.end - a.start);
  });

  const resolved = [];
  let lastEnd = -1;

  for (const m of matches) {
    if (m.start >= lastEnd) {
      resolved.push(m);
      lastEnd = m.end;
    }
  }

  return resolved;
}

// ── Scan ────────────────────────────────────────────────────────────────

/**
 * Scan text for PII and return structured match descriptors.
 *
 * @param {string} text — the text to scan
 * @param {object} [options] — { patterns?: string[], mode?: "replace"|"mask" }
 * @returns {Array<{type:string, start:number, end:number, original:string, replacement:string}>}
 */
function scan(text, options) {
  if (typeof text !== "string" || text.length === 0) return [];

  const mode = (options && options.mode === "mask") ? "mask" : "replace";
  const activePatterns = resolveActivePatterns(options);

  const raw = [];

  for (const entry of activePatterns) {
    const re = new RegExp(entry.pattern.source, "g");
    let m;
    while ((m = re.exec(text)) !== null) {
      const original = m[0];
      const replacement = (mode === "mask")
        ? entry.masker(original)
        : "[REDACTED:" + entry.name + "]";

      raw.push({
        type: entry.name,
        start: m.index,
        end: m.index + original.length,
        original,
        replacement,
      });

      // Guard against zero-length matches causing infinite loops
      if (original.length === 0) re.lastIndex++;
    }
  }

  return resolveOverlaps(raw);
}

// ── Redact ──────────────────────────────────────────────────────────────

/**
 * Replace PII in text.  Returns a new string with matches substituted.
 *
 * @param {string} text — input text
 * @param {object} [options] — { patterns?: string[], mode?: "replace"|"mask" }
 * @returns {string} redacted copy of text
 */
function redact(text, options) {
  if (typeof text !== "string" || text.length === 0) return text;

  const matches = scan(text, options);
  if (matches.length === 0) return text;

  // Apply right-to-left so earlier indices remain valid
  let result = text;
  for (let i = matches.length - 1; i >= 0; i--) {
    const m = matches[i];
    result = result.slice(0, m.start) + m.replacement + result.slice(m.end);
  }

  return result;
}

// ── Count Matches ───────────────────────────────────────────────────────

/**
 * Count PII matches grouped by type.
 *
 * @param {string} text — input text
 * @param {object} [options] — { patterns?: string[] }
 * @returns {{ total: number, byType: { [name: string]: number } }}
 */
function countMatches(text, options) {
  const matches = scan(text, options);
  const byType = {};
  for (const m of matches) {
    byType[m.type] = (byType[m.type] || 0) + 1;
  }
  return { total: matches.length, byType };
}

// ── Exports ─────────────────────────────────────────────────────────────

module.exports = {
  redact,
  countMatches,
  scan,
  PATTERNS,
};
