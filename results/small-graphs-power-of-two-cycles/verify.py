#!/usr/bin/env python3
"""Independent checker for the constructions in this result (no Lean, no dependencies).

Usage:  python3 verify.py            (full check, a few minutes)
        python3 verify.py --quick    (skips the exhaustive 16-cycle searches)

The checker rebuilds every witness from `data/constructions.json` (which
`scripts/extract_lean_data.py` extracts from the Lean sources) and verifies it
with code written independently of the Lean proofs:

1. Gadgets: port degrees, internal degrees, exact port-to-port distances by
   BFS, and the full internal cycle spectrum by exhaustive enumeration.
2. Lifts: the lifted graph is built from scratch; order, degrees,
   2-connectivity (no cut vertex, by Tarjan's algorithm), and equality with the
   committed graph6 certificate.
3. Forbidden cycles, by two methods:
   (a) direct exhaustive search for cycles of length 4, 8, 16 where feasible;
   (b) base-cycle analysis: every cycle of the lift that is not inside one
       gadget projects to a base cycle D and has length at least
       w(D) = sum over v in D of (1 + d_v(in, out)), where d_v is the
       port-to-port distance in the gadget at v. All base cycles short enough to
       matter are enumerated and w(D) is checked to exceed the target length.
4. The 702-vertex base: equality with the House of Graphs file, girth 16,
   the orientation has no directed cycle of length <= 16, the sources have
   in-degree 0 and pairwise distance >= 9, and every 16-cycle D satisfies
   w(D) >= 65; longer base cycles are handled by the inequality in the paper.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import deque
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = json.loads((HERE / "data" / "constructions.json").read_text())
FAILURES: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        FAILURES.append(msg)


# ---------------------------------------------------------------- graph basics

def adjacency(n: int, edges) -> list[list[int]]:
    adj = [[] for _ in range(n)]
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    return adj


def bfs(adj, s: int) -> list[int]:
    dist = [-1] * len(adj)
    dist[s] = 0
    q = deque([s])
    while q:
        u = q.popleft()
        for v in adj[u]:
            if dist[v] < 0:
                dist[v] = dist[u] + 1
                q.append(v)
    return dist


def has_cycle_of_length(adj, L: int) -> bool:
    """Exhaustive search: is there a simple cycle of length exactly L?
    Each cycle is found from its smallest vertex s, using only vertices > s;
    BFS distance to s prunes paths that cannot close in time."""
    n = len(adj)
    for s in range(n):
        dist = bfs(adj, s)
        on = [False] * n
        on[s] = True

        def dfs(u: int, depth: int) -> bool:
            if depth == L - 1:
                return s in adj[u]
            for v in adj[u]:
                if v > s and not on[v] and dist[v] <= L - depth - 1:
                    on[v] = True
                    if dfs(v, depth + 1):
                        return True
                    on[v] = False
            return False

        if dfs(s, 0):
            return True
    return False


def cycle_lengths(adj) -> set[int]:
    """All simple cycle lengths (exhaustive; small graphs only)."""
    n, found = len(adj), set()
    for s in range(n):
        on = [False] * n
        on[s] = True

        def dfs(u: int, depth: int) -> None:
            for v in adj[u]:
                if v == s and depth >= 2:
                    found.add(depth + 1)
                elif v > s and not on[v]:
                    on[v] = True
                    dfs(v, depth + 1)
                    on[v] = False

        dfs(s, 0)
    return found


def simple_cycles_up_to(adj, maxlen: int):
    """Yield every simple cycle (as a vertex list) of length <= maxlen once
    (smallest vertex first, second vertex < last vertex)."""
    n = len(adj)
    for s in range(n):
        dist = bfs(adj, s)
        path = [s]
        on = [False] * n
        on[s] = True

        def dfs(u: int):
            for v in adj[u]:
                if v == s and len(path) >= 3 and path[1] < path[-1]:
                    yield list(path)
                elif v > s and not on[v] and len(path) + dist[v] <= maxlen:
                    on[v] = True
                    path.append(v)
                    yield from dfs(v)
                    path.pop()
                    on[v] = False

        yield from dfs(s)


def is_2_connected(adj) -> bool:
    n = len(adj)
    if n < 3:
        return False
    disc, low, cut = [-1] * n, [0] * n, False
    sys.setrecursionlimit(max(10000, 4 * n))
    timer = [0]

    def dfs(u: int, parent: int) -> None:
        nonlocal cut
        disc[u] = low[u] = timer[0]
        timer[0] += 1
        children = 0
        for v in adj[u]:
            if disc[v] < 0:
                children += 1
                dfs(v, u)
                low[u] = min(low[u], low[v])
                if parent >= 0 and low[v] >= disc[u]:
                    cut = True
            elif v != parent:
                low[u] = min(low[u], disc[v])
        if parent < 0 and children > 1:
            cut = True

    dfs(0, -1)
    return not cut and all(d >= 0 for d in disc)


def encode_graph6(adj) -> str:
    n = len(adj)
    assert n < 258048
    out = [n + 63] if n <= 62 else [126, (n >> 12) + 63, ((n >> 6) & 63) + 63, (n & 63) + 63]
    bits = [1 if u in adj[v] else 0 for v in range(1, n) for u in range(v)]
    bits += [0] * (-len(bits) % 6)
    out += [63 + int("".join(map(str, bits[i:i + 6])), 2) for i in range(0, len(bits), 6)]
    return "".join(map(chr, out)) + "\n"


def decode_graph6(s: str) -> list[set[int]]:
    s = s.strip()
    b = [ord(c) - 63 for c in s]
    if b[0] != 63:
        n, pos = b[0], 1
    else:
        n, pos = (b[1] << 12) | (b[2] << 6) | b[3], 4
    adj = [set() for _ in range(n)]
    buf = left = 0
    for v in range(1, n):
        for u in range(v):
            if left == 0:
                buf, left, pos = b[pos], 6, pos + 1
            left -= 1
            if (buf >> left) & 1:
                adj[u].add(v)
                adj[v].add(u)
    return adj


# ---------------------------------------------------------------- gadgets

GADGETS = {}
for name, g in DATA["gadgets"].items():
    GADGETS[name] = {"order": g["order"], "adj": adjacency(g["order"], g["edges"]),
                     "ports": g["ports"]}
GADGETS["U1"] = {"order": 1, "adj": [[]], "ports": [0, 0, 0]}


def port_dist(name: str, a: int, b: int) -> int:
    if name == "U1":
        return 0
    g = GADGETS[name]
    return bfs(g["adj"], g["ports"][a])[g["ports"][b]]


def check_gadgets() -> None:
    print("Gadgets")
    expect = {"H7": ([2, 2, 3], {3, 5, 6, 7}),
              "H8star": ([3, 3, 2], None),
              "H15": ([3, 3, 5], {3, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15})}
    for name, (dists, spectrum) in expect.items():
        g = GADGETS[name]
        adj, ports = g["adj"], g["ports"]
        check(all(len(adj[p]) == 2 for p in ports), f"{name}: every port has internal degree 2")
        others = [len(adj[x]) for x in range(g["order"]) if x not in ports]
        check(min(others) >= 3, f"{name}: every non-port vertex has degree >= 3 (degrees {sorted(set(others))})")
        got = [port_dist(name, 0, 1), port_dist(name, 0, 2), port_dist(name, 1, 2)]
        check(got == dists, f"{name}: port distances d(0,1), d(0,2), d(1,2) = {got}")
        lens = cycle_lengths(adj)
        check(not lens & {4, 8, 16}, f"{name}: internal cycle lengths {sorted(lens)} avoid 4, 8, 16")
        if spectrum is not None:
            check(lens == spectrum, f"{name}: cycle spectrum matches García's table")


# ---------------------------------------------------------------- lifts

def build_lift(base, gadget, choice):
    """Vertex (v, x) gets number offset[v] + x, matching the Lean encoding."""
    offset, total = [], 0
    for v in range(len(base)):
        offset.append(total)
        total += GADGETS[gadget[v]]["order"]

    def slot(v: int, k: int) -> int:          # base neighbour index k -> port slot
        return (k + 3 - choice[v] % 3) % 3

    def port_vertex(v: int, w: int) -> int:
        k = base[v].index(w)
        return offset[v] + GADGETS[gadget[v]]["ports"][slot(v, k)]

    edges = set()
    for v in range(len(base)):
        for a, b in (e for x, nb in enumerate(GADGETS[gadget[v]]["adj"]) for e in ((x, y) for y in nb)):
            if a < b:
                edges.add((offset[v] + a, offset[v] + b))
        for w in base[v]:
            if v < w:
                edges.add(tuple(sorted((port_vertex(v, w), port_vertex(w, v)))))
    return total, adjacency(total, sorted(edges)), slot


def base_weight(base, gadget, slot, cycle) -> int:
    """w(D): lower bound on the length of any lifted cycle projecting to D."""
    L, w = len(cycle), 0
    for i, v in enumerate(cycle):
        prev, nxt = cycle[i - 1], cycle[(i + 1) % L]
        a, b = slot(v, base[v].index(prev)), slot(v, base[v].index(nxt))
        w += 1 + port_dist(gadget[v], a, b)
    return w


CERTS = {
    "pet73v1": "delta3_k4_n73_petersen_3H8star_7H7.g6",
    "pet73v2": "delta3_k4_n73_petersen_1U1_9H8star.g6",
    "pet78": "cubic_k4_n78_petersen_1H15_9H7.g6",
    "tc345": "delta3_k5_n345_tuttecoxeter_15H15_15H8star.g6",
    "tc370": "cubic_k5_n370_tuttecoxeter_20H15_10H7.g6",
}
WRITE_CERTS = False

LIFTS = [
    # name, order, cubic?, forbidden lengths, max base cycle length to examine
    ("pet73v1", 73, False, [4, 8, 16], 10),
    ("pet73v2", 73, False, [4, 8, 16], 10),
    ("pet78", 78, True, [4, 8, 16], 10),
    ("tc345", 345, False, [4, 8, 16, 32], 10),
    ("tc370", 370, True, [4, 8, 16, 32], 10),
]


def check_lifts(quick: bool) -> None:
    for name, order, cubic, forbidden, maxbase in LIFTS:
        spec = DATA["lifts"][name]
        base = DATA["bases"][spec["base"]]
        n, adj, slot = build_lift(base, spec["gadget"], spec["choice"])
        print(f"Lift {name} ({spec['base']} base)")
        check(n == order, f"order = {n}")
        degs = sorted({len(a) for a in adj})
        check(degs == [3] if cubic else min(degs) >= 3, f"degrees {degs}" + (" (cubic)" if cubic else " (min degree >= 3)"))
        check(is_2_connected(adj), "2-connected")
        if name in CERTS:
            path = HERE / "certificates" / CERTS[name]
            if WRITE_CERTS:
                path.write_text(encode_graph6([set(a) for a in adj]))
            cert = decode_graph6(path.read_text())
            check(cert == [set(a) for a in adj], f"identical to certificates/{CERTS[name]}")
        # (b) base-cycle analysis
        target = max(forbidden)
        bad, count, minw = [], 0, 10**9
        base_adj = [list(t) for t in base]
        min_step = min(1 + min(port_dist(g, a, b) for a, b in ((0, 1), (0, 2), (1, 2)))
                       for g in spec["gadget"])
        if min_step * (maxbase + 1) <= target and maxbase < len(base):
            maxbase = len(base)   # cannot cut off by length: examine every base cycle
        for cyc in simple_cycles_up_to(base_adj, maxbase):
            count += 1
            w = base_weight(base, spec["gadget"], slot, cyc)
            minw = min(minw, w)
            if w <= target:
                bad.append(cyc)
        check(not bad, f"base-cycle analysis: {count} base cycles of length <= {maxbase}, "
                       f"min lifted length {minw} > {target}; longer base cycles lift to length "
                       f">= {min_step} * {maxbase + 1} > {target}" if maxbase < len(base) else
              f"base-cycle analysis: all {count} base cycles, min lifted length {minw} > {target}")
        # (a) direct search
        for L in forbidden:
            if L == 32 or (quick and L == 16):
                continue
            t0 = time.time()
            check(not has_cycle_of_length(adj, L), f"direct search: no {L}-cycle ({time.time() - t0:.1f}s)")


# ---------------------------------------------------------------- f_cubic(6) <= 10498

def check_f6(quick: bool) -> None:
    print("Base k3_g16_n702 and f_cubic(6) <= 10,498")
    base = DATA["bases"]["k3_g16_n702"]
    hog = HERE / "data" / "k3_g16_n702.g6"
    raw = hog.read_text()
    check(hashlib.sha256(raw.encode()).hexdigest().startswith("b94c67a6"),
          "data/k3_g16_n702.g6 has the House of Graphs SHA-256 b94c67a6...")
    check(decode_graph6(raw) == [set(t) for t in base], "Lean adjacency equals the House of Graphs graph")
    adj = [list(t) for t in base]
    n = len(adj)
    girth = 10**9
    for s in range(n):
        dist, par = [-1] * n, [-1] * n
        dist[s] = 0
        q = deque([s])
        while q:
            u = q.popleft()
            for v in adj[u]:
                if dist[v] < 0:
                    dist[v], par[v] = dist[u] + 1, u
                    q.append(v)
                elif par[u] != v:
                    girth = min(girth, dist[u] + dist[v] + 1)
    check(girth == 16, f"girth = {girth}")
    chosen, S = DATA["f6"]["chosen"], DATA["f6"]["sources"]
    check(all(chosen[u] in adj[u] for u in range(n)), "orientation: every vertex points to a neighbour")
    ok = True
    for u in range(n):
        x = u
        for _ in range(16):
            x = chosen[x]
            if x == u:
                ok = False
    check(ok, "orientation has no directed cycle of length <= 16")
    indeg = [0] * n
    for u in range(n):
        indeg[chosen[u]] += 1
    check(all(indeg[s] == 0 for s in S), f"sources {S} have in-degree 0")
    pd = min(bfs(adj, a)[b] for a, b in combinations(S, 2))
    check(pd >= 9, f"sources pairwise distance >= 9 (min {pd})")
    gadget = ["H7" if v in S else "H15" for v in range(n)]
    choice = [base[v].index(chosen[v]) for v in range(n)]
    N, ladj, slot = build_lift(base, gadget, choice)
    check(N == 10498, f"lift order = {N}")
    check({len(a) for a in ladj} == {3}, "lift is cubic")
    check(not has_cycle_of_length(ladj, 4) and not has_cycle_of_length(ladj, 8),
          "direct search: no 4-cycle, no 8-cycle")
    # Every lifted cycle outside a gadget projects to a base cycle of length >= 16,
    # so it has length >= 3*16 = 48 > 32; only length 64 needs an argument.
    if quick:
        print("  skip 16-cycle enumeration (--quick)")
        return
    t0 = time.time()
    count, minw = 0, 10**9
    for cyc in simple_cycles_up_to(adj, 16):
        count += 1
        minw = min(minw, base_weight(base, gadget, slot, cyc))
    check(minw >= 65, f"all {count} base 16-cycles lift to length >= {minw} > 64 ({time.time() - t0:.0f}s)")
    print("  note: base cycles of length l >= 17 lift to length >= 4l - floor(l/9) >= 67 > 64,"
          " because H15 contributes >= 4 per vertex, H7 >= 3, and a base cycle meets at most"
          " floor(l/9) sources (pairwise distance >= 9).")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--write-certificates", action="store_true",
                    help="(re)write certificates/*.g6 from the construction data")
    args = ap.parse_args()
    global WRITE_CERTS
    WRITE_CERTS = args.write_certificates
    t0 = time.time()
    check_gadgets()
    check_lifts(args.quick)
    check_f6(args.quick)
    print(f"\n{'ALL CHECKS PASSED' if not FAILURES else f'{len(FAILURES)} CHECK(S) FAILED'}"
          f" in {time.time() - t0:.0f}s")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
