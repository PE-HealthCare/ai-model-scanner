# src/p1_static_engine — FORMAT-ADAPTIVE STATIC STEGANALYSIS

## 1. OWNERSHIP & SCOPE
- **Owner:** P1 (static analysis authority)
- **Purpose:** Per-layer statistical feature extraction against intra-model baseline
- **Allowed Files:** analyzer.py, format_gate.py, baseline_calculator.py, tests/
- **FORBIDDEN FILES:** ML models, probing code, risk aggregation, dashboard logic

## 2. HARD STOP CONDITIONS (MANDATORY)
Agent MUST HALT and report BLOCKED if ANY of these are true:
- CP2 != PASS (intake not verified)
- features.schema.json unresolved (D1) or empty
- MAD guard behavior undefined (D7)
- Layer identity preservation broken
- Intra-model MAD baseline degenerate (near-zero/low layers) without guard
- Agent invents feature semantics/ordering not in approved schema
- External reference model used (intra-model ONLY)

## 3. INPUT CONTRACT
- **Required Artifact:** Trusted graph from `data/models/` via analyzer.py
- **Schema:** contracts/features.schema.json (exact fields/types/ordering)
- **Preconditions:** CP2 = PASS + D1 resolved
- **Format Gate:** FP32/FP16 -> full feature set; Quantized -> whole-weight KS ONLY

## 4. OUTPUT CONTRACT
- **Produced Artifact:** features.json matching features.schema.json EXACTLY
- **Feature Semantics:** Use only the feature names, meanings, representation, and ordering explicitly established by the approved contract/finalized specification. Do not invent additional feature names or ordering.
- **Provenance:** producer=P1, mock_status, contract_version, generation_commit

## 5. SECURITY BOUNDARIES
- Use safetensors.safe_open ONLY for weight access
- Bounded resource limits during feature extraction
- No external model downloads or network calls
- Fail CLOSED on malformed layer data - NO partial features

## 6. WHEN THIS FOLDER IS USED IN PIPELINE
- **Phase:** 03 Static Steganalysis
- **Trigger:** CP2 = PASS
- **Consumed By:** P3 ML classifier (CRITICAL DEPENDENCY for Phase 4 training)
- **Dependency Lock:** P3 Phase 4 CANNOT begin until P1 Phase 3 VERIFIED-REAL
