# AI Model Scanner — Contribution & Agent Execution Rules

**Project:** Precision Care Challenge 2026 — Detection of Steganographic Malware Hidden in AI Model Weights
**Repository:** `PE-HealthCare/ai-model-scanner`
**Status:** **FROZEN FOR EXECUTION**
**Primary Source of Truth:** `AI_Model_Scanner_FINAL_MASTER_DISCOVERY_GRAPH.md`

---

## 1. Purpose

This document defines the rules governing:

* human contributions;
* autonomous/agentic coding;
* ownership;
* branch and change scope;
* shared contracts;
* dependency management;
* verification;
* artifact provenance;
* phase gates;
* cross-owner changes;
* failure handling;
* merge authority.

These rules are mandatory.

They exist to prevent an autonomous coding agent from:

* redesigning the finalized architecture;
* silently resolving an unresolved decision;
* treating scaffolding as implementation;
* training on mock features and presenting the result as real;
* changing feature semantics without retraining downstream models;
* recalculating another subsystem's outputs;
* bypassing security boundaries;
* approving its own work;
* merging unverified code;
* silently changing dependencies;
* weakening fail-closed behavior.

---

# 2. Authority Hierarchy

When project documents disagree, agents MUST NOT choose based on:

* document proximity;
* document recency;
* implementation convenience;
* apparent specificity;
* personal preference;
* generated-code assumptions.

The following authority order applies:

1. **Frozen Master Graph**

   * `AI_Model_Scanner_FINAL_MASTER_DISCOVERY_GRAPH.md`

2. **Explicitly approved project decisions**

   * decisions recorded against D1–D9 or an equivalent authoritative decision record.

3. **Frozen project requirements / roadmap / state**

   * `REQUIREMENTS.md`
   * `ROADMAP.md`
   * `STATE.md`

4. **Frozen phase plans and verification contracts**

   * phase `PLAN.md`
   * phase `VERIFICATION.md`

5. **Solution architecture**

   * `docs/solution-architecture.md`
   * or the repository's explicitly designated resolved solution document.

6. **Threat model**

   * `docs/threat-model.md`

7. **Contribution rules**

   * this document.

8. **Implementation details**

   * source code, comments, examples, scaffolding, tests, generated artifacts.

### Conflict Rule

If a lower-level document conflicts with a higher-level source:

> **The higher-level source wins.**

If the conflict cannot be resolved by the hierarchy:

> **STOP. Mark the work BLOCKED. Surface the conflict. Do not implement a guess.**

---

# 3. Immutable Source-of-Truth Rule

The Master Graph is immutable during normal implementation.

Agents MUST NOT modify:

`AI_Model_Scanner_FINAL_MASTER_DISCOVERY_GRAPH.md`

unless the team explicitly reopens the architecture.

A normal implementation task is **not** authorization to modify the Master Graph.

If implementation appears impossible without changing the Master Graph:

1. stop implementation;
2. report the conflict;
3. identify the affected requirement;
4. request an explicit architecture decision.

No agent may reinterpret an architectural conflict as permission to redesign.

---

# 4. Frozen Architecture

The finalized detection pipeline is:

```text
Declared Architecture + Untrusted .safetensors
        ↓
P1 — Zero-Trust Intake
        ↓
P1 — Static Steganalysis
        ↓
features.json
        ↓
P3 — LightGBM + TreeSHAP
        ↓
ml_results.json
        ↓
P2 — STRIP Behavioral Probing
        ↓
P2 — Risk Aggregation / MRS / Verdict
        ↓
risk_results.json
        ↓
P3 — Security Report / Dashboard
```

The implementation phases are:

1. Phase 1 — Mock Pipeline
2. Phase 2 — Zero-Trust Intake
3. Phase 3 — Static Steganalysis
4. Phase 4 — ML Classification
5. Phase 5 — Behavioral + Risk
6. Phase 6 — Integration + Demo

The five detection stages and six implementation phases MUST NOT be conflated.

---

# 5. Ownership Boundaries

## P1 — Eyes

Owns:

`src/p1_static_engine/`

Primary implementation surface:

`src/p1_static_engine/analyzer.py`

P1 owns:

* safe intake;
* bounded SafeTensors handling;
* trusted architecture instantiation;
* architecture/tensor validation;
* domain tagging;
* quantization tagging;
* static steganalysis;
* statistical feature extraction.

P1 does NOT own:

* LightGBM;
* TreeSHAP;
* P2 behavioral scoring;
* MRS;
* verdict logic;
* dashboard logic.

---

## P2 — Muscle

Owns:

`src/p2_behavioral_risk/`

Primary implementation surface:

`src/p2_behavioral_risk/prober.py`

P2 owns:

* domain-aware STRIP probing;
* behavioral scoring;
* MAD risk aggregation;
* model-level risk aggregation;
* MRS;
* PASS / REVIEW / FAIL verdict.

P2 is the **sole authority for risk aggregation and verdict calculation**.

P2 does NOT own:

* P1 feature extraction;
* LightGBM training;
* TreeSHAP;
* dashboard presentation.

---

## P3 — Brain & Voice

Owns:

`src/p3_ml_dashboard/`

Primary implementation surfaces:

* `classifier.py`
* `dashboard.py`

P3 owns:

* synthetic tampering workflow;
* LightGBM training;
* classifier artifact;
* TreeSHAP;
* `P_tamper`;
* security report;
* dashboard/presentation.

P3 does NOT own:

* P1 feature extraction;
* P2 behavioral scoring;
* MRS calculation.

---

## Root Orchestration

`scan_model.py`

`scan_model.py` is an integration/orchestration surface.

It MUST:

* call P1;
* pass verified P1 output to P3;
* pass verified outputs to P2;
* pass verified results to P3 reporting.

It MUST NOT:

* reimplement P1;
* reimplement P2;
* reimplement P3;
* calculate MRS independently;
* calculate a second verdict;
* silently transform feature semantics;
* become a fourth subsystem owner.

---

## Shared Utilities

`src/common/`

Shared code is permitted only for genuinely shared infrastructure.

`src/common/` MUST NOT become a dumping ground for:

* P1 detection logic;
* P2 scoring logic;
* P3 classifier logic;
* subsystem-specific policy.

A shared utility change that affects multiple owners requires impact analysis and reverification by every affected owner.

---

# 6. Shared Contracts

The following are interfaces, not implementation suggestions:

* `features.schema.json`
* `ml_results.schema.json`
* `risk_results.schema.json`

Current empty schemas MUST remain treated as empty until D1 is explicitly resolved.

Conceptual fields in documentation are NOT implemented fields.

A field becomes authoritative only when its contract is explicitly approved.

---

# 7. Contract Change Rule

Any change to a shared contract requires:

1. identification of affected producers;
2. identification of affected consumers;
3. semantic impact analysis;
4. explicit coordination;
5. downstream reverification;
6. updated verification evidence.

The following count as semantic changes:

* field name;
* field type;
* units;
* numerical range;
* representation;
* ordering;
* normalization;
* meaning;
* layer association;
* feature extraction formula;
* missing-value behavior.

A schema-compatible change can still be a breaking semantic change.

---

# 8. Agent Execution State Machine

Every autonomous implementation task MUST follow this sequence:

```text
READ
 ↓
CHECK AUTHORITY
 ↓
CHECK STATE
 ↓
CHECK PREREQUISITES
 ↓
CHECK DECISIONS
 ↓
DEFINE SCOPE
 ↓
IMPLEMENT
 ↓
VERIFY
 ↓
COLLECT EVIDENCE
 ↓
CLASSIFY ARTIFACT
 ↓
UPDATE STATE / VERIFICATION
 ↓
COMMIT
 ↓
REQUEST INDEPENDENT REVIEW
 ↓
MERGE ONLY IF AUTHORIZED
```

An agent MUST NOT skip directly from implementation to merge.

---

# 9. Mandatory Pre-Implementation Inspection

Before changing code, an agent MUST inspect:

* current `STATE.md`;
* applicable `ROADMAP.md`;
* applicable `REQUIREMENTS.md`;
* applicable phase `PLAN.md`;
* applicable `VERIFICATION.md`;
* relevant source files;
* relevant schemas;
* Master Graph;
* unresolved decisions affecting the task.

The agent MUST establish:

* current phase;
* current checkpoint;
* current artifact status;
* applicable prerequisites;
* affected owners;
* unresolved decisions;
* allowed file scope.

---

# 10. Decision Required Rule

The Master Graph contains decisions marked **DECISION REQUIRED**.

These include:

* D1 — exact contract schemas;
* D2 — trusted graph handoff;
* D3 — STRIP baseline;
* D4 — behavioral normalization;
* D5 — per-layer to model-level aggregation;
* D6 — highest-risk-layer aggregation;
* D7 — MAD zero/near-zero guard;
* D8 — model staleness protection;
* D9 — dependency pinning.

An agent MUST NOT silently select an implementation for an unresolved decision.

If the current task requires such a decision:

> **Status = BLOCKED**

The agent may prepare non-authoritative scaffolding around the decision only if doing so does not imply that the decision has been resolved.

---

# 11. Status Vocabulary

Every significant implementation artifact MUST have one of these states:

### MOCK

Synthetic or simulated output used only for pipeline development.

### SCAFFOLD

Structure exists but production behavior is incomplete.

### VERIFIED-REAL

Implemented against real upstream inputs and verified through required tests/evidence.

### STALE

Previously valid artifact whose upstream semantics, dependency environment, model, schema, or contract has changed.

### BLOCKED

Cannot safely proceed because a required prerequisite or decision is unresolved.

### FAIL

Implementation or verification produced a failure.

### PASS

All applicable mandatory verification requirements have passed.

Existence of a file does not imply `VERIFIED-REAL`.

---

# 12. Artifact Provenance

Important artifacts MUST be traceable to their source.

At minimum, provenance SHOULD identify:

* producer;
* artifact type;
* source model/input;
* mock vs real status;
* feature semantic version where applicable;
* schema version;
* generation/run identifier;
* timestamp;
* relevant code revision;
* model/classifier revision where applicable;
* cryptographic hash where practical.

A downstream artifact MUST NOT be considered valid merely because the file exists.

---

# 13. Mock Contamination Prevention

Mock data is allowed during scaffolding.

Mock artifacts MUST NOT silently enter production execution.

In particular:

* P3 MUST NOT train the final classifier on placeholder P1 features.
* P2 MUST NOT calculate final risk from mock upstream outputs.
* Phase 6 MUST NOT present mock outputs as scanner results.
* Demo output MUST identify simulated content when mocks are intentionally used.

A production gate MUST fail if mock provenance is detected where verified-real provenance is required.

---

# 14. P3 Training Integrity

Final LightGBM training MUST use the actual verified P1 feature extractor.

The training workflow MUST NOT contain a copied, independently reimplemented feature extractor whose output merely resembles P1.

The authoritative chain is:

```text
P1 extractor
      ↓
real feature vector
      ↓
training data
      ↓
LightGBM
      ↓
classifier artifact
      ↓
TreeSHAP
```

If P1 feature semantics change after training:

```text
P1 semantic change
      ↓
classifier STALE
      ↓
P3 retraining required
      ↓
TreeSHAP remapping/reverification required
      ↓
downstream gates BLOCKED until verified
```

This invalidation is mandatory.

---

# 15. TreeSHAP and Highest-Risk Layer

TreeSHAP explains feature contribution to the classifier.

TreeSHAP MUST NOT be treated as a substitute for the highest-risk-layer aggregation mechanism.

These are separate concepts:

```text
TreeSHAP
= why classifier prediction changed

Highest-risk-layer
= which neural-network layer is highest risk
```

D5/D6 remain authoritative for unresolved aggregation behavior.

---

# 16. Branch Rules

Branch names MUST communicate ownership and scope.

Preferred pattern:

```text
feature/p1-static
feature/p2-behavioral
feature/p3-ml-dashboard
feature/shared-contracts
feature/scan-model-orchestration
```

These names are examples of the intended naming convention, not permission to create unrelated branches.

A branch MUST NOT contain unrelated subsystem work merely for convenience.

---

# 17. File Scope

An agent MUST modify only files required for its assigned task.

An agent MUST NOT:

* refactor unrelated code;
* reformat unrelated files;
* rename unrelated files;
* change architecture documents unnecessarily;
* alter another subsystem's implementation without authorization;
* modify the Master Graph.

Cross-boundary changes require explicit impact identification.

---

# 18. Cross-Owner Change Protocol

The following changes require affected-owner notification and reverification:

* feature semantics;
* feature ordering;
* feature names;
* `input_domain`;
* `is_quantized`;
* P1 → P2 handoff;
* `P_tamper`;
* STRIP baseline;
* behavioral normalization;
* MAD guard;
* layer aggregation;
* MRS formula;
* output schemas;
* classifier artifact semantics.

Verification status MUST record the affected downstream work.

---

# 19. Self-Approval Prohibition

An autonomous agent MUST NOT:

* approve its own PR;
* approve its own verification;
* declare its own checkpoint independently passed;
* authorize its own merge;
* override an independent verification failure.

Implementation and approval MUST be treated as separate responsibilities.

Where repository policy permits only one actor, the agent MUST still record verification evidence rather than treating its own assertion as independent approval.

---

# 20. Verification Evidence Standard

A checkbox is NOT evidence.

Every mandatory PASS MUST identify:

1. command/test performed;
2. expected result;
3. actual result;
4. artifact/path inspected;
5. relevant code or commit;
6. date/run identifier where useful.

Example:

```text
Check: SafeTensors malformed-header regression
Command: pytest tests/security/test_header_limits.py
Expected: malformed/oversized headers rejected
Actual: PASS — 12/12 tests
Evidence: test output + implementation revision
Status: PASS
```

---

# 21. Mandatory Security Regression Coverage

Verification MUST include applicable tests for:

* malformed SafeTensors header;
* oversized header;
* excessive metadata;
* excessive tensor count;
* pathological tensor dimensions;
* invalid tensor offsets;
* invalid dtype;
* architecture/tensor mismatch;
* unknown architecture;
* unsupported input domain;
* malformed contract;
* missing required field;
* unexpected field;
* wrong feature ordering;
* wrong feature semantics;
* NaN/Inf values;
* zero/near-zero MAD;
* one-layer or degenerate models;
* quantized behavioral bypass;
* malformed P2 output;
* malformed P3 output;
* stale classifier;
* mock artifact leakage;
* upstream stage failure;
* partial output generation;
* timeout/resource exhaustion conditions.

Additional regression tests MUST be added when a security-relevant bug is fixed.

---

# 22. Fail-Closed Rule

For safety-critical scanner execution:

> **Unexpected upstream failure MUST STOP downstream scoring.**

If P1 fails:

* P3 MUST NOT fabricate features;
* P2 MUST NOT fabricate risk;
* no MRS;
* no verdict.

If P3 fails:

* P2 MUST NOT substitute an invented `P_tamper`;
* no final MRS;
* no final verdict.

If P2 fails:

* no final verdict.

The scanner MUST NOT convert technical failure into PASS.

---

# 23. Partial Output Rule

A partial artifact MUST NOT be presented as a complete scanner result.

If execution stops:

```text
execution_status = FAILED / BLOCKED
```

and the report MUST NOT fabricate:

* MRS;
* PASS;
* REVIEW;
* FAIL;
* highest-risk layer;
* behavioral evidence.

---

# 24. Network and Secret Policy

Autonomous agents MUST NOT:

* exfiltrate model weights;
* upload scanner inputs to external services;
* send proprietary artifacts to external APIs;
* expose credentials;
* commit secrets;
* use credentials found inside model artifacts;
* enable arbitrary network access merely to make a test pass.

External network access is permitted only when explicitly required and authorized.

The scanner itself MUST NOT require external network access for runtime model scanning unless the frozen architecture explicitly permits it.

---

# 25. Dependency Supply-Chain Rule

Dependencies are part of the security boundary.

Before D9 is resolved, agents MUST NOT silently choose production dependency versions.

Agents may identify compatibility requirements, but final dependency versions MUST be pinned through the approved dependency-resolution process.

Unpinned production dependencies MUST prevent final release readiness.

Dependency changes require:

* justification;
* version identification;
* compatibility verification;
* security impact review;
* downstream regression testing.

---

# 26. Phase Gate Rule

A phase advances only when its gate is:

```text
PASS
```

The following states do NOT permit advancement:

* BLOCKED;
* FAIL;
* STALE;
* unresolved required decision;
* missing verification evidence;
* mock-only implementation;
* incomplete prerequisite;
* unverified dependency.

No wording such as "mostly complete" or "open decision but safe to continue" may substitute for a required gate.

---

# 27. Downstream Invalidation

If an upstream artifact changes in a way that can affect downstream semantics, dependent artifacts MUST automatically be treated as STALE until reverified.

Examples:

```text
P1 feature semantics changed
→ P3 classifier STALE
→ TreeSHAP STALE
→ dependent P2 risk integration STALE
→ Phase 6 BLOCKED
```

```text
MRS formula changed
→ risk results STALE
→ dashboard/report STALE
→ integration verification required
```

---

# 28. Merge Rules

A change may merge only when:

* scope is authorized;
* required tests pass;
* applicable verification evidence exists;
* no required decision remains silently unresolved;
* no required artifact is stale;
* cross-owner impacts are addressed;
* no security regression is known;
* dependency requirements are satisfied;
* independent review/approval requirements are satisfied.

A green unit-test suite alone does not constitute a phase gate.

---

# 29. Rollback Rule

If a merged change causes:

* security regression;
* contract incompatibility;
* stale downstream artifact;
* incorrect scoring;
* architecture violation;
* failed gate;

the affected downstream work MUST be marked STALE or BLOCKED immediately.

The team may revert the offending change rather than patching around a frozen architecture violation.

---

# 30. Independent vs. Blocked Work

### May proceed independently

* Phase 1 mocks;
* P2 probe design against mocks;
* P3 synthetic tampering generation;
* P3 LightGBM scaffolding;
* P3 TreeSHAP scaffolding;

provided these activities do not claim final validity and do not silently resolve D1–D9.

### Must remain blocked

* final P3 training before verified P1 real features;
* final P2 risk integration before required real upstream outputs;
* final dashboard/report before verified upstream results;
* any work requiring an unresolved mandatory decision.

---

# 31. General Agent Rules

Every agent must:

1. inspect before editing;
2. obey the authority hierarchy;
3. preserve the frozen architecture;
4. respect subsystem ownership;
5. avoid unrelated changes;
6. surface unresolved decisions;
7. fail closed on ambiguity;
8. preserve provenance;
9. distinguish MOCK/SCAFFOLD from VERIFIED-REAL;
10. record verification evidence;
11. never self-approve;
12. never fabricate downstream results;
13. never silently change feature semantics;
14. never silently weaken security controls.

**If in doubt: STOP, report the ambiguity, and mark the work BLOCKED.**

---

# 32. Final Principle

> **An autonomous agent is an implementer, not an architect, approver, or policy authority.**

The agent may implement approved decisions.

It may verify against approved requirements.

It may identify conflicts.

It may propose changes.

It may **not silently decide the architecture, security boundary, contract semantics, risk mathematics, or unresolved Master Graph decisions.**
