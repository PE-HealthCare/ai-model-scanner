# artifacts — TRANSIENT HANDOFF STORAGE

## 1. OWNERSHIP & SCOPE
- **Owner:** SHARED (transient storage only)
- **Purpose:** Temporary holding for intermediate JSON artifacts between phases; purged after downstream VERIFICATION = PASS
- **Allowed Files:** Only JSON artifacts produced by P1/P2/P3 during active phase execution
- **FORBIDDEN FILES:** Any .py, .md, schema files, planning docs, or non-artifact content

## 2. HARD STOP CONDITIONS (MANDATORY)
Agent MUST HALT and report BLOCKED if ANY of these are true:
- Upstream phase VERIFICATION.md state != PASS
- Artifact lacks required provenance metadata fields
- Artifact fails validation against corresponding contracts/*.schema.json
- Mock artifact presented without mock_status=MOCK tag
- Agent asked to store non-JSON or non-artifact content
- Downstream consumer has not yet consumed artifact within same branch

## 3. INPUT CONTRACT
- **Required Artifacts:** Produced exclusively by authorized upstream phase owner
- **Schema Validation:** Mandatory pre-storage validation against contracts/*.schema.json
- **Preconditions:** Producing phase CP[N] = APPROVED
- **Mock Protection:** If input contains mock_status=MOCK -> store ONLY if current phase = 01-mock-pipeline; else REJECT

## 4. OUTPUT CONTRACT
- **Produced Artifact:** N/A (this folder consumes, does not produce)
- **Provenance Metadata (REQUIRED in stored artifact):**
  - producer: [P1|P2|P3]
  - mock_status: MOCK | VERIFIED-REAL | STALE
  - contract_version: [sha of schema used]
  - generation_commit: [git sha of producing commit]
  - phase_checkpoint: [CP1|CP2|CP3|CP4|CP5|CP6]

## 5. SECURITY BOUNDARIES
- Never deserialize or execute contents of stored artifacts
- Never expose artifact contents to network or external services
- Fail CLOSED on malformed JSON -> delete partial file, report FAIL

## 6. WHEN THIS FOLDER IS USED IN PIPELINE
- **Phase:** 01-05 (transient); 06 (final outputs only)
- **Trigger:** After upstream CP[N] = PASS
- **Consumed By:** Next phase owner per PROJECT.md pipeline flow
- **Transition Rule:** MOCK artifacts auto-deleted upon real producer VERIFIED-REAL confirmation; NEVER relabel
