# `ErdosGyarfas` — Lean 4 library

A self-contained Lean 4 (`v4.36.0`) formalization of finite simple graphs,
simple cycles, a 3-port vertex-replacement ("gadget lift") construction, and
the concrete constructions and certificate checkers used in this repository.

- No Mathlib and no other dependencies: only the Lean 4 core library.
- No `sorry`, no `native_decide`, no custom axioms. Every finite computation
  (cycle searches, BFS potentials, automorphism checks) is reduced by the Lean
  kernel itself.
- Every headline theorem depends only on Lean's standard axioms
  `propext`, `Classical.choice`, and `Quot.sound`. CI enforces this on every
  push.

## Build and audit

```bash
cd lean
lake build                      # kernel-checks every proof (about 1 minute)
cd ..
python3 scripts/check_axioms.py     # #print axioms gate over lean/Audit.lean
python3 scripts/check_forbidden.py  # no sorry / native_decide / axiom in code
```

## Core definitions (`ErdosGyarfas/Graph.lean`)

These are the definitions on which every statement rests. They should be read
before any theorem.

| Definition | Meaning |
|---|---|
| `FinGraph n` | a graph on `Fin n` with a Boolean adjacency relation that is symmetric and irreflexive |
| `FinGraph.deg`, `IsCubic`, `MinDegAtLeast d` | degree = number of neighbours; every degree is 3; every degree is at least `d` |
| `SimpleCycle G L` | `L ≥ 3` and an injective map `Fin L → Fin n` whose cyclically consecutive vertices are adjacent |
| `HasCycle G L` | `Nonempty (SimpleCycle G L)` |
| `FinGraph.Is2Connected` (`Connectivity.lean`) | `n ≥ 3` and deleting any one vertex leaves the remaining vertices connected |

## Modules

| Module | Contents |
|---|---|
| `Graph` | Core definitions; BFS distance-potential lower bound; sound bitmask DFS cycle checker (`not_hasCycle_of_dfs`); sound weighted short-cycle checker. |
| `GadgetLift` | 3-port vertex-replacement lift `liftGraph`; degree preservation; cycle dichotomy `liftGraph_cycle_dichotomy` (a cycle of the lift lies in one gadget or projects to a base cycle with a length lower bound); corollary `liftGraph_no_cycle`. |
| `Gadgets` | The gadgets `H7` (7 vertices), `H8star` (8 vertices), `H15` (15 vertices) with certified port distances and local `{C4, C8}`-freeness. |
| `UpperBounds` | `f_delta3_4_le_73`, `f_delta3_4_le_73_alt`, `f_cubic_5_le_370`, `f_delta3_5_le_345`; general 4-packing theorem `f_cubic_6_4packing`. |
| `Connectivity` | 2-connectivity, a sound checker, preservation under lifts (`liftGraph_is2Connected`), `f_cubic_4_le_78`, and 2-connectivity of all witnesses. |
| `SourcePacking` | Source 8-packing lift theorem `f_cubic_6_source_8packing`; the three `(3,10)`-cages contain a 16-cycle. |
| `Girth16Data`, `CubicF6` | The 702-vertex cubic graph `k3_g16_n702` (House of Graphs), a kernel proof that its girth is at least 16, and `f_cubic_6_le_10498`. |
| `TutteCoxeter` | Double counting over the 90 8-cycles of the Tutte–Coxeter graph and soundness of the cardinality constraint used in the SAT encoding. |
| `CubicBipartite` | Reductions for cubic bipartite graphs and soundness of the witness checkers used by the exhaustive search. |

## What the library does and does not prove

The upper bounds (`f_*_le_*`) are complete existence proofs: the theorem states
that a graph with the stated properties exists, and the kernel checks it.

`TutteCoxeter` and `CubicBipartite` prove only the mathematical reductions and
the soundness of checkers. The exhaustive searches and SAT/DRAT refutations
that rely on them run outside Lean. Results that depend on those computations
are labelled as computer-assisted wherever they are stated.
