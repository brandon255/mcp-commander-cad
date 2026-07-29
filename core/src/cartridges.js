/**
 * cartridges.js — Cartridge mount, verify, and isolation module.
 *
 * Cartridges are isolated, permission-scoped modules that mount through Bay 0.
 * Each cartridge has a signed JSON manifest (cartridge.json) declaring its
 * capabilities, write tiers, and tool count.
 *
 * Mount registry is persisted in HOT storage (mounts.json) so that mounted
 * cartridges survive across CLI invocations within a session.
 *
 * RT references:
 *   RT-08: No cross-cartridge data access (enforced by permissions model)
 *   RT-11: Signed cartridge manifests (Ed25519)
 *   RT-13: Cartridge isolation — each cartridge declares write tiers and owned stages
 */

"use strict";

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const paths = require("./paths");

// ── Internal helpers ──────────────────────────────────────────────────

const MOUNTS_FILE = path.join(paths.HOT, "mounts.json");

const VALID_WRITE_TIERS = new Set(["hot", "warm", "cold"]);
const SEMVER_RE = /^\d+\.\d+\.\d+(-[\w.]+)?(\+[\w.]+)?$/;

/**
 * Read and parse the mount registry. Returns [] if file doesn't exist.
 * @returns {string[]}
 */
function readMountRegistry() {
  if (!fs.existsSync(MOUNTS_FILE)) {
    return [];
  }
  try {
    const data = JSON.parse(fs.readFileSync(MOUNTS_FILE, "utf-8"));
    if (Array.isArray(data)) {
      return data.filter(function (entry) {
        return typeof entry === "string";
      });
    }
    return [];
  } catch (_) {
    return [];
  }
}

/**
 * Persist the mount registry to disk.
 * @param {string[]} mounts
 */
function writeMountRegistry(mounts) {
  fs.writeFileSync(MOUNTS_FILE, JSON.stringify(mounts, null, 2) + "\n", "utf-8");
}

/**
 * Attempt to load an Ed25519 public key from a file path.
 * Supports PEM-encoded SPKI keys and raw 32-byte hex-encoded keys.
 *
 * @param {string} publicKeyPath
 * @returns {crypto.KeyObject|null}
 */
function loadEd25519PublicKey(publicKeyPath) {
  if (!fs.existsSync(publicKeyPath)) {
    return null;
  }

  const raw = fs.readFileSync(publicKeyPath, "utf-8").trim();

  // Attempt 1: PEM format (contains -----BEGIN)
  if (raw.includes("-----BEGIN")) {
    try {
      return crypto.createPublicKey(raw);
    } catch (_) {
      return null;
    }
  }

  // Attempt 2: Raw 32-byte hex-encoded Ed25519 public key
  const hex = raw.replace(/\s+/g, "");
  if (/^[0-9a-fA-F]{64}$/.test(hex)) {
    try {
      const rawBuf = Buffer.from(hex, "hex");
      // Wrap the raw 32-byte key as a JWK so Node's crypto can consume it
      return crypto.createPublicKey({
        key: {
          kty: "OKP",
          crv: "Ed25519",
          x: rawBuf.toString("base64url"),
        },
        format: "jwk",
      });
    } catch (_) {
      return null;
    }
  }

  // Attempt 3: Raw base64url-encoded Ed25519 public key
  try {
    const rawBuf = Buffer.from(hex, "base64url");
    if (rawBuf.length === 32) {
      return crypto.createPublicKey({
        key: {
          kty: "OKP",
          crv: "Ed25519",
          x: rawBuf.toString("base64url"),
        },
        format: "jwk",
      });
    }
  } catch (_) {
    // fall through
  }

  return null;
}

// ── Public API ────────────────────────────────────────────────────────

/**
 * Scan the cartridges directory for available cartridges.
 * A cartridge is "available" if its subdirectory contains a cartridge.json file.
 *
 * @returns {string[]} Array of cartridge names (directory names).
 */
function listAvailable() {
  if (!fs.existsSync(paths.CARTRIDGES)) {
    return [];
  }

  try {
    const entries = fs.readdirSync(paths.CARTRIDGES, { withFileTypes: true });
    const available = [];
    for (const entry of entries) {
      if (!entry.isDirectory()) continue;
      const manifestPath = path.join(paths.CARTRIDGES, entry.name, "cartridge.json");
      if (fs.existsSync(manifestPath)) {
        available.push(entry.name);
      }
    }
    return available.sort();
  } catch (_) {
    return [];
  }
}

/**
 * List currently mounted cartridges.
 *
 * @returns {string[]} Array of mounted cartridge names.
 */
function listMounted() {
  return readMountRegistry();
}

/**
 * Verify a cartridge manifest's structure and optional Ed25519 signature.
 *
 * Checks required fields (name, version, description, permissions, tools),
 * validates write tiers and tool array, and optionally verifies a
 * cryptographic signature when a public key path is provided.
 *
 * @param {object} manifest - Parsed cartridge.json object.
 * @param {string} [publicKeyPath] - Path to Ed25519 public key for signature verification.
 * @returns {{ valid: boolean, errors: string[] }}
 */
function verifyManifest(manifest, publicKeyPath) {
  const errors = [];

  // ── Required top-level fields ──
  if (!manifest || typeof manifest !== "object") {
    return { valid: false, errors: ["Manifest must be a non-null object."] };
  }

  if (typeof manifest.name !== "string" || manifest.name.length === 0) {
    errors.push("Missing or invalid 'name' field (expected non-empty string).");
  }

  if (typeof manifest.version !== "string" || !SEMVER_RE.test(manifest.version)) {
    errors.push(
      "Missing or invalid 'version' field (expected semver string, e.g. '1.0.0')."
    );
  }

  if (typeof manifest.description !== "string" || manifest.description.length === 0) {
    errors.push("Missing or invalid 'description' field (expected non-empty string).");
  }

  // ── Permissions ──
  if (
    !manifest.permissions ||
    typeof manifest.permissions !== "object" ||
    Array.isArray(manifest.permissions)
  ) {
    errors.push("Missing or invalid 'permissions' field (expected object with writeTiers and allowedStages).");
  } else {
    const perms = manifest.permissions;

    if (!Array.isArray(perms.writeTiers)) {
      errors.push("'permissions.writeTiers' must be an array.");
    } else {
      const invalidTiers = perms.writeTiers.filter(function (t) {
        return !VALID_WRITE_TIERS.has(t);
      });
      if (invalidTiers.length > 0) {
        errors.push(
          `Invalid write tier(s): ${invalidTiers.join(", ")}. Allowed: hot, warm, cold.`
        );
      }
    }

    if (!Array.isArray(perms.allowedStages)) {
      errors.push("'permissions.allowedStages' must be an array.");
    }
  }

  // ── Tools ──
  if (!Array.isArray(manifest.tools)) {
    errors.push("Missing or invalid 'tools' field (expected array).");
  } else if (manifest.tools.length === 0) {
    errors.push("'tools' array must contain at least one tool.");
  } else {
    for (let i = 0; i < manifest.tools.length; i++) {
      const tool = manifest.tools[i];
      if (!tool || typeof tool !== "object") {
        errors.push(`tools[${i}] must be an object.`);
        continue;
      }
      if (typeof tool.name !== "string" || tool.name.length === 0) {
        errors.push(`tools[${i}].name must be a non-empty string.`);
      }
      if (typeof tool.description !== "string" || tool.description.length === 0) {
        errors.push(`tools[${i}].description must be a non-empty string.`);
      }
    }
  }

  // ── Signature verification (RT-11) ──
  if (publicKeyPath && manifest.signature && manifest.signedData) {
    const pubKey = loadEd25519PublicKey(publicKeyPath);
    if (!pubKey) {
      errors.push(
        "Signature verification failed: could not load Ed25519 public key from " +
          publicKeyPath +
          "."
      );
    } else {
      try {
        const sigBuf = Buffer.from(manifest.signature, "hex");
        const dataBuf = Buffer.from(manifest.signedData, "hex");
        const isValid = crypto.verify("ed25519", dataBuf, pubKey, sigBuf);
        if (!isValid) {
          errors.push(
            "Signature verification failed: Ed25519 signature does not match signedData."
          );
        }
      } catch (err) {
        errors.push(
          "Signature verification failed: " + err.message
        );
      }
    }
  }

  return {
    valid: errors.length === 0,
    errors: errors,
  };
}

/**
 * Mount a cartridge.
 *
 * Validates the cartridge manifest, optionally verifies its Ed25519
 * signature (when a signing public key is present), and registers it
 * in the mount registry.
 *
 * @param {string} name - Cartridge name (directory name under paths.CARTRIDGES).
 * @throws {Error} Descriptive error if any step fails.
 */
function mount(name) {
  if (!name || typeof name !== "string") {
    throw new Error("Cartridge name must be a non-empty string.");
  }

  // 1. Check cartridge directory and manifest exist
  const manifestPath = path.join(paths.CARTRIDGES, name, "cartridge.json");
  if (!fs.existsSync(paths.CARTRIDGES)) {
    throw new Error(
      "Cartridges directory does not exist: " + paths.CARTRIDGES +
        ". Run 'init' first."
    );
  }
  if (!fs.existsSync(manifestPath)) {
    throw new Error(
      `Cartridge '${name}' not found. No cartridge.json at ` + manifestPath + "."
    );
  }

  // 2. Read and parse manifest
  let manifest;
  try {
    manifest = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));
  } catch (err) {
    throw new Error(
      `Failed to parse cartridge.json for '${name}': ` + err.message
    );
  }

  // 3. Verify manifest
  const publicKeyPath = fs.existsSync(paths.SIGNING_PUB) ? paths.SIGNING_PUB : null;
  const result = verifyManifest(manifest, publicKeyPath);
  if (!result.valid) {
    throw new Error(
      `Cartridge '${name}' manifest validation failed:\n  ` +
        result.errors.join("\n  ")
    );
  }

  // 4. Check that manifest name matches directory name (RT-08 isolation)
  if (manifest.name !== name) {
    throw new Error(
      `Cartridge manifest name '${manifest.name}' does not match directory name '${name}'.`
    );
  }

  // 5. Check for duplicate mount
  const mounted = readMountRegistry();
  if (mounted.includes(name)) {
    throw new Error(
      `Cartridge '${name}' is already mounted.`
    );
  }

  // 6. Register in mount registry
  mounted.push(name);
  writeMountRegistry(mounted);
}

/**
 * Unmount a cartridge.
 *
 * Removes the cartridge from the mount registry. Does NOT delete
 * the cartridge's files on disk. Logs an unmount event via the
 * integrity module for audit trail.
 *
 * @param {string} name - Cartridge name to unmount.
 */
function unmount(name) {
  if (!name || typeof name !== "string") {
    throw new Error("Cartridge name must be a non-empty string.");
  }

  const mounted = readMountRegistry();
  const index = mounted.indexOf(name);
  if (index === -1) {
    // Not mounted — nothing to do, but still log for audit
  } else {
    mounted.splice(index, 1);
    writeMountRegistry(mounted);
  }

  // Log via integrity module for audit trail (RT-13)
  try {
    const integrity = require("./integrity");
    integrity.appendEntry({
      type: "unmount",
      cartridge: name,
      timestamp: new Date().toISOString(),
    });
  } catch (_) {
    // Integrity module may not be available in all contexts;
    // unmount itself should not fail because of logging.
  }
}

/**
 * Read and return the parsed cartridge.json for a given cartridge.
 *
 * @param {string} name - Cartridge name (directory name).
 * @returns {object|null} Parsed manifest, or null if not found.
 */
function getManifest(name) {
  if (!name || typeof name !== "string") {
    return null;
  }

  const manifestPath = path.join(paths.CARTRIDGES, name, "cartridge.json");
  if (!fs.existsSync(manifestPath)) {
    return null;
  }

  try {
    return JSON.parse(fs.readFileSync(manifestPath, "utf-8"));
  } catch (_) {
    return null;
  }
}

/**
 * Get the tools array from a mounted cartridge's manifest.
 *
 * @param {string} name - Cartridge name.
 * @returns {Array<{name: string, description: string}>} Tools array, or empty array if not found or not mounted.
 */
function getCartridgeTools(name) {
  if (!name || typeof name !== "string") {
    return [];
  }

  // Verify the cartridge is currently mounted
  const mounted = readMountRegistry();
  if (!mounted.includes(name)) {
    return [];
  }

  const manifest = getManifest(name);
  if (!manifest || !Array.isArray(manifest.tools)) {
    return [];
  }

  return manifest.tools;
}

/**
 * Check if a mounted cartridge has permission to write to a given tier and stage.
 *
 * Enforces RT-08 (no cross-cartridge data access) and RT-13 (cartridge
 * isolation with declared write tiers and owned stages).
 *
 * @param {string} cartridgeName - Name of the mounted cartridge.
 * @param {string} tier - Storage tier to check ("hot", "warm", or "cold").
 * @param {string} stage - CAD stage to check (e.g. "sketch", "features").
 * @returns {{ allowed: boolean, reason?: string }}
 */
function checkPermission(cartridgeName, tier, stage) {
  if (!cartridgeName || typeof cartridgeName !== "string") {
    return { allowed: false, reason: "Cartridge name must be a non-empty string." };
  }

  if (!tier || typeof tier !== "string") {
    return { allowed: false, reason: "Tier must be a non-empty string." };
  }

  if (!stage || typeof stage !== "string") {
    return { allowed: false, reason: "Stage must be a non-empty string." };
  }

  // Verify the cartridge is mounted
  const mounted = readMountRegistry();
  if (!mounted.includes(cartridgeName)) {
    return {
      allowed: false,
      reason: `Cartridge '${cartridgeName}' is not mounted.`,
    };
  }

  // Load the manifest
  const manifest = getManifest(cartridgeName);
  if (!manifest || !manifest.permissions) {
    return {
      allowed: false,
      reason: `Cartridge '${cartridgeName}' has no valid permissions in its manifest.`,
    };
  }

  const perms = manifest.permissions;

  // Check write tier
  if (!Array.isArray(perms.writeTiers) || !perms.writeTiers.includes(tier)) {
    return {
      allowed: false,
      reason: `Cartridge '${cartridgeName}' does not have permission to write to tier '${tier}'. ` +
        `Allowed tiers: [${(perms.writeTiers || []).join(", ")}].`,
    };
  }

  // Check stage (wildcard "*" grants access to all stages)
  if (!Array.isArray(perms.allowedStages)) {
    return {
      allowed: false,
      reason: `Cartridge '${cartridgeName}' declares no allowedStages.`,
    };
  }

  const stagesAllowed = perms.allowedStages.includes("*") || perms.allowedStages.includes(stage);
  if (!stagesAllowed) {
    return {
      allowed: false,
      reason: `Cartridge '${cartridgeName}' does not have permission to operate on stage '${stage}'. ` +
        `Allowed stages: [${perms.allowedStages.join(", ")}].`,
    };
  }

  return { allowed: true };
}

module.exports = {
  listAvailable,
  listMounted,
  mount,
  unmount,
  getManifest,
  verifyManifest,
  getCartridgeTools,
  checkPermission,
};
