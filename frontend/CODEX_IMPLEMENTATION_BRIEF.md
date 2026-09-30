# SIGTENSOR --- Codex UI Implementation Brief

## Goal

Build the production SIGTENSOR frontend inside the repository's
`frontend/` folder.

SIGTENSOR is not meant to look like a generic Streamlit dashboard. It
should feel like a polished, forensic AI-security product: minimal,
technical, high-confidence, visually distinctive, and easy to understand
during a fast hackathon demo. The interface should make the depth of the
backend visible without overwhelming the operator.

The repository itself is the implementation truth. Before building the
UI, inspect the current backend architecture, contracts, outputs,
branches/files available in the working tree, and existing integration
points. The backend may have evolved since the UI specification was
written: stages may have been renamed, combined, removed, or added;
fields may differ; and newer outputs may now exist. Understand the
current system first, then implement the UI around what actually exists.

Do not blindly force an older UI concept onto a newer backend.

## Reference package

Use the material under:

``` text
ui-reference/
│
├── UI_SPECIFICATION.md
├── CODEX_IMPLEMENTATION_BRIEF.md
├── previews/
│   ├── page-01-landing.png
│   ├── page-02-intake.png
│   ├── page-03-static.png
│   ├── page-04-explainability.png
│   ├── page-05-behavior.png
│   ├── page-06-risk.png
│   └── page-07-report.png
│
└── assets/
    ├── hero/
    │   ├── hand-left.png
    │   ├── hand-right.png
    │   ├── hands-both.png
    │   ├── hero-dot-field.png
    │   ├── sigtensor-full-dark.png
    │   └── sigtensor-mark-dark.png
    │
    └── shared/
        ├── mesh-left.png
        ├── mesh-right.png
        └── mesh-full.png
```

Treat these references intelligently rather than literally.

`UI_SPECIFICATION.md` captures the intended product content, page
purpose, interactions, states, terminology, visual system, and backend
information that would be useful to expose.

The preview images are **composition references**, not screenshots to
reproduce pixel-for-pixel. They communicate the desired visual family:
spacing, information density, typography, card hierarchy,
forensic/technical character, mesh placement, charts, and overall page
rhythm. Some previews may contain stale navigation, illustrative values,
missing interactions, incorrect logos, old wording, imperfect colors,
non-glass cards, or other design inferences that were never intended to
become requirements. Resolve those intelligently using the
specification, approved assets, current backend, and the overall product
goal.

The supplied assets are the actual design assets. Prefer them over
approximations visible inside previews. In particular, use the supplied
SIGTENSOR branding rather than recreating a logo from a preview.

## Product experience

Create one coherent seven-page experience:

``` text
NEW SCAN
INTAKE
STATIC
EXPLAINABILITY
BEHAVIOR
RISK
REPORT
```

Each page should have enough room to communicate its own stage. Do not
cram multiple substantial stages together merely because an older
preview or navigation concept grouped them.

The narrative should naturally feel like:

``` text
Upload
  ↓
Safely understand the artifact
  ↓
Inspect the weights
  ↓
Explain relevant evidence
  ↓
Test behavior / bounded trigger evidence when applicable
  ↓
Fuse authoritative evidence into risk
  ↓
Produce a traceable final assessment
```

If the current backend has evolved from this exact sequence, adapt the
UI intelligently. Preserve the user's mental model while accurately
representing the real pipeline. A genuinely new backend stage or
valuable output should not be hidden simply because an older mockup does
not show it. Likewise, do not keep a dead UI section for a backend
component that no longer exists.

## Visual direction

The landing page is the visual hook. Pages after it become more
information-dense, but all seven pages must unmistakably belong to the
same product.

Use the approved SIGTENSOR visual language from the specification:
chalk/light canvas, strong near-black typography, fine structural
borders, restrained monochrome surfaces, technical mono labels, subtle
dotted/mesh/steganographic fields, and semantic color only where it
communicates an actual state.

The landing page should feel more cinematic than the analytical pages.
Use the supplied hero hands/dot field and approved logo assets. The
central upload surface should have the intended refined **glassmorphic**
quality rather than becoming a plain opaque Streamlit card. Preserve the
visual interaction between the hands and upload surface when
implementing the composition.

Pages 2--7 should share a reusable shell: navigation, page spacing, card
geometry, typography, borders, background mesh treatment, status
language, expansion behavior, and chart styling. Their data
visualizations can differ according to the analysis being shown.

Use the supplied `mesh-left`, `mesh-right`, or `mesh-full` artwork where
appropriate as low-priority structural decoration. It should support the
interface, never compete with evidence.

The interface should look intentional at normal laptop/demo resolutions
and degrade sensibly at narrower widths.

## Build a real interface, not a static mockup

The previews show only snapshots. The implemented product should include
the interactions that make sense for the actual system even when a
preview cannot show them.

That includes, where useful:

-   expandable evidence/detail cards;
-   dialogs or popovers for deeper evidence;
-   layer selection and drill-down;
-   hover/tooltips for graphs;
-   stage-progress states;
-   loading and processing states;
-   architecture/intake failure details;
-   evidence trace navigation;
-   assumptions/limitations expansion;
-   validation details;
-   report/export actions;
-   empty, unavailable, skipped, blocked, failed, and limited-assessment
    states.

Keep the default view disciplined. The product philosophy is:

> **Less visible content, not less available content.**

The first screen of a page should answer the page's main question.
Technical depth should be one interaction away rather than permanently
dumped onto the canvas.

## Backend integration

Do not build the UI around hardcoded demo numbers.

Inspect the backend first and identify what it currently exposes. Wire
the UI to real outputs wherever possible.

The UI should expose useful intermediate evidence, not only the final
verdict. If the backend already computes values that improve technical
understanding---per-layer statistics, distributions, calibration
observations, probe results, trigger repetitions, timing, provenance,
validation state, contribution ledgers, evidence IDs, hashes, or other
meaningful outputs---surface them appropriately through cards, graphs,
expandable details, or the final report.

If a visualization or important UI state requires a small, sensible
backend change to expose data that the backend already computes
internally, it is acceptable to make that integration change. Prefer
exposing existing computation cleanly over duplicating security logic in
the frontend.

If the current backend contains newer architecture or outputs not
anticipated by the specification, understand their meaning and
incorporate them where they genuinely improve the product.

If something described in the UI specification was dropped from the
backend, do not fake it. Adapt the UI to the current architecture and
preserve the intent of the page.

Avoid redesigning core detection algorithms merely to satisfy a mockup.
Backend changes should primarily improve clean exposure, serialization,
provenance, or frontend integration unless the repository itself clearly
requires something else.

## Evidence and security semantics

The frontend is a presentation and investigation layer over the scanner,
not a second security engine.

Where the backend has authoritative concepts---final score, verdict,
evidence applicability, selected/highest-risk layer,
trigger-verification result, contribution ledger, stage status,
validation state---prefer the backend's result rather than independently
creating a competing interpretation in the frontend.

Never fabricate observations just to complete a graph. Missing evidence
should produce an honest state rather than a plausible-looking zero or
synthetic series.

Preserve distinctions such as:

-   unavailable versus zero;
-   skipped versus not applicable;
-   blocked intake versus security failure;
-   scan completion versus security verdict;
-   advisory evidence versus scored evidence;
-   bounded trigger-consistent evidence versus universal backdoor
    confirmation;
-   no evidence found within tested scope versus a guarantee of safety.

Use the current backend and specification together to determine the
exact terminology.

The architecture previously treated LightGBM/TreeSHAP as advisory rather
than authoritative MRS evidence. Verify the current backend before
implementation. If that remains the architecture, make the separation
visually and structurally obvious. If the backend has legitimately
changed, represent the current validated architecture accurately rather
than preserving stale UI text.

## Data visualization

Choose visualizations because they communicate actual evidence, not
because every page needs a chart.

Examples of useful mappings include:

-   intake → structure, coverage, stage timing, resource/provenance
    summaries;
-   static analysis → layer × feature heatmap, selected-layer
    distribution, bit/statistical evidence, ranked evidence;
-   explainability → contribution/waterfall-style views and feature
    attribution;
-   behavior → probe distributions, baseline comparisons, repetition
    consistency, clean-vs-trigger comparisons;
-   risk → authoritative contribution waterfall / evidence fusion;
-   report → concise assessment, traceable findings, assurance, scope,
    integrity and exports.

These are design directions, not mandatory graph quotas. Use what the
current backend can support truthfully.

Graphs should share the same visual system and remain readable during a
presentation.

## Page 7

Treat the final report as the scanner's **audit certificate**, not
merely another analytics page.

It should quickly communicate the final assessment, the strongest
traceable findings, advisory evidence where relevant, detector
assurance/validation state, scope and limitations, integrity/provenance,
and export actions.

Where supported, findings should connect back to their underlying
evidence and earlier investigation pages.

The downloaded report/evidence should be consistent with what the UI
displays. Prefer one finalized assessment/report representation over
independently reconstructing the result from stale stage files.

## Streamlit implementation

Use Streamlit as the application framework, but do not accept default
Streamlit aesthetics where custom layout/CSS/components are needed to
achieve the intended product quality.

Create reusable components and shared styling instead of duplicating
page-specific HTML/CSS everywhere.

Keep application state coherent across navigation so one scan flows
through the whole interface. Preserve scan identity and evidence
identity across pages.

Use native Streamlit behavior where it is sufficient; use carefully
scoped HTML/CSS or supported interactive patterns where necessary for
the design. Keep the implementation maintainable.

## How to work

Start by auditing the repository and the `ui-reference` package.

Understand:

1.  the actual current backend pipeline;
2.  the current data contracts and artifacts;
3.  what intermediate/final values already exist;
4.  what small backend exposure changes would materially improve the UI;
5.  the existing frontend/Streamlit structure, if any;
6.  the approved visual assets;
7.  the page specification and preview intent.

Then design the shared shell and data adapters before filling every
page.

Implement the real flow end-to-end rather than polishing one isolated
screenshot while other pages remain disconnected.

Use your judgment. If the specification, a preview, and the current
backend disagree, investigate why and choose the implementation that
best satisfies the **current scanner architecture, factual correctness,
coherent UX, and intended SIGTENSOR visual identity**. Do not preserve
stale material simply because it exists in a reference file.

At the end, verify the application as a complete product: navigation,
scan lifecycle, real-data rendering, failure states, responsive layout,
expandable details, graphs, semantic states, evidence traceability,
report consistency, and asset usage.

The desired result is a UI that makes judges immediately understand two
things:

> **SIGTENSOR has a serious technical backend.**

and

> **The interface makes that backend understandable, inspectable, and
> auditable without exaggerating what it proves.**
