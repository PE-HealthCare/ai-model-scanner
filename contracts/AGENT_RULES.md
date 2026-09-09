# contracts — IMMUTABLE DATA GOVERNANCE & SCHEMA AUTHORITY

## 1. OWNERSHIP & SCOPE
- **Owner:** SHARED GOVERNANCE
- **Purpose:** Authoritative JSON Schema definitions for cross-phase JSON data contracts. These files are the single source of truth for contract validation once the corresponding contract decision is explicitly resolved.
- **Allowed Files:** `features.schema.json`, `ml_results.schema.json`, `risk_results.schema.json`
- **Agent Write Access:** READ-ONLY for autonomous implementation agents. Schema changes require an explicit human/team decision and approved repository change.

## 2. HARD STOP CONDITIONS (MANDATORY)
Agent MUST HALT and report BLOCKED if ANY of these are true:
- A schema is missing, malformed, or unexpectedly empty for a task that requires a resolved contract.
- The schema conflicts with an unresolved D1 decision.
- The agent attempts to invent or add fields from documentation, implementation convenience, or inference.
- Producer/consumer code assumes fields not present in the approved schema.
- Contract-version expectations are inconsistent.
- A mock artifact lacks the schema-required `mock_status` field.
- Schema validation fails under the declared JSON Schema dialect.

## 3. INPUT CONTRACT (SCHEMA CONSUMPTION)
- **Source:** Explicit project/team decision for D1 plus the committed schema.
- **Read Access:** All agents may READ schemas for validation and contract inspection.
- **Write Access:** ZERO for autonomous implementation agents.
- **Preconditions:** D1 = RESOLVED before contract-dependent final implementation. Phase-1 mock scaffolding may be prepared only to the extent explicitly permitted by the phase plan; it MUST NOT invent unresolved fields.
- **Validation Rule:** Every produced JSON artifact MUST validate against its corresponding approved schema before it is treated as contract-compliant.

## 4. CONTRACT VERSIONING & PROVENANCE
- `contract_version` identifies the contract/schema version used to validate the artifact. It is NOT the same thing as a source-code commit.
- `generation_commit` identifies the repository commit/version of the producer that generated the artifact. It is NOT the schema version.
- Schema changes require explicit review and re-verification of affected producers/consumers.
- Producers and consumers MUST NOT silently reinterpret a contract field while keeping the same contract version.

## 5. SECURITY BOUNDARIES
- Schemas are trusted governance inputs; they do not replace validation of untrusted model files.
- No agent may use schema absence or ambiguity as justification to invent fields.
- Schema validation failures MUST record the exact error path/message.
- Mock versus real artifact status MUST remain explicit and MUST NOT be relabeled by convenience.

## 6. ADVERSARIAL / CONSISTENCY REQUIREMENTS
Before consuming a contract, verify:
- the exact schema path;
- declared JSON Schema dialect;
- required fields and types;
- producer/consumer alignment;
- contract version;
- mock/real status semantics;
- cross-phase dependency order where applicable.

Do not require unrelated cross-schema audits when the task is isolated and does not cross those dependencies. Expand the audit only when a producer/consumer dependency actually requires it.

## 7. WHEN THIS FOLDER IS USED IN PIPELINE
- **Phase:** ALL phases (01–06)
- **Trigger:** Before producing or consuming a contract-governed JSON artifact.
- **Consumed By:** Contract producers, consumers, and verification gates.
- **Governance Rule:** A schema change invalidates dependent verification evidence until affected producers/consumers are re-verified.

## 8. EVIDENCE REQUIREMENTS
Schema use requires:
- exact schema path;
- validation command/result and exit status;
- contract version/hash;
- artifact generation commit/version where applicable;
- producer/consumer alignment evidence.

Self-declaration of schema compliance without validation evidence is INVALID.
