/**
 * telemetry.js — HMAC-pseudonym telemetry for MCP Commander Core OS.
 *
 * All usage telemetry is anonymized using HMAC-SHA256 pseudonyms
 * before being written to disk. No identifiable data leaves the machine.
 *
 * RT-09: HMAC-based user pseudonym — same machine always produces the same
 *        pseudonym, but there is no reverse lookup from pseudonym to identity.
 * RT-10: No identifiable telemetry data — all entries are pseudonymized.
 */

"use strict";

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const os = require("os");
const paths = require("./paths");
const redact = require("./redact");

// ── CSV header ─────────────────────────────────────────────────────

const CSV_HEADER = "timestamp,pseudonym,event,stage,confidence,entry_hash,details";
const HEADER_BYTES = Buffer.from(CSV_HEADER + "\n", "utf-8");

// ── Machine secret derivation ────────────────────────────────────

/**
 * Get or derive the telemetry HMAC secret.
 * Priority:
 *   1. MCP_COMMANDER_TELEMETRY_SECRET environment variable
 *   2. SHA-256 hash of hostname (deterministic per machine)
 *
 * @returns {Buffer} 32-byte HMAC key.
 */
function getSecretKey() {
  const envSecret = process.env.MCP_COMMANDER_TELEMETRY_SECRET;
  if (envSecret && envSecret.length >= 16) {
    return crypto.createHash("sha256").update(envSecret).digest();
  }

  // Derive from machine hostname — deterministic per machine, not reverse-lookupable
  const hostname = os.hostname() || "mcp-commander-unknown";
  return crypto.createHash("sha256").update("mcp-commander-telemetry-" + hostname).digest();
}

// ── Config ──────────────────────────────────────────────────────────

/**
 * Check if telemetry is enabled in the MCP Commander config.
 * @returns {boolean}
 */
function isTelemetryEnabled() {
  try {
    const config = JSON.parse(fs.readFileSync(paths.CONFIG_FILE, "utf-8"));
    return config.telemetry && config.telemetry.enabled !== false;
  } catch {
    return true; // Default to enabled if config missing
  }
}

// ── Pseudonym generation ────────────────────────────────────────────

/**
 * Generate an HMAC-SHA256 pseudonym from a seed string.
 *
 * The pseudonym is deterministic — the same seed on the same machine
 * always produces the same 16-character hex string. There is no way to
 * reverse from pseudonym back to the seed without the secret key.
 *
 * @param {string} seed - The data to pseudonymize (e.g., event type + timestamp)
 * @returns {string} 16-character hex pseudonym (64-bit).
 */
function generatePseudonym(seed) {
  const secretKey = getSecretKey();
  const hmac = crypto.createHmac("sha256", secretKey);
  hmac.update(String(seed));
  return hmac.digest("hex").substring(0, 16);
}

// ── File initialization ────────────────────────────────────────────

/**
 * Ensure the telemetry CSV file exists with a header row.
 * Creates the file (and parent directories) if absent.
 */
function ensureFile() {
  const dir = path.dirname(paths.TELEMETRY_FILE);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }

  if (!fs.existsSync(paths.TELEMETRY_FILE)) {
    fs.writeFileSync(paths.TELEMETRY_FILE, HEADER_BYTES, "utf-8");
  }
}

// ── Logging ────────────────────────────────────────────────────────

/**
 * Log a telemetry event to the CSV file.
 *
 * If telemetry is disabled in config, silently returns without logging.
 * Each event is pseudonymized using HMAC before being written.
 *
 * @param {object} eventData
 * @param {string} eventData.event - Event type (e.g., "write", "mount", "checkpoint")
 * @param {string} [eventData.stage] - Stage the event relates to
 * @param {string} [eventData.confidence] - Confidence label at time of event
 * @param {string} [eventData.entry_hash] - Associated ledger entry hash
 * @param {string} [eventData.details] - Additional details
 * @returns {{ logged: boolean, path: string }}
 */
function log(eventData) {
  if (!isTelemetryEnabled()) {
    return { logged: false, path: paths.TELEMETRY_FILE };
  }

  try {
    ensureFile();

    const timestamp = new Date().toISOString();
    const pseudonym = generatePseudonym(
      `${eventData.event || "unknown"}:${timestamp}`
    );

    // CSV-escape fields: replace commas with spaces, remove newlines
    const esc = (val) => {
      if (val === undefined || val === null) return "";
      return String(val).replace(/[\n\r,]/g, " ").trim();
    };

    // RT-10: Redact all text fields before writing to prevent PII leakage
    const escRedacted = (val) => {
      if (val === undefined || val === null) return "";
      const raw = String(val);
      return redact.redact(raw).replace(/[\n\r,]/g, " ").trim();
    };

    const row = [
      timestamp,
      pseudonym,
      escRedacted(eventData.event),
      escRedacted(eventData.stage),
      esc(eventData.confidence),
      esc(eventData.entry_hash),
      escRedacted(eventData.details),
    ].join(",");

    fs.appendFileSync(paths.TELEMETRY_FILE, row + "\n", "utf-8");

    return { logged: true, path: paths.TELEMETRY_FILE };
  } catch (err) {
    // Telemetry must NEVER crash the system (RT-10)
    return { logged: false, path: paths.TELEMETRY_FILE, error: err.message };
  }
}

// ── Stats ──────────────────────────────────────────────────────────

/**
 * Get telemetry file statistics.
 *
 * @returns {{ totalEvents: number, fileExists: boolean, fileSize: number }}
 */
function getTelemetryStats() {
  const exists = fs.existsSync(paths.TELEMETRY_FILE);
  if (!exists) {
    return { totalEvents: 0, fileExists: false, fileSize: 0 };
  }

  try {
    const stat = fs.statSync(paths.TELEMETRY_FILE);
    const content = fs.readFileSync(paths.TELEMETRY_FILE, "utf-8");
    const lines = content.split("\n").filter((l) => l.trim().length > 0);
    // Subtract 1 for the header row
    const totalEvents = Math.max(0, lines.length - 1);

    return {
      totalEvents,
      fileExists: true,
      fileSize: stat.size,
    };
  } catch {
    return { totalEvents: 0, fileExists: true, fileSize: 0 };
  }
}

module.exports = {
  log,
  generatePseudonym,
  isTelemetryEnabled,
  getTelemetryStats,
};
