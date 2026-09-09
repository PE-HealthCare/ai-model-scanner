# START HERE

This repository already contains the project architecture. You do **not** need to read every Markdown file before starting work.

## 1. Know your ownership

- **P1:** `src/p1_static_engine/`
- **P2:** `src/p2_behavioral_risk/`
- **P3:** `src/p3_ml_dashboard/`

Keep feature-specific code inside your assigned folder.

## 2. Check the current phase

Read:
- `.planning/ROADMAP.md`
- `.planning/STATE.md`

Then read **only** the `PLAN.md` and `VERIFICATION.md` for the current phase.

## 3. Read the essentials

Before coding, read:
- `README.md`
- `docs/solution-architecture.md`
- `docs/contribution-rules.md`
- your current phase `PLAN.md`

You do not need to study all planning documents first.

## 4. Start with the current phase

Implement only what the current phase requires.

Do not build the entire pipeline at once. Make the smallest working implementation first, then improve it within the phase.

## 5. Respect the contracts

Module communication is defined by:

`contracts/`

The main contracts are:
- `features.schema.json`
- `ml_results.schema.json`
- `risk_results.schema.json`

Do not change a shared contract casually. Coordinate schema changes with the team.

## 6. Keep `common/` small

`src/common/` is shared infrastructure, not a fourth ownership area.

Only genuinely reusable, project-wide utilities belong there. Static-analysis, behavioral, ML, or dashboard logic belongs in the appropriate owner folder.

## 7. Verify your work

When implementation is complete, run the checks described in the current phase's `VERIFICATION.md`.

**Do not move to the next phase until the current phase passes verification.**

## 8. Keep `main` stable

`main` is the stable branch.

Development should happen on the team's agreed working branch. Only tested and verified work should be merged into `main`.

## 9. If you are using an AI coding agent

Give the agent:
1. Your ownership area.
2. The current phase.
3. The relevant `PLAN.md`.
4. The relevant `VERIFICATION.md`.

Tell it to inspect the existing code first, implement only the current phase, respect the contracts and ownership rules, and run verification before declaring the work complete.

Do **not** ask the agent to redesign the architecture unless the team explicitly decides that a change is necessary.
