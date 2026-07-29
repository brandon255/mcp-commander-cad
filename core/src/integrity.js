/**
 * integrity.js — SHA-256 hash chain + WORM ledger for MCP Commander Core OS.
 *
 * Provides an immutable, tamper-evident audit trail stored as JSONL.
 * Every entry chains to the previous entry via SHA-256(prev_hash + serialized data),
 * making any in-place modification of the ledger detectable by verifyLedger().
 *
 * RT findings addressed:
 *   RT-02  Immutable audit trail  — append-only writes, sequence numbers, no delete API
 *   RT-04  Hash-chain integrity   — SHA-256(prev_hash + JSON.stringify(data)) per entry
 *   RT-18  WORM storage           — fs.appendFileSync only; no overwrite, no truncate
 *
 * Ledger file: paths.LEDGER_FILE  (core/storage/hot/ledger.jsonl)
 * Config:      paths.CONFIG_FILE  (config/mcp-commander.config.json)
 */

"use strict";

const crypto = require("crypto");
const fs = require("fs");
const path = require("path");
const paths = require("./paths");

// ── Internal helpers ──────────────────────────────────────────────────

const GENESIS = "GENESIS";

/**
 * Compute SHA-256 hex digest of a string.
 * @param {string} input
 * @returns {string}
 */
function sha256(input) {
  return crypto.createHash("sha256").update(input, "utf8").digest("hex");
}

/**
 * Ensure the parent directory of a file path exists.
 * @param {string} filePath
 */
function ensureDir(filePath) {
  const dir = path.dirname(filePath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

/**
 * Read and parse every line from the ledger file.
 * Returns an empty array if the file does not exist.
 * @returns {Array<Object>}
 */
function readAllEntries() {
  if (!fs.existsSync(paths.LEDGER_FILE)) {
    return [];
  }
  const raw = fs.readFileSync(paths.LEDGER_FILE, "utf8");
  if (raw.trim() === "") {
    return [];
  }
  const lines = raw.split("\n");
  const entries = [];
  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed === "") continue;
    try {
      entries.push(JSON.parse(trimmed));
    } catch (_) {
      // Malformed line — recorded as-is so verifyLedger can report it
      entries.push(null);
    }
  }
  return entries;
}

// ── Public API ────────────────────────────────────────────────────────

/**
 * Append a JSON entry to the WORM ledger.
 *
 * Each entry contains:
 *   sequence   — auto-incrementing integer starting at 1
 *   timestamp  — ISO 8601 string
 *   prev_hash  — SHA-256 hash of the previous entry ("GENESIS" for the first)
 *   hash       — SHA-256(prev_hash + JSON.stringify(data))
 *   data       — the original payload object
 *
 * Uses fs.appendFileSync to enforce the WORM pattern.
 *
 * @param {Object} data — arbitrary payload to record
 * @returns {Object} the complete ledger entry that was written
 */
function appendEntry(data) {
  ensureDir(paths.LEDGER_FILE);

  const existing = readAllEntries();
  const lastValid = (() => {
    for (let i = existing.length - 1; i >= 0; i--) {
      if (existing[i] !== null) return existing[i];
    }
    return null;
  })();

  const prevHash = lastValid ? lastValid.hash : GENESIS;
  const sequence = lastValid ? lastValid.sequence + 1 : 1;
  const timestamp = new Date().toISOString();

  const hashInput = prevHash + JSON.stringify(data);
  const hash = sha256(hashInput);

  const entry = {
    sequence,
    timestamp,
    prev_hash: prevHash,
    hash,
    data,
  };

  fs.appendFileSync(paths.LEDGER_FILE, JSON.stringify(entry) + "\n", "utf8");

  return entry;
}

/**
 * Verify the integrity of the entire ledger by recomputing every
 * hash-chain link and checking each entry against its predecessor.
 *
 * @returns {{ ok: boolean, total: number, valid: number, compromised: number, firstBreak: number|null }}
 */
function verifyLedger() {
  const entries = readAllEntries();

  if (entries.length === 0) {
    return { ok: true, total: 0, valid: 0, compromised: 0, firstBreak: null };
  }

  let valid = 0;
  let compromised = 0;
  let firstBreak = null;
  let prevHash = GENESIS;

  for (const entry of entries) {
    if (entry === null) {
      compromised++;
      if (firstBreak === null) firstBreak = -1;
      continue;
    }

    const expectedHash = sha256(prevHash + JSON.stringify(entry.data));
    const prevHashCorrect = entry.prev_hash === prevHash;
    const hashCorrect = entry.hash === expectedHash;

    if (prevHashCorrect && hashCorrect) {
      valid++;
    } else {
      compromised++;
      if (firstBreak === null) firstBreak = entry.sequence;
    }

    prevHash = entry.hash;
  }

  return {
    ok: compromised === 0,
    total: entries.length,
    valid,
    compromised,
    firstBreak,
  };
}

/**
 * Quick health check for the ledger.
 *
 * Returns ok=true with entryCount=0 when the file does not exist yet
 * (a fresh, un-initialised ledger is considered healthy).
 *
 * @returns {{ ok: boolean, entryCount: number, reason?: string }}
 */
function ledgerHealth() {
  if (!fs.existsSync(paths.LEDGER_FILE)) {
    return { ok: true, entryCount: 0 };
  }

  try {
    const raw = fs.readFileSync(paths.LEDGER_FILE, "utf8");
    if (raw.trim() === "") {
      return { ok: true, entryCount: 0 };
    }

    const lines = raw.split("\n").filter((l) => l.trim() !== "");
    let entryCount = 0;
    for (const line of lines) {
      JSON.parse(line.trim()); // will throw on malformed JSON
      entryCount++;
    }
    return { ok: true, entryCount };
  } catch (err) {
    return {
      ok: false,
      entryCount: 0,
      reason: `Ledger parse error: ${err.message}`,
    };
  }
}

/**
 * Retrieve entries from the ledger, optionally filtered.
 *
 * @param {Function} [filter] — optional predicate(entry) => boolean
 * @returns {Array<Object>}
 */
function getEntries(filter) {
  const entries = readAllEntries();
  const valid = entries.filter((e) => e !== null);
  if (typeof filter === "function") {
    return valid.filter(filter);
  }
  return valid;
}

/**
 * Return the last entry in the ledger, or null if the ledger is empty.
 *
 * @returns {Object|null}
 */
function getLastEntry() {
  const entries = readAllEntries();
  if (entries.length === 0) {
    return null;
  }
  // Walk backwards to skip any trailing nulls (malformed lines)
  for (let i = entries.length - 1; i >= 0; i--) {
    if (entries[i] !== null) {
      return entries[i];
    }
  }
  return null;
}

// ── Exports ───────────────────────────────────────────────────────────

module.exports = {
  appendEntry,
  verifyLedger,
  ledgerHealth,
  getEntries,
  getLastEntry,
};
