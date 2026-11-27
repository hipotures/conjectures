# Conjectures

Formally verified results on open problems in graph theory, published with
their Lean 4 proofs, graph certificates, and independent checkers.

**Author:** Andrzej Marszałek (Independent Researcher) · **License:** CC0 1.0
(public domain) · [![verify](https://github.com/hipotures/conjectures/actions/workflows/verify.yml/badge.svg)](https://github.com/hipotures/conjectures/actions/workflows/verify.yml)

---

## Erdős–Gyárfás conjecture: small graphs without power-of-two cycles

> **Conjecture (Erdős–Gyárfás, 1995).** Every finite simple graph with minimum
> degree at least 3 contains a cycle whose length is a power of two.

The conjecture is open. A counterexample would have to avoid cycles of lengths
4, 8, 16, 32, … simultaneously. The extremal functions below measure how small
a graph can be while avoiding only the first few of these lengths:

- **f(k)** — the minimum order of a graph with minimum degree at least 3 that
  has no cycle of length 4, 8, …, 2^k;
- **f_cubic(k)** — the same, restricted to 3-regular graphs.

### Results

Category **A** means the statement is proved in full by the Lean kernel (no
external computation is trusted). Category **B** means the result is
computer-assisted: Lean proves the reductions and the soundness of the
certificate checkers, but the exhaustive search or SAT refutation runs outside
Lean.

| Result | Previous bound | Cat. | Lean theorem |
|---|---|:-:|---|
| f(4) ≤ **73** | 78 (cubic, Exoo) | A | `f_delta3_4_le_73`, `f_delta3_4_le_73_alt` |
| f(5) ≤ **345** | 370 (cubic, Henry 2026) | A | `f_delta3_5_le_345` |
| f_cubic(5) ≤ 370 | 370 (Henry 2026, found first) | A | `f_cubic_5_le_370` |
| f_cubic(6) ≤ **10,498** | 10,522 (Henry's theorem with the 702-vertex girth-16 graph) | A | `f_cubic_6_le_10498` |
| f_cubic(4) ≤ 78 | 78 (Exoo; optimal per Ripatti 2017) | A | `f_cubic_4_le_78` |
| Gadget-lift cycle theorem | — | A | `liftGraph_cycle_dichotomy`, `liftGraph_no_cycle` |
| Every cubic bipartite graph on ≤ 84 vertices has a C4, C8, or C16 | ≤ 68 (Zhuge 2026) | B | reductions in `CubicBipartite` |
| 370 and 345 are optimal among Tutte–Coxeter lifts by H7, H8\*, H15 | — | B | reductions in `TutteCoxeter` |

All witnesses in category A are also proved 2-connected
(`*_is2Connected`). Full statements, constructions, and references will be
given in the accompanying papers (in preparation).

## Verify it yourself

```bash
# Lean 4 via elan: https://github.com/leanprover/elan
cd lean && lake build && cd ..
python3 scripts/check_axioms.py
python3 scripts/check_forbidden.py
```

`lake build` kernel-checks every proof in about a minute on a desktop CPU.
CI repeats these checks on every push.

## Repository layout

| Path | Contents |
|---|---|
| `lean/` | Lean 4 library `ErdosGyarfas` (no dependencies). See [`lean/README.md`](lean/README.md). |
| `lean/Audit.lean` | `#print axioms` for every headline theorem. |
| `scripts/` | Axiom and forbidden-construct gates. |

## Use of AI

These results were obtained with substantial help from AI systems: mainly
Gemini 4 Neon (Google) and Claude Opus 5.5 (Anthropic), working through the
Antigravity and Claude Code tools. AI systems are not authors. Every
category-A statement is checked by the Lean kernel, and the author takes
responsibility for the statements, their attribution, and their presentation.

## Citation

See [`CITATION.cff`](CITATION.cff). Each tagged release is archived on Zenodo
with a DOI.
