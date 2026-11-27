# Lifts of the Tutte–Coxeter graph without 32-cycles

**Work in progress** (category B: Lean counting lemma + SAT with DRAT proofs). No paper yet.

> **Claim.** Every lift of the Tutte–Coxeter graph by the gadgets H7, H8\* and
> H15 that has no 32-cycle has at least 345 vertices, and at least 370 if it is
> cubic (no H8\*). Both bounds are attained (paper 1).

Port-to-port path lengths in all three gadgets form intervals, so a lift has a
32-cycle iff some cycle D of the base has weight w(D) ≤ 32. The counting lemma
(Lean, `lean/ErdosGyarfas/TutteCoxeter.lean`) reduces the claim to three CNF
instances that encode the necessary condition w(D) ≥ 33 on the 90 8-cycles.

| File | Role |
|---|---|
| [`encode.py`](encode.py) | CNF encoder and instance list |
| [`test_encoding.py`](test_encoding.py) | independent tests (own TC construction, real lift graphs, explicit 32-cycles, own DPLL), ~15 s |
| [`prove.py`](prove.py) | builds pinned CaDiCaL 2.1.3 and drat-trim, solves, checks every UNSAT proof with drat-trim, checks SAT controls as graphs |

The full run of `prove.py` has not been done yet.
