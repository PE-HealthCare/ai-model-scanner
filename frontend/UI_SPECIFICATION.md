# SIGTENSOR — UI Specification

**Status:** Authoritative pre-Codex UI specification  
**Project:** Precision Care Challenge 2026 — detection of steganographic or anomalous evidence in AI model weights  
**Implementation:** Python + Streamlit  
**Demo focus:** VISION / ResNet18 / `.safetensors`

---

## 1. Purpose of this specification

This file is the authoritative UI specification for implementing SIGTENSOR.

It defines:

- the seven-page judge-facing product flow;
- the visual system and semantic color rules;
- the page-by-page content hierarchy;
- progressive disclosure and interaction behavior;
- how the frontend should consume backend data;
- the backend outputs that should be exposed for useful visualizations;
- unavailable, blocked, skipped, failed, and limited states;
- report/evidence traceability expectations;
- rules that prevent the frontend from inventing or overclaiming evidence.

The intent is not to reproduce screenshots literally. The interface should feel coherent, polished, forensic, and technically credible while remaining understandable during a short hackathon demo.

The product principle is:

> **Less visible content, not less available content.**

Each analytical page should answer one primary question, show two or three supporting pieces of evidence, and keep deep engineering detail behind expansion, tabs, dialogs, or evidence drill-down.

---

# 2. Frozen product decisions

## 2.1 Runtime and supported model

The application is a one-file scanning flow.

The user uploads one `.safetensors` artifact.

The current build supports:

```text
Domain        VISION
Architecture  ResNet18
Format        .safetensors
```

There is **no architecture selector**.

There is **no domain selector**.

There is **no precision selector**.

Architecture, domain, precision, and quantization state are backend-detected and authoritative.

The scanner validates the uploaded tensor structure against the trusted ResNet18 implementation.

No uploader-supplied code is executed.

If the artifact does not match the trusted ResNet18 tensor structure, intake stops. This is an **architecture mismatch / unsupported intake state**, not a security FAIL verdict.

A clean external reference model is not required during normal runtime scanning.

---

## 2.2 Seven-page navigation

The product has seven distinct pages:

```text
NEW SCAN
INTAKE
STATIC
EXPLAINABILITY
BEHAVIOR
RISK
REPORT
```

Mapping:

| Navigation | Destination |
|---|---|
| **NEW SCAN** | Page 1 — Landing / Upload |
| **INTAKE** | Page 2 — Intake & Validation |
| **STATIC** | Page 3 — Static Steganalysis |
| **EXPLAINABILITY** | Page 4 — Advisory Explainability |
| **BEHAVIOR** | Page 5 — Behavioral & Trigger Verification |
| **RISK** | Page 6 — Risk & Evidence Fusion |
| **REPORT** | Page 7 — Final Security Report |

Do not group substantial pages together simply because older concepts did so.

The persistent navbar should reflect the seven-page product architecture.

Before a scan exists, later pages may remain visible but muted/disabled.

Once a scan begins, navigation availability should follow the actual scan/stage state.

---

## 2.3 Product narrative

```text
PAGE 1 — NEW SCAN
What model are we scanning?
        ↓
PAGE 2 — INTAKE
Can we safely accept and interpret it?
        ↓
PAGE 3 — STATIC
What unusual statistical evidence exists in the weights?
        ↓
PAGE 4 — EXPLAINABILITY
What features drove the advisory analysis?
        ↓
PAGE 5 — BEHAVIOR
Does the model behave suspiciously?
        └── suspicious → bounded trigger verification
        ↓
PAGE 6 — RISK
What does the validated evidence imply together?
        ↓
PAGE 7 — REPORT
What is the final assessment, and can every claim be traced?
```

---

# 3. Global visual system

## 3.1 Design character

SIGTENSOR should feel like a refined forensic AI-security product rather than a default Streamlit dashboard.

The visual language should be:

- minimal;
- technical;
- high-confidence;
- monochrome-first;
- data-dense only where useful;
- strong hierarchy;
- restrained semantic color;
- fine borders;
- mono metadata labels;
- subtle dot/mesh/steganographic artwork;
- consistent across Pages 2–7.

Landing can be more dramatic and cinematic.

Pages 2–7 should be more analytical, but must remain unmistakably part of the same system.

---

## 3.2 UI colors

| Token | Hex | Purpose |
|---|---:|---|
| `--chalk` | `#f3f3f3` | Main canvas/background |
| `--carbon` | `#080808` | Primary text, strongest hand particles |
| `--obsidian` | `#101010` | Dark surfaces / alternate near-black |
| `--graphite` | `#212121` | Strong borders, controls |
| `--iron` | `#474747` | Secondary structural dark |
| `--smoke` | `#9c9c9c` | Muted text, metadata |
| `--ash` | `#c1c1c1` | Light borders/dividers |
| `--faint-red` | `#e63946` | Payload/tampering signature |
| `--safe-green` | `#3f5f45` | PASS / normal / successful safe operation |
| `--review-amber` | `#a47724` | REVIEW / low-to-moderate concern / caution |
| `--fail-red` | `#9f2f38` | FAIL / high-risk verdict |
| `--info-slate` | `#52606d` | N/A / skipped / informational states |

```css
:root {
  /* Core neutrals */
  --chalk: #f3f3f3;
  --carbon: #080808;
  --obsidian: #101010;
  --graphite: #212121;
  --iron: #474747;
  --smoke: #9c9c9c;
  --ash: #c1c1c1;

  /* Security signature */
  --faint-red: #e63946;

  /* Semantic states */
  --safe-green: #3f5f45;
  --review-amber: #a47724;
  --fail-red: #9f2f38;
  --info-slate: #52606d;

  /* Semantic aliases — components should use THESE */
  --color-bg: var(--chalk);
  --color-text: var(--carbon);
  --color-text-secondary: var(--iron);
  --color-text-muted: var(--smoke);
  --color-border: var(--ash);
  --color-border-strong: var(--graphite);

  --color-pass: var(--safe-green);
  --color-review: var(--review-amber);
  --color-fail: var(--fail-red);
  --color-payload: var(--faint-red);
  --color-na: var(--info-slate);
}
```

---

## 3.3 Semantic color rules

Freeze this mapping:

- **PASS / NORMAL / completed successfully → Safe Green**
- **REVIEW / SUSPICIOUS / INCONCLUSIVE → Review Amber**
- **FAIL / high risk → Fail Red**
- **TRIGGER-CONSISTENT evidence / malicious-payload visualization → Faint Red**
- **NOT_APPLICABLE / NOT_REQUIRED / SKIPPED / informational → Info Slate**
- **Pending / running / analyzing → Graphite/Carbon**

Important:

- red is not decorative;
- green is not decorative;
- amber is not decorative;
- blue/purple should not be introduced as arbitrary semantic colors;
- advisory information should use neutral/info treatment rather than implying risk.

Positive SHAP contribution does **not** automatically mean malicious evidence. Therefore SHAP direction should normally use neutral structural colors unless an independent backend status justifies a risk color.

---

## 3.4 Typography and component language

Use:

- strong sans-serif for primary headings;
- monospaced type for scan IDs, hashes, feature names, evidence IDs, versions, timings, technical values;
- high-contrast Carbon primary text;
- Iron/Smoke secondary metadata;
- fine Ash/Graphite separators;
- consistent icon family;
- consistent card radius and padding;
- restrained shadows.

Avoid generic rainbow security-dashboard styling.

---

## 3.5 Cards and surfaces

Landing upload surface should feel refined and **glassmorphic**:

- translucent light surface;
- soft blur where practical;
- fine Ash/Graphite edge;
- subtle shadow;
- not a plain opaque Streamlit box.

Pages 2–7 may use lightly elevated cards, but keep them calm and consistent.

Large technical pages should rely on grouping and hierarchy rather than dozens of independent KPI cards.

---

## 3.6 Decorative mesh / dot artwork

Use the supplied left/right/full mesh assets as low-priority background structure.

Typical layering:

```css
.page-shell { position: relative; min-height: 100vh; }

.page-shell::before {
  content: "";
  position: absolute;
  inset: 0;
  opacity: 0.10-0.20;
  z-index: 0;
  pointer-events: none;
}

.page-content {
  position: relative;
  z-index: 2;
}
```

The decoration must not reduce readability.

Use Faint Red only on the anomalous/payload side where the visual language intentionally represents suspicious manipulation.

---

# 4. Approved assets

Expected asset package:

```text
assets/
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

Use the supplied assets directly.

Do not recreate the logo from a preview.

Do not regenerate or approximate the hands when the approved assets exist.

The hero hands are conceptual/decorative, not scanner output.

---

# 5. Global interaction philosophy

Each page should follow:

### Level 1 — Judge must see

One primary answer.

Large, obvious, understandable in ~5 seconds.

### Level 2 — Judge should see

Two or three supporting pieces of evidence.

Charts/tables/cards that explain the answer.

### Level 3 — Judge may inspect

Expandable details:

- technical tables;
- exact thresholds;
- model metadata;
- per-layer detail;
- probe detail;
- evidence records;
- assumptions;
- limitations.

### Level 4 — Audit/debug

Deep provenance:

- hashes;
- generation commits;
- detector versions;
- complete repetition matrices;
- raw evidence ledgers;
- contract details.

These remain accessible but must not compete with the primary result.

---

# 6. Canonical execution and evidence states

Execution status and security verdict are separate concepts.

## 6.1 Scan execution

Typical execution states:

```text
SCAN READY
SCAN IN PROGRESS
SCAN COMPLETE
SCAN FAILED
SCAN BLOCKED
```

## 6.2 Security assessment

```text
PASS
REVIEW
FAIL
```

`SCAN COMPLETE` does not mean `PASS`.

---

## 6.3 Canonical stage/data states

The backend/UI contract should distinguish at minimum:

```text
PENDING
RUNNING
COMPLETED
FAILED
BLOCKED
INVALID
UNSUPPORTED
SKIPPED
NOT_REQUIRED
NOT_APPLICABLE
NOT_AVAILABLE
STALE
INCOMPLETE
WITHHELD
```

Missing values are not zero.

`NOT_APPLICABLE`, `NOT_AVAILABLE`, `FAILED`, and `0.0` are different states.

---

# 7. Page 1 — NEW SCAN / Landing

## 7.1 Question

> What model are we scanning?

## 7.2 Default page hierarchy

Persistent navbar:

```text
[SIGTENSOR]

NEW SCAN   INTAKE   STATIC   EXPLAINABILITY   BEHAVIOR   RISK   REPORT
```

Hero headline:

> **Analyze AI weights.**  
> **Detect hidden payloads.**

Supporting copy:

> Inspect a ResNet18 `.safetensors` model for statistical and behavioral evidence of hidden manipulation.

Do not place MRS, PASS/REVIEW/FAIL, LightGBM, TreeSHAP, trigger verification, backdoor terminology, or limitation text in the main hero.

---

## 7.3 Hero artwork

Left label:

```text
expected_distribution
```

Right label:

```text
anomalous_pattern
```

Use the prepared transparent hand assets.

The intended composition is two hands reaching toward the upload surface.

The upload card should overlap the hand composition deliberately; only the intended fingertip interaction should cross behind/under the card.

The hero remains conceptual artwork.

Faint Red may appear only in the anomalous/right-hand manipulation pattern.

---

## 7.4 Upload card

Visible content:

```text
UPLOAD MODEL ARTIFACT

Drop a .safetensors file here
or browse files

ResNet18 only

[ START SCAN ]

.safetensors only · ResNet18 · no uploader-supplied code executed
```

After selection:

```text
resnet18_candidate.safetensors
44.7 MB

[ START SCAN ]
```

Do not show:

- `Use Demo Model`;
- architecture dropdown;
- domain dropdown;
- precision dropdown;
- theme toggle.

---

## 7.5 Expandable explanation

Small interaction:

```text
How does the scan work? →
```

Expanded content:

```text
01 ZERO-TRUST INTAKE
Validate the .safetensors artifact against the trusted ResNet18 structure.

02 STATIC STEGANALYSIS
Inspect model weights layer-by-layer for statistical evidence of hidden manipulation.

03 EXPLAINABILITY
Explain which statistical features influence the advisory model.
LightGBM / TreeSHAP
ADVISORY ONLY · NOT USED IN MRS

04 BEHAVIORAL ANALYSIS
Run bounded perturbation probes and compare responses against the behavioral baseline.

suspicious behavior?
        └── TRIGGER VERIFICATION
            Run bounded candidate trigger tests.

05 RISK FUSION
Combine validated static and applicable behavioral evidence.

MODEL RISK SCORE
0–100

06 FINAL REPORT
Produce a traceable security assessment with evidence, scope, limitations and exportable reporting.
```

---

## 7.6 Landing error states

### Architecture mismatch

```text
ARCHITECTURE MISMATCH

This build supports ResNet18 only.

The uploaded tensor structure does not match
the expected ResNet18 architecture.

View mismatch details →

[ CHOOSE ANOTHER FILE ]
```

Architecture mismatch is not a security FAIL verdict.

### Invalid artifact

```text
INVALID MODEL ARTIFACT

The artifact could not pass intake validation.
No downstream analysis was performed.

[ CHOOSE ANOTHER FILE ]
```

No downstream security result should be invented.

---

# 8. Page 2 — INTAKE & VALIDATION

## 8.1 Question

> Can we safely accept and interpret this artifact?

## 8.2 Frozen hierarchy

Page 2 should be simple.

Use:

1. header + compact artifact strip;
2. one Intake Verdict hero;
3. one Validation Evidence card;
4. one Pipeline/Runtime region.

Do not create separate permanent cards for every backend concept.

---

## 8.3 Header

Eyebrow:

```text
STAGE 01 / INTAKE
```

Heading:

> **Validate before you analyze.**

Supporting copy:

> Verify the artifact and establish a trusted boundary before analysis begins.

Compact artifact strip:

```text
resnet18_candidate.safetensors
44.7 MB · SHA 91A7…D84C · ResNet18 · VISION · FP32
```

---

## 8.4 Intake Verdict hero

Concept:

```text
UNTRUSTED ARTIFACT
        ↓

ZERO-TRUST VALIDATION

SafeTensors      ResNet18      Structure
✓ PARSED         ✓ MATCH       ✓ VALID

UPLOADER CODE: NOT EXECUTED

        ↓

✓ INTAKE VERIFIED
READY FOR ANALYSIS
```

Tiny supporting row:

```text
102 / 102 tensors · FP32 · Quantized: No · Resources: Within limits
```

This one hero communicates:

- valid format;
- expected architecture;
- trusted structure;
- uploader code not executed;
- safe to continue.

---

## 8.5 Validation Evidence

One visible engineering-proof card:

```text
VALIDATION EVIDENCE

CHECK                 EXPECTED        OBSERVED        STATUS
Architecture          ResNet18        ResNet18         MATCH
Tensor count          102             102              MATCH
Tensor names          Trusted schema  Validated        VALID
Tensor shapes         Trusted schema  Validated        VALID
Dtypes                 Trusted schema  Validated        VALID
Resource gate          Within policy   Accepted         VALID

View technical details →
```

Expanded technical details may include:

- complete tensor names;
- expected vs observed shapes;
- dtypes;
- missing/unexpected keys;
- header details;
- actual resource limits;
- observed resource measurements;
- layer count;
- full SHA;
- provenance identifiers.

---

## 8.6 Pipeline and runtime

Compact status flow:

```text
01 INTAKE ── 02 STATIC ── 03 EXPLAIN ── 04 BEHAVIOR ── 05 FUSION ── 06 REPORT
   DONE          RUNNING       PENDING       PENDING        PENDING      PENDING
```

Tiny timing strip:

```text
INTAKE 0.42s · STATIC 2.81s · ELAPSED 3.23s · PEAK 318 MB
```

Integrity badge:

```text
CURRENT GENERATION
```

Deep action:

```text
Scan details →
```

Expanded scan details may contain:

- stage timings;
- per-stage memory;
- generation commit;
- contract version;
- producer;
- mock/real status;
- provenance chain.

---

## 8.7 Failure variants

If intake fails, the failure becomes the hero.

Example:

```text
INTAKE BLOCKED

RESOURCE LIMIT EXCEEDED

Observed       612 MB
Allowed        500 MB

Downstream analysis was not run.
```

Show complexity only when relevant.

---

# 9. Page 3 — STATIC STEGANALYSIS

## 9.1 Question

> What unusual statistical evidence exists inside the weights?

## 9.2 Header

Eyebrow:

```text
STAGE 02 / STATIC STEGANALYSIS
```

Heading:

> **Inspect what the weights reveal.**

Supporting copy:

> Analyze each layer for statistical patterns associated with hidden manipulation.

Status:

```text
STATIC ANALYSIS COMPLETE
```

or:

```text
ANALYZING WEIGHTS
```

Compact context:

```text
resnet18_candidate.safetensors
ResNet18 · VISION · FP32 · 102 layers · Scan S-0241
```

---

## 9.3 Primary visual — Layer Evidence Map

Title:

```text
LAYER EVIDENCE MAP
```

Supporting line:

> Compare static indicators across the model. Select any cell or layer to investigate further.

Rows:

```text
conv1
layer1...
layer2...
layer3...
layer4...
fc
```

Grouped columns:

```text
STEGANOGRAPHIC SIGNALS
Entropy | PoV χ² | LSB-KL | KS

DISTRIBUTION SHAPE
Mean | Std | Skew | Kurtosis

STRUCTURAL STATISTICS
Sparsity | Outlier %
```

Use Faint Red only when backend-defined presentation logic marks evidence as anomalous.

Clicking a row/cell updates the selected-layer investigation panel.

---

## 9.4 Evidence summary strip

Under the heatmap:

```text
HIGHEST-RISK LAYER
layer4.1.conv2

STRONGEST INDICATORS
LSB-KL · PoV χ² · Entropy

LAYERS FLAGGED
3 / 102
```

Only show concepts that actually exist in the backend.

If flagged-layer count does not exist, omit it.

---

## 9.5 Selected Layer Investigation

Title:

```text
SELECTED LAYER / layer4.1.conv2
```

Optional tiny navigator:

```text
conv1 → layer1 → layer2 → layer3 → [layer4] → fc
```

Tabs:

```text
OVERVIEW | DISTRIBUTION | BIT EVIDENCE | RAW STATISTICS
```

### Overview

Possible radar/spider view with 5–6 meaningful indicators:

- entropy;
- PoV χ²;
- LSB-KL;
- KS;
- sparsity;
- outlier %.

Beside it, show backend-supported explanation:

```text
WHY THIS LAYER STANDS OUT
```

Do not manufacture comparative claims.

### Distribution

Show selected-layer distribution.

Only show baseline/reference distribution if a real comparison exists.

Never create a synthetic clean Gaussian for appearance.

### Bit Evidence

Only show if backend exposes real bit-level evidence.

Possible:

- LSB zero/one frequency;
- pair-of-values counts;
- bit-position entropy;
- other genuine bit-level arrays.

If unavailable:

```text
Bit-level detail not available for this scan.
```

### Raw Statistics

Technical table:

```text
entropy
pov_chi2
lsb_kl
ks_stat
mean
std
skewness
kurtosis
sparsity
outlier_pct
```

Optional if real:

- shape;
- dtype;
- parameter count;
- robust z;
- median;
- MAD.

---

# 10. Page 4 — EXPLAINABILITY

## 10.1 Question

> Which statistical features drove the advisory model response?

## 10.2 Header

Eyebrow:

```text
STAGE 03 / EXPLAINABILITY
```

Heading:

> **Explain the advisory response.**

Supporting copy:

> See which statistical features pushed the advisory model output higher or lower.

Status:

```text
EXPLAINABILITY AVAILABLE
```

or:

```text
EXPLAINABILITY NOT AVAILABLE
```

Do not use PASS/FAIL/SUSPICIOUS as Page 4 status.

---

## 10.3 Advisory banner

Always visible:

```text
ADVISORY ONLY

LightGBM / TreeSHAP explains an auxiliary model response.
It does not contribute to MRS or the final PASS / REVIEW / FAIL verdict.
```

Use Info Slate / neutral styling.

---

## 10.4 Primary visual — Feature Contribution

Title:

```text
FEATURE CONTRIBUTION
```

Use SHAP-style contribution/waterfall logic from actual backend values.

Concept:

```text
BASE VALUE

LSB-KL       +...
Entropy      +...
PoV χ²       +...
KS           +...
Sparsity     -...
Kurtosis     -...

ADVISORY OUTPUT
```

Actual values must come from:

```text
expected_value
feature_value
shap_value
raw_output
```

Positive SHAP is not automatically payload evidence.

---

## 10.5 Compact interpretation strip

Examples:

```text
TOP UPWARD DRIVER
LSB-KL

NEXT
Entropy

STRONGEST DOWNWARD DRIVER
Sparsity
```

No need for a redundant second contribution chart.

---

## 10.6 Selected Feature panel

Title:

```text
SELECTED FEATURE / LSB-KL
```

Tabs:

```text
EXPLANATION | ALL FEATURES | MODEL DETAILS
```

Default:

```text
OBSERVED VALUE
...

SHAP CONTRIBUTION
...

DIRECTION
Raised advisory output
```

Plain-English wording should explain influence without claiming causality or malware proof.

### Model Details

May expose:

- model version;
- model hash;
- training corpus ID;
- training sample count;
- validation state;
- expected/base value;
- raw advisory output.

If detector-level validation is not established, state that clearly.

---

# 11. Page 5 — BEHAVIORAL & TRIGGER VERIFICATION

## 11.1 Question

> Did the model behave abnormally under probing, and did bounded trigger testing reproduce that behavior?

## 11.2 Header

Eyebrow:

```text
STAGE 04 / BEHAVIOR
```

Heading:

> **Test how the model behaves.**

Supporting copy:

> Compare bounded perturbation responses against the behavioral baseline and verify suspicious behavior when required.

Top-right state:

```text
BEHAVIOR NORMAL
BEHAVIOR SUSPICIOUS
BEHAVIOR NOT APPLICABLE
```

Quantized path should show `NOT APPLICABLE`, not FAILED or zero.

---

## 11.3 Primary visual — Behavioral Response

Title:

```text
BEHAVIORAL RESPONSE
```

Supporting line:

> Compare the current model's probe responses against the calibrated baseline distribution.

Preferred visual:

- baseline observations as neutral points/distribution;
- baseline median;
- accepted/calibrated band if backend supplies one;
- threshold only if backend supplies it;
- current model as a stronger marker.

Compact summary:

```text
STATUS
SUSPICIOUS

OBSERVED SCORE
...

BASELINE MEDIAN
...

DEVIATION
...
```

Only show fields actually produced.

---

## 11.4 Probe Evidence

One card with tabs:

```text
OVERVIEW | PROBE MATRIX | TECHNICAL DETAILS
```

### Overview

Show actual probe-level data if available.

Summary can include:

- probe count;
- repetition count;
- baseline median;
- observed median;
- status.

### Probe Matrix

Only if backend exposes probe × repetition values.

Do not synthesize a matrix.

### Technical Details

May show:

- calibration mean;
- median;
- std;
- threshold;
- sample count;
- aggregate statistics;
- deviation from baseline;
- probe IDs;
- perturbation type;
- repetition counts.

---

## 11.5 Conditional Trigger Verification

This region appears only if:

1. behavioral screening is suspicious; and
2. backend actually executed trigger verification.

Header:

```text
TRIGGER VERIFICATION ACTIVATED
```

Supporting line:

> Suspicious behavioral deviation triggered bounded candidate testing.

Preferred default comparison:

```text
CLEAN CONDITION          TRIGGERED CONDITION
Response                 Response
...                      ...

Consistency              Consistency
...                      ...
```

Summary:

```text
CANDIDATES TESTED
...

REPETITIONS
...

RESPONSE CONSISTENCY
...

FINAL RESULT
...
```

Canonical final result examples:

```text
NO_TRIGGER_EVIDENCE_FOUND
INCONCLUSIVE
TRIGGER_CONSISTENT_EVIDENCE
```

Do not relabel this as `BACKDOOR DETECTED` unless the current backend explicitly supports that stronger conclusion.

Trigger details should be expandable.

---

## 11.6 Quantized behavior state

If behavior is not applicable:

```text
Behavioral analysis not applicable

This precision path does not run behavioral probing
for the current model representation.

MODEL
Quantized

BEHAVIOR
NOT APPLICABLE

REASON
<backend-provided reason>
```

Do not show a blank graph.

---

# 12. Page 6 — RISK & EVIDENCE FUSION

## 12.1 Question

> Given the validated evidence, what does the scanner conclude?

## 12.2 Header

Eyebrow:

```text
STAGE 05 / RISK FUSION
```

Heading:

> **Combine the evidence.**

Supporting copy:

> See how validated static and behavioral evidence contributes to the final Model Risk Score.

Status:

```text
RISK ASSESSMENT COMPLETE
```

Context:

```text
resnet18_candidate.safetensors
ResNet18 · VISION · FP32 · Scan S-0241
```

---

## 12.3 Primary result — Model Risk Score

Large central result:

```text
MODEL RISK SCORE

61 / 100

REVIEW
```

Interpretation:

> Validated evidence places this model in the REVIEW range.

Threshold band should use semantic state colors.

Current hackathon contract:

```text
PASS      0–34
REVIEW    35–69
FAIL      70–100
```

The backend is authoritative for `mrs` and `verdict`.

The frontend must not independently recompute the verdict from a rounded display score.

---

## 12.4 Primary visual — How the Score Was Built

Use one contribution waterfall.

Concept:

```text
STATIC EVIDENCE       +...
BEHAVIORAL EVIDENCE   +...
────────────────────────
MODEL RISK SCORE       ...
```

Values must come from the backend contribution ledger.

For a quantized path:

```text
STATIC EVIDENCE       +...
BEHAVIORAL EVIDENCE   N/A
────────────────────────
MODEL RISK SCORE       ...
```

Do not display behavioral contribution as zero when it is not applicable.

---

## 12.5 Evidence Summary

One card:

```text
STATIC
Highest-risk layer: ...
Strongest indicators: ...

BEHAVIOR
Status: ...
Trigger result: ...
```

For normal behavior:

```text
Trigger verification: NOT REQUIRED
```

For quantized:

```text
BEHAVIOR
N/A

Reason
<backend-provided reason>
```

---

## 12.6 Deep action

```text
Why this score? →
```

Expanded details may show:

- exact static contribution;
- exact behavioral contribution;
- formula ID;
- formula version;
- threshold version;
- behavior applicability;
- trigger effect;
- missing/N/A evidence;
- score generation metadata.

Do not make the exact equation the dominant default visual.

---

## 12.7 Incomplete risk state

If required evidence is unexpectedly unavailable:

```text
RISK ASSESSMENT INCOMPLETE

Required evidence for the configured fusion path is unavailable.

STATIC
AVAILABLE

BEHAVIOR
NOT AVAILABLE

MRS
WITHHELD
```

Do not silently calculate around missing evidence.

---

# 13. Page 7 — FINAL SECURITY REPORT

## 13.1 Question

> What should the operator conclude, what evidence supports that conclusion, and can every claim be traced?

Page 7 is the scanner's **audit certificate**, not another analytics dashboard.

The default screen has three major regions:

```text
FINAL ASSESSMENT
→ TRACEABLE FINDINGS
→ ASSURANCE & EXPORT
```

---

## 13.2 Header

Eyebrow:

```text
STAGE 06 / FINAL REPORT
```

Finalized heading:

> **From evidence to assessment.**

Supporting copy:

> Review the final security assessment, trace every conclusion to its evidence, and export the complete report.

Top-right:

```text
REPORT READY
All required evidence for this assessment has been finalized.
```

If important evidence is missing:

```text
ASSESSMENT LIMITED
```

Do not fake a complete report.

---

## 13.3 Artifact strip

```text
resnet18_candidate.safetensors

SHA 91A7…D84C · ResNet18 · VISION · FP32
Scan S-0241 · Report R-0241
```

Do not repeat all Intake details.

---

## 13.4 Region 1 — Final Assessment

Left:

```text
FINAL ASSESSMENT

61 / 100

REVIEW
```

Interpretation should be deterministic from backend states.

Possible state rows:

```text
STATIC          ELEVATED
BEHAVIOR        SUSPICIOUS
TRIGGER         TRIGGER_CONSISTENT_EVIDENCE
```

or:

```text
STATIC          LOW
BEHAVIOR        NORMAL
TRIGGER         NOT REQUIRED
```

Do not use “Backdoor confirmed.”

---

## 13.5 Evidence Trail

Compact trace:

```text
UPLOAD
VALIDATION
STATIC
EXPLAINABILITY   ADVISORY
BEHAVIOR
TRIGGER VERIFY
FUSION
REPORT
```

Each meaningful node should navigate back to the relevant evidence page/state where practical.

This is navigation + traceability, not decoration.

---

## 13.6 Region 2 — Key Findings

One wide card with three internal columns.

### Static Evidence

Show only the most important scan-specific facts:

```text
STATIC EVIDENCE
ELEVATED

Highest-risk layer
layer4.1.conv2.weight

Strongest indicators
LSB-KL
PoV χ²
Entropy

View layer evidence →
```

### Behavior + Trigger

```text
BEHAVIOR
SUSPICIOUS

Trigger verification
EXECUTED

Result
TRIGGER_CONSISTENT_EVIDENCE

Candidate family
<if returned>

Response consistency
<if returned>

View behavioral evidence →
```

### Advisory Explainability

Keep deliberately separate:

```text
ADVISORY EXPLAINABILITY

LightGBM / TreeSHAP
AVAILABLE

Top drivers
...

ADVISORY ONLY
Not used in MRS
```

That final line is essential when this remains the current backend role.

---

## 13.7 Region 3 — Assurance, Scope & Export

### Detector Assurance

Show factual status, not invented accuracy:

```text
DETECTOR ASSURANCE

Static detector
HELD-OUT VALIDATION      VERIFIED / NOT ESTABLISHED

OOD evaluation
REPORTED / NOT AVAILABLE

Behavioral calibration
VERIFIED / NOT ESTABLISHED

Trigger verifier
VALIDATED / EXPERIMENTAL

Benchmark
<benchmark ID>
```

### Scope & Limitations

Default view:

```text
DETECTION SCOPE

Supported build
ResNet18 · SafeTensors

Behavioral scope
Bounded Vision probes + bounded trigger families

PASS meaning
No evidence found within tested scope — not guaranteed safe

View assumptions & limitations →
```

### Integrity & Export

```text
EVIDENCE INTEGRITY

Artifact SHA       ...
Generation         CURRENT
Contract           MATCHED
Report SHA         ...
```

Actions:

```text
Download Security Report — PDF
Download Evidence — JSON
```

Optional later:

```text
Download Evidence Bundle
```

---

# 14. Final report / PDF structure

The PDF is an evidence dossier, not a screenshot of the UI.

Recommended sections:

| PDF section | What it proves |
|---|---|
| **1. Executive Security Assessment** | Verdict, MRS, interpretation, artifact identity, assessment state |
| **2. Intake & Trust Boundary** | SafeTensors validation, ResNet18 match, uploader code not executed, quantization/domain/precision |
| **3. Static Forensic Evidence** | `S_static`, highest-risk layer, strongest real indicators, selected-layer evidence |
| **4. Advisory Explainability** | LightGBM/TreeSHAP output, SHAP drivers, model/version, advisory-only disclaimer |
| **5. Behavioral & Trigger Evidence** | Screening result, calibration, trigger status, candidates/repetitions/consistency where available |
| **6. Risk Fusion & Detector Assurance** | Authoritative contribution ledger, thresholds, formula/version, validation/OOD/calibration state |
| **7. Scope, Limitations & Provenance** | Coverage, unsupported areas, PASS semantics, hashes, versions, timestamps |

Appendices:

```text
A — Complete Layer Evidence Table
B — Probe / Trigger Evidence
C — Benchmark & Validation Metrics
D — Evidence IDs / Provenance Ledger
```

Do not show validation metrics that do not exist.

---

# 15. Backend → UI Exposure Contract

The backend should expose more than the final verdict.

Every intermediate value useful for understanding, plotting, explaining, validating, or auditing the scan should be available in a structured contract when the backend actually computes it.

The frontend must never manufacture security evidence.

---

## 15.1 Universal stage envelope

Where practical, stage outputs should include:

```text
status
reason_code
reason_message
started_at
completed_at
duration_ms
evidence_ids[]
```

Every result should be tied to:

```text
scan_id
artifact_id / artifact_sha256
analysis_version
contract_version
generation_id or generation_commit
```

---

## 15.2 Page 1 backend exposure

Useful fields:

```text
scan_id
artifact_filename
artifact_size_bytes
upload_status
validation_start_status
supported_architecture
supported_format

status
reason_code
reason_message
details
```

Canonical intake/upload outcomes may include:

```text
READY
UPLOADING
ACCEPTED
INVALID
UNSUPPORTED
BLOCKED
ARCHITECTURE_MISMATCH
FAILED
```

The frontend must not infer architecture from filename.

---

## 15.3 Page 2 backend exposure

### Artifact identity

```text
scan_id
artifact_id
artifact_filename
artifact_size_bytes
artifact_sha256
submitted_at
analysis_started_at
format
architecture
input_domain
precision
is_quantized
```

Optional:

```text
provenance_status
source_type
producer
```

### SafeTensors / structure validation

```text
header_status
header_parse_time_ms
format_validation_status

tensor_count_observed
tensor_count_expected

tensor_name_check
tensor_shape_check
dtype_check
resource_check
architecture_match_status
```

Detailed mismatch evidence:

```text
missing_keys[]
unexpected_keys[]

shape_mismatches[]
  tensor_name
  expected_shape
  observed_shape

dtype_mismatches[]
  tensor_name
  expected_dtype
  observed_dtype
```

### Resource gate

```text
resource_checks[]
  resource
  observed
  limit
  unit
  status
  reason
```

### Pipeline state

```text
stages[]
  stage_id
  stage_name
  status
  started_at
  completed_at
  duration_ms
  peak_memory_bytes
  reason
```

### Provenance

```text
generation_id
generation_commit
contract_version
producer_version
mock_status
generation_status
```

---

## 15.4 Page 3 backend exposure

Do not return only `S_static`.

Expose per-layer evidence.

```text
static_analysis:
  layers[]
    layer_id
    layer_name
    tensor_name
    shape
    dtype
    parameter_count

    features:
      entropy
      pov_chi2
      lsb_kl
      ks_stat
      mean
      std
      skewness
      kurtosis
      sparsity
      outlier_pct
```

Feature values should ideally carry:

```text
value
status
unit
availability_reason
```

Optional comparison values when genuinely computed:

```text
baseline_value
baseline_median
mad
deviation
robust_z_score
normalized_score
```

Layer summary:

```text
selected_highest_risk_layer
selected_highest_risk_layer_id
selected_highest_risk_score
selected_highest_risk_evidence[]
```

Optional if defined:

```text
layer_rank
layer_status
flagged_layer_count
analyzed_layer_count
```

Histogram support:

```text
distribution:
  bin_edges[]
  counts[]
```

Optional real baseline:

```text
baseline_distribution:
  bin_edges[]
  counts[]
```

Bit evidence when available:

```text
bit_evidence:
  lsb_zero_count
  lsb_one_count
  bit_positions[]
    bit_index
    zero_count
    one_count
    entropy
  pov_pairs[]
```

Static summary:

```text
static_status
s_static
static_summary_status
strongest_evidence[]
evidence_ids[]
```

---

## 15.5 Page 4 backend exposure

```text
explainability:
  status
  advisory_only
  contributes_to_mrs

  model_name
  model_version
  model_hash
  training_corpus_id
  training_sample_count
  validation_status

  expected_value
  raw_output
  output_scale

  shap_attributions[]
    feature_name
    feature_value
    shap_value
    direction

  top_attributions[]
```

Unavailable state:

```text
status
reason_code
reason_message
```

If current architecture still treats this stage as advisory:

```text
advisory_only = true
contributes_to_mrs = false
```

---

## 15.6 Page 5 backend exposure

Behavior:

```text
behavior:
  status
  applicable
  reason
  score
  metric_name
  metric_unit
```

Calibration:

```text
calibration:
  calibration_id
  sample_count
  mean
  median
  std
  threshold
  threshold_direction
  lower_bound
  upper_bound
```

If plotting observations:

```text
baseline_observations[]
```

Probe results:

```text
probes[]
  probe_id
  perturbation_type
  perturbation_parameters
  status

  repetitions[]
    repetition_id
    metric
    output_summary
    duration_ms
```

Aggregate:

```text
aggregate:
  mean
  median
  std
  min
  max
  deviation_from_baseline
```

Trigger verification:

```text
trigger_verification:
  executed
  activation_reason
  status

  candidates[]
    trigger_id
    trigger_family
    parameters
    repetitions
    clean_response
    triggered_response
    clean_trigger_separation
    response_consistency
    status
    evidence_ids[]

  final_result
  reason
  candidate_count
  repetition_count
  tested_trigger_families[]
  scope_statement
```

---

## 15.7 Page 6 backend exposure

Risk should be backend-authoritative:

```text
risk:
  assessment_state
  mrs
  verdict

  s_static
  s_behavior_final

  static_contribution
  behavior_contribution

  behavior_applicable
  trigger_effect_applied

  formula_id
  formula_version
  score_version
```

Thresholds:

```text
thresholds:
  pass_max
  review_max
  fail_min
```

Also expose:

```text
score_precision
rounding_rule
threshold_boundary_rule
```

Contribution ledger:

```text
contributions[]
  source_id
  source_name
  raw_score
  contribution
  applicable
  status
  evidence_ids[]
```

Evidence summary:

```text
static_status
behavior_status
trigger_result
highest_risk_layer
strongest_evidence[]
```

Incomplete state:

```text
assessment_state = INCOMPLETE
mrs = null
verdict = null
missing_evidence[]
```

---

## 15.8 Page 7 backend exposure

Page 7 should consume one finalized immutable assessment snapshot.

Concept:

```text
FinalSecurityAssessment

identity
  report_id
  scan_id
  artifact_filename
  artifact_sha256
  architecture
  domain
  precision
  quantization

assessment
  assessment_state
  mrs
  verdict
  interpretation_code
  thresholds
  formula_id
  formula_version
  contributions

static
  status
  score
  highest_risk_layer
  strongest_evidence[]
  evidence_ids[]

explainability
  status
  advisory_only
  model_version
  model_hash
  top_attributions[]
  evidence_ids[]

behavior
  status
  applicable
  score
  calibration_summary
  evidence_ids[]

trigger_verification
  executed
  result
  candidate_family
  response_consistency
  clean_trigger_separation
  evidence_ids[]

validation
  benchmark_id
  static_validation_status
  behavioral_validation_status
  trigger_validation_status
  ood_status
  calibration_status
  metrics_summary

coverage
  supported[]
  partial[]
  not_covered[]

provenance
  generation_commit
  contract_version
  detector_versions
  generated_at
  mock_status
  evidence_bundle_hash

limitations[]

report
  report_sha256
```

Additional page state:

```text
report_ready
assessment_limited
limitation_reasons[]
```

Evidence trail:

```text
stage_trace[]
  stage_id
  status
  started_at
  completed_at
  evidence_ids[]
  result_summary
```

---

# 16. Common Evidence Record

Every important `evidence_id` should resolve to a structured record.

Concept:

```text
EvidenceRecord

evidence_id
scan_id
artifact_id

detector_id
detector_version
engine
category
subcategory

feature_name

observed_value
baseline_value
deviation
normalized_score
confidence
unit

layer_id
layer_name
tensor_name
probe_id
trigger_id

status
limitations[]

generation_commit
analysis_version
created_at
```

Not every field is required for every record.

The same evidence identity should survive:

```text
Page 3 evidence
    ↓
Page 6 contribution
    ↓
Page 7 finding
    ↓
PDF appendix
```

---

# 17. Detector assurance and benchmark exposure

When real validation exists, expose it.

Do not invent headline accuracy.

Possible static validation metrics:

```text
Held-out source models
ROC-AUC
PR-AUC
Precision
Recall
F1
FPR
FNR
```

Where available, separate results by:

- attack family;
- attack strength;
- source model;
- OOD/distributed manipulation.

Possible trigger-verification validation:

```text
Known clean models
Known backdoored models

Backdoor recall
False positive rate
Precision
Trigger verification success

Trigger family results
Held-out image validation
```

If validation is not established:

```text
NOT ESTABLISHED
```

This is preferable to fabricated certainty.

---

# 18. Coverage and limitations

The report may include challenge coverage:

| Capability | Coverage |
|---|---|
| Abnormal weight distributions | SUPPORTED where implemented |
| High entropy / structured weight noise | SUPPORTED where implemented |
| Bit-level / precision evidence | SUPPORTED / PARTIAL according to backend |
| Layer-localized evidence | SUPPORTED |
| Trigger-based behavior | SUPPORTED within tested trigger families |
| Hidden/covert outputs | NOT COVERED if not implemented |
| Clean vs suspicious assessment | SUPPORTED |
| Human-readable explanation | SUPPORTED |
| Model Risk Score | SUPPORTED |

Never claim support that the backend does not implement.

---

# 19. Report integrity

Prefer:

1. create finalized JSON assessment snapshot;
2. canonicalize it;
3. hash it;
4. generate the PDF from the same snapshot.

PDF/report footer may include:

```text
Artifact SHA-256
Report ID
Evidence Bundle SHA-256
Generation Commit
Contract Version
Generated At
```

Page 7, PDF, and JSON should all correspond to the same finalized assessment snapshot.

---

# 20. No frontend inference rule

> **The frontend may format, sort, navigate, and visualize backend evidence, but must not create security evidence, infer a verdict, invent a baseline, manufacture missing graph points, upgrade bounded trigger evidence into a backdoor claim, or treat unavailable values as zero.**

The backend owns security semantics when those semantics exist.

This includes:

- MRS;
- verdict;
- contribution ledger;
- highest-risk layer selection;
- trigger result;
- applicability;
- stage status;
- validation status;
- assessment completeness;
- thresholds.

The frontend may apply deterministic presentation logic that is explicitly part of the contract, but should not create a second independent security engine.

---

# 21. Current advisory isolation

When LightGBM/TreeSHAP remains advisory:

```text
advisory_only = true
contributes_to_mrs = false
```

Page 4 explains the advisory response.

Page 6 must not include it in the MRS contribution waterfall.

Page 7 must visually separate it from scored evidence.

Do not present `P_tamper` as final malware probability.

---

# 22. Trigger-verification claim boundaries

Trigger testing is bounded.

Acceptable result wording includes:

```text
NO_TRIGGER_EVIDENCE_FOUND
INCONCLUSIVE
TRIGGER_CONSISTENT_EVIDENCE
```

Do not automatically present:

```text
BACKDOOR CONFIRMED
MODEL IS SAFE
ATTACKER IDENTIFIED
PAYLOAD EXTRACTED
CRYPTOGRAPHIC PROOF
```

unless future backend architecture legitimately supports and validates those claims.

---

# 23. Unavailable and failure rendering

Never substitute zero-valued charts for missing data.

Examples:

- static feature N/A due precision path → `NOT APPLICABLE`;
- expected feature missing unexpectedly → `NOT AVAILABLE`;
- SHAP stage failed → `EXPLAINABILITY NOT AVAILABLE`;
- behavior skipped for quantized path → `NOT APPLICABLE`;
- required risk evidence missing → `MRS WITHHELD`;
- intake mismatch → `ARCHITECTURE MISMATCH`;
- resource gate failure → `INTAKE BLOCKED`.

Show the exact backend reason where available.

---

# 24. Streamlit application behavior

Use Streamlit as the application framework.

Custom CSS and carefully scoped HTML are allowed.

Build reusable components rather than seven unrelated page implementations.

Recommended shared concerns:

- persistent navigation;
- scan session state;
- current scan identity;
- artifact context;
- stage state;
- status badges;
- evidence links;
- dialogs/expanders;
- mesh/background treatment;
- chart formatting;
- report/export actions.

Use coherent multipage state so the scan follows the user across pages.

Avoid raw links or navigation patterns that unnecessarily reset scan state.

---

# 25. Preview-image interpretation

Preview images are **visual composition references only**.

They may contain:

- stale navigation;
- illustrative values;
- missing popups;
- missing expanders;
- incorrect logo treatment;
- missing glassmorphism;
- old wording;
- placeholder graphs;
- outdated colors;
- UI sections that later changed.

Therefore:

1. use previews for layout rhythm, hierarchy, density, card composition, and visual character;
2. use this specification for current content, semantics, states, and wording;
3. use the approved assets for logo/hands/mesh;
4. use the current backend as the truth for actual available data and current architecture.

Do not copy a preview error merely because it appears in an image.

---

# 26. Handling backend evolution

The backend may evolve after this document was written.

Codex should inspect the current implementation before wiring UI data.

If the backend:

- **adds a meaningful new stage/output** → incorporate it intelligently without breaking the product hierarchy;
- **renames a field** → adapt the UI data adapter;
- **drops an old field** → remove or gracefully degrade the corresponding UI;
- **changes a stage role** → reflect the current validated architecture rather than stale text;
- **exposes richer intermediate evidence** → use it when it materially improves judge understanding;
- **cannot support a planned chart** → do not fabricate data; choose a truthful alternative.

Do not force stale UI assumptions onto a newer backend.

---

# 27. Suggested implementation priority

## P0 — must work

- real upload/scan flow;
- seven-page navigation;
- actual stage states;
- intake validation;
- static evidence;
- explainability state;
- behavior applicability/results;
- MRS/verdict;
- final report;
- PDF/JSON export path;
- unavailable/blocked/failed states;
- correct semantic colors;
- approved logo/assets;
- no fabricated values.

## P1 — technical depth

- richer selected-layer views;
- real histograms;
- bit evidence;
- probe matrices;
- trigger comparison details;
- evidence modals;
- detector-assurance drill-down;
- evidence IDs and provenance interactions.

## P2 — polish

- fine animation;
- secondary decorative transitions;
- optional visual refinements that do not affect correctness.

---

# 28. Final implementation checklist

Before calling the UI complete, verify:

- [ ] seven distinct pages exist;
- [ ] landing uses approved hero assets;
- [ ] full SIGTENSOR logo is correct;
- [ ] upload card has intended glassmorphic treatment;
- [ ] no architecture/domain/precision selector exists;
- [ ] no visible `Use Demo Model` button exists;
- [ ] ResNet18-only mismatch is fail-closed;
- [ ] Pages 2–7 share a consistent shell;
- [ ] expanders/dialogs expose deep details;
- [ ] static heatmap uses real backend data;
- [ ] selected-layer tabs degrade honestly;
- [ ] explainability is correctly scoped;
- [ ] behavior page branches correctly;
- [ ] trigger verification appears only when executed;
- [ ] quantized behavior is N/A rather than zero;
- [ ] backend owns MRS/verdict/contributions;
- [ ] missing evidence can withhold MRS;
- [ ] Page 7 title is `From evidence to assessment.`;
- [ ] Page 7 separates scored and advisory evidence;
- [ ] PASS wording does not imply universal safety;
- [ ] evidence IDs are traceable where available;
- [ ] PDF/JSON correspond to the same finalized assessment;
- [ ] no graph uses invented observations;
- [ ] semantic colors follow the frozen palette;
- [ ] red/green/amber are not decorative;
- [ ] no stale preview detail overrides this specification.

---

# 29. Final product principle

The interface should make two things immediately obvious:

> **SIGTENSOR has a serious technical backend.**

and

> **The UI makes that backend understandable, inspectable, traceable, and auditable without exaggerating what the scanner proves.**

Earlier pages discover evidence.

Page 6 synthesizes validated evidence.

Page 7 proves that the conclusion is traceable, scoped, and exportable.
