/**
 * vault.js — AES-256-GCM encrypted storage module for MCP Commander Core OS.
 *
 * Provides authenticated encryption for data at rest using AES-256-GCM.
 * Keys are derived from passwords via PBKDF2 with a high iteration count.
 * Vault files are stored as JSON containing algorithm identifier, salt, IV,
 * authentication tag, and ciphertext — no plaintext ever touches the disk.
 *
 * RT-03 : AES-256-GCM encryption for data at rest
 * RT-05 : PBKDF2 key derivation with high iteration count
 * RT-15 : Zero plaintext exposure — only encrypted data written to disk
 */

"use strict";

const crypto = require("crypto");
const fs = require("fs");
const path = require("path");
const paths = require("./paths");

// ── Defaults ──────────────────────────────────────────────────────────

const DEFAULT_ALGORITHM = "aes-256-gcm";
const DEFAULT_KEY_LENGTH = 32; // 256 bits
const DEFAULT_IV_LENGTH = 12;  // 96 bits — standard for GCM
const DEFAULT_SALT_LENGTH = 16;
const DEFAULT_ITERATIONS = 100000;
const DIGEST = "sha512";

// ── Config helpers ────────────────────────────────────────────────────

/**
 * Read the storage/encryption section from the project config file.
 * Returns the merged config with sensible defaults applied.
 */
function _readConfig() {
  try {
    const raw = fs.readFileSync(paths.CONFIG_FILE, "utf8");
    const cfg = JSON.parse(raw);
    const storage = cfg.storage || {};
    return {
      algorithm: storage.encryption_algorithm || DEFAULT_ALGORITHM,
      iterations: storage.iterations || DEFAULT_ITERATIONS,
    };
  } catch (_) {
    // Config file missing or unparseable — use safe defaults
    return {
      algorithm: DEFAULT_ALGORITHM,
      iterations: DEFAULT_ITERATIONS,
    };
  }
}

/**
 * Ensure every directory in `filePath` exists, creating them recursively.
 */
function _ensureDir(filePath) {
  const dir = path.dirname(filePath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

// ── Public API ────────────────────────────────────────────────────────

/**
 * Derive a 256-bit key from a password using PBKDF2.
 *
 * @param {string|Buffer} password - User password or passphrase.
 * @param {Buffer} [salt] - Optional salt. If omitted a random 16-byte salt is generated.
 * @returns {{ key: Buffer, salt: Buffer }} Derived key and the salt used (save the salt!).
 */
function deriveKey(password, salt) {
  const cfg = _readConfig();
  const iterations = cfg.iterations || DEFAULT_ITERATIONS;

  if (!salt) {
    salt = crypto.randomBytes(DEFAULT_SALT_LENGTH);
  }

  const key = crypto.pbkdf2Sync(
    Buffer.isBuffer(password) ? password : Buffer.from(password, "utf8"),
    salt,
    iterations,
    DEFAULT_KEY_LENGTH,
    DIGEST
  );

  return { key, salt };
}

/**
 * Encrypt a string or Buffer and write the vault file to disk.
 *
 * The on-disk format is JSON:
 * ```json
 * { "alg": "aes-256-gcm", "salt": "<hex>", "iv": "<hex>", "tag": "<hex>", "data": "<hex>" }
 * ```
 *
 * @param {string|Buffer} plaintext - Data to encrypt.
 * @param {string|Buffer} password - Encryption password.
 * @param {string} filePath - Absolute path for the output vault file.
 * @returns {{ filePath: string, iv: string, salt: string }} Metadata about the written vault.
 */
function encrypt(plaintext, password, filePath) {
  const input = Buffer.isBuffer(plaintext)
    ? plaintext
    : Buffer.from(plaintext, "utf8");

  const { key, salt } = deriveKey(password);
  const iv = crypto.randomBytes(DEFAULT_IV_LENGTH);

  const cipher = crypto.createCipheriv(DEFAULT_ALGORITHM, key, iv);
  const encrypted = Buffer.concat([cipher.update(input), cipher.final()]);
  const tag = cipher.getAuthTag();

  const vault = {
    alg: DEFAULT_ALGORITHM,
    salt: salt.toString("hex"),
    iv: iv.toString("hex"),
    tag: tag.toString("hex"),
    data: encrypted.toString("hex"),
  };

  _ensureDir(filePath);
  fs.writeFileSync(filePath, JSON.stringify(vault, null, 2), "utf8");

  return {
    filePath,
    iv: iv.toString("hex"),
    salt: salt.toString("hex"),
  };
}

/**
 * Decrypt a vault file and return the plaintext string.
 *
 * @param {string} filePath - Absolute path to the vault file.
 * @param {string|Buffer} password - Decryption password.
 * @returns {string} Decrypted plaintext as a UTF-8 string.
 * @throws {Error} If the file is missing, corrupted, uses an unsupported algorithm,
 *   or the password is wrong (authentication tag mismatch).
 */
function decrypt(filePath, password) {
  if (!fs.existsSync(filePath)) {
    throw new Error(`Vault file not found: ${filePath}`);
  }

  let vault;
  try {
    const raw = fs.readFileSync(filePath, "utf8");
    vault = JSON.parse(raw);
  } catch (_) {
    throw new Error(`Corrupted vault file: ${filePath}`);
  }

  if (vault.alg !== DEFAULT_ALGORITHM) {
    throw new Error(
      `Unsupported algorithm "${vault.alg}". Expected "${DEFAULT_ALGORITHM}".`
    );
  }

  const salt = Buffer.from(vault.salt, "hex");
  const iv = Buffer.from(vault.iv, "hex");
  const tag = Buffer.from(vault.tag, "hex");
  const data = Buffer.from(vault.data, "hex");

  const { key } = deriveKey(password, salt);

  const decipher = crypto.createDecipheriv(DEFAULT_ALGORITHM, key, iv);
  decipher.setAuthTag(tag);

  let decrypted;
  try {
    decrypted = Buffer.concat([decipher.update(data), decipher.final()]);
  } catch (_) {
    throw new Error("Decryption failed — wrong password or corrupted data.");
  }

  return decrypted.toString("utf8");
}

/**
 * Encrypt a Buffer and write the vault file to disk.
 * Identical to `encrypt` but guarantees the input is treated as raw bytes.
 *
 * @param {Buffer} buffer - Raw bytes to encrypt.
 * @param {string|Buffer} password - Encryption password.
 * @param {string} filePath - Absolute path for the output vault file.
 * @returns {{ filePath: string, iv: string, salt: string }} Metadata about the written vault.
 */
function encryptBuffer(buffer, password, filePath) {
  if (!Buffer.isBuffer(buffer)) {
    throw new TypeError("encryptBuffer requires a Buffer as the first argument.");
  }
  return encrypt(buffer, password, filePath);
}

/**
 * Create an empty vault file (containing a zero-length ciphertext) at the
 * given path. Useful for reserving a vault location before data is available.
 *
 * @param {string} vaultPath - Absolute path where the vault file should be created.
 * @param {string|Buffer} password - Encryption password.
 * @returns {{ filePath: string, iv: string, salt: string }} Metadata about the created vault.
 */
function createVault(vaultPath, password) {
  return encrypt("", password, vaultPath);
}

/**
 * Check whether a file is a valid MCP Commander vault.
 *
 * A valid vault must be a JSON object containing all of the required
 * fields: `alg`, `salt`, `iv`, `tag`, and `data`.
 *
 * @param {string} filePath - Absolute path to the file to check.
 * @returns {boolean} `true` if the file is a valid MCP Commander vault, `false` otherwise.
 */
function isVaultFile(filePath) {
  if (!fs.existsSync(filePath)) {
    return false;
  }

  try {
    const raw = fs.readFileSync(filePath, "utf8");
    const obj = JSON.parse(raw);

    return (
      obj !== null &&
      typeof obj === "object" &&
      typeof obj.alg === "string" &&
      typeof obj.salt === "string" &&
      typeof obj.iv === "string" &&
      typeof obj.tag === "string" &&
      typeof obj.data === "string"
    );
  } catch (_) {
    return false;
  }
}

// ── Exports ───────────────────────────────────────────────────────────

module.exports = {
  deriveKey,
  encrypt,
  decrypt,
  encryptBuffer,
  createVault,
  isVaultFile,
};
