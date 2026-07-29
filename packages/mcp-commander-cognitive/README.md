# MCP Commander Cognitive Cartridge

**Cognitive architecture cartridge implementing 9 background operations for engineering design intelligence.**

## Overview

This cartridge provides an MCP (Model Context Protocol) server with 9 cognitive tools designed to augment mechanical and product engineering workflows. Each operation embeds real engineering knowledge bases covering materials, processes, fastening, tolerancing, structural design, and manufacturing methods.

## Architecture

```
mcp-commander-cognitive/
├── cartridge.json          # Cartridge manifest with permissions and tool definitions
├── pyproject.toml          # Python package configuration with MCP CLI entry point
├── README.md
└── src/
    └── mcp_commander_cognitive/
        ├── __init__.py
        ├── server.py       # FastMCP server — registers all 9 tools
        └── operations/
            ├── __init__.py
            ├── divergent.py     # Divergent thinking
            ├── convergent.py    # Convergent thinking
            ├── cross_domain.py  # Cross-domain transfer
            ├── uncommon.py      # Uncommon manufacturing methods
            ├── pattern.py       # Pattern recognition
            ├── compression.py   # Compression thinking
            ├── spatial.py       # Spatial reasoning
            ├── diagnostics.py   # Context diagnostics
            └── rationale.py     # Design rationale
```

## The 9 Cognitive Operations

### 1. Divergent Thinking (`divergent_thinking`)
Generates alternative design approaches for a given design intent. Draws from embedded knowledge bases spanning **fastening** (thread-forming screws, snap-fits, ultrasonic welds, PEM fasteners), **sealing** (O-ring glands, FIPG, PTFE lip seals, foam gaskets), **mounting** (kinematic mounts, wire rope isolators, magnetic pads), **structural** approaches, **material** strategies, and **heat management** techniques.

### 2. Convergent Thinking (`convergent_thinking`)
Evaluates and ranks design alternatives against weighted engineering criteria using a Pugh-like scoring matrix. Criteria include **cost**, **weight**, **manufacturability**, **strength**, and **lead time**. Accepts explicit scores or generates heuristic estimates from alternative descriptions.

### 3. Cross-Domain Transfer (`cross_domain_transfer`)
Transfers proven design solutions between industry domains. Knowledge base covers mappings from aerospace, automotive, medical, marine, consumer electronics, semiconductor, and construction fields. Each entry includes source solution, target application, and detailed adaptation notes.

### 4. Uncommon Methods (`uncommon_methods`)
Suggests non-traditional manufacturing methods including 3D printed jigs/fixtures, foam pattern casting, investment casting, waterjet cutting, wire EDM, RTV silicone tooling, electron beam welding, additive casting, and laser powder bed fusion (DMLS/SLM). Each method includes pros, cons, material options, cost ranges, and lead times.

### 5. Pattern Recognition (`pattern_recognition`)
Identifies recurring design inefficiencies and anti-patterns. Detects over-tolerancing, redundant fasteners, unnecessary stock sizes, over-constrained mounting, sheet metal feature creep, standard parts avoidance, excessive surface finish specs, inadequate draft angles, tolerance stack gaps, and over-engineered wall thickness.

### 6. Compression Thinking (`compression_thinking`)
Simplifies over-engineered assemblies through 8 consolidation rules: fastener consolidation, feature merging, material unification, tolerance stack reduction, multi-function part integration, redundant stiffening removal, process step elimination, and sub-assembly elimination. Estimates part count and weight reduction potential.

### 7. Spatial Reasoning (`spatial_reasoning`)
Parses natural-language geometry descriptions to infer 3D spatial relationships. Recognizes 11 relationship types: concentric, perpendicular, coplanar, parallel, offset, tangent, symmetric, intersecting, angled, clearance fit, and interference fit. Extracts dimensions, feature types, and generates implied engineering constraint checklists.

### 8. Context Diagnostics (`context_diagnostics`)
Identifies missing constraints and specification gaps in design descriptions. Checks 10 categories: material, tolerance, loading, environment, surface finish, quantity, regulatory, assembly, inspection, and interface. Reports completeness score with prioritized action checklist.

### 9. Design Rationale (`design_rationale`)
Captures and retrieves design rationale linking decisions to engineering requirements. Supports capture, search, and suggest actions across 8 categories: material selection, manufacturing process, geometric design, tolerance allocation, fastening strategy, surface treatment, safety compliance, and cost optimization.

## Quick Start

```bash
# Install dependencies
pip install -e .

# Run the MCP server
mcp-commander-cognitive
```

The server runs on **stdio transport** and is designed to operate as a background cognitive cartridge within the MCP Commander ecosystem.

## Configuration

**Permissions:** Write access to `hot` and `warm` tiers. Operations target `analysis`, `knowledge`, and `validation` stages.

**Dependencies:** `mcp[cli]` (FastMCP server framework).

## License

Proprietary — MCP Commander Ecosystem.
