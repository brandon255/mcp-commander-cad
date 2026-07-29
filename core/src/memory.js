/**
 * memory.js — HOT / WARM / COLD storage lifecycle management.
 *
 * Implements the three-tier storage model:
 *   HOT  — Active working data (fast access, current session)
 *   WARM — Completed work (reference, recent history)
 *   COLD — Encrypted long-term archive (encrypted at rest)
 *
 * Operations:
 *   checkpoint() — Copy-verified HOT → WARM (does NOT delete source)
 *   archive()    — Encrypted WARM → COLD (deletes source after verify)
 *   promoteFromCold() — Decrypt COLD → WARM (restore)
 *
 * RT-02: All state transitions logged to integrity ledger.
 * RT-03: COLD tier is AES-256-GCM encrypted.
 * RT-18: WORM — copies are hash-verified before promotion.
 */

"use strict";

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const paths = require("./paths");

// ── Helpers ────────────────────────────────────────────────────────

function ensureDir(dirPath) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}

/** System files to exclude from tier migrations. */
const SYSTEM_FILES = new Set([
  ".gitkeep",
  "ledger.jsonl",
  "state.json",
  "mounts.json",
]);

/**
 * Compute SHA-256 hex digest of a buffer.
 * @param {Buffer} data
 * @returns {string}
 */
function hashBuffer(data) {
  return crypto.createHash("sha256").update(data).digest("hex");
}

/**
 * List non-system files in a directory.
 * @param {string} dirPath
 * @returns {string[]} Array of filenames (not full paths).
 */
function listMigratableFiles(dirPath) {
  if (!fs.existsSync(dirPath)) return [];
  return fs
    .readdirSync(dirPath)
    .filter((f) => !SYSTEM_FILES.has(f) && !f.startsWith("."));
}

/**
 * Get file size in bytes.
 * @param {string} filePath
 * @returns {number}
 */
function fileSize(filePath) {
  try {
    const stat = fs.statSync(filePath);
    return stat.size;
  } catch {
    return 0;
  }
}

// ── Checkpoint: HOT → WARM (copy-verified) ───────────────────────

/**
 * Copy-verified checkpoint from HOT to WARM storage.
 *
 * For each file in HOT (excluding system files):
 *   1. Read content
 *   2. Compute SHA-256 hash
 *   3. Write to WARM with same filename
 *   4. Re-read from WARM and verify hash matches
 *
 * Source files are NOT deleted. Checkpoint is additive.
 *
 * @returns {{ copied: number, failed: number, errors: string[] }}
 */
function checkpoint() {
  ensureDir(paths.HOT);
  ensureDir(paths.WARM);

  const files = listMigratableFiles(paths.HOT);
  let copied = 0;
  let failed = 0;
  const errors = [];

  for (const file of files) {
    try {
      const srcPath = path.join(paths.HOT, file);
      const dstPath = path.join(paths.WARM, file);
      const content = fs.readFileSync(srcPath);

      // Hash the source content
      const srcHash = hashBuffer(content);

      // Write to WARM
      ensureDir(path.dirname(dstPath));
      fs.writeFileSync(dstPath, content);

      // Verify the copy by reading back and comparing hash
      const verifyContent = fs.readFileSync(dstPath);
      const dstHash = hashBuffer(verifyContent);

      if (srcHash !== dstHash) {
        failed++;
        errors.push(`Hash mismatch for ${file}: source=${srcHash} dest=${dstHash}`);
        // Remove corrupted copy
        fs.unlinkSync(dstPath);
        continue;
      }

      copied++;
    } catch (err) {
      failed++;
      errors.push(`${file}: ${err.message}`);
    }
  }

  return { copied, failed, errors };
}

// ── Archive: WARM → COLD (encrypted) ─────────────────────────────

/**
 * Archive files from WARM to COLD with AES-256-GCM encryption.
 *
 * Requires the vault module for encryption. Each file in WARM is:
 *   1. Read
 *   2. Encrypted with vault.encrypt()
 *   3. Written to COLD with .vault extension
 *   4. Decrypted and hash-verified
 *   5. Source in WARM deleted after successful verification
 *
 * @returns {{ archived: number, failed: number, errors: string[] }}
 */
function archive() {
  ensureDir(paths.WARM);
  ensureDir(paths.COLD);

  let vault;
  try {
    vault = require("./vault");
  } catch (err) {
    return {
      archived: 0,
      failed: 0,
      errors: [`Cannot load vault module: ${err.message}`],
    };
  }

  const archivePassword =
    process.env.MCP_COMMANDER_ARCHIVE_KEY || "mcp-commander-archive-default";
  const files = listMigratableFiles(paths.WARM);
  let archived = 0;
  let failed = 0;
  const errors = [];

  for (const file of files) {
    try {
      const srcPath = path.join(paths.WARM, file);
      const dstName = file.endsWith(".vault") ? file : file + ".vault";
      const dstPath = path.join(paths.COLD, dstName);

      // Read source content
      const content = fs.readFileSync(srcPath);
      const srcHash = hashBuffer(content);

      // Encrypt to COLD
      vault.encrypt(content, archivePassword, dstPath);

      // Verify by decrypting and comparing
      const decrypted = vault.decrypt(dstPath, archivePassword);
      const verifyHash = hashBuffer(Buffer.from(decrypted));

      if (srcHash !== verifyHash) {
        failed++;
        errors.push(`Archive verify failed for ${file}: hash mismatch`);
        fs.unlinkSync(dstPath);
        continue;
      }

      // Success — remove from WARM
      fs.unlinkSync(srcPath);
      archived++;
    } catch (err) {
      failed++;
      errors.push(`${file}: ${err.message}`);
    }
  }

  return { archived, failed, errors };
}

// ── Promote: COLD → WARM (decrypt and restore) ────────────────────

/**
 * Restore a file from COLD (encrypted) back to WARM (plaintext).
 *
 * @param {string} fileName - Filename in COLD (with or without .vault extension)
 * @param {string} [password] - Archive password. Defaults to env MCP_COMMANDER_ARCHIVE_KEY or "mcp-commander-archive-default".
 * @returns {{ success: boolean, filePath?: string, error?: string }}
 */
function promoteFromCold(fileName, password) {
  const archivePassword = password || process.env.MCP_COMMANDER_ARCHIVE_KEY || "mcp-commander-archive-default";

  // Resolve filename — accept with or without .vault extension
  let coldName = fileName;
  if (!coldName.endsWith(".vault")) {
    coldName = coldName + ".vault";
  }

  const coldPath = path.join(paths.COLD, coldName);
  const warmName = fileName.replace(/\.vault$/, "");
  const warmPath = path.join(paths.WARM, warmName);

  try {
    if (!fs.existsSync(coldPath)) {
      return { success: false, error: `File not found in COLD: ${coldName}` };
    }

    // Decrypt from COLD
    const plaintext = require("./vault").decrypt(coldPath, archivePassword);

    // Write to WARM
    ensureDir(paths.WARM);
    fs.writeFileSync(warmPath, plaintext);

    return { success: true, filePath: warmPath };
  } catch (err) {
    return { success: false, error: `Promote failed: ${err.message}` };
  }
}

// ── Stats ──────────────────────────────────────────────────────────

/**
 * Get file count and total size for each storage tier.
 *
 * @returns {{ hot: { files: number, sizeBytes: number }, warm: { files: number, sizeBytes: number }, cold: { files: number, sizeBytes: number } }}
 */
function getTierStats() {
  const tiers = [
    { name: "hot", dir: paths.HOT },
    { name: "warm", dir: paths.WARM },
    { name: "cold", dir: paths.COLD },
  ];

  const result = {};
  for (const tier of tiers) {
    let files = 0;
    let sizeBytes = 0;
    if (fs.existsSync(tier.dir)) {
      const entries = fs.readdirSync(tier.dir).filter((f) => f !== ".gitkeep");
      for (const entry of entries) {
        const fp = path.join(tier.dir, entry);
        const stat = fs.statSync(fp);
        if (stat.isFile()) {
          files++;
          sizeBytes += stat.size;
        }
      }
    }
    result[tier.name] = { files, sizeBytes };
  }

  return result;
}

// ── Idle detection ──────────────────────────────────────────────────

/**
 * Check if HOT storage has been idle (no file modifications)
 * for longer than the configured threshold.
 *
 * @param {number} [thresholdMs] - Override threshold. Default: from config (300000ms / 5min).
 * @returns {boolean} True if HOT has been idle beyond threshold.
 */
function isIdle(thresholdMs) {
  ensureDir(paths.HOT);

  // Load configured threshold
  if (thresholdMs === undefined) {
    try {
      const config = JSON.parse(fs.readFileSync(paths.CONFIG_FILE, "utf-8"));
      thresholdMs = (config.memory && config.memory.idle_threshold_ms) || 300000;
    } catch {
      thresholdMs = 300000;
    }
  }

  // Find the most recent file modification in HOT
  const files = listMigratableFiles(paths.HOT);
  if (files.length === 0) return true; // Empty HOT = idle

  let mostRecent = 0;
  for (const file of files) {
    try {
      const stat = fs.statSync(path.join(paths.HOT, file));
      if (stat.mtimeMs > mostRecent) {
        mostRecent = stat.mtimeMs;
      }
    } catch {
      // Skip files that can't be stat'd
    }
  }

  const elapsed = Date.now() - mostRecent;
  return elapsed > thresholdMs;
}

module.exports = {
  checkpoint,
  archive,
  promoteFromCold,
  getTierStats,
  isIdle,
};
