/**
 * bootstrap.js — Idempotent scaffold for MCP Commander project.
 *
 * Creates all required directories, config files, and initial state
 * on first run.  Safe to run repeatedly — never overwrites existing files
 * or data (RT-21 idempotency).
 *
 * Usage:
 *   node core/src/bootstrap.js          # scaffold the project
 *   node core/src/cli.js init           # also calls bootstrap internally
 */

"use strict";

const fs = require("fs");
const path = require("path");
const paths = require("./paths");

// ── Helpers ──────────────────────────────────────────────────────────

function mkdirIfAbsent(dirPath) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
    return true; // created
  }
  return false; // already existed
}

/**
 * Write `content` to `filePath` ONLY if the file does not already exist.
 * Returns true if written, false if skipped.
 */
function writeIfAbsent(filePath, content) {
  if (fs.existsSync(filePath)) return false;
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, content, "utf-8");
  return true;
}

// ── Default config ────────────────────────────────────────────────────

const DEFAULT_CONFIG = {
  status: "DRAFT",
  pilot_seats: [],
  pricing_model: null,
  packet_cap: null,
  llm: {
    backend: "ollama",        // "ollama" | "llamacpp" | "none"
    model: "llama3:8b",
    base_url: "http://localhost:11434",
    timeout_ms: 30000,
  },
  memory: {
    idle_threshold_ms: 300000,  // 5 minutes idle → eligible for checkpoint
    max_hot_entries: 10000,
  },
  gates: {
    min_why_length: 20,        // RT-20: minimum explanation length
    approve_token: "APPROVE",   // exact token required to pass gate
  },
  telemetry: {
    enabled: true,
    hmac_pseudonym: true,       // RT-09: HMAC-based user pseudonym
  },
  redact: {
    patterns: [
      "ssn",
      "credit_card",
      "phone",
      "email",
      "api_key",
    ],
  },
  storage: {
    encryption_algorithm: "aes-256-gcm",  // RT-03
    key_derivation: "pbkdf2",
    iterations: 100000,
  },
};

const DEFAULT_CLAUDE_MD = `# MCP Commander CAD MCP — Project Rules

## Core OS Enforcement
- All safety guarantees are enforced by deterministic code, not prompt instructions.
- Local-first: private data never leaves the machine.
- Cloud CAD APIs (Onshape, Fusion 360) are gated external touchpoints only.

## Architecture
- Bay 0 (core/) is the base OS layer. All cartridges mount through it.
- Cartridges are isolated: each declares permitted write tiers and owned stages.
- The cognitive engine (mcp-commander-cognitive) runs in the background on every operation.

## Working Rules
- Never skip a gate. Every write passes through gates.js.
- Never store PII without redaction. Every write passes through redact.js.
- Every state change appends to the WORM ledger (integrity.js).
- Storage lifecycle: HOT (active) → WARM (completed) → COLD (encrypted archive).

## Prohibited
- No prompt-based safety overrides. Code-only enforcement.
- No cross-cartridge data access. Cartridges are sandboxed.
- No telemetry without HMAC pseudonym.
`;

const DEFAULT_GITIGNORE = `# MCP Commander CAD MCP
node_modules/
config/.keys/
core/storage/hot/*
core/storage/warm/*
core/storage/cold/*
!core/storage/hot/.gitkeep
!core/storage/warm/.gitkeep
!core/storage/cold/.gitkeep
*.log
.env
__pycache__/
*.pyc
.DS_Store
`;

// ── Scaffold ─────────────────────────────────────────────────────────

function scaffold() {
  const created = [];
  const skipped = [];

  // Directories
  const dirs = [
    paths.MCP_COMMANDER_ROOT,
    paths.CORE,
    paths.CORE_SRC,
    paths.CORE_CONFIG,
    paths.HOT,
    paths.WARM,
    paths.COLD,
    paths.CARTRIDGES,
    paths.CONFIG_DIR,
    paths.KEYS_DIR,
    paths.DOCS,
    path.join(paths.DOCS, "architecture"),
    path.join(paths.DOCS, "research"),
    paths.REDTEAM,
    path.join(paths.TESTS, "Unit"),
    path.join(paths.TESTS, "Integration"),
  ];

  for (const dir of dirs) {
    if (mkdirIfAbsent(dir)) {
      created.push(`dir: ${path.relative(paths.MCP_COMMANDER_ROOT, dir)}`);
    } else {
      skipped.push(`dir: ${path.relative(paths.MCP_COMMANDER_ROOT, dir)} (exists)`);
    }
  }

  // Config files
  if (writeIfAbsent(paths.CONFIG_FILE, JSON.stringify(DEFAULT_CONFIG, null, 2) + "\n")) {
    created.push(`file: mcp-commander.config.json`);
  } else {
    skipped.push(`file: mcp-commander.config.json (exists)`);
  }

  if (writeIfAbsent(paths.CLAUDE_MD, DEFAULT_CLAUDE_MD)) {
    created.push(`file: .claude.md`);
  } else {
    skipped.push(`file: .claude.md (exists)`);
  }

  if (writeIfAbsent(paths.GITIGNORE, DEFAULT_GITIGNORE)) {
    created.push(`file: .gitignore`);
  } else {
    skipped.push(`file: .gitignore (exists)`);
  }

  // .gitkeep files in storage dirs
  for (const tier of [paths.HOT, paths.WARM, paths.COLD]) {
    const gitkeep = path.join(tier, ".gitkeep");
    if (writeIfAbsent(gitkeep, "")) {
      created.push(`file: ${path.relative(paths.MCP_COMMANDER_ROOT, gitkeep)}`);
    }
  }

  return { created, skipped };
}

// ── CLI entry ──────────────────────────────────────────────────────────

if (require.main === module) {
  const result = scaffold();
  console.log(`MCP Commander Bootstrap complete.`);
  console.log(`  Created: ${result.created.length}`);
  for (const item of result.created) console.log(`    + ${item}`);
  console.log(`  Skipped: ${result.skipped.length}`);
  for (const item of result.skipped) console.log(`    . ${item}`);
}

module.exports = { scaffold };
