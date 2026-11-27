# Conjectures

Results on open problems in mathematics, each published with a paper, a Lean 4
proof checked by the Lean kernel, an independent checker, and the data needed
to reproduce it.

**Author:** Andrzej Marszałek (Independent Researcher, ORCID
[0009-0006-6148-2965](https://orcid.org/0009-0006-6148-2965)) ·
**License:** CC0 1.0 (public domain) ·
[![verify](https://github.com/hipotures/conjectures/actions/workflows/verify.yml/badge.svg)](https://github.com/hipotures/conjectures/actions/workflows/verify.yml)

## Catalog

| Problem | Result | Status | Category | Artifacts |
|---|---|---|:-:|---|
| [Erdős–Gyárfás](#erdősgyárfás-conjecture) | [Small graphs without cycles of length a power of two](results/small-graphs-power-of-two-cycles/) | draft paper | A | [PDF](results/small-graphs-power-of-two-cycles/paper.pdf) · [TeX](results/small-graphs-power-of-two-cycles/paper.tex) · [Lean](lean/ErdosGyarfas) · [Python](results/small-graphs-power-of-two-cycles/verify.py) · [Data](results/small-graphs-power-of-two-cycles/data) |
| [Erdős–Gyárfás](#erdősgyárfás-conjecture) | Cubic bipartite graphs on at most 84 vertices contain a cycle of length 4, 8 or 16 | in preparation | B | [Lean reductions](lean/ErdosGyarfas/CubicBipartite.lean) |

**Categories.** **A**: every claim is proved by the Lean kernel; no external
computation is trusted. **B**: computer-assisted; Lean proves the reductions
and the soundness of the certificate checkers, while the exhaustive search runs
outside Lean and is reproducible from the published code.

Each result lives in its own folder under `results/`, and each problem has its
own Lean library under `lean/`. New problems are added the same way.

---

## Erdős–Gyárfás conjecture

> **Conjecture (Erdős–Gyárfás, 1995).** Every finite simple graph with minimum
> degree at least 3 contains a cycle whose length is a power of two.

`f_δ≥3(k)` and `f_cubic(k)` denote the least order of a graph with minimum
degree at least 3 (respectively, a cubic graph) that has no cycle of length
4, 8, …, 2^k.

| Bound | Previous | Lean theorem | Notes |
|---|---|---|---|
| f_δ≥3(4) ≤ **73** | 78 (cubic; Exoo, Ripatti) | `f_delta3_4_le_73`, `f_delta3_4_le_73_alt` | new gadget H8\* |
| f_δ≥3(5) ≤ **345** | 370 (cubic; Henry 2026) | `f_delta3_5_le_345` | new |
| f_cubic(6) ≤ **10,498** | 10,522 (Henry 2026, conditional) | `f_cubic_6_le_10498` | source-packing theorem; girth of the 702-vertex base proved in Lean |
| f_cubic(5) ≤ 370 | Henry 2026 (first) | `f_cubic_5_le_370` | independent rediscovery; formal proof |
| f_cubic(4) ≤ 78 | Exoo | `f_cubic_4_le_78` | formal proof of a known bound |

The cycle-projection lemma for gadget lifts and the gadgets H7 and H15 are due
to García (2026) and Henry (2026); this repository formalizes them. All
category-A witnesses are proved 2-connected.

---

## Verification

Every push runs [`verify.yml`](.github/workflows/verify.yml):

1. **Kernel build.** `lake build` checks every proof (Lean 4.36.0, no Mathlib,
   about a minute).
2. **Axiom audit.** [`scripts/check_axioms.py`](scripts/check_axioms.py) runs
   `#print axioms` over [`lean/Audit.lean`](lean/Audit.lean) and accepts only
   `propext`, `Classical.choice`, `Quot.sound`.
3. **Forbidden constructs.** [`scripts/check_forbidden.py`](scripts/check_forbidden.py)
   rejects `sorry`, `native_decide`, `implemented_by`, `extern` and `axiom` in
   code.
4. **Independent checks.** Each result's `verify.py` rebuilds the constructions
   from data extracted from the Lean sources and checks them with separately
   written code.

To reproduce locally:

```bash
cd lean && lake build && cd ..
python3 scripts/check_axioms.py
python3 scripts/check_forbidden.py
python3 results/small-graphs-power-of-two-cycles/verify.py
```

## Use of AI

These results were obtained with substantial help from AI systems, mainly
Gemini 4 Neon (Google) and Claude Opus 5.5 (Anthropic), working through the
Antigravity and Claude Code tools. AI systems are not authors. Category-A
statements are checked by the Lean kernel. The author takes responsibility for
the statements, their attribution, and their presentation.

## Citation

See [`CITATION.cff`](CITATION.cff). Tagged releases are archived on Zenodo with
a DOI.
