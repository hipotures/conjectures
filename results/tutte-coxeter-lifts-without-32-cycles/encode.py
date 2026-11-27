#!/usr/bin/env python3
"""CNF encoding of 32-cycle-free gadget lifts of the Tutte-Coxeter graph.

A lift assigns to every vertex v of the Tutte-Coxeter graph TC a gadget
g in {H15, H8star, H7} and a vertex q(v) = adj[v][p] adjacent to v whose edge goes
to port 0 of the gadget. The variable x(v, g, p) says exactly that.

For a cycle D of TC and a vertex v of D whose third edge (the one not on D)
is adj[v][o], the gadget at v contributes d(g, p, o) = d_g(1, 2) if p == o
and d_g(0, 1) otherwise; w(D) = len(D) + sum of contributions. The paper shows
that a lift without 32-cycles has w(D) >= 33 for every 8-cycle D of TC. Only
this necessary condition is encoded, so an unsatisfiable CNF rules out every
lift with the given counts. Every auxiliary variable below is defined by an
equivalence, so the CNF says exactly:

  * every vertex has exactly one state (g, p) with g in the allowed gadgets;
  * w(D) >= 33 for every 8-cycle D;
  * optional: at most A copies of H15, at least C copies of H7;
  * optional ("slack"): at most S 8-cycles have w(D) >= 34, where S is the
    largest value of the double-counting identity over the allowed counts
    (Lean: ErdosGyarfas.tc_slack_card_sound);
  * optional ("symmetry"): vertex 0 has a gadget from a given set, with
    port 0 on the edge to adj[0][0] (TC is arc-transitive).

Standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import deque
from itertools import combinations, product
from pathlib import Path

HERE = Path(__file__).resolve().parent
GADGETS = ("H15", "H8star", "H7")
BOUND = 33  # w(D) >= BOUND for every cycle D


# ---------------------------------------------------------------- the model

def tutte_coxeter() -> list[list[int]]:
    """TC from its LCF notation [-13,-9,7,-7,9,13]^5; neighbour lists sorted."""
    lcf = (-13, -9, 7, -7, 9, 13)
    adj = [set() for _ in range(30)]
    for i in range(30):
        for j in ((i + 1) % 30, (i + lcf[i % 6]) % 30):
            adj[i].add(j)
            adj[j].add(i)
    assert all(len(a) == 3 for a in adj)
    return [sorted(a) for a in adj]


def cycles(adj: list[list[int]], lengths: tuple[int, ...]) -> list[list[int]]:
    """All cycles of the given lengths, each once (smallest vertex first,
    second vertex smaller than the last)."""
    out = []
    top = max(lengths)

    def go(start, path, seen):
        x = path[-1]
        if len(path) in lengths and start in adj[x] and path[1] < x:
            out.append(list(path))
        if len(path) == top:
            return
        for y in adj[x]:
            if y > start and y not in seen:
                path.append(y)
                seen.add(y)
                go(start, path, seen)
                seen.discard(y)
                path.pop()

    for s in range(len(adj)):
        go(s, [s], {s})
    return out


def off_edges(adj, cyc):
    """(v, o) along the cycle: adj[v][o] is the neighbour of v off the cycle."""
    res = []
    for i, v in enumerate(cyc):
        a, b = cyc[i - 1], cyc[(i + 1) % len(cyc)]
        (o,) = [k for k in range(3) if adj[v][k] not in (a, b)]
        res.append((v, o))
    return res


def load_gadgets() -> dict:
    return json.loads((HERE / "data" / "gadgets.json").read_text())["gadgets"]


def port_distances(g: dict) -> tuple[int, int]:
    """(d(0,1), d(1,2)) for a gadget; asserts d(0,1) == d(0,2)."""
    n = g["order"]
    adj = [[] for _ in range(n)]
    for a, b in g["edges"]:
        adj[a].append(b)
        adj[b].append(a)
    p = g["ports"]

    def dist(s, t):
        d = {s: 0}
        q = deque([s])
        while q:
            x = q.popleft()
            for y in adj[x]:
                if y not in d:
                    d[y] = d[x] + 1
                    q.append(y)
        return d[t]

    d01, d02, d12 = dist(p[0], p[1]), dist(p[0], p[2]), dist(p[1], p[2])
    assert d01 == d02
    return d01, d12


# ---------------------------------------------------------------- CNF

class CNF:
    def __init__(self):
        self.n = 0
        self.clauses: list[tuple[int, ...]] = []

    def var(self) -> int:
        self.n += 1
        return self.n

    def add(self, *lits: int) -> None:
        self.clauses.append(tuple(lits))

    def define_or(self, lits: list[int]) -> int:
        """New y with y <-> OR(lits)."""
        y = self.var()
        for l in lits:
            self.add(-l, y)
        self.add(-y, *lits)
        return y

    def at_most(self, lits: list[int], k: int) -> None:
        """Sinz sequential counter: at most k of lits are true."""
        n = len(lits)
        if k >= n:
            return
        if k < 0:
            self.add()
            return
        if k == 0:
            for l in lits:
                self.add(-l)
            return
        # s[i][j]: at least j+1 of lits[0..i] are true (one direction suffices)
        s = [[self.var() for _ in range(k)] for _ in range(n - 1)]
        self.add(-lits[0], s[0][0])
        for j in range(1, k):
            self.add(-s[0][j])
        for i in range(1, n - 1):
            self.add(-lits[i], s[i][0])
            self.add(-s[i - 1][0], s[i][0])
            for j in range(1, k):
                self.add(-lits[i], -s[i - 1][j - 1], s[i][j])
                self.add(-s[i - 1][j], s[i][j])
            self.add(-lits[i], -s[i - 1][k - 1])
        self.add(-lits[n - 1], -s[n - 2][k - 1])

    def dimacs(self, comments=()) -> str:
        head = [f"c {c}" for c in comments] + [f"p cnf {self.n} {len(self.clauses)}"]
        return "\n".join(head + [" ".join(map(str, c)) + " 0" for c in self.clauses]) + "\n"


def encode(gadgets=GADGETS, max_h15=30, min_h7=0, slack=False, symmetry=None):
    """Return (cnf, x, info); x[(v, g, p)] is the state variable."""
    data = load_gadgets()
    dist = {g: port_distances(data[g]) for g in gadgets}
    adj = tutte_coxeter()
    cyc = cycles(adj, (8,))
    cnf = CNF()
    x = {(v, g, p): cnf.var() for v in range(30) for g in gadgets for p in range(3)}
    states = [(g, p) for g in gadgets for p in range(3)]

    for v in range(30):  # exactly one state
        lits = [x[(v, g, p)] for g, p in states]
        cnf.add(*lits)
        for a, b in combinations(lits, 2):
            cnf.add(-a, -b)

    def d(g, p, o):
        d01, d12 = dist[g]
        return d12 if p == o else d01

    # e(v, o) = d - 2 takes values in E; lit[(v, o, k)] <-> e(v, o) == k
    E = sorted({d(g, p, o) - 2 for g, p in states for o in range(3)})
    assert min(E) >= 0
    elit = {}
    for v in range(30):
        for o in range(3):
            for k in E:
                elit[(v, o, k)] = cnf.define_or(
                    [x[(v, g, p)] for g, p in states if d(g, p, o) - 2 == k])

    flags = []
    for c in cyc:
        L = len(c)
        need = BOUND - 3 * L  # sum of e >= need  <=>  w(D) >= 33
        top = need + 1 if slack else need
        prev = None  # prev[t]: prefix sum >= t, as literal or True/False
        for i, (v, o) in enumerate(off_edges(adj, c)):
            cur = {}
            for t in range(1, top + 1):
                def before(tt):
                    if tt <= 0:
                        return True
                    return False if prev is None else prev[tt]
                opts = [(elit[(v, o, k)], before(t - k)) for k in E]
                if all(b is False for _, b in opts):
                    cur[t] = False
                    continue
                y = cnf.var()
                cur[t] = y
                # y <-> OR_k (e_k and before(t-k)); exactly one e_k holds
                for e, b in opts:
                    if b is True:
                        cnf.add(-e, y)
                    elif b is False:
                        cnf.add(-y, -e)
                    else:
                        cnf.add(-e, -b, y)
                        cnf.add(-y, -e, b)
            prev = cur
        final = prev[need]
        if final is False:
            cnf.add()
        else:
            cnf.add(final)
        if slack:
            flags.append(prev[need + 1])

    order = {g: data[g]["order"] for g in gadgets}
    kind = {g: [cnf.define_or([x[(v, g, p)] for p in range(3)]) for v in range(30)]
            for g in gadgets}
    if "H15" in gadgets and max_h15 < 30:
        cnf.at_most(kind["H15"], max_h15)
    if min_h7 > 0:
        cnf.at_most([-l for l in kind["H7"]], 30 - min_h7)

    S = None
    if slack:
        # sum over 8-cycles D of (w(D) - 33) = 8 * sum_v sum_o d(v, o) + 90*8 - 90*33,
        # because each (v, o) lies on exactly 8 of the 90 8-cycles.
        inc = {}
        c8 = cyc
        for c in c8:
            for vo in off_edges(adj, c):
                inc[vo] = inc.get(vo, 0) + 1
        assert len(c8) == 90 and set(inc.values()) == {8} and len(inc) == 90
        per = {g: 8 * sum(d(g, 0, o) for o in range(3)) for g in gadgets}
        best = None
        for cnt in product(range(31), repeat=len(gadgets)):
            if sum(cnt) != 30:
                continue
            c = dict(zip(gadgets, cnt))
            if c.get("H15", 0) > max_h15 or c.get("H7", 0) < min_h7:
                continue
            val = sum(per[g] * c[g] for g in gadgets) + 90 * 8 - 90 * BOUND
            best = val if best is None else max(best, val)
        S = best
        flag_lits = [f for f in flags if f is not False]
        if S is None or S < 0:
            cnf.add()
        else:
            cnf.at_most(flag_lits, S)

    if symmetry:
        cnf.add(*[x[(0, g, 0)] for g in symmetry])

    info = {"gadgets": list(gadgets), "max_h15": max_h15, "min_h7": min_h7,
            "slack": S, "symmetry": list(symmetry or []),
            "cycles": len(cyc),
            "max_order": max_order(gadgets, max_h15, min_h7, order)}
    return cnf, x, info


def max_order(gadgets, max_h15, min_h7, order):
    best = 0
    for cnt in product(range(31), repeat=len(gadgets)):
        c = dict(zip(gadgets, cnt))
        if sum(cnt) == 30 and c.get("H15", 0) <= max_h15 and c.get("H7", 0) >= min_h7:
            best = max(best, sum(order[g] * c[g] for g in gadgets))
    return best


# ---------------------------------------------------------------- instances

# UNSAT instances that, with the counting lemma, prove the theorem; and two
# satisfiable controls at the optimum.
INSTANCES = {
    "delta3_a14": dict(gadgets=("H15", "H8star"), max_h15=14, slack=True, symmetry=("H8star",)),
    "delta3_a15_c1": dict(gadgets=GADGETS, max_h15=15, min_h7=1, slack=True, symmetry=("H7",)),
    "cubic_a19": dict(gadgets=("H15", "H7"), max_h15=19, slack=True, symmetry=("H7",)),
    "control_delta3_a15": dict(gadgets=("H15", "H8star"), max_h15=15, slack=True, symmetry=("H8star",)),
    "control_cubic_a20": dict(gadgets=("H15", "H7"), max_h15=20, slack=True, symmetry=("H7",)),
}
EXPECT = {"delta3_a14": "UNSAT", "delta3_a15_c1": "UNSAT", "cubic_a19": "UNSAT",
          "control_delta3_a15": "SAT", "control_cubic_a20": "SAT"}


def cubes(name, x):
    """Disjoint unit-clause cubes that together cover the instance.

    cubic_a19 is split on the states of the three neighbours 1, 29, 17 of
    vertex 0: all 36 state pairs of (1, 29), and the four pairs where both are
    H15 with port 0 not on adj[.][0] are split further over the 6 states of 17.
    """
    if name != "cubic_a19":
        return [("all", [])]
    st = [(g, p) for g in ("H15", "H7") for p in range(3)]
    out = []
    for i, s1 in enumerate(st):
        for j, s2 in enumerate(st):
            base = [x[(1, *s1)], x[(29, *s2)]]
            if i in (1, 2) and j in (1, 2):
                for k, s3 in enumerate(st):
                    out.append((f"c_{i}_{j}_{k}", base + [x[(17, *s3)]]))
            else:
                out.append((f"c_{i}_{j}", base))
    return out


def write_instance(name, outdir: Path) -> list[dict]:
    cnf, x, info = encode(**INSTANCES[name])
    outdir.mkdir(parents=True, exist_ok=True)
    rows = []
    for tag, units in cubes(name, x):
        text = cnf.dimacs([f"{name} {tag}", json.dumps(info)])
        if units:
            head, body = text.split("p cnf ", 1)
            nv, nc, rest = body.split(None, 2)
            text = head + f"p cnf {nv} {int(nc) + len(units)}\n" + rest + "".join(f"{u} 0\n" for u in units)
        path = outdir / f"{name}.{tag}.cnf"
        path.write_text(text)
        rows.append({"instance": name, "cube": tag, "file": path.name,
                     "vars": cnf.n, "clauses": len(cnf.clauses) + len(units),
                     "sha256": hashlib.sha256(text.encode()).hexdigest(), **info})
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("names", nargs="*", default=list(INSTANCES))
    a = ap.parse_args()
    for name in a.names:
        rows = write_instance(name, a.out)
        print(f"{name}: {len(rows)} file(s), {rows[0]['vars']} vars, {rows[0]['clauses']} clauses")


if __name__ == "__main__":
    main()
