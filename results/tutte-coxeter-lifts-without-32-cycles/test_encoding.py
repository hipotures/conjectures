#!/usr/bin/env python3
"""Independent tests of encode.py. Standard library only, no SAT solver.

The Tutte-Coxeter graph is rebuilt here as the incidence graph of the
generalized quadrangle GQ(2,2) (pairs and synthemes of a 6-set) and matched to
encode.py's numbering by an isomorphism search. Lifts are then built as real
graphs from the gadget edge lists, and

  1. the gadget facts the paper uses are recomputed: port distances, the
     path-length intervals between ports, no 4-, 8-, 16- or 32-cycles;
  2. TC facts: 90 8-cycles, 72 10-cycles, girth 8, each (vertex, edge) pair on
     exactly 8 of the 8-cycles, 1440 automorphisms, arc-transitive;
  3. for 300 lifts near the optimum: the weight w(D), computed from paths in
     the real lift, matches the BFS length of the shortest cycle through an
     edge between gadgets; the CNF accepts the lift iff w(D) >= 33 for every
     8-cycle D; every rejected lift gets an explicit 32-cycle, checked edge by
     edge; every accepted lift also satisfies the CNF with its own counts, the
     slack constraint and symmetry breaking;
  4. the cubes of cubic_a19 partition the states of vertices 1, 29, 17;
  5. the cardinality encoding is exact on all small cases.

CNF satisfiability under a full assignment of the state variables is decided
by a small DPLL below, and every model is checked against every clause.
"""

from __future__ import annotations

import json
import random
import sys
from collections import deque
from itertools import combinations, permutations
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import encode  # noqa: E402  (the code under test)

sys.setrecursionlimit(100000)
FAILS = []


def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


# ------------------------------------------------------------------ graphs

def gq22_levi():
    pts = [frozenset(p) for p in combinations(range(6), 2)]
    lines = []
    for m in permutations(range(6)):
        s = frozenset(frozenset(m[i:i + 2]) for i in (0, 2, 4))
        if s not in lines:
            lines.append(s)
    assert len(pts) == 15 and len(lines) == 15
    adj = [set() for _ in range(30)]
    for i, p in enumerate(pts):
        for j, l in enumerate(lines):
            if p in l:
                adj[i].add(15 + j)
                adj[15 + j].add(i)
    return [sorted(a) for a in adj]


def isomorphisms(A, B, first_only=False):
    """All bijections f with f(A-edges) = B-edges (A, B cubic, connected)."""
    n = len(A)
    order, seen = [], {0}
    q = deque([0])
    while q:  # BFS order of A so that every vertex after 0 has an earlier neighbour
        x = q.popleft()
        order.append(x)
        for y in A[x]:
            if y not in seen:
                seen.add(y)
                q.append(y)
    Bset = [set(b) for b in B]
    out, f, used = [], {}, set()

    def go(i):
        if i == n:
            out.append(dict(f))
            return first_only
        x = order[i]
        cands = range(n) if i == 0 else Bset[f[next(y for y in A[x] if y in f)]]
        for c in cands:
            if c in used:
                continue
            if all((f[y] in Bset[c]) for y in A[x] if y in f):
                f[x] = c
                used.add(c)
                if go(i + 1):
                    return True
                del f[x]
                used.discard(c)
        return False

    go(0)
    return out


def cycles_by_length(adj, top):
    cnt = {}
    found = []

    def go(s, path, seen):
        x = path[-1]
        if len(path) >= 3 and s in adj[x] and path[1] < x:
            cnt[len(path)] = cnt.get(len(path), 0) + 1
            found.append(tuple(path))
        if len(path) == top:
            return
        for y in adj[x]:
            if y > s and y not in seen:
                seen.add(y)
                path.append(y)
                go(s, path, seen)
                path.pop()
                seen.discard(y)

    for s in range(len(adj)):
        go(s, [s], {s})
    return cnt, found


# ------------------------------------------------------------------ gadgets

def gadget_adj(g):
    adj = [[] for _ in range(g["order"])]
    for a, b in g["edges"]:
        adj[a].append(b)
        adj[b].append(a)
    return adj


def port_paths(g):
    """paths[(i, j)][length] = one i-j port path (vertex list) of that length."""
    adj = gadget_adj(g)
    P = g["ports"]
    res = {}
    for i in range(3):
        for j in range(3):
            if i == j:
                continue
            got = {}

            def go(path, seen):
                x = path[-1]
                if x == P[j]:
                    got.setdefault(len(path) - 1, list(path))
                    return
                for y in adj[x]:
                    if y not in seen:
                        seen.add(y)
                        path.append(y)
                        go(path, seen)
                        path.pop()
                        seen.discard(y)

            go([P[i]], {P[i]})
            res[(i, j)] = got
    return res


# ------------------------------------------------------------------ lifts

class Lift:
    """Lift of TC (encode.py numbering, via iso to the Levi graph)."""

    def __init__(self, base, gad, perm, gadgets):
        # perm[v][k] = port of gadget at v used by the edge to base[v][k]
        self.base, self.gad, self.perm, self.G = base, gad, perm, gadgets
        self.off, n = [], 0
        for v in range(30):
            self.off.append(n)
            n += gadgets[gad[v]]["order"]
        self.n = n
        self.adj = [set() for _ in range(n)]
        for v in range(30):
            for a, b in gadgets[gad[v]]["edges"]:
                self._edge(self.off[v] + a, self.off[v] + b)
        self.cross = []
        for u in range(30):
            for k, v in enumerate(base[u]):
                if u < v:
                    a = self.port(u, perm[u][k])
                    b = self.port(v, perm[v][base[v].index(u)])
                    self._edge(a, b)
                    self.cross.append((a, b))

    def _edge(self, a, b):
        assert b not in self.adj[a]
        self.adj[a].add(b)
        self.adj[b].add(a)

    def port(self, v, i):
        return self.off[v] + self.G[self.gad[v]]["ports"][i]

    def state(self, v):
        return self.gad[v], self.perm[v].index(0)

    def cross_girth(self):
        """Shortest cycle through an edge between two gadgets (BFS)."""
        best = 10 ** 9
        for a, b in self.cross:
            dist = {a: 0}
            q = deque([a])
            while q and b not in dist:
                x = q.popleft()
                for y in self.adj[x]:
                    if (x, y) in ((a, b), (b, a)) or y in dist:
                        continue
                    dist[y] = dist[x] + 1
                    q.append(y)
            if b in dist:
                best = min(best, dist[b] + 1)
        return best

    def counts(self):
        return {g: self.gad.count(g) for g in self.G}


def weight_and_c32(lift, cyc, paths):
    """w(D) for the base cycle cyc; if w(D) <= 32, an explicit 32-cycle."""
    L = len(cyc)
    runs = []
    for i, v in enumerate(cyc):
        a = lift.perm[v][lift.base[v].index(cyc[i - 1])]
        b = lift.perm[v][lift.base[v].index(cyc[(i + 1) % L])]
        runs.append(paths[lift.gad[v]][(a, b)])
    w = L + sum(min(r) for r in runs)
    if w > 32:
        return w, None
    need = 32 - L
    pick = [min(r) for r in runs]
    for i, r in enumerate(runs):  # raise lengths one gadget at a time
        while sum(pick) < need and pick[i] + 1 in r:
            pick[i] += 1
    assert sum(pick) == need, "path lengths are not intervals"
    cycle = []
    for v, r, l in zip(cyc, runs, pick):
        cycle += [lift.off[v] + x for x in r[l]]
    return w, cycle


def is_cycle(adj, c):
    return (len(set(c)) == len(c) >= 3 and
            all(c[(i + 1) % len(c)] in adj[c[i]] for i in range(len(c))))


# ------------------------------------------------------------------ DPLL

def dpll(nvars, clauses, units):
    occ = [[] for _ in range(2 * nvars + 2)]
    for ci, c in enumerate(clauses):
        if not c:
            return None
        for l in c:
            occ[l + nvars].append(ci)
    val = [0] * (nvars + 1)
    trail = []

    def assign(l):
        v = abs(l)
        if val[v]:
            return val[v] == (1 if l > 0 else -1)
        val[v] = 1 if l > 0 else -1
        trail.append(v)
        q = [l]
        while q:
            lit = q.pop()
            for ci in occ[-lit + nvars]:
                unassigned, sat = None, False
                n_un = 0
                for m in clauses[ci]:
                    s = val[abs(m)]
                    if s == 0:
                        n_un += 1
                        unassigned = m
                    elif (s > 0) == (m > 0):
                        sat = True
                        break
                if sat:
                    continue
                if n_un == 0:
                    return False
                if n_un == 1:
                    u = unassigned
                    val[abs(u)] = 1 if u > 0 else -1
                    trail.append(abs(u))
                    q.append(u)
        return True

    def undo(mark):
        while len(trail) > mark:
            val[trail.pop()] = 0

    for c in clauses:
        if len(c) == 1 and not assign(c[0]):
            return None
    for u in units:
        if not assign(u):
            return None

    def search(start):
        v = next((i for i in range(start, nvars + 1) if val[i] == 0), None)
        if v is None:
            return True
        for lit in (-v, v):
            mark = len(trail)
            if assign(lit) and search(v + 1):
                return True
            undo(mark)
        return False

    if not search(1):
        return None
    model = list(val)
    assert all(any((model[abs(l)] > 0) == (l > 0) for l in c) for c in clauses)
    return model


# ------------------------------------------------------------------ tests

def main():
    rng = random.Random(20261127)
    G = encode.load_gadgets()
    paper1 = json.loads((HERE.parent / "small-graphs-power-of-two-cycles" / "data" /
                         "constructions.json").read_text())
    check(G == paper1["gadgets"], "gadgets.json equals the gadgets of paper 1")

    # 1. gadgets
    paths = {}
    for name, g in G.items():
        pp = port_paths(g)
        paths[name] = pp
        iv = {k: (min(v), max(v)) for k, v in pp.items()}
        contiguous = all(sorted(v) == list(range(min(v), max(v) + 1)) for v in pp.values())
        d01, d12 = encode.port_distances(g)
        check(contiguous and iv[(0, 1)][0] == d01 and iv[(1, 2)][0] == d12 and
              min(lo for lo, _ in iv.values()) >= 2 and min(hi for _, hi in iv.values()) >= 3,
              f"{name}: port path lengths are intervals "
              f"01:{iv[(0, 1)]} 02:{iv[(0, 2)]} 12:{iv[(1, 2)]}")
        cnt, _ = cycles_by_length(gadget_adj(g), g["order"])
        check(not any(l in cnt for l in (4, 8, 16, 32)), f"{name}: cycle lengths {sorted(cnt)}")

    # 2. Tutte-Coxeter
    base = encode.tutte_coxeter()
    check(base == paper1["bases"]["tutte_coxeter"], "encode.py's TC equals paper 1's base graph")
    levi = gq22_levi()
    check(bool(isomorphisms(levi, base, first_only=True)), "GQ(2,2) incidence graph is isomorphic to it")
    cnt, found = cycles_by_length(base, 12)
    check(min(cnt) == 8 and cnt[8] == 90 and cnt[10] == 72 and 9 not in cnt and 11 not in cnt,
          f"cycles up to length 12: {dict(sorted(cnt.items()))}")
    enc_c = encode.cycles(base, (8, 10))
    check(sorted(tuple(c) for c in enc_c) == sorted(c for c in found if len(c) in (8, 10)),
          "encode.py lists exactly these 8- and 10-cycles")
    c8 = [list(c) for c in found if len(c) == 8]
    inc = {}
    for c in found:
        if len(c) == 8:
            for vo in encode.off_edges(base, list(c)):
                inc[vo] = inc.get(vo, 0) + 1
    check(len(inc) == 90 and set(inc.values()) == {8}, "each (vertex, edge) pair is off exactly 8 of the 8-cycles")
    auts = isomorphisms(base, base)
    arcs = {(f[0], f[base[0][0]]) for f in auts}
    check(len(auts) == 1440 and len(arcs) == 90, f"|Aut(TC)| = {len(auts)}, arc orbit size {len(arcs)}")
    c8c10 = [list(c) for c in found if len(c) in (8, 10)]

    # 3. lifts versus the CNF
    core, xcore, _ = encode.encode()
    seeds = []
    for name in ("tc345", "tc370"):
        L = paper1["lifts"][name]
        perm = [[(k - L["choice"][v]) % 3 for k in range(3)] for v in range(30)]
        seeds.append(Lift(base, list(L["gadget"]), perm, G))
    for s, n in zip(seeds, (345, 370)):
        check(s.n == n and s.cross_girth() >= 33, f"paper 1 lift on {n} vertices: cross girth {s.cross_girth()}")

    def units(lift, x):
        return [x[(v, *lift.state(v))] for v in range(30)]

    stats = {"accepted": 0, "rejected": 0}
    slack_cache = {}
    lifts = []
    for t in range(300):
        s = seeds[t % 2]
        f = auts[rng.randrange(len(auts))]
        inv = {b: a for a, b in f.items()}
        gad = [s.gad[inv[v]] for v in range(30)]
        perm = [[s.perm[inv[v]][base[inv[v]].index(inv[u])] for u in base[v]] for v in range(30)]
        for _ in range(rng.randint(1, 3)):
            v = rng.randrange(30)
            if rng.random() < 0.6:
                gad[v] = rng.choice(list(G))
            perm[v] = list(rng.sample(range(3), 3))
        for _ in range(rng.randint(0, 3)):
            gad[rng.randrange(30)] = "H15"
        lifts.append(Lift(base, gad, perm, G))

    bad = 0
    for lift in lifts:
        cg = lift.cross_girth()
        ws = [weight_and_c32(lift, c, paths) for c in c8c10]
        ok_c32 = all(is_cycle(lift.adj, c) and len(c) == 32 for _, c in ws if c is not None)
        w8 = min(weight_and_c32(lift, c, paths)[0] for c in c8)
        sat = dpll(core.n, core.clauses, units(lift, xcore)) is not None
        good = (cg == min(w for w, _ in ws)) and ok_c32 and (sat == (w8 >= 33))
        if sat:
            stats["accepted"] += 1
            c = lift.counts()
            key = (c["H15"], c["H7"])
            if key not in slack_cache:
                slack_cache[key] = encode.encode(max_h15=key[0], min_h7=key[1], slack=True)
            cnf, x, _ = slack_cache[key]
            good &= dpll(cnf.n, cnf.clauses, units(lift, x)) is not None
            # symmetry breaking: move a vertex of some gadget and its port-0 arc to (0, base[0][0])
            v = rng.randrange(30)
            g, p = lift.state(v)
            f = next(a for a in auts if a[v] == 0 and a[base[v][p]] == base[0][0])
            inv = {b: a for a, b in f.items()}
            moved = Lift(base, [lift.gad[inv[u]] for u in range(30)],
                         [[lift.perm[inv[u]][base[inv[u]].index(inv[w])] for w in base[u]]
                          for u in range(30)], G)
            good &= moved.cross_girth() == cg and moved.state(0) == (g, 0)
            cnf2, x2, _ = encode.encode(max_h15=key[0], min_h7=key[1], slack=True, symmetry=(g,))
            good &= dpll(cnf2.n, cnf2.clauses, units(moved, x2)) is not None
        else:
            stats["rejected"] += 1
        bad += not good
    check(bad == 0 and min(stats.values()) >= 30,
          f"{len(lifts)} lifts: weights match BFS, CNF accepts iff all 8-cycle weights >= 33, "
          f"every rejection has a 32-cycle "
          f"({stats['accepted']} accepted, {stats['rejected']} rejected)")

    # 4. cubes
    cnf, x, _ = encode.encode(**encode.INSTANCES["cubic_a19"])
    cb = encode.cubes("cubic_a19", x)
    st = [(g, p) for g in ("H15", "H7") for p in range(3)]
    cover = {}
    for tag, us in cb:
        for s1 in st:
            for s2 in st:
                for s3 in st:
                    lits = {x[(1, *s1)], x[(29, *s2)], x[(17, *s3)]}
                    if set(us) <= lits:
                        cover[(s1, s2, s3)] = cover.get((s1, s2, s3), 0) + 1
    check(len(cb) == 56 and len(cover) == 216 and set(cover.values()) == {1},
          f"{len(cb)} cubes cover each of the 216 states of (1, 29, 17) exactly once")

    # 5. cardinality encoding
    ok = True
    for n in range(1, 7):
        for k in range(-1, n + 1):
            for mask in range(1 << n):
                c = encode.CNF()
                xs = [c.var() for _ in range(n)]
                c.at_most(xs, k)
                us = [xs[i] if mask >> i & 1 else -xs[i] for i in range(n)]
                ok &= (dpll(c.n, c.clauses, us) is not None) == (bin(mask).count("1") <= k)
    check(ok, "at_most(k) is exact for n <= 6, all k and all assignments")

    print("ALL TESTS PASSED" if not FAILS else f"{len(FAILS)} FAILED")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
