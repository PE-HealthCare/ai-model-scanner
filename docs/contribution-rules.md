# Contribution Rules

## Ownership

- `src/p1_static_engine/` → Person 1
- `src/p2_behavioral_risk/` → Person 2
- `src/p3_ml_dashboard/` → Person 3

## Common

`src/common/` is shared infrastructure only. Put only genuinely reusable, project-wide utilities there. Do not put static-analysis, behavioral, ML, risk, or dashboard logic in `common/`.

Before changing `src/common/`, verify the functionality does not belong in an ownership folder and inform the other contributors.

## Contracts

Changes to `contracts/` require team agreement because they affect cross-module communication.

## Phases

Implement work according to the active phase plan. Do not advance to the next phase until the current `VERIFICATION.md` gate passes.
