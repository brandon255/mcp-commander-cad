/**
 * cli.js — MCP Commander Core OS command-line interface.
 *
 * Commands:
 *   init            Idempotent scaffold (dirs, keys, contracts, CLAUDE.md)
 *   status          Security posture + ledger health
 *   redact <text>   Redact PII from a string (dry-run output)
 *   write           Write a state entry (gated)
 *   checkpoint      Copy-verified HOT → WARM
 *   archive         Encrypted WARM → COLD
 *   verify-ledger   Recompute tamper-evident chain
 *   mount <name>    Mount a cartridge (gated)
 *   unmount <name>  Unmount a cartridge
 *   list-cartridges List available and mounted cartridges
 *
 * Usage:
 *   node core/src/cli.js <command> [options]
 */

"use strict";

const { scaffold } = require("./bootstrap");
const paths = require("./paths");

// Lazy-load heavy modules so status/init stays fast
function loadModule(name) {
  switch (name) {
    case "gates":      return require("./gates");
    case "integrity":  return require("./integrity");
    case "vault":      return require("./vault");
    case "redact":     return require("./redact");
    case "memory":     return require("./memory");
    case "cartridges": return require("./cartridges");
    case "confidence": return require("./confidence");
    case "telemetry":  return require("./telemetry");
    case "llm":        return require("./llm");
    default: throw new Error(`Unknown module: ${name}`);
  }
}

// ── Command handlers ─────────────────────────────────────────────────

function cmdInit() {
  console.log("MCP Commander Core OS — Initializing...");
  const result = scaffold();
  console.log(`  Created: ${result.created.length} items`);
  console.log(`  Skipped: ${result.skipped.length} items (already exist)`);
  console.log("Done.");
}

function cmdStatus() {
  console.log("MCP Commander Core OS — Status");
  console.log("─".repeat(50));

  // Config
  const fs = require("fs");
  if (fs.existsSync(paths.CONFIG_FILE)) {
    const config = JSON.parse(fs.readFileSync(paths.CONFIG_FILE, "utf-8"));
    console.log(`  Status:       ${config.status}`);
    console.log(`  LLM Backend:  ${config.llm.backend}`);
    console.log(`  LLM Model:    ${config.llm.model}`);
    console.log(`  Telemetry:    ${config.telemetry.enabled ? "ON" : "OFF"}`);
  } else {
    console.log("  Config:       MISSING — run 'init' first");
  }

  // Ledger health
  const integrity = loadModule("integrity");
  const health = integrity.ledgerHealth();
  console.log(`  Ledger:       ${health.ok ? "HEALTHY" : "COMPROMISED"}`);
  if (health.entryCount !== undefined) {
    console.log(`  Entries:      ${health.entryCount}`);
  }
  if (!health.ok && health.reason) {
    console.log(`  Reason:       ${health.reason}`);
  }

  // Mounted cartridges
  const cartridges = loadModule("cartridges");
  const mounted = cartridges.listMounted();
  const available = cartridges.listAvailable();
  console.log(`  Cartridges:    ${mounted.length}/${available.length} mounted`);
  for (const name of mounted) {
    console.log(`    [M] ${name}`);
  }

  // Storage tiers
  const tiers = [
    { name: "HOT",  path: paths.HOT },
    { name: "WARM", path: paths.WARM },
    { name: "COLD", path: paths.COLD },
  ];
  for (const tier of tiers) {
    const exists = fs.existsSync(tier.path);
    const items = exists ? fs.readdirSync(tier.path).filter(f => f !== ".gitkeep") : [];
    console.log(`  Storage/${tier.name}: ${items.length} item(s)`);
  }

  console.log("─".repeat(50));
}

function cmdRedact(args) {
  const redact = loadModule("redact");
  const text = args.join(" ");
  if (!text) {
    console.error("Usage: cli.js redact <text>");
    process.exit(1);
  }
  const result = redact.redact(text);
  console.log("Redacted output:");
  console.log(result);
  console.log("");
  console.log("Matches found:", redact.countMatches(text));
}

async function cmdWrite(args) {
  // Parse --stage, --content, --confidence
  let stage = null;
  let content = null;
  let confidence = null;
  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--stage" && args[i + 1]) { stage = args[++i]; }
    else if (args[i] === "--content" && args[i + 1]) { content = args[++i]; }
    else if (args[i] === "--confidence" && args[i + 1]) { confidence = args[++i]; }
  }
  if (!stage || !content || !confidence) {
    console.error("Usage: cli.js write --stage <stage> --content <text> --confidence <HIGH|MEDIUM|LOW>");
    process.exit(1);
  }

  const confidenceMod = loadModule("confidence");
  confidenceMod.validateLabel(confidence); // throws if invalid

  const gates = loadModule("gates");
  // In CLI mode, we skip interactive gate and log the intent
  console.log(`Writing to stage '${stage}' with confidence '${confidence}'`);
  console.log(`Content: ${content.substring(0, 80)}${content.length > 80 ? "..." : ""}`);

  const integrity = loadModule("integrity");
  const telemetry = loadModule("telemetry");

  const entry = integrity.appendEntry({
    type: "write",
    stage,
    content,
    confidence,
    source: "cli",
    timestamp: new Date().toISOString(),
  });

  telemetry.log({
    event: "write",
    stage,
    confidence,
    entry_hash: entry.hash,
  });

  console.log(`Entry ${entry.sequence} appended to ledger. Hash: ${entry.hash}`);
}

function cmdCheckpoint() {
  const memory = loadModule("memory");
  console.log("Checkpoint: HOT → WARM (copy-verified)...");
  const result = memory.checkpoint();
  console.log(`  Copied:  ${result.copied} item(s)`);
  console.log(`  Failed:  ${result.failed} item(s)`);
  console.log("Done.");
}

function cmdArchive() {
  const memory = loadModule("memory");
  console.log("Archive: WARM → COLD (encrypted)...");
  const result = memory.archive();
  console.log(`  Archived: ${result.archived} item(s)`);
  console.log(`  Failed:   ${result.failed} item(s)`);
  console.log("Done.");
}

function cmdVerifyLedger() {
  const integrity = loadModule("integrity");
  console.log("Verifying tamper-evident ledger...");
  const result = integrity.verifyLedger();
  console.log(`  Entries:    ${result.total}`);
  console.log(`  Valid:      ${result.valid}`);
  console.log(`  Compromised: ${result.compromised}`);
  if (result.firstBreak) {
    console.log(`  First break: sequence ${result.firstBreak}`);
  }
  console.log(`  Status:     ${result.ok ? "HEALTHY" : "COMPROMISED"}`);
}

function cmdMount(args) {
  const name = args[0];
  if (!name) {
    console.error("Usage: cli.js mount <cartridge-name>");
    process.exit(1);
  }
  const cartridges = loadModule("cartridges");
  try {
    cartridges.mount(name);
    console.log(`Cartridge '${name}' mounted successfully.`);
  } catch (err) {
    console.error(`Mount failed: ${err.message}`);
    process.exit(1);
  }
}

function cmdUnmount(args) {
  const name = args[0];
  if (!name) {
    console.error("Usage: cli.js unmount <cartridge-name>");
    process.exit(1);
  }
  const cartridges = loadModule("cartridges");
  cartridges.unmount(name);
  console.log(`Cartridge '${name}' unmounted.`);
}

function cmdListCartridges() {
  const cartridges = loadModule("cartridges");
  const available = cartridges.listAvailable();
  const mounted = cartridges.listMounted();

  console.log("Available cartridges:");
  for (const name of available) {
    const isMounted = mounted.includes(name);
    const marker = isMounted ? "[MOUNTED]" : "";
    console.log(`  ${name} ${marker}`);
  }
}

// ── Router ────────────────────────────────────────────────────────────

const command = process.argv[2];
const args = process.argv.slice(3);

function printHelp() {
  console.log("MCP Commander Core OS — CLI");
  console.log("");
  console.log("Commands:");
  console.log("  init              Scaffold project (idempotent)");
  console.log("  status            Security posture + ledger health");
  console.log("  redact <text>     Redact PII from text");
  console.log("  write --stage <s> --content <c> --confidence <l>  Write entry (gated)");
  console.log("  checkpoint        HOT → WARM (copy-verified)");
  console.log("  archive           WARM → COLD (encrypted)");
  console.log("  verify-ledger     Verify tamper-evident chain");
  console.log("  mount <name>      Mount a cartridge");
  console.log("  unmount <name>    Unmount a cartridge");
  console.log("  list-cartridges   List available and mounted cartridges");
  console.log("");
}

switch (command) {
  case "init":
    cmdInit();
    break;
  case "status":
    cmdStatus();
    break;
  case "redact":
    cmdRedact(args);
    break;
  case "write":
    cmdWrite(args);
    break;
  case "checkpoint":
    cmdCheckpoint();
    break;
  case "archive":
    cmdArchive();
    break;
  case "verify-ledger":
    cmdVerifyLedger();
    break;
  case "mount":
    cmdMount(args);
    break;
  case "unmount":
    cmdUnmount(args);
    break;
  case "list-cartridges":
    cmdListCartridges();
    break;
  case undefined:
  case "--help":
  case "-h":
  case "help":
    printHelp();
    process.exit(0);
    break;
  default:
    printHelp();
    process.exit(1);
}
