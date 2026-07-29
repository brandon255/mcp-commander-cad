# MCP Commander — Red-Team Security Tests

Automated red-team findings for the MCP Commander Core OS. Each test exercises
a specific security boundary and reports **PASS** or **FAIL** with a detail
string explaining the outcome.

## How to run

```bash
cd /path/to/mcp-commander-cad
MCP_COMMANDER_ROOT=/tmp/mcp-test-root node tests/redteam/runner.js
```

> `runner.js` loads `rt-01-to-10.js` and `rt-11-to-21.js`, runs every test,
> and prints results to stdout.

## Test output format

```
[RT-11] PASS  Signed cartridge manifests (Ed25519)
         Manifest validation correctly enforces structure; signature optional
[RT-12] FAIL  Cartridge isolation — write tier enforcement
         warm tier should be blocked (not in writeTiers)
...
21 tests, 19 passed, 2 failed
```

Each test returns `{ passed: boolean, detail: string }`.

## What the 21 RT-findings test

| ID    | Title | Module |
|-------|-------|--------|
| RT-01 | No magic override word | gates.js |
| RT-02 | Immutable audit trail | integrity.js |
| RT-03 | AES-256-GCM at rest | vault.js |
| RT-04 | SHA-256 hash chain | integrity.js |
| RT-05 | PBKDF2 key derivation | vault.js |
| RT-06 | Config only in project root | paths.js |
| RT-07 | LLM localhost-only | llm.js |
| RT-08 | No cross-cartridge data access | cartridges.js |
| RT-09 | Redaction of secrets | redact.js |
| RT-10 | Telemetry no secrets | telemetry.js |
| **RT-11** | **Signed cartridge manifests (Ed25519 optional)** | cartridges.js |
| **RT-12** | **Write-tier enforcement** | cartridges.js |
| **RT-13** | **Stage-ownership enforcement** | cartridges.js |
| **RT-14** | **LLM DNS rebinding & private-IP blocking** | llm.js |
| **RT-15** | **Zero plaintext on disk** | vault.js |
| **RT-16** | **HOT storage cleanup design** | memory.js |
| **RT-17** | **COLD archive uses vault encryption** | memory.js + vault.js |
| **RT-18** | **WORM append-only ledger** | integrity.js |
| **RT-19** | **Gate race-condition prevention** | gates.js |
| **RT-20** | **Minimum explanation length** | gates.js |
| **RT-21** | **DoS prevention — bounded ops & cleanup** | gates.js + cartridges.js |

## Self-contained with temp directories

Every test run creates a fresh temp directory via `fs.mkdtempSync`. Cartridge
tests use unique timestamp-prefixed names under the real `cartridges/` tree and
are cleaned up on process exit. Vault tests write to temp paths only. The
integrity ledger is append-only so test entries are harmless.

## Adding a new test

1. Add an entry to the exported array in `rt-11-to-21.js` (or create a new
   `rt-22-to-XX.js` file).
2. Follow the format: `{ id, title, run: async () => ({ passed, detail }) }`.
3. Import any needed Core OS module via `require("../../core/src/<module>")`.
4. Create temp resources with `fs.mkdtempSync` and clean up in a `process.on("exit")` handler.
