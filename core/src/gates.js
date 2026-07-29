/**
 * gates.js — Deterministic gate enforcement.
 *
 * Every write, cartridge mount, and operation transition passes through
 * this module. Safety is enforced by code, not by prompt instructions.
 *
 * Gate flow:
 *   1. explainWhy — the actor must explain WHY they want to proceed.
 *   2. validate — the explanation is checked for minimum length and structure.
 *   3. approve — the actor must produce the exact APPROVE token to pass.
 *
 * RT-01: No "override" magic word. Advancement only via explicit confirmation.
 * RT-20: Minimum explanation length is enforced (MIN_WHY_LENGTH).
 *
 * There is no way to bypass a gate from within the system.
 */

"use strict";

const path = require("path");
const paths = require("./paths");
const fs = require("fs");

// ── Config loader ─────────────────────────────────────────────────────

function loadGateConfig() {
  const configPath = paths.CONFIG_FILE;
  if (fs.existsSync(configPath)) {
    const config = JSON.parse(fs.readFileSync(configPath, "utf-8"));
    return config.gates || { min_why_length: 20, approve_token: "APPROVE" };
  }
  return { min_why_length: 20, approve_token: "APPROVE" };
}

// ── Gate states ───────────────────────────────────────────────────────

/**
 * Gate represents a single transition checkpoint.
 * A gate is in one of three states:
 *   - PENDING: waiting for explanation
 *   - EXPLAINED: explanation received, waiting for approval
 *   - PASSED: gate has been passed
 *   - DENIED: gate was denied or expired
 */
class Gate {
  constructor(id, description, options = {}) {
    this.id = id;
    this.description = description;
    this.state = "PENDING";
    this.explanation = null;
    this.approvedAt = null;
    this.deniedAt = null;
    this.createdAt = Date.now();
    this.ttl = options.ttl || 300000; // 5 minutes default
    this.metadata = options.metadata || {};
  }

  /**
   * Submit a WHY explanation for this gate.
   * Validates length and structure before accepting.
   * @param {string} explanation
   * @returns {{ accepted: boolean, reason?: string }}
   */
  explain(explanation) {
    if (this.state !== "PENDING") {
      return { accepted: false, reason: `Gate is not PENDING (current: ${this.state})` };
    }

    if (!explanation || typeof explanation !== "string") {
      return { accepted: false, reason: "Explanation must be a non-empty string" };
    }

    const config = loadGateConfig();
    if (explanation.trim().length < config.min_why_length) {
      return {
        accepted: false,
        reason: `Explanation too short. Minimum ${config.min_why_length} characters required (got ${explanation.trim().length}). Explain WHY you want to proceed.`,
      };
    }

    // Check for expiration
    if (Date.now() - this.createdAt > this.ttl) {
      this.state = "DENIED";
      this.deniedAt = Date.now();
      return { accepted: false, reason: "Gate expired. Create a new gate." };
    }

    this.explanation = explanation;
    this.state = "EXPLAINED";
    return { accepted: true };
  }

  /**
   * Attempt to approve this gate with a token.
   * Must match the exact configured approve token.
   * @param {string} token
   * @returns {{ passed: boolean, reason?: string }}
   */
  approve(token) {
    if (this.state !== "EXPLAINED") {
      return { passed: false, reason: `Gate must be EXPLAINED before approval (current: ${this.state})` };
    }

    // Check for expiration
    if (Date.now() - this.createdAt > this.ttl) {
      this.state = "DENIED";
      this.deniedAt = Date.now();
      return { passed: false, reason: "Gate expired. Create a new gate." };
    }

    const config = loadGateConfig();
    if (token !== config.approve_token) {
      return { passed: false, reason: "Incorrect approval token." };
    }

    this.state = "PASSED";
    this.approvedAt = Date.now();
    return { passed: true };
  }

  /**
   * Explicitly deny this gate.
   */
  deny() {
    this.state = "DENIED";
    this.deniedAt = Date.now();
  }

  /**
   * Check if this gate is expired.
   */
  isExpired() {
    return Date.now() - this.createdAt > this.ttl;
  }

  /**
   * Serialize gate state for persistence.
   */
  toJSON() {
    return {
      id: this.id,
      description: this.description,
      state: this.state,
      explanation: this.explanation,
      approvedAt: this.approvedAt,
      deniedAt: this.deniedAt,
      createdAt: this.createdAt,
      ttl: this.ttl,
      metadata: this.metadata,
    };
  }
}

// ── Gate registry ────────────────────────────────────────────────────

const activeGates = new Map();

/**
 * Create a new gate and register it.
 * @param {string} id - Unique gate identifier
 * @param {string} description - What this gate protects
 * @param {object} options
 * @returns {Gate}
 */
function createGate(id, description, options = {}) {
  if (activeGates.has(id)) {
    throw new Error(`Gate '${id}' already exists. Complete or deny it first.`);
  }
  const gate = new Gate(id, description, options);
  activeGates.set(id, gate);
  return gate;
}

/**
 * Get an existing gate by ID.
 * @param {string} id
 * @returns {Gate|null}
 */
function getGate(id) {
  return activeGates.get(id) || null;
}

/**
 * Remove a completed/denied gate.
 * @param {string} id
 */
function removeGate(id) {
  activeGates.delete(id);
}

/**
 * Check if a gate has been passed.
 * @param {string} id
 * @returns {boolean}
 */
function isPassed(id) {
  const gate = activeGates.get(id);
  return gate && gate.state === "PASSED";
}

/**
 * Execute a gated operation.
 * Creates a gate, collects explanation and approval, then runs the action.
 *
 * @param {string} id - Gate ID
 * @param {string} description - What this gate protects
 * @param {string} explanation - WHY the actor wants to proceed
 * @param {string} approvalToken - The exact approval token
 * @param {function} action - Function to execute if gate passes. Receives no args.
 * @returns {{ passed: boolean, result?: any, reason?: string }}
 */
function executeGated(id, description, explanation, approvalToken, action) {
  const gate = createGate(id, description);

  // Step 1: Explain
  const explainResult = gate.explain(explanation);
  if (!explainResult.accepted) {
    removeGate(id);
    return { passed: false, reason: explainResult.reason };
  }

  // Step 2: Approve
  const approveResult = gate.approve(approvalToken);
  if (!approveResult.passed) {
    return { passed: false, reason: approveResult.reason };
  }

  // Step 3: Execute
  try {
    const result = action();
    removeGate(id);
    return { passed: true, result };
  } catch (err) {
    return { passed: false, reason: `Action failed: ${err.message}` };
  }
}

/**
 * Clean up expired gates.
 * @returns {number} Number of gates cleaned up
 */
function cleanupExpired() {
  let cleaned = 0;
  for (const [id, gate] of activeGates) {
    if (gate.isExpired()) {
      gate.deny();
      activeGates.delete(id);
      cleaned++;
    }
  }
  return cleaned;
}

module.exports = {
  Gate,
  createGate,
  getGate,
  removeGate,
  isPassed,
  executeGated,
  cleanupExpired,
  loadGateConfig,
};
