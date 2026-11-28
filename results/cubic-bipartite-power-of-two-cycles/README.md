# Cubic bipartite graphs on at most 88 vertices have a cycle of length 4, 8 or 16

**Category B** (computer-assisted). Paper: [`paper.pdf`](paper.pdf) ([TeX](paper.tex)).
Release v1.2.0. The previous version (n ≤ 84) is release v1.1.0,
[doi:10.5281/zenodo.24599605](https://doi.org/10.5281/zenodo.24599605).

> **Theorem.** Every simple cubic bipartite graph on at most 88 vertices contains
> a cycle of length 4, 8 or 16. Hence a cubic bipartite counterexample to the
> Erdős–Gyárfás conjecture has at least 90 vertices.
>
> **Theorem.** Every simple cubic bipartite graph of girth at least 10 on at most
> 88 vertices contains a 16-cycle (the girth-10 case, proved by Branch B alone).

Previous bounds for the same statement: 58 vertices (Tranquilli,
arXiv:2608.02675) and 68 vertices (Zhuge, doi:10.5281/zenodo.21981786).

## How the proof works

A cubic bipartite graph is the Levi graph of a configuration of points and
3-element blocks. Without 4- and 8-cycles it either has a 6-cycle or has girth
at least 10, and there are two searches:

| Branch | Graphs | Root | Program |
|---|---|---|---|
| A | with a 6-cycle | Tranquilli's two triangle orbits | [`src/triangle_search.cpp`](src/triangle_search.cpp) |
| B | girth ≥ 10 | a forced 15-block subtree on 31 points | [`src/girth10_search.cpp`](src/girth10_search.cpp), [`src/girth10_verify.cpp`](src/girth10_verify.cpp) |

Both extend the root in Tranquilli's restricted-growth order. Each candidate
block is rejected by a degree or pair rule, or by an explicit witness that it
closes a 6-, 8- or 16-cycle, or is expanded. A checker replays the schedule
and verifies every witness without searching for cycles. Both searches end with
zero completed configurations at cap 44.

## What is checked, and by what

| Claim | Checked by |
|---|---|
| Case split (6-cycle or girth ≥ 10); witness cycles are real cycles; triangle root orbits | Lean 4, [`lean/ErdosGyarfas/CubicBipartite.lean`](../../lean/ErdosGyarfas/CubicBipartite.lean) |
| Every rejection in every search | the witness checkers in `src/` |
| The enumeration (Branch A) | Tranquilli's unchanged program gives the same counters at every cap tested, from 20 to 44 ([`data/upstream_crosscheck.json`](data/upstream_crosscheck.json)); at cap 44 it ran for 16 hours |
| The enumeration (both branches, small caps) | [`independent_check.py`](independent_check.py), a separate Python implementation with a different cycle test |
| Branch B reaches real girth-10 graphs | `independent_check.py` replays the three (3,10)-cages from all 210 roots |
| The three (3,10)-cages have a 16-cycle | Lean 4, `cage310_1_certified` … `cage310_3_certified` in [`lean/ErdosGyarfas/SourcePacking.lean`](../../lean/ErdosGyarfas/SourcePacking.lean) |

Not formalized: the coverage argument (Proposition 3.1 of the paper), the
Branch B root labelling, and the C++ programs themselves.

## Reproduce

```bash
python3 independent_check.py      # ~30 s, standard library only
python3 reproduce.py --quick      # ~5 s, small caps (CI runs this)
python3 reproduce.py              # full proof, ~80 min on 16 cores
```

`reproduce.py` needs a C++17 compiler. It compiles `src/`, reruns both
branches, checks every witness stream, and compares all counters with
[`data/expected_counts.json`](data/expected_counts.json).

## Licence

The C++ programs in `src/` adapt Tranquilli's MIT-licensed code
([floor-licker/erdos-gyarfas-cubic-bipartite](https://github.com/floor-licker/erdos-gyarfas-cubic-bipartite),
commit `67adc92d`) and are under the MIT License ([`src/LICENSE`](src/LICENSE)).
Everything else in this folder is CC0.
