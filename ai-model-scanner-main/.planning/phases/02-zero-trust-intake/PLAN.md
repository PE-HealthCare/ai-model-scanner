# Phase 02 — Zero-Trust Intake — PLAN

**Owner:** P1 (`src/p1_static_engine/analyzer.py`)
**Dependency:** Phase 01 (CP1) gate passed; dependencies installed.

## Objective

Implement real, bounded, zero-trust intake of an untrusted `.safetensors` file plus its declared architecture, producing a trusted graph and associated metadata (`input_domain`, `is_quantized`) for downstream stages. This phase does not perform static feature extraction (Phase 3) or any classification/probing.

## Scope of Implementation

### Bounded SafeTensors Header Parsing

- Parse the SafeTensors header only within defined bounds; do not treat header content as trusted beyond what is needed to identify tensor names, shapes, and dtypes.
- Use `safetensors.safe_open` for weight access, per the frozen security boundary — this avoids unrestricted deserialization.

### No Pickle

- **No Pickle-based loading is used anywhere in intake.** This is a hard constraint carried from the Master Graph's security boundary (Section 1: "No unrestricted pickle loading is used").

### Uploader-Declared Recognizable Architecture

- The uploader declares an architecture; P1 does not attempt to infer an arbitrary/unknown architecture.
- **Do not assume automatic architecture detection for arbitrary unlabeled models.** If the declared architecture is not recognizable against the trusted, standard-library set, intake must fail closed rather than guessing.

### Trusted Graph Instantiation from Standard Libraries

- Only trusted, standard-library architecture definitions are instantiated (per the Security Boundary diagram in the Master Graph, Section 1).
- Weights from the SafeTensors file are mapped onto this trusted graph; the graph structure itself is never derived by executing any uploader-supplied code.

### Tensor Shape/Dtype Extraction

- Extract tensor shape and dtype metadata for each tensor as part of intake, needed both for trusted-graph weight mapping and for downstream quantization/domain tagging.

### INT8/FP8 Quantization Tagging

- Set `is_quantized = TRUE` when SafeTensors dtype indicates INT8 or FP8; otherwise `is_quantized = FALSE`, per the Master Graph's Intake feature/semantic graph (Section 5).

### mmap/Streaming Weight Access

- Weight access should use mmap/streaming access patterns (consistent with the Master Graph's Practical Feasibility evaluation criterion: "SafeTensors mmap-based access, bounded inference"), rather than loading the full file into memory at once where avoidable.

### Vision/NLP Domain Tagging

- Determine `input_domain` from the model's input shape/type characteristics, per the agreed canonical wording in the Master Graph (Section 5):
  - **VISION:** 4D float tensors
  - **NLP:** 2D/3D integer token tensors
- This tagging must use the input shape/type characteristics as the sole basis, not an inferred guess from architecture name or metadata not specified by the finalized pipeline.

### Trusted Graph and Metadata Handoff to Downstream Stages

- Hand off the trusted graph, `input_domain`, and `is_quantized` to the P1 Static Steganalysis stage (Phase 3) and, per the pipeline, ultimately to P2 for domain-aware probing (Phase 5).
- **The exact in-process mechanism for handing off the trusted graph from P1 to P2 through `scan_model.py` is DECISION REQUIRED (D2).** This plan does not invent that mechanism; it flags it for team resolution before P2's real integration (Phase 5) can rely on it.

## Explicit Security Boundary (Preserved)

- **Never execute arbitrary uploaded model code.** No uploader-supplied `model.py` is executed under any circumstance in this phase.
- Only the declared architecture (used to select a trusted, standard-library definition) and the SafeTensors weight bytes are treated as untrusted input; both are handled via bounded parsing, never execution.

## Explicit Non-Goals for This Phase

- No static feature extraction (entropy, chi-square, KL-divergence, KS, moments) — that is Phase 3.
- No ML classification or TreeSHAP — that is Phase 4.
- No behavioral probing — that is Phase 5.
- No redesign of the trusted-graph or security-boundary architecture.

## Preserved Unresolved Decision

- **D2 — Trusted graph handoff:** exact in-process mechanism between P1 and P2 through `scan_model.py` remains DECISION REQUIRED and must not be silently invented during this phase's implementation.
