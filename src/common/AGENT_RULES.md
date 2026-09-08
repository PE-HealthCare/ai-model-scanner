# src/common — SHARED INFRASTRUCTURE UTILITIES

## 1. OWNERSHIP & SCOPE
- **Owner:** SHARED INFRASTRUCTURE (cross-cutting concern)
- **Purpose:** Pure, phase-agnostic utility functions ONLY - JSON I/O, logging, config loading, type helpers, and generic schema-validation helpers
- **Allowed Files:** utils.py, __init__.py, helper modules with ZERO business logic
- **FORBIDDEN CONTENT:** Analysis, classification, probing, risk calculation, model loading, orchestration

## 2. HARD STOP CONDITIONS (MANDATORY)
Agent MUST HALT and report BLOCKED if ANY of these are true:
- Agent adds ANY analysis/classification/probing/risk logic -> IMMEDIATE HALT
- Function has side effects beyond I/O/logging
- Utility embeds phase-specific business rules or hard-coded artifact semantics
- Change impacts multiple owners without impact analysis
- Agent modifies utils.py to bypass phase gates or security boundaries

## 3. INPUT CONTRACT
- **Parameters:** Generic, phase-agnostic inputs only
- **Dependencies:** Standard library + approved pinned packages ONLY
- **Preconditions:** Authorization from the owner(s) materially affected by the shared utility change. Do not require unrelated owners to approve an isolated utility change that has no impact on their subsystem.

## 4. OUTPUT CONTRACT
- **Return Type:** Deterministic, side-effect-free values
- **Error Handling:** Explicit exceptions for invalid inputs - NO silent fallbacks

## 5. SECURITY BOUNDARIES
- No network access, file system traversal beyond intended scope
- No credential handling or secret management
- Input validation on ALL parameters - assume adversarial usage

## 6. WHEN THIS FOLDER IS USED IN PIPELINE
- **Phase:** ALL phases (imported as dependency)
- **Trigger:** Shared need identified across >=2 owners
- **Consumed By:** P1, P2, P3, scan_model.py
- **Stability Guarantee:** Interface changes require deprecation period + migration plan
