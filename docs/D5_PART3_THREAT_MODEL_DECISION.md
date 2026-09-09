# D5 Part 3 — Threat-Model Coverage

**Status:** RESOLVED / LOCKED — Part 3 sub-decision only  
**Parent decision:** D5 — Per-layer → model-level risk aggregation  
**Date:** 2026-09-09

## 1. Decision

The D5 aggregation operator for model-level `S_static` must account for both **localized** and **distributed** static manipulation, as well as mixed patterns in which both occur.

This Part 3 decision defines the threat-model coverage requirements for evaluating candidate operators. It does **not** select the mathematical aggregation operator.

## 2. Threat-model patterns

### 2.1 Localized manipulation

A small subset of eligible layers may contain substantially stronger static anomaly evidence than the remainder of the model.

The eventual operator must remain sensitive to concentrated evidence and must not allow numerous normal layers to dilute that evidence to the point that it loses model-level significance.

### 2.2 Distributed manipulation

Static anomaly evidence may be spread across many eligible layers such that individual layers are only moderately anomalous.

The eventual operator must remain sensitive to coherent distributed evidence and must not require a single extreme layer.

### 2.3 Mixed manipulation

Concentrated and distributed evidence may coexist. The eventual operator must behave coherently when a small number of layers are strongly anomalous while a broader set of layers also contains weaker but consistent anomaly evidence.

## 3. Requirements for candidate D5 operators

Before an operator is locked, candidate operators must be evaluated for:

1. **Localized sensitivity:** strong concentrated evidence can materially increase `S_static`.
2. **Distributed sensitivity:** broad coherent evidence can materially increase `S_static` even without one extreme layer.
3. **Mixed-pattern behavior:** the operator behaves coherently when concentrated and distributed evidence coexist.
4. **Monotonicity:** strengthening valid anomaly evidence must not reduce `S_static`.
5. **Dilution resistance:** unrelated normal layers must not arbitrarily erase strong localized evidence.
6. **Determinism:** identical authoritative evidence produces identical `S_static`.
7. **D7 compliance:** invalid or blocked evidence states remain governed by D7 and are not silently overridden.
8. **D6 preservation:** the operator must not discard the authoritative per-layer evidence and layer identity required for downstream highest-risk-layer selection/reporting.

These requirements constrain the later operator decision; they do not imply `max`, mean, median, top-k, weighted aggregation, or any other specific operator.

## 4. Why this boundary is appropriate

The locked D7 robust Z/MAD path establishes anomaly evidence relative to the model's intra-model layer-vs-layer baseline. Robust anomaly detection is specifically concerned with identifying observations that deviate from a majority/reference population, while robust estimation literature also distinguishes resistance to isolated outliers from behavior under broader contamination. This supports evaluating both concentrated and distributed contamination patterns, but does not by itself establish a particular cross-layer aggregation operator.

Therefore, external statistical literature is used here only to validate the threat-model distinction and evaluation criteria. It is not treated as authority for selecting the eventual D5 operator.

## 5. What this decision does NOT authorize

This Part 3 decision does not authorize or define:

- `max`, mean, median, top-k, weighted aggregation, voting, or any other D5 operator;
- a new per-layer score name such as `S_static_layer`;
- layer-level `P_tamper`;
- layer-level `S_behavior`;
- a new baseline or threshold;
- TreeSHAP-based layer selection;
- D6 highest-risk-layer selection;
- any change to the frozen MRS formulas;
- any change to the P1 feature definitions or D7 validity rules.

## 6. Parent D5 status

This sub-decision resolves **Part 3 only**: the threat-model coverage and evaluation requirements for the eventual D5 aggregation operator.

D5 as a whole remains:

> **RESOLVED / LOCKED — METHODOLOGY BOUNDARY; EXACT OPERATOR PENDING**

The next D5 sub-decision is the mathematical candidate comparison and evidence-based selection of the aggregation operator against Parts 1–3 requirements.
