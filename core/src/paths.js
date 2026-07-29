/**
 * paths.js — Absolute path resolution from project root.
 *
 * All file-system references in MCP Commander MUST go through this module.
 * No relative paths, no process.cwd() drift, no cross-platform surprises.
 *
 * Resolves every path against MCP_COMMANDER_ROOT (project root), which is detected
 * by walking upward from __dirname until a marker file (mcp-commander.config.json)
 * is found. Falls back to dirname of this file's grandparent if no marker exists.
 *
 * RT-12 compliance: all lifecycle paths are absolute.
 */

"use strict";

const path = require("path");
const fs = require("fs");

// ── Root detection ──────────────────────────────────────────────────
function findProjectRoot(startDir) {
  let dir = startDir;
  const marker = "mcp-commander.config.json";
  while (true) {
    const candidate = path.join(dir, marker);
    if (fs.existsSync(candidate)) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) break; // filesystem root
    dir = parent;
  }
  // Fallback: two levels up from this file  (core/src/ -> project root)
  return path.resolve(__dirname, "..", "..");
}

const MCP_COMMANDER_ROOT = findProjectRoot(__dirname);

// ── Sub-path builders ────────────────────────────────────────────────

const CORE = path.join(MCP_COMMANDER_ROOT, "core");
const CORE_SRC = path.join(CORE, "src");
const CORE_CONFIG = path.join(CORE, "config");

const STORAGE = path.join(CORE, "storage");
const HOT = path.join(STORAGE, "hot");
const WARM = path.join(STORAGE, "warm");
const COLD = path.join(STORAGE, "cold");

const CARTRIDGES = path.join(MCP_COMMANDER_ROOT, "cartridges");

const CONFIG_DIR = path.join(MCP_COMMANDER_ROOT, "config");
const CONFIG_FILE = path.join(CONFIG_DIR, "mcp-commander.config.json");
const SIGNING_PUB = path.join(CONFIG_DIR, "cartridge_signing.pub");
const KEYS_DIR = path.join(CONFIG_DIR, ".keys");

const DOCS = path.join(MCP_COMMANDER_ROOT, "docs");
const REDTEAM = path.join(MCP_COMMANDER_ROOT, "redteam");
const TESTS = path.join(MCP_COMMANDER_ROOT, "tests");

const LEDGER_FILE = path.join(HOT, "ledger.jsonl");
const STATE_FILE = path.join(HOT, "state.json");
const TELEMETRY_FILE = path.join(WARM, "telemetry.csv");

const CLAUDE_MD = path.join(MCP_COMMANDER_ROOT, ".claude.md");
const GITIGNORE = path.join(MCP_COMMANDER_ROOT, ".gitignore");

// ── Helpers ──────────────────────────────────────────────────────────

/**
 * Join one or more segments to the project root.
 * Ensures absolute path on every platform.
 */
function root(...segments) {
  return path.resolve(MCP_COMMANDER_ROOT, ...segments);
}

/**
 * Join one or more segments to the HOT storage tier.
 */
function hot(...segments) {
  return path.resolve(HOT, ...segments);
}

/**
 * Join one or more segments to the WARM storage tier.
 */
function warm(...segments) {
  return path.resolve(WARM, ...segments);
}

/**
 * Join one or more segments to the COLD storage tier.
 */
function cold(...segments) {
  return path.resolve(COLD, ...segments);
}

/**
 * Join one or more segments to the cartridges directory.
 */
function cartridge(cartridgeName, ...segments) {
  return path.resolve(CARTRIDGES, cartridgeName, ...segments);
}

module.exports = {
  MCP_COMMANDER_ROOT,
  CORE,
  CORE_SRC,
  CORE_CONFIG,
  STORAGE,
  HOT,
  WARM,
  COLD,
  CARTRIDGES,
  CONFIG_DIR,
  CONFIG_FILE,
  SIGNING_PUB,
  KEYS_DIR,
  DOCS,
  REDTEAM,
  TESTS,
  LEDGER_FILE,
  STATE_FILE,
  TELEMETRY_FILE,
  CLAUDE_MD,
  GITIGNORE,
  root,
  hot,
  warm,
  cold,
  cartridge,
};
