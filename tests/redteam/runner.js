#!/usr/bin/env node
/**
 * runner.js — Red-team test harness for MCP Commander Core OS.
 *
 * Scans the tests/redteam/ directory for rt-*.js files, runs each exported
 * test suite, captures pass/fail/pending results with per-test timing,
 * and outputs a formatted summary table.
 *
 * Usage:
 *   node tests/redteam/runner.js
 *   node tests/redteam/runner.js          # run all rt-*.js files
 *   node tests/redteam/runner.js --only RT-01  # (future: filter)
 *
 * Exit codes:
 *   0  — all tests passed
 *   1  — one or more tests failed
 *   2  — runner error (no test files found, etc.)
 */

"use strict";

const fs = require("fs");
const path = require("path");

// ── ANSI helpers ─────────────────────────────────────────────────────────

const CLR = {
  reset: "\x1b[0m",
  bold: "\x1b[1m",
  dim: "\x1b[2m",
  red: "\x1b[31m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  cyan: "\x1b[36m",
  gray: "\x1b[90m",
  white: "\x1b[37m",
};

function passBadge() { return `${CLR.green}${CLR.bold}  PASS${CLR.reset}`; }
function failBadge() { return `${CLR.red}${CLR.bold}  FAIL${CLR.reset}`; }
function pendBadge() { return `${CLR.yellow}${CLR.bold}  SKIP${CLR.reset}`; }

// ── Banner ──────────────────────────────────────────────────────────────

function printBanner() {
  console.log("");
  console.log(`${CLR.cyan}${CLR.bold}  ╔══════════════════════════════════════════════════════════════╗${CLR.reset}`);
  console.log(`${CLR.cyan}${CLR.bold}  ║     MCP Commander Core OS — Red-Team Security Harness     ║${CLR.reset}`);
  console.log(`${CLR.cyan}${CLR.bold}  ╚══════════════════════════════════════════════════════════════╝${CLR.reset}`);
  console.log("");
}

// ── Summary table ───────────────────────────────────────────────────────

function printSummary(results) {
  const total = results.length;
  const passed = results.filter((r) => r.status === "passed").length;
  const failed = results.filter((r) => r.status === "failed").length;
  const skipped = results.filter((r) => r.status === "skipped").length;
  const totalMs = results.reduce((sum, r) => sum + r.elapsed, 0);

  console.log("");
  console.log(`${CLR.bold}  ┌─────────────────────────────────────────────────────────────┐${CLR.reset}`);
  console.log(`${CLR.bold}  │  RED-TEAM SUMMARY                                          │${CLR.reset}`);
  console.log(`${CLR.bold}  ├─────────────────────────────────────────────────────────────┤${CLR.reset}`);
  console.log(`${CLR.bold}  │${CLR.reset}  ${CLR.cyan}Total:   ${CLR.reset}${String(total).padEnd(46)}${CLR.bold}│${CLR.reset}`);
  console.log(`${CLR.bold}  │${CLR.reset}  ${CLR.green}Passed:  ${CLR.reset}${String(passed).padEnd(46)}${CLR.bold}│${CLR.reset}`);
  console.log(`${CLR.bold}  │${CLR.reset}  ${CLR.red}Failed:  ${CLR.reset}${String(failed).padEnd(46)}${CLR.bold}│${CLR.reset}`);
  console.log(`${CLR.bold}  │${CLR.reset}  ${CLR.yellow}Skipped: ${CLR.reset}${String(skipped).padEnd(46)}${CLR.bold}│${CLR.reset}`);
  console.log(`${CLR.bold}  │${CLR.reset}  ${CLR.dim}Time:    ${totalMs}ms${" ".repeat(Math.max(0, 39 - String(totalMs).length))}${CLR.bold}│${CLR.reset}`);
  console.log(`${CLR.bold}  └─────────────────────────────────────────────────────────────┘${CLR.reset}`);
  console.log("");

  // Individual results table
  console.log(`${CLR.bold}  ┌──────────┬──────────────────────────────────────────┬─────────┬──────────┐${CLR.reset}`);
  console.log(`${CLR.bold}  │ ID       │ Title                                     │ Status  │ Time(ms) │${CLR.reset}`);
  console.log(`${CLR.bold}  ├──────────┼──────────────────────────────────────────┼─────────┼──────────┤${CLR.reset}`);

  for (const r of results) {
    const id = r.id.padEnd(8);
    const title = r.title.length > 40 ? r.title.substring(0, 37) + "..." : r.title.padEnd(40);
    let status;
    if (r.status === "passed") status = `${CLR.green}PASS${CLR.reset}    `;
    else if (r.status === "failed") status = `${CLR.red}FAIL${CLR.reset}    `;
    else status = `${CLR.yellow}SKIP${CLR.reset}    `;
    const time = String(r.elapsed).padEnd(8);

    console.log(`  │ ${id} │ ${title} │ ${status} │ ${time} │`);
  }

  console.log(`${CLR.bold}  └──────────┴──────────────────────────────────────────┴─────────┴──────────┘${CLR.reset}`);
  console.log("");

  // Failed test details
  const failures = results.filter((r) => r.status === "failed");
  if (failures.length > 0) {
    console.log(`${CLR.red}${CLR.bold}  ── FAILURES ──────────────────────────────────────────────────${CLR.reset}`);
    for (const f of failures) {
      console.log(`${CLR.red}  ✗ ${f.id}: ${f.title}${CLR.reset}`);
      console.log(`${CLR.gray}    ${f.detail}${CLR.reset}`);
    }
    console.log("");
  }
}

// ── Test discovery ───────────────────────────────────────────────────────

function discoverTestFiles(suiteDir) {
  if (!fs.existsSync(suiteDir)) {
    return [];
  }
  const files = fs.readdirSync(suiteDir).filter((f) => /^rt-.*\.js$/.test(f));
  // Sort naturally: rt-01, rt-02, ...
  files.sort((a, b) => {
    const numA = parseInt(a.replace(/^rt-/, ""), 10);
    const numB = parseInt(b.replace(/^rt-/, ""), 10);
    return numA - numB;
  });
  return files.map((f) => path.join(suiteDir, f));
}

// ── Single test runner ─────────────────────────────────────────────────

async function runTest(testObj) {
  if (testObj.skip) {
    return {
      id: testObj.id,
      title: testObj.title,
      status: "skipped",
      elapsed: 0,
      detail: "Skipped",
    };
  }

  if (typeof testObj.run !== "function") {
    return {
      id: testObj.id,
      title: testObj.title,
      status: "failed",
      elapsed: 0,
      detail: "Test has no run() function",
    };
  }

  const start = process.hrtime.bigint();

  try {
    const result = await testObj.run();
    const elapsed = Number(process.hrtime.bigint() - start) / 1e6; // ms

    if (result && result.passed === true) {
      return {
        id: testObj.id,
        title: testObj.title,
        status: "passed",
        elapsed: Math.round(elapsed),
        detail: result.detail || "",
      };
    } else {
      return {
        id: testObj.id,
        title: testObj.title,
        status: "failed",
        elapsed: Math.round(elapsed),
        detail: result ? result.detail || "Assertion failed" : "No result returned",
      };
    }
  } catch (err) {
    const elapsed = Number(process.hrtime.bigint() - start) / 1e6;
    return {
      id: testObj.id,
      title: testObj.title,
      status: "failed",
      elapsed: Math.round(elapsed),
      detail: `Exception: ${err.message}`,
    };
  }
}

// ── Main ────────────────────────────────────────────────────────────────

async function main() {
  printBanner();

  const suiteDir = path.resolve(__dirname);
  const testFiles = discoverTestFiles(suiteDir);

  if (testFiles.length === 0) {
    console.log(`${CLR.yellow}  No rt-*.js test files found in ${suiteDir}${CLR.reset}`);
    console.log("");
    process.exit(2);
  }

  console.log(`${CLR.dim}  Discovered ${testFiles.length} test file(s) in ${suiteDir}${CLR.reset}`);
  console.log("");

  const allResults = [];

  for (const filePath of testFiles) {
    const fileName = path.basename(filePath);

    // Clear require cache so each file loads fresh
    delete require.cache[require.resolve(filePath)];

    console.log(`${CLR.cyan}${CLR.bold}  ── ${fileName} ──────────────────────────────────────────${CLR.reset}`);

    let testSuite;
    try {
      testSuite = require(filePath);
    } catch (err) {
      console.log(`${CLR.red}  ✗ Failed to load ${fileName}: ${err.message}${CLR.reset}`);
      console.log("");
      allResults.push({
        id: fileName,
        title: `Load error: ${fileName}`,
        status: "failed",
        elapsed: 0,
        detail: err.message,
      });
      continue;
    }

    // Normalize: testSuite can be an array or an object with .tests array
    const tests = Array.isArray(testSuite)
      ? testSuite
      : Array.isArray(testSuite.tests)
        ? testSuite.tests
        : [];

    if (tests.length === 0) {
      console.log(`${CLR.yellow}  (no tests exported)${CLR.reset}`);
      console.log("");
      continue;
    }

    for (const testObj of tests) {
      const result = await runTest(testObj);
      allResults.push(result);

      if (result.status === "passed") {
        console.log(`  ${passBadge()}  ${CLR.dim}${result.id}${CLR.reset}  ${result.title}${CLR.gray} (${result.elapsed}ms)${CLR.reset}`);
      } else if (result.status === "skipped") {
        console.log(`  ${pendBadge()}  ${CLR.dim}${result.id}${CLR.reset}  ${result.title}`);
      } else {
        console.log(`  ${failBadge()}  ${CLR.dim}${result.id}${CLR.reset}  ${result.title}${CLR.gray} (${result.elapsed}ms)${CLR.reset}`);
        console.log(`${CLR.gray}           ${result.detail}${CLR.reset}`);
      }
    }

    console.log("");
  }

  // ── Summary ──────────────────────────────────────────────────────────
  printSummary(allResults);

  const hasFailures = allResults.some((r) => r.status === "failed");
  if (hasFailures) {
    process.exit(1);
  } else {
    process.exit(0);
  }
}

main().catch((err) => {
  console.error(`${CLR.red}  Runner fatal error: ${err.message}${CLR.reset}`);
  process.exit(2);
});
