# The smallest Tutte–Coxeter lifts without cycles of length 32

**Category B** (Lean counting lemma; SAT with DRAT proofs checked by
drat-trim). Paper: [`paper.pdf`](paper.pdf) ([TeX](paper.tex)). Release v1.2.0.

> **Theorem.** Replace every vertex of the Tutte–Coxeter graph by one of the
> gadgets H7, H8\*, H15, with any port bijections. If the resulting graph has no
> cycle of length 32, it has at least 345 vertices, and at least 370 if it is
> cubic (no H8\*).

Both bounds are attained by the 345- and 370-vertex lifts of
[paper 1](../small-graphs-power-of-two-cycles/), which have no cycle of length
4, 8, 16 or 32 (Henry was first to reach 370 with a construction of this type). So these constructions cannot be
improved with the same base and gadgets. The theorem says nothing about other
bases or gadgets, or about lower bounds for f(5) itself.

## How the proof goes

1. Path lengths between two ports of each gadget form an interval, so a lift
   has a 32-cycle exactly when some cycle D of the base has weight w(D) ≤ 32.
2. Each (vertex, edge) pair of the Tutte–Coxeter graph lies off exactly 8 of its
   90 eight-cycles. Summing w(D) − 33 over them gives 24a − 8c − 330 (a copies
   of H15, c of H7). This is proved in Lean
   ([`lean/ErdosGyarfas/TutteCoxeter.lean`](../../lean/ErdosGyarfas/TutteCoxeter.lean))
   and leaves three cases.
3. Each case is a CNF formula. CaDiCaL 2.1.3 refutes it, and drat-trim checks
   every DRAT proof. The cubic case is split into 56 disjoint subcases.

## What is checked, and by what

| Claim | Checked by |
|---|---|
| The CNF says what the paper says | [`test_encoding.py`](test_encoding.py): own Tutte–Coxeter graph (incidence graph of GQ(2,2)), 300 lifts built as graphs and compared with the formula, an explicit 32-cycle for every rejected lift, own DPLL solver, exhaustive test of the cardinality encoding |
| The counting identity | Lean 4 (`tc_incidence_eq_8`, `tc_double_counting_eq`, `tc_slack_card_sound`); the test checks that Lean's list of 8-cycles is the encoder's |
| Every formula is unsatisfiable | DRAT proof from CaDiCaL, checked by drat-trim; CNF hashes in [`data/results.json`](data/results.json) |
| The optimum is reached | two satisfiable controls; their models are decoded and checked as graphs (345 and 370 vertices, shortest cycle between gadgets 33) |
| The 56 subcases cover the cubic case | the test checks that they cover all 216 states of three vertices exactly once |

## Reproduce

```bash
python3 test_encoding.py   # ~15 s, standard library only
python3 prove.py           # builds the solvers, solves and checks everything
```

`prove.py` needs a C/C++ compiler and make. It downloads CaDiCaL 2.1.3 and
drat-trim (pinned, SHA-256 checked) into `~/.cache/conjectures-tc-lifts` (or
`$TC_LIFT_CACHE`), and rewrites `data/results.json` and `results_table.tex`.

## Licence

CC0. CaDiCaL and drat-trim are downloaded from their authors and keep their own
licences.
