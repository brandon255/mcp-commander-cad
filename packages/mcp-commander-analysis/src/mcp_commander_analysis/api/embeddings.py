"""RAG Embeddings & Search for CAD engineering knowledge.

Provides a ``KnowledgeBase`` class backed by sentence-transformers embeddings
and a FAISS index for fast similarity search.  On first use the base is
seeded with ~20 entries covering common engineering drawing standards,
GD&T, sheet metal rules, machining tolerances, weld symbols, and more.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default CAD knowledge entries (seeded on first use)
# ---------------------------------------------------------------------------

_DEFAULT_KNOWLEDGE: list[dict[str, str]] = [
    # 1. Sketching basics
    {
        "id": "sketch_basics_01",
        "title": "Sketching Fundamentals for Parametric CAD",
        "category": "sketching",
        "content": (
            "Parametric sketching is the foundation of 3D CAD modeling. A fully-defined sketch "
            "uses geometric constraints (coincident, tangent, parallel, perpendicular, symmetric, "
            "equal, fixed, midpoint, pierce, horizontal, vertical) and dimensional constraints to "
            "lock all degrees of freedom. Under-constrained sketches can move freely and may cause "
            "unexpected model changes downstream. Over-constrained sketches (with redundant dimensions) "
            "will be flagged in blue in SolidWorks and Fusion 360. Best practice: start with the origin, "
            "apply symmetry about centerlines, dimension the overall envelope first, then add detail "
            "dimensions. Avoid auto-constraints that you did not intend by hovering over reference geometry."
        ),
        "source": "mcp-commander-analysis:builtin",
    },
    # 2. Dimensioning standards
    {
        "id": "dim_standards_01",
        "title": "ASME Y14.5 Dimensioning and Tolerancing Fundamentals",
        "category": "dimensioning",
        "content": (
            "ASME Y14.5-2018 is the primary standard for dimensioning and tolerancing in the United States. "
            "It defines how to specify and interpret geometric dimensions and tolerances (GD&T) on engineering "
            "drawings. Key principles: (1) Every feature must be fully defined — no ambiguity. (2) Dimensions "
            "should not be redundant; each dimension should appear only once. (3) The drawing must define the "
            "part completely — no verbal instructions needed for manufacturing. (4) Dimensions are in millimeters "
            "unless explicitly noted otherwise (for metric drawings). The standard covers linear dimensions, angular "
            "dimensions, diametric dimensions, radial dimensions, coordinate dimensions, and geometric tolerances. "
            "Default tolerances are typically noted in the title block (e.g., ±0.5 for 1-decimal, ±0.25 for 2-decimal)."
        ),
        "source": "mcp-commander-analysis:builtin",
    },
    # 3. GD&T overview
    {
        "id": "gdnt_overview_01",
        "title": "Geometric Dimensioning and Tolerancing (GD&T) Overview",
        "category": "gdnt",
        "content": (
            "GD&T is a symbolic language used on engineering drawings to specify the allowable variation in "
            "a part's geometry. It uses 14 standard symbols organized into five categories: (1) Form — "
            "straightness, flatness, circularity, cylindricity. (2) Orientation — perpendicularity, parallelism, "
            "angularity. (3) Location — position, concentricity, symmetry. (4) Runout — circular runout, "
            "total runout. (5) Profile — profile of a line, profile of a surface. A feature control frame (FCF) "
            "contains: the geometric characteristic symbol, the tolerance zone (with modifiers like MMC ⊕ or LMC ⊖), "
            "and datum references (A, B, C). GD&T provides more precise communication than ± tolerancing alone, "
            "ensuring parts assemble correctly regardless of individual feature size."
        ),
        "source": "mcp-commander-analysis:builtin",
    },
    # 4. GD&T - flatness and straightness
    {
        "id": "gdnt_form_01",
        "title": "Form Tolerances: Flatness and Straightness",
        "category": "gdnt",
        "content": (
            "Flatness controls how flat a surface must be. It is a form tolerance applied to a single surface "
            "without requiring any datum reference. The tolerance zone is the space between two parallel planes "
            "separated by the specified tolerance (e.g., flatness within 0.05 mm). Flatness is critical for "
            "sealing surfaces, mounting surfaces, and bearing seats. Straightness controls how straight a line "
            "element must be. It can apply to a surface line (no datum) or a derived median line (requires datum). "
            "For a shaft in a bearing, straightness of the axis ensures smooth rotation. Typical values: precision "
            "ground surfaces — 0.001-0.005 mm, milled surfaces — 0.01-0.05 mm, rough machined — 0.1-0.5 mm."
        ),
        "source": "mcp-commander-analysis:builtin",
    },
    # 5. GD&T - position tolerance
    {
        "id": "gdnt_position_01",
        "title": "Position Tolerance and True Position",
        "category": "gdnt",
        "content": (
            "Position tolerance (⌖) controls the location of a feature (usually a hole) relative to datums. "
            "It defines a cylindrical tolerance zone centered at the true position (theoretically exact location). "
            "Position at MMC (Maximum Material Condition) allows bonus tolerance: as the hole gets larger, the "
            "position tolerance increases. For example, a 10mm ±0.1 hole at position 0.2M means at MMC (9.9mm), "
            "the position tolerance zone is a cylinder of ⌀0.2mm. At 10.1mm (LMC), bonus tolerance adds 0.2mm "
            "for a total ⌀0.4mm zone. Position is the most widely used GD&T tolerance for hole patterns. "
            "It replaces traditional ± location dimensions and provides clearer functional intent. Composite "
            "position (PLTZF and FRTZF) controls hole pattern location and hole-to-hole spacing separately."
        ),
        "source": "mcp-commander-analysis:builtin",
    },
    # 6. Sheet metal design rules
    {
        "id": "sheet_metal_01",
        "title": "Sheet Metal Design Rules and Best Practices",
        "category": "sheet_metal",
        "content": (
            "Sheet metal design follows specific rules to ensure manufacturability. Key rules: "
            "(1) Minimum bend radius: typically equal to the material thickness for mild steel, 1.5× for aluminum, "
            "to avoid cracking. (2) K-factor: the ratio of the neutral axis position to material thickness; "
            "typically 0.3-0.5 depending on material and bend method. (3) Bend relief: small cuts or notches "
            "at bend intersections to prevent tearing; minimum relief width = thickness, depth = thickness + bend radius. "
            "(4) Hole-to-edge distance: minimum 1.5× material thickness from hole center to edge. "
            "(5) Flange height: minimum 2× material thickness + bend radius to allow tooling clearance. "
            "(6) Wall thickness uniformity: avoid sudden thickness changes. "
            "(7) Tab/slot connections: minimum 2× thickness for tab width. "
            "These rules apply to both press brake bending and laser/waterjet cutting operations."
        ),
        "source": "mcp-commander-analysis:builtin",
    },
    # 7. Machining tolerances
    {
        "id": "machining_tol_01",
        "title": "Common Machining Tolerances by Process",
        "category": "manufacturing",
        "content": (
            "Different manufacturing processes achieve different tolerance ranges. Understanding these helps "
            "select the right process and avoid over-specifying tolerances (which increases cost dramatically). "
            "Rough machining (turning, milling): ±0.1-0.5 mm. Standard machining: ±0.025-0.1 mm. "
            "Precision machining (grinding, honing): ±0.005-0.025 mm. Ultra-precision (lapping, polishing): "
            "±0.001-0.005 mm. Boring (precision holes): ±0.013-0.05 mm. Reaming: ±0.01-0.025 mm. "
            "Wire EDM: ±0.005-0.015 mm. Sinker EDM: ±0.01-0.03 mm. Investment casting: ±0.1-0.25 mm. "
            "Die casting: ±0.05-0.1 mm. 3D printing (FDM): ±0.2-0.5 mm. 3D printing (SLA): ±0.05-0.1 mm. "
            "Rule of thumb: every halving of tolerance roughly doubles manufacturing cost. Always specify the "
            "loosest tolerance that meets the functional requirement."
        ),
        "source": "mcp-commander-analysis:builtin",
    },
    # 8. Weld symbols
    {
        "id": "weld_symbols_01",
        "title": "AWS Welding Symbol Interpretation",
        "category": "standards",
        "content": (
            "Welding symbols per AWS A2.4 communicate joint design, weld type, size, length, pitch, and "
            "other requirements. The symbol has a reference line (horizontal arrow), with the arrow pointing "
            "to the joint. Information above the line applies to the other side; below applies to the arrow "
            "side. Common weld types: fillet (triangle), groove (V, U, J, square), plug (rectangle), slot "
            "(rectangle with length), spot (circle), seam (circle with fanning lines). Fillet weld size is "
            "the leg length (written to the left of the symbol). Length and pitch go to the right: e.g., 5-100 "
            "means 5mm weld, 100mm pitch for intermittent welds. Tail contains process specification (GMAW, GTAW, "
            "SMAW) and NDT requirements. All-around weld symbol (circle at bend) means continuous welding "
            "around the entire joint perimeter."
        ),
        "source": "mcp-commander-analysis:builtin",
    },
    # 9. Surface finish symbols
    {
        "id": "surface_finish_01",
        "title": "Surface Finish and Roughness Specifications",
        "category": "standards",
        "content": (
            "Surface finish (also called surface texture or roughness) specifies the microscopic deviations "
            "from a nominally flat surface. Common parameters: Ra (arithmetic average roughness) is the most "
            "widely used; Rz (mean peak-to-valley height) is more sensitive to extremes. Typical Ra values by "
            "process: sawing — 6.3-25 µm, rough turning — 3.2-12.5 µm, finish turning — 0.8-3.2 µm, "
            "grinding — 0.2-1.6 µm, honing — 0.05-0.4 µm, lapping — 0.012-0.1 µm. On drawings, surface "
            "finish is indicated with the checkmark symbol (√) followed by the Ra value (e.g., √ Ra 1.6). "
            "ISO 1302 and ASME Y14.36 define the symbol format. Lay direction (parallel, perpendicular, "
            "cross-hatched, circular, radial, multidirectional, particulate) can be specified with additional "
            "symbols. Surface finish affects friction, wear, fatigue life, appearance, and coating adhesion."
        ),
        "source": "mcp-commander-analysis:builtin",
    },
    # 10. Material properties basics
    {
        "id": "material_props_01",
        "title": "Common Engineering Material Properties",
        "category": "materials",
        "content": (
            "Selecting materials requires understanding key properties: Yield Strength (the stress at which "
            "permanent deformation begins), Ultimate Tensile Strength (maximum stress before fracture), "
            "Elongation (ductility — % strain at fracture), Hardness (resistance to indentation, measured "
            "in Rockwell, Brinell, or Vickers), Density (mass per volume), Thermal Conductivity (W/m·K), "
            "Coefficient of Thermal Expansion (µm/m·°C), and Machinability (relative ease of cutting). "
            "Common metals: Aluminum 6061-T6 — yield 276 MPa, density 2.7 g/cm³, excellent machinability. "
            "Steel 1045 — yield 530 MPa, density 7.85 g/cm³, good weldability. Stainless 304 — yield 215 MPa, "
            "density 8.0 g/cm³, excellent corrosion resistance. Titanium Ti-6Al-4V — yield 880 MPa, "
            "density 4.43 g/cm³, excellent strength-to-weight ratio but difficult to machine. "
            "Material selection considers function, cost, manufacturability, weight, and environmental factors."
        ),
        "source": "mcp-commander-analysis:builtin",
    },
    # 11. Drawing view standards
    {
        "id": "drawing_views_01",
        "title": "Engineering Drawing View Standards and Conventions",
        "category": "drawing_views",
        "content": (
            "Standard engineering drawings use orthographic projection (first-angle or third-angle). "
            "Third-angle projection (common in US/Canada) places the top view above the front view, right "
            "view to the right. First-angle projection (common in Europe/Asia) places the top view below "
            "and the right view to the left. The projection symbol should appear in the title block. "
            "Essential views: Front view (most descriptive), Top view (above/below front), Right-side view "
            "(right/left of front). Additional views as needed: Isometric (3D pictorial), Section views "
            "(cutting plane reveals internal features — full, half, offset, broken-out, aligned, revolved), "
            "Detail views (circular or rectangular enlargement of small areas), Auxiliary views (true shape "
            "of inclined surfaces). Remove hidden lines in section views. Hatching at 45° represents cut material. "
            "Section cutting plane is labeled (A-A, B-B) and corresponding section view carries the same label."
        ),
        "source": "mcp-commander-analysis:builtin",
    },
    # 12. Section view conventions
    {
        "id": "section_views_01",
        "title": "Section View Types and Drawing Conventions",
        "category": "drawing_views",
        "content": (
            "Section views reveal internal features by 'cutting' the part with an imaginary plane. "
            "Types: (1) Full section — cutting plane passes entirely through the part. (2) Half section — "
            "only half the view is sectioned, the other half shows the exterior. (3) Offset section — cutting "
            "plane is stepped to pass through multiple features at different depths. (4) Broken-out section — "
            "a small portion is removed locally with a freehand break line. (5) Revolved section — cross-section "
            "is rotated 90° and superimposed on the view. (6) Removed section — cross-section drawn elsewhere "
            "at a larger scale. Conventions: Hatching is used for cut surfaces at 45° with uniform spacing. "
            "Thin features (webs, ribs) are NOT hatched when aligned with the cutting plane (to avoid the false "
            "impression of a solid cross-section). Standard parts (shafts, bolts, bearings) are drawn unsectioned. "
            "Hidden lines behind the cutting plane are generally omitted in the section view."
        ),
        "source": "mcp-commander-analysis:builtin",
    },
    # 13. Title block requirements
    {
        "id": "title_block_01",
        "title": "Title Block Requirements per ASME Y14.1",
        "category": "standards",
        "content": (
            "The title block is a standardized area on the drawing sheet containing essential identification "
            "and administrative information. Per ASME Y14.1, a complete title block includes: (1) Title/Description "
            "of the part or assembly. (2) Drawing number (unique identifier). (3) Revision letter and revision "
            "history table. (4) Scale (noted as FULL, HALF, 1:2, 2:1, etc.). (5) Sheet size (A, B, C, D, E or "
            "A0-A4). (6) Sheet number (e.g., 1 of 3). (7) Units (INCH or MM). (8) Default tolerances — typically "
            "X.X ±0.5, X.XX ±0.25, X.XXX ±0.1 for mm drawings. (9) Material specification. (10) Finish/treatment "
            "requirements. (11) Weight (if applicable). (12) Drawn by / Date. (13) Checked by / Date. "
            "(14) Approved by / Date. (15) Company name and logo. The title block is typically in the lower-right "
            "corner. Additional notes blocks appear near the title block or in the margins."
        ),
        "source": "mcp-commander-analysis:builtin",
    },
    # 14. BOM standards
    {
        "id": "bom_standards_01",
        "title": "Bill of Materials (BOM) Standards for Assembly Drawings",
        "category": "assembly",
        "content": (
            "The Bill of Materials (BOM) is a tabulated list on assembly drawings that identifies every "
            "component. Standard columns: (1) Item number (sequential bubble number matching balloons on the "
            "drawing). (2) Part number / Drawing number. (3) Description (part name, specification, or catalog "
            "number). (4) Material. (5) Quantity needed in the assembly. (6) Notes (optional — special instructions, "
            "vendor info). BOMs are placed above the title block on the first sheet. Parts are listed in "
            "ascending item order, not in assembly sequence. Standard parts (fasteners, bearings, O-rings) use "
            "catalog numbers and specifications rather than drawing numbers. Phantom items (reference assemblies) "
            "are shown in parentheses or dashed lines. Top-level BOM vs. indented (multi-level) BOM: the drawing "
            "BOM is typically flat (single level); the ERP BOM is indented showing sub-assemblies."
        ),
        "source": "mcp-commander-analysis:builtin",
    },
    # 15. Hole and wire sizing
    {
        "id": "hole_wire_01",
        "title": "Standard Hole Sizes and Wire Gauge Reference",
        "category": "manufacturing",
        "content": (
            "Standard drill sizes follow numbered (#1-#80), letter (A-Z), fractional (1/64 inch increments), and "
            "metric (0.1 mm increments) systems. For clearance holes, the hole diameter = bolt diameter + "
            "clearance. ANSI clearance fits: Close (1/64 inch), Normal (1/32 inch), Loose (1/16 inch). Tapped holes: for "
            "UNC threads, tap drill = major diameter - pitch (e.g., 1/4-20 UNC -> 0.201 inch (#7) tap drill). "
            "Wire gauges: AWG (American Wire Gauge) — as gauge number increases, diameter decreases. "
            "Common gauges: 10 AWG = 2.588 mm diameter, 12 AWG = 2.053 mm, 14 AWG = 1.628 mm, "
            "16 AWG = 1.291 mm, 20 AWG = 0.812 mm, 24 AWG = 0.511 mm. SWG (Standard Wire Gauge) is "
            "used in the UK and follows a different scale. For manufacturing, always specify the decimal "
            "equivalent rather than relying solely on gauge numbers to avoid ambiguity."
        ),
        "source": "mcp-commander-analysis:builtin",
    },
    # 16. Thread specifications
    {
        "id": "thread_specs_01",
        "title": "Thread Specification Standards (Unified and Metric)",
        "category": "manufacturing",
        "content": (
            "Thread specifications communicate the thread form, size, pitch, tolerance class, and sometimes "
            "the number of starts. Unified threads (inch): designated as 'Nominal Diameter - Threads Per Inch "
            "Series Class'. E.g., 1/4-20 UNC-2A means: 0.25\" major diameter, 20 TPI, Unified National Coarse, "
            "Class 2 external (A=external, B=internal). UNC = coarse (common), UNF = fine (better vibration "
            "resistance), UNEF = extra fine. Metric threads: M Diameter × Pitch Tolerance Class. "
            "E.g., M10×1.5-6H means: 10mm major diameter, 1.5mm pitch, tolerance class 6H (internal). "
            "Common metric pitches: M6×1.0, M8×1.25, M10×1.5, M12×1.75, M16×2.0. Thread fit classes: "
            "Loose (3H/3g), Normal (6H/6g), Tight (4H/4g). Acme threads (29°) for power transmission, "
            "pipe threads (NPT) for pressure connections."
        ),
        "source": "mcp-commander-analysis:builtin",
    },
    # 17. Bend allowance formulas
    {
        "id": "bend_allowance_01",
        "title": "Bend Allowance and Bend Deduction Formulas for Sheet Metal",
        "category": "sheet_metal",
        "content": (
            "Bend allowance (BA) is the length of the neutral axis arc through the bend. It determines "
            "the flat pattern length of a sheet metal part. Formula: BA = (π/180) × Bend Angle × (R + K × T), "
            "where R = inside bend radius, K = K-factor (typically 0.3-0.5), T = material thickness. "
            "Bend Deduction (BD) = 2 × (R + T) × tan(Bend Angle / 2) - BA. The K-factor depends on material, "
            "bend method, and bend radius. For air bending (most common): K ≈ 0.33-0.42. For coining: K ≈ 0.5 "
            "(neutral axis at center). For bottoming: K ≈ 0.42-0.45. CAD software like SolidWorks and Fusion 360 "
            "auto-calculate bend allowance using a K-factor or bend deduction table. Key tip: always verify flat "
            "pattern dimensions with a test piece before production runs. Material springback (2-5° depending "
            "on material and radius) must be compensated for in the bend angle setting."
        ),
        "source": "mcp-commander-analysis:builtin",
    },
    # 18. Assembly constraints and mates
    {
        "id": "assembly_01",
        "title": "Assembly Modeling: Mates, Constraints, and Best Practices",
        "category": "assembly",
        "content": (
            "Assembly modeling joins individual parts using mates/constraints. In SolidWorks: standard mates "
            "(coincident, concentric, distance, angle, tangent, parallel, perpendicular), advanced mates (symmetric, "
            "cam, gear, rack-pinion, limit, width, linear coupler), mechanical mates (slot, hinge, screw, "
            "universal joint, belt/chain). In Fusion 360: joints (rigid, revolute, slider, cylindrical, "
            "pin slot, planar, ball). Best practices: (1) Fully constrain every component — no degrees of freedom "
            "remain unless intentional. (2) Mate to reference planes and origins when possible for stability. "
            "(3) Use sub-assemblies to manage complexity — insert a sub-assembly as a single unit. "
            "(4) Avoid circular references. (5) Ground the first component (fix it to the origin). "
            "(6) Use collision detection to verify assembly. (7) Top-down modeling (layout sketches, skeleton "
            "parts) ensures components fit together. (8) exploded views for documentation and assembly instructions."
        ),
        "source": "mcp-commander-analysis:builtin",
    },
    # 19. Coordinate systems and datum references
    {
        "id": "datum_refs_01",
        "title": "Datum Reference Frames in GD&T",
        "category": "gdnt",
        "content": (
            "Datums are theoretically exact points, axes, or planes used as references for GD&T tolerances. "
            "They are identified by capital letters (A, B, C...) in a feature control frame. Datum features are "
            "the actual physical surfaces on the part that establish the datum. Primary datum (A) constrains 3 "
            "degrees of freedom (typically a plane). Secondary datum (B) constrains 2 more (typically an axis "
            "perpendicular to A). Tertiary datum (C) constrains the remaining 1 (typically a point or short axis). "
            "Datum precedence matters: A constrains the most, B next, C last. Datum modifiers: MMC (Maximum "
            "Material Condition) allows the datum feature to shift within its tolerance zone, providing bonus "
            "tolerance. LMC (Least Material Condition) is used for minimum material conditions. RFS (Regardless "
            "of Feature Size) — no modifier, applies at all sizes. Proper datum selection is critical: choose "
            "functional mating surfaces, not arbitrary surfaces."
        ),
        "source": "mcp-commander-analysis:builtin",
    },
    # 20. Fits and clearances
    {
        "id": "fits_clearances_01",
        "title": "Shaft and Hole Fits: Clearance, Interference, and Transition",
        "category": "manufacturing",
        "content": (
            "Fits describe the relationship between a shaft and a hole. ISO 286 / ASME B4.1 define standard "
            "tolerance classes. Clearance fit: hole is always larger than shaft — allows free rotation/sliding. "
            "Examples: H7/g6 (running fit), H7/f7 (precision sliding), H11/c11 (loose clearance). "
            "Interference fit: shaft is always larger than hole — requires pressing or thermal assembly. "
            "Examples: H7/p6 (light press), H7/s6 (medium press), H7/u6 (heavy press). Transition fit: "
            "may result in either clearance or interference depending on actual sizes. Example: H7/k6. "
            "Selection factors: load, speed, temperature, assembly method, material. Bearing fits: shaft "
            "typically j5-k5 (light), m5 (normal), p5 (heavy load). Housing fits: J6 (light), H7 (normal). "
            "Surface finish of mating surfaces affects actual fit; Ra ≤ 1.6 µm for precision fits. "
            "Always verify with tolerance stack analysis for critical assemblies."
        ),
        "source": "mcp-commander-analysis:builtin",
    },
    # 21. CNC machining design guidelines
    {
        "id": "cnc_guidelines_01",
        "title": "Design for CNC Machining: Practical Guidelines",
        "category": "manufacturing",
        "content": (
            "Design for CNC machining optimizes parts for efficient, accurate manufacturing. Key guidelines: "
            "(1) Minimum wall thickness: 1.5 mm for aluminum, 2 mm for steel (avoid thin walls that chatter). "
            "(2) Minimum feature size: 0.5 mm for end mills. (3) Fillet all internal corners — end mills are "
            "cylindrical, so sharp internal corners require EDM. Minimum fillet radius = tool radius. "
            "(4) Deep pockets: limit depth to 4× width for standard tools; deeper requires special tooling. "
            "(5) Avoid undercuts — they require 5-axis machining or special tool holders. "
            "(6) Hole depth: up to 10× diameter with standard drills; deeper requires peck drilling or gun drilling. "
            "(7) Threaded holes: minimum 1.5D from edge, 3D between hole centers. "
            "(8) Tolerance: avoid tolerances tighter than ±0.025 mm unless functionally necessary. "
            "(9) Part orientation: minimize setups — features accessible from fewer sides reduce cost. "
            "(10) Avoid large flat surfaces requiring extensive facing."
        ),
        "source": "mcp-commander-analysis:builtin",
    },
    # 22. 3D printing considerations
    {
        "id": "3dp_design_01",
        "title": "Design for 3D Printing (Additive Manufacturing)",
        "category": "manufacturing",
        "content": (
            "3D printing (additive manufacturing) has unique design considerations by technology. "
            "FDM (Fused Deposition Modeling): minimum wall thickness 1.2 mm, minimum feature 0.5 mm, layer "
            "height 0.1-0.3 mm creates visible layer lines, overhangs beyond 45° need supports, bridging "
            "span up to 10 mm without support. SLA/DLP (Resin): superior surface finish (layer lines nearly "
            "invisible), minimum wall 0.5 mm, overhangs still need supports, resin is brittle. SLS (Selective "
            "Laser Sintering): no supports needed (powder acts as support), minimum wall 0.7 mm, good for "
            "interlocking parts and complex geometries, powdery surface finish. Metal 3D (DMLS/SLM): expensive, "
            "requires supports and thermal stress relief, minimum wall 0.5 mm, Ra ≈ 6-15 µm as-printed. "
            "General rules: orient for strength along layer lines, add fillets at sharp transitions, "
            "include alignment features for multi-part assemblies, account for shrinkage (0.5-2% depending on process)."
        ),
        "source": "mcp-commander-analysis:builtin",
    },
]


class KnowledgeBase:
    """FAISS-backed RAG knowledge base for CAD and engineering topics.

    Usage::

        kb = KnowledgeBase()
        results = kb.search("how to specify GD&T position tolerance", top_k=3)

    On first search the index is built from the built-in knowledge entries.
    Call ``save`` / ``load`` for persistence across sessions.
    """

    DEFAULT_MODEL = "all-MiniLM-L6-v2"

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        index_path: Optional[str] = None,
    ) -> None:
        self.model_name = model_name
        self.index_path = index_path

        # Lazy-loaded
        self._model: Any = None
        self._index: Any = None
        self._documents: list[dict[str, str]] = []
        self._embeddings: Any = None  # numpy array
        self._initialized = False

    # ------------------------------------------------------------------
    # Lazy initialization
    # ------------------------------------------------------------------

    def _ensure_initialized(self) -> None:
        """Initialize model, seed documents, and build index on first use."""
        if self._initialized:
            return
        self._initialized = True

        # Try loading from disk
        if self.index_path:
            try:
                self.load(self.index_path)
                return
            except Exception:
                logger.debug("No persisted index found at %s — building from defaults", self.index_path)

        # Seed with built-in documents
        self._documents = list(_DEFAULT_KNOWLEDGE)
        self.build_index()

    def _load_model(self) -> Any:
        """Lazily load the sentence-transformers model."""
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers not installed. Run: pip install sentence-transformers"
            ) from exc

        cache_dir = os.getenv("MCP_COMMANDER_MODEL_CACHE_DIR")
        kwargs = {}
        if cache_dir:
            kwargs["cache_folder"] = cache_dir

        logger.info("Loading embedding model: %s", self.model_name)
        self._model = SentenceTransformer(self.model_name, **kwargs)
        return self._model

    # ------------------------------------------------------------------
    # Document management
    # ------------------------------------------------------------------

    def add_documents(self, docs: list[dict[str, str]]) -> int:
        """Add documents to the knowledge base and rebuild the index.

        Each doc should have ``{"id", "title", "content", "source"}`` and
        optionally ``"category"``.

        Returns the number of documents added.
        """
        if not docs:
            return 0

        self._ensure_initialized()
        before = len(self._documents)
        self._documents.extend(docs)
        self.build_index()
        return len(self._documents) - before

    def build_index(self) -> None:
        """(Re)build the FAISS index from all stored documents."""
        if not self._documents:
            self._index = None
            self._embeddings = None
            return

        try:
            import faiss
        except ImportError as exc:
            raise ImportError("faiss-cpu not installed. Run: pip install faiss-cpu") from exc

        import numpy as np

        model = self._load_model()

        # Embed document content (title + content for richer representation)
        texts = [
            f"{doc.get('title', '')} {doc.get('category', '')} {doc['content']}"
            for doc in self._documents
        ]

        logger.info("Embedding %d knowledge documents...", len(texts))
        self._embeddings = model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        # Build FAISS index (inner product on normalized vectors ≈ cosine similarity)
        dim = self._embeddings.shape[1]
        self._index = faiss.IndexFlatIP(dim)
        self._index.add(self._embeddings.astype("float32"))
        logger.info("FAISS index built with %d vectors", self._index.ntotal)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Search the knowledge base for entries relevant to *query*.

        Returns:
            List of dicts with ``{"id", "title", "category", "content", "source", "score"}``.
        """
        self._ensure_initialized()

        if not self._documents or self._index is None:
            return []

        model = self._load_model()
        import numpy as np

        q_embedding = model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).astype("float32")

        k = min(top_k, self._index.ntotal)
        scores, indices = self._index.search(q_embedding, k)

        results: list[dict[str, Any]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            doc = self._documents[idx]
            results.append({
                "id": doc.get("id", ""),
                "title": doc.get("title", ""),
                "category": doc.get("category", ""),
                "content": doc.get("content", ""),
                "source": doc.get("source", ""),
                "score": round(float(score), 4),
            })

        return results

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        """Persist the index, embeddings, and documents to *path* directory."""
        self._ensure_initialized()

        import json
        import numpy as np

        try:
            import faiss
        except ImportError as exc:
            raise ImportError("faiss-cpu not installed") from exc

        save_dir = Path(path)
        save_dir.mkdir(parents=True, exist_ok=True)

        faiss.write_index(self._index, str(save_dir / "faiss.index"))
        np.save(str(save_dir / "embeddings.npy"), self._embeddings)

        with open(save_dir / "documents.json", "w", encoding="utf-8") as f:
            json.dump(self._documents, f, indent=2, ensure_ascii=False)

        logger.info("Knowledge base saved to %s", save_dir)

    def load(self, path: str) -> None:
        """Load a previously saved knowledge base from *path* directory."""
        import json
        import numpy as np

        try:
            import faiss
        except ImportError as exc:
            raise ImportError("faiss-cpu not installed") from exc

        load_dir = Path(path)

        self._index = faiss.read_index(str(load_dir / "faiss.index"))
        self._embeddings = np.load(str(load_dir / "embeddings.npy"))

        with open(load_dir / "documents.json", "r", encoding="utf-8") as f:
            self._documents = json.load(f)

        self._initialized = True
        logger.info("Knowledge base loaded from %s (%d documents)", load_dir, len(self._documents))
