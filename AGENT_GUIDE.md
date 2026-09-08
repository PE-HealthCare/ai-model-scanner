# AGENT GUIDE

**Status:** Active execution control
**Purpose:** Deterministic context routing and safe execution policy for AI coding agents
**Authority:** Routing policy only. This file does not replace project requirements, architecture, phase plans, contracts, or verification criteria.

---

## 1. Purpose

`AGENT_GUIDE.md` defines how an AI coding agent should determine **what it needs to know before acting**.

The repository contains multiple planning, architecture, security, contract, and phase documents. Agents must not load the entire documentation tree by default.

The operating principle is:

> **Determine role, phase, and task first. Load the minimum authoritative context required to execute that task correctly. Expand context only when a defined trigger requires it.**

This reduces irrelevant context, architectural drift, accidental invention, and unnecessary changes.

---

# 2. Authority Boundary

This guide is a **routing layer**, not the project's architectural source of truth.

Project facts and decisions remain in the repository's authoritative planning, architecture, security, contract, and phase documents.

An agent must **not** infer authority from:

* document proximity;
* document length;
* implementation convenience;
* file creation date;
* which document was read most recently;
* which document appears more specific;
* its own prior assumptions.

If authoritative documents conflict:

1. Identify the applicable authority defined by the project.
2. Consult the relevant higher-authority source.
3. If the conflict cannot be resolved from existing project authority, **STOP** and report the conflict.
4. Never silently choose the interpretation that is easiest to implement.

**Not reading a document does not grant permission to override it.**

## 2A. GSD Reconciliation / Documentation-Change Control

When the task is to audit, reconcile, synchronize, or update project documentation, agents MUST enter **read-only reconciliation mode before editing**.

The required order is:

```text
MASTER GRAPH
    ↓
PROJECT / REQUIREMENTS / ROADMAP
    ↓
STATE
    ↓
PHASE PLAN / VERIFICATION
    ↓
AGENT_RULES / SUPPORTING DOCS
    ↓
ACTUAL REPOSITORY STRUCTURE / IMPLEMENTATION
```

The agent MUST first reconstruct current project state and report discrepancies without modification. Each discrepancy MUST be classified as one of:

```text
NO ISSUE
FACTUAL DRIFT
DOCUMENTATION DRIFT
STATE DRIFT
GOVERNANCE DRIFT
ARCHITECTURAL CONFLICT
DECISION REQUIRED
IMPLEMENTATION GAP
```

A documentation audit MUST NOT silently resolve project decisions. In particular:

* file existence does not prove a decision is resolved;
* populated schemas do not by themselves prove D1 is resolved;
* implementation presence does not prove design approval;
* scaffolding is not implementation;
* checkpoint `PASS` is distinct from independent/human approval;
* lower-authority documentation MUST NOT be changed to make an implementation appear unblocked.

After reconciliation, edits may be made only for explicitly identified drift or for an explicitly authorized decision update. A second read-only verification pass MUST confirm that the edited documentation remains consistent with the frozen architecture.

**READ → COMPARE → CLASSIFY → RESOLVE EXPLICIT DECISIONS → EDIT → VERIFY**

Never use:

**READ → ASSUME → EDIT**

---

# 3. Default Context-Minimization Policy

Agents must not read unrelated repository documentation merely because it exists.

### Read minimally by default

Do not automatically load:

* every `.md` file;
* every phase plan;
* every subsystem specification;
* every source directory;
* unrelated implementation files;
* unrelated contracts;
* future-phase details.

### Expand only when triggered

Additional context may be loaded when:

* the assigned task depends on it;
* a contract is involved;
* an ownership boundary is crossed;
* a security boundary is involved;
* an architectural ambiguity appears;
* an unresolved decision is encountered;
* a dependency or prerequisite must be verified;
* an upstream artifact is consumed;
* a downstream semantic dependency may be affected;
* verification requires additional evidence.

### Context expansion rule

Before expanding context, identify:

```text
TRIGGER:
What requires additional context?

SOURCE:
Which authoritative file/section can answer it?

PURPOSE:
What specific question must be answered?
```

Read only enough of that source to resolve the question.

---

# 4. Agent Boot Sequence

Every coding task should follow this sequence:

```text
1. IDENTIFY ROLE
2. IDENTIFY PHASE
3. IDENTIFY TASK
4. READ CURRENT STATE
5. LOAD TASK-SPECIFIC CONTEXT
6. CHECK PREREQUISITES
7. CHECK UNRESOLVED DECISIONS
8. CHECK OWNERSHIP / SCOPE
9. IMPLEMENT ONLY AUTHORIZED WORK
10. VERIFY AGAINST ACCEPTANCE CRITERIA
11. RECORD REQUIRED EVIDENCE
12. STOP
```

The sequence is a **control checklist**, not an additional project-management state machine.

The authoritative project state remains in `.planning/STATE.md`.

---

# 5. Step 1 — Identify ROLE

Determine which ownership boundary the task belongs to.

| Role                     | Primary responsibility                                                                                 |
| ------------------------ | ------------------------------------------------------------------------------------------------------ |
| **P1 — Static Analysis** | Zero-trust intake, trusted architecture, SafeTensors handling, static steganalysis, feature extraction |
| **P2 — Behavioral Risk** | STRIP probing, behavioral scoring, MAD risk aggregation, MRS, verdict                                  |
| **P3 — ML / Dashboard**  | LightGBM, synthetic training, TreeSHAP, `P_tamper`, reporting/dashboard                                |
| **Integration**          | `scan_model.py` orchestration and verified cross-stage integration                                     |

`src/common/utils.py` is shared infrastructure. It is not a fourth ownership subsystem.

`scan_model.py` is orchestration only. It must not absorb subsystem logic or independently recalculate risk.

If ownership is unclear, do not guess.

---

# 6. Step 2 — Identify PHASE

Determine the active implementation phase from `.planning/STATE.md`.

The project currently defines:

1. `01-mock-pipeline`
2. `02-zero-trust-intake`
3. `03-static-stegananalysis`
4. `04-ml-classification`
5. `05-behavioral-probing`
6. `06-risk-integration-demo`

Only work authorized by the current project state and applicable phase plan may be implemented.

A future phase does not become active merely because its code or documentation already exists.

---

# 7. Step 3 — Identify TASK

Reduce the request to a concrete task before reading broadly.

Use:

```text
ROLE:
PHASE:
TASK:
TARGET FILE(S):
EXPECTED OUTPUT:
VERIFICATION:
```

Example:

```text
ROLE: P1
PHASE: 3
TASK: Implement real static feature extraction
TARGET: src/p1_static_engine/analyzer.py
EXPECTED OUTPUT: Verified feature extraction using finalized semantics
VERIFICATION: Phase 3 verification criteria
```

If the task cannot be stated clearly enough to determine its authorized scope, treat it as **scope ambiguity** rather than inventing requirements.

---

# 8. Tiered Context Model

## Tier 0 — Always

Read:

```text
START.md
AGENT_GUIDE.md
.planning/STATE.md
```

`STATE.md` determines the current project state.

---

## Tier 1 — Current Task

Read only the documents directly relevant to the assigned role and phase:

```text
.planning/phases/<current-phase>/PLAN.md
.planning/phases/<current-phase>/VERIFICATION.md
```

Then load the relevant portions of:

```text
docs/contribution-rules.md
docs/solution-architecture.md
docs/threat-model.md
contracts/AGENT_RULES.md
contracts/<relevant-schema>.json
```

Do not automatically read unrelated sections.

---

## Tier 2 — Triggered Expansion

Expand context only when required.

| Trigger                             | Expand to                                           |
| ----------------------------------- | --------------------------------------------------- |
| Ownership or file-boundary question | Relevant `contribution-rules.md` section            |
| Architecture question               | Relevant `solution-architecture.md` section         |
| Security-boundary question          | Relevant `threat-model.md` section                  |
| Contract producer/consumer question | Relevant schema + contract rules                    |
| Feature-semantic change             | P1/P3 dependency and staleness rules                |
| Risk/MRS question                   | P2 risk ownership and relevant phase rules          |
| Integration question                | Orchestration, contracts, upstream/downstream rules |
| Unresolved decision                 | Specific D-item and its authoritative context       |
| Document conflict                   | Applicable authority source                         |
| Artifact validity question          | Provenance, lifecycle, and verification rules       |
| Dependency/version question         | Dependency governance and pinning requirements      |

---

# 9. Role + Phase Routing

The following is a **default routing matrix**, not an exhaustive reading requirement.

| Situation  | Read first                                                              | Expand when required                                              |
| ---------- | ----------------------------------------------------------------------- | ----------------------------------------------------------------- |
| Any task   | `STATE.md`, current PLAN/VERIFICATION                                   | Relevant governance/architecture/contracts                        |
| P1 Phase 2 | Phase 2 PLAN/VERIFICATION + P1 ownership + intake architecture          | Relevant threat model/contracts                                   |
| P1 Phase 3 | Phase 3 PLAN/VERIFICATION + P1 ownership + static-analysis architecture | Feature contract, Master Graph/authority context                  |
| P3 Phase 4 | Phase 4 PLAN/VERIFICATION + P3 ownership + classifier architecture      | P1 feature semantics, staleness dependencies                      |
| P2 Phase 5 | Phase 5 PLAN/VERIFICATION + P2 ownership + behavioral/risk architecture | P3 result contract, unresolved risk decisions                     |
| Phase 6    | Phase 6 PLAN/VERIFICATION + integration rules                           | Verified upstream outputs, relevant contracts and reporting rules |

### Important

"Read first" does **not** mean "read every line of every repository document."

"Expand when required" means the agent should retrieve the smallest additional authoritative context necessary to resolve the dependency.

---

# 10. Master Architecture Authority

The project's frozen Master Graph, when present in the repository, is an architectural authority and escalation reference.

Its exact repository path must be **verified from the repository before being referenced as a file path**.

Do not invent or assume its location.

The Master Graph should not be treated as an everyday full-read document.

Use it when:

* architecture is ambiguous;
* an implementation appears to conflict with the finalized pipeline;
* a document conflict cannot be resolved locally;
* a frozen design decision must be confirmed;
* an unresolved `D` decision is relevant.

If the authoritative architecture says:

```text
DECISION REQUIRED
```

the agent must not silently create a value or implementation.

---

# 11. Unresolved Decisions

The repository contains explicit unresolved decisions.

An unresolved decision is **not an invitation to choose a reasonable default**.

Examples include:

```text
D1 — Exact contract schemas
D2 — Trusted graph handoff
D3 — STRIP baseline
D4 — Behavioral normalization
D5 — Model-level risk aggregation
D6 — Highest-risk-layer aggregation
D7 — MAD zero/near-zero guard
D8 — Model staleness protection
D9 — Dependency pinning
```

Before implementing behavior governed by one of these decisions:

1. Determine whether the decision has been resolved.
2. Read the authoritative decision context.
3. If still unresolved and required for the task, STOP.
4. Report the applicable HALT code and the exact decision required.

Never replace an unresolved decision with an undocumented implementation choice.

---

# 12. Unknown → Context Expansion → Halt

Not every unknown requires an immediate halt.

Use this decision process:

```text
UNKNOWN
   │
   ▼
Can existing authorized project context answer it?
   │
   ├── YES ──► READ ──► CONTINUE
   │
   └── NO
        │
        ▼
Is it an unresolved project decision,
authority conflict, prerequisite, or scope issue?
        │
        ├── YES ──► HALT
        │
        └── NO ──► Request clarification / report limitation
```

The agent must not use "uncertainty" as justification for arbitrary invention.

---

# 13. Ownership and Scope Rules

An agent may modify only files necessary for the assigned task.

### Do not:

* refactor unrelated code;
* redesign another subsystem;
* modify another owner's implementation without authorization;
* alter contracts casually;
* change architecture to make implementation easier;
* modify shared utilities without dependency-impact analysis;
* change planning documents merely to make a task appear unblocked;
* silently expand task scope.

### Cross-owner change

If the task requires a change across ownership boundaries:

1. Identify the boundary.
2. Identify the affected owner(s).
3. Inspect the relevant contract/dependency.
4. Determine whether the change is already authorized.
5. If not authorized, STOP or request the required decision/approval.

---

# 14. Contracts Are Boundaries

The schemas under:

```text
contracts/
```

define stage interfaces.

Before changing a producer or consumer, inspect the relevant contract.

Do not infer that conceptual fields are implemented fields.

In particular:

> **An empty schema is still empty.**

Do not invent fields merely because they appear conceptually useful elsewhere.

A contract change can affect:

```text
producer
    ↓
schema
    ↓
consumer(s)
    ↓
verification
    ↓
downstream artifacts
```

Therefore contract changes require dependency analysis and appropriate reverification.

---

# 15. Artifact Lifecycle

Do not confuse file existence with implementation validity.

Artifacts may exist in different states:

```text
MOCK
SCAFFOLD
VERIFIED-REAL
STALE
```

### MOCK

Synthetic or placeholder output used for pipeline development.

### SCAFFOLD

Structure exists but required real behavior is not implemented or verified.

### VERIFIED-REAL

Produced by the intended real implementation and verified against the applicable acceptance criteria.

### STALE

Previously valid output/model whose upstream semantics or dependencies have changed such that its validity can no longer be assumed.

An agent must not present `MOCK`, `SCAFFOLD`, or `STALE` artifacts as verified production behavior.

---

# 16. Provenance

When an artifact materially affects downstream behavior, preserve or verify its provenance where required by the project.

Relevant provenance may include:

```text
source artifact
source/model version
feature semantic version
producer
run identifier
mock vs real status
hash/integrity information where applicable
```

"Same extraction code" means the downstream process uses the actual authorized P1 extractor, not a copied or independently reimplemented approximation.

---

# 17. Training and Semantic Dependencies

P3 final classifier training depends on verified real P1 feature extraction and exact feature semantics.

Therefore:

```text
P1 real extractor
      ↓
verified feature semantics
      ↓
P3 final training
      ↓
TreeSHAP mapping
      ↓
verification
```

If feature semantics change after classifier training:

```text
classifier becomes stale
        ↓
retrain required
        ↓
TreeSHAP remap/reverification
        ↓
Phase 4 reverification
```

Do not silently continue using a classifier whose feature semantics are stale.

---

# 18. TreeSHAP Is Not Highest-Risk-Layer Aggregation

TreeSHAP explains classifier contribution/importance.

Highest-risk-layer determination is a separate project requirement.

Do not assume:

```text
TreeSHAP
   =
highest-risk-layer logic
```

unless the authoritative project specification explicitly defines that mapping.

If the mapping is unresolved, do not invent it.

---

# 19. Risk Ownership

P2 owns:

* behavioral scoring;
* MAD risk aggregation;
* model-level risk aggregation;
* MRS;
* verdict.

P3 may consume verified P2 results for reporting/dashboard purposes.

Phase 6 integrates verified upstream behavior.

`scan_model.py` orchestrates the stages but does not independently recalculate risk or duplicate subsystem logic.

---

# 20. Verification Is Evidence, Not Self-Attestation

A verification checkbox is not proof by itself.

Where applicable, evidence should identify:

```text
COMMAND / TEST:
RESULT:
ARTIFACT / PATH:
CODE OR COMMIT EVIDENCE:
```

Agents must not mark a verification item complete merely because the implementation "looks correct."

Verification must correspond to the current implementation state.

---

# 21. Fail-Closed Execution

If an upstream required stage fails:

```text
STOP
↓
non-zero failure
↓
no fabricated downstream output
↓
no fabricated MRS
↓
no fabricated verdict
```

Do not convert an upstream failure into a plausible-looking fallback result unless the project explicitly defines that fallback.

Unknown, malformed, unsupported, unsafe, or ambiguous input must not silently become a successful scan.

---

# 22. Security Boundary

The scanner processes untrusted model artifacts.

Agents must preserve the project's security boundaries, including applicable controls for:

* untrusted model files;
* bounded parsing;
* malformed metadata;
* pathological tensor dimensions;
* invalid offsets;
* resource exhaustion;
* arbitrary code execution;
* network egress;
* credentials/secrets;
* dependency/package supply chain;
* output artifact integrity;
* scanner-host isolation.

Do not introduce external network access, arbitrary execution, credential use, or model-data exfiltration merely because it makes development easier.

---

# 23. Dependency Changes

Dependencies are part of the project's supply-chain boundary.

Do not autonomously select production dependency versions when the required dependency decision has not been resolved.

Where dependency pinning is required:

```text
version
↓
environment
↓
verification
```

must be reproducible and consistent with the project's dependency policy.

Unresolved dependency requirements are blockers, not invitations to guess.

---

# 24. Source-Code Inspection Policy

Do not read an entire source directory unless the task genuinely requires it.

Instead:

```text
Identify target
    ↓
Inspect target file
    ↓
Inspect directly imported/dependent code
    ↓
Inspect relevant tests
    ↓
Expand only if required
```

The objective is **minimum sufficient context**, not minimum possible context.

Insufficient context is also unsafe.

---

# 25. Halt Codes

Use a specific halt code when the agent cannot safely continue.

| Code                           | Meaning                                                                           |
| ------------------------------ | --------------------------------------------------------------------------------- |
| `HALT_01_GATE_LOCKED`          | Current phase/checkpoint is not authorized to proceed                             |
| `HALT_02_DECISION_REQUIRED`    | Required project decision remains unresolved                                      |
| `HALT_03_BOUNDARY_BREACH`      | Requested work crosses an unauthorized ownership/scope boundary                   |
| `HALT_04_CONTRACT_CONFLICT`    | Contract/schema interpretation cannot be resolved                                 |
| `HALT_05_AUTHORITY_CONFLICT`   | Authoritative project documents conflict                                          |
| `HALT_06_MISSING_PREREQUISITE` | Required upstream dependency or prerequisite is absent/unverified                 |
| `HALT_07_UNVERIFIED_ARTIFACT`  | Required artifact exists but has not been sufficiently verified                   |
| `HALT_08_STALE_ARTIFACT`       | Required artifact/model is invalidated by upstream semantic or dependency changes |
| `HALT_09_SECURITY_BOUNDARY`    | Continuing would violate a security constraint                                    |
| `HALT_10_SCOPE_AMBIGUITY`      | Task scope cannot be determined safely                                            |

### HALT is a valid control outcome

A HALT is **not an agent failure** when the repository does not authorize safe continuation.

The correct outcome is:

> **Do not invent. Surface the blocker. Stop.**

---

# 26. What a HALT Report Must Contain

When stopping, report concisely:

```text
STATUS: HALT

CODE: HALT_XX_...

ROLE:
PHASE:
TASK:

BLOCKER:
<exact unresolved issue>

AUTHORITATIVE SOURCE:
<file / section / decision>

WHY EXECUTION CANNOT SAFELY CONTINUE:
<short explanation>

REQUIRED RESOLUTION:
<decision, approval, prerequisite, or clarification>
```

Do not "work around" the blocker without authorization.

---

# 27. Completion Model

A task is not complete merely because code was written.

The intended lifecycle is:

```text
CONTEXT
   ↓
AUTHORIZED SCOPE
   ↓
IMPLEMENT
   ↓
VERIFY
   ↓
EVIDENCE
   ↓
STATE UPDATE IF REQUIRED
   ↓
STOP
```

Valid outcomes include:

```text
PASS
BLOCKED
HALT
FAIL
```

The agent's objective is not:

> "Always produce an implementation."

The objective is:

> **"Produce only authorized, correctly scoped, verifiable work."**

---

# 28. Final Agent Checklist

Before acting:

```text
[ ] Role identified
[ ] Current phase identified
[ ] Task clearly defined
[ ] STATE.md checked
[ ] Current PLAN.md read
[ ] Current VERIFICATION.md read
[ ] Relevant ownership boundary understood
[ ] Relevant contracts identified
[ ] Required architecture/security context loaded
[ ] Unresolved decisions checked
[ ] Prerequisites checked
[ ] Scope confirmed
```

Before finishing:

```text
[ ] Only authorized files changed
[ ] No unrelated refactoring introduced
[ ] No unresolved decision was invented
[ ] No contract semantics were silently invented
[ ] No stale artifact was treated as current
[ ] Required tests/verification executed
[ ] Evidence recorded where required
[ ] Required state/phase documentation updated
[ ] Working tree changes reviewed
```

If any critical condition cannot be satisfied safely:

```text
STOP
→ use the appropriate HALT/BLOCKED status
→ report the exact blocker
→ do not improvise
```

---

# 29. Core Operating Principle

> **Load less context, not less truth.**

The agent should minimize irrelevant information while preserving access to every authoritative source required to make the current decision correctly.

```text
START
  ↓
AGENT GUIDE
  ↓
ROLE + PHASE + TASK
  ↓
STATE
  ↓
MINIMUM REQUIRED CONTEXT
  ↓
TRIGGERED EXPANSION WHEN NECESSARY
  ↓
AUTHORIZED IMPLEMENTATION
  ↓
EVIDENCE-BASED VERIFICATION
  ↓
PASS / BLOCKED / HALT / FAIL
  ↓
STOP
```

**Never invent an unresolved project decision.**
**Never treat missing context as permission to guess.**
**Never treat not-reading as permission to override.**
**Never expand scope merely because additional work is possible.**
