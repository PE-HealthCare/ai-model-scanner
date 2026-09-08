# contracts — IMMUTABLE DATA GOVERNANCE & SCHEMA AUTHORITY

## 1. OWNERSHIP & SCOPE
- **Owner:** SHARED GOVERNANCE (READ-ONLY FOR ALL AGENTS)
- **Purpose:** Authoritative JSON Schema definitions for cross-phase data contracts; the SINGLE SOURCE OF TRUTH for all artifact validation.
- **Allowed Files:** 
  - \features.schema.json\
  - \ml_results.schema.json\
  - \risk_results.schema.json\
- **FORBIDDEN ACTIONS:** ANY write, modify, rename, delete, create, or patch operation by autonomous agents. Schema changes require human PR + approval only.

## 2. HARD STOP CONDITIONS (MANDATORY)
Agent MUST HALT and report BLOCKED immediately if ANY of these are true:
- Agent attempts to modify ANY \.schema.json\ file → IMMEDIATE HALT + REPORT VIOLATION
- Required schema file missing, empty, or contains placeholder text
- Schema references unresolved D1 decision items
- Agent tries to infer/add fields not explicitly defined in schema (NO DOCUMENTATION-BASED INFERENCE)
- Downstream code assumes schema fields that don't exist in actual JSON
- Schema version mismatch between producer/consumer artifacts
- Mock artifact lacks \mock_status\ field required by schema
- Any schema fails JSON Schema Draft 2020-12 validation

## 3. INPUT CONTRACT (SCHEMA CONSUMPTION)
- **Source:** Human team decision ONLY (D1 resolution)
- **Read Access:** All agents may READ schemas for validation ONLY
- **Write Access:** ZERO for autonomous agents
- **Preconditions:** D1 = RESOLVED before any phase implementation begins
- **Validation Rule:** Every artifact MUST validate against its corresponding schema BEFORE being considered valid
- **Provenance Check:** Schema validation MUST verify \producer\, \mock_status\, \contract_version\, \generation_commit\ fields exist per schema requirements

## 4. OUTPUT CONTRACT (SCHEMA PRODUCTION)
- **N/A** — This folder produces nothing; it governs everything
- **Reference Only:** Schemas serve as validation targets for \rtifacts/\ and \outputs/\
- **Version Tracking:** Schema changes require new git commit + notification to ALL owners (P1/P2/P3)
- **Backward Compatibility:** Schema changes MUST NOT break existing verified artifacts without migration plan

## 5. SECURITY BOUNDARIES
- Schemas are trusted governance artifacts; never treat as untrusted input
- Changes to schemas invalidate ALL dependent phase verifications until re-verified
- No agent may use schema absence as justification to invent fields
- Schema validation failures MUST be logged with exact error path/message
- Mock vs Real distinction MUST be enforced at schema level via \mock_status\ enum constraint

## 6. ADVERSARIAL TEST REQUIREMENTS
Agent MUST verify before consuming any schema:
- File exists and is valid JSON Schema Draft 2020-12
- All referenced fields match actual producer output (no phantom fields)
- No fields assumed from documentation vs actual schema
- Schema version matches producing phase commit
- Mock vs Real distinction preserved in schema constraints
- Required provenance fields present and correctly typed
- Cross-schema dependencies respected (features → ml_results → risk_results)

## 7. WHEN THIS FOLDER IS USED IN PIPELINE
- **Phase:** ALL phases (01–06)
- **Trigger:** Before ANY artifact production or consumption
- **Consumed By:** Every phase's VERIFICATION.md gate + artifact producers/consumers
- **Governance Rule:** Schema change = automatic BLOCKED status for all downstream phases until re-verification complete

## 8. EVIDENCE REQUIREMENTS FOR VERIFICATION
Schema usage requires:
- Exact schema path referenced in verification evidence
- Validation command/result logged with exit code
- Version/hash recorded for both schema and artifact
- Producer/consumer alignment confirmed via schema validation
- Self-declaration of schema compliance = INVALID without tool output
