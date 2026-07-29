/**
 * confidence.js — Confidence label enforcement at the write boundary.
 *
 * Every piece of data written to the MCP Commander system must carry a confidence
 * label. This module validates, assigns, and gates writes based on label
 * tier permissions.
 *
 * Label hierarchy (low → high):
 *   UNKNOWN < LOW < MEDIUM < HIGH
 *
 * Write tier permissions by confidence:
 *   LOW / UNKNOWN → HOT only
 *   MEDIUM         → HOT + WARM
 *   HIGH           → HOT + WARM + COLD
 *
 * RT-19: Confidence labels are enforced at write boundary, not by prompt.
 */

"use strict";

const VALID_LABELS = ["HIGH", "MEDIUM", "LOW", "UNKNOWN"];

// ── Validation ──────────────────────────────────────────────────────

/**
 * Validate that a confidence label is recognized.
 * Case-insensitive. Throws on invalid input.
 *
 * @param {string} label
 * @throws {Error} If label is not a recognized confidence level.
 */
function validateLabel(label) {
  if (!label || typeof label !== "string") {
    throw new Error(
      `Confidence label must be a non-empty string. Got: ${typeof label}`
    );
  }
  const upper = label.toUpperCase();
  if (!VALID_LABELS.includes(upper)) {
    throw new Error(
      `Invalid confidence label: "${label}". Must be one of: ${VALID_LABELS.join(", ")}`
    );
  }
  return upper;
}

/**
 * Normalize a label to uppercase canonical form.
 * Returns "UNKNOWN" for unrecognized labels (non-throwing).
 *
 * @param {string} label
 * @returns {string}
 */
function normalizeLabel(label) {
  if (!label || typeof label !== "string") return "UNKNOWN";
  const upper = label.toUpperCase();
  return VALID_LABELS.includes(upper) ? upper : "UNKNOWN";
}

// ── Auto-assignment ────────────────────────────────────────────────

/**
 * Auto-assign a confidence label based on context clues.
 *
 * Rules:
 *   - source "human" or verified: true → HIGH
 *   - source "llm" without verification → MEDIUM
 *   - source "automated" without verification → LOW
 *   - No context or unrecognized → UNKNOWN
 *
 * @param {object} context
 * @param {string} [context.source] - "human", "llm", "automated", etc.
 * @param {boolean} [context.verified] - Whether a human verified this data.
 * @returns {string} Normalized confidence label.
 */
function labelFromContext(context) {
  if (!context || typeof context !== "object") return "UNKNOWN";

  // Highest priority: explicit human verification
  if (context.verified === true || context.source === "human") {
    return "HIGH";
  }

  // LLM-generated content without verification
  if (context.source === "llm" && !context.verified) {
    return "MEDIUM";
  }

  // Automated tool output without verification
  if (context.source === "automated" && !context.verified) {
    return "LOW";
  }

  // Default: not enough information to assign confidence
  return "UNKNOWN";
}

// ── Write gating ──────────────────────────────────────────────────

/**
 * Tier permission map — which labels can write to which tiers.
 * @type {Object<string, string[]>}
 */
const TIER_PERMISSIONS = {
  LOW: ["hot"],
  UNKNOWN: ["hot"],
  MEDIUM: ["hot", "warm"],
  HIGH: ["hot", "warm", "cold"],
};

/**
 * Check if data with a given confidence label can be written
 * to a specific storage tier.
 *
 * @param {string} label - Confidence label (HIGH, MEDIUM, LOW, UNKNOWN)
 * @param {string} targetTier - Target storage tier (hot, warm, cold)
 * @returns {{ allowed: boolean, reason?: string }}
 */
function canWrite(label, targetTier) {
  const normalized = normalizeLabel(label);
  const allowedTiers = TIER_PERMISSIONS[normalized] || [];

  if (!targetTier || typeof targetTier !== "string") {
    return {
      allowed: false,
      reason: `Invalid target tier: must be "hot", "warm", or "cold".`,
    };
  }

  const tier = targetTier.toLowerCase();
  if (allowedTiers.includes(tier)) {
    return { allowed: true };
  }

  return {
    allowed: false,
    reason: `Confidence "${normalized}" cannot write to "${tier}" tier. ` +
      `Allowed tiers: ${allowedTiers.join(", ")}. ` +
      `Promote confidence label or verify data to unlock higher tiers.`,
  };
}

// ── Label promotion ────────────────────────────────────────────────

/**
 * Promotion map — what a label becomes after verification.
 * @type {Object<string, string>}
 */
const PROMOTION_MAP = {
  LOW: "MEDIUM",
  MEDIUM: "HIGH",
  HIGH: "HIGH",    // Already at top, no change
  UNKNOWN: "MEDIUM", // Verification lifts unknown to at least medium
};

/**
 * Promote a confidence label based on verification status.
 *
 * @param {string} currentLabel - Current confidence label
 * @param {boolean} verification - Whether the data has been verified
 * @returns {string} New confidence label (may be the same)
 */
function promoteLabel(currentLabel, verification) {
  const normalized = normalizeLabel(currentLabel);

  if (verification !== true) {
    return normalized; // No promotion without verification
  }

  return PROMOTION_MAP[normalized] || normalized;
}

module.exports = {
  validateLabel,
  normalizeLabel,
  labelFromContext,
  canWrite,
  promoteLabel,
  VALID_LABELS,
  TIER_PERMISSIONS,
};
