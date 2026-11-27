#!/usr/bin/env python3
"""Negative controls for check_witnesses.py: each corrupted witness must be rejected.

    python3 test_checker.py

Uses two small graphs built here: the Moebius-Kantor graph GP(8,3) (16 vertices,
girth 6, shortest power-of-two cycle 8, Hamiltonian) and the Heawood graph.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_witnesses as cw  # noqa: E402


def gp83():
    adj = [[] for _ in range(16)]
    def e(u, v):
        adj[u].append(v)
        adj[v].append(u)
    for i in range(8):
        e(i, (i + 1) % 8)
        e(i, 8 + i)
        e(8 + i, 8 + (i + 3) % 8)
    return adj


def heawood():
    # Levi graph of the Fano plane: points 0..6, lines 7..13, line j = {j, j+1, j+3}
    adj = [[] for _ in range(14)]
    for j in range(7):
        for p in (j, (j + 1) % 7, (j + 3) % 7):
            adj[p].append(7 + j)
            adj[7 + j].append(p)
    return adj


def find_cycle(adj, s, L):
    on, path = {s}, [s]
    def go(x):
        if len(path) == L:
            return s in adj[x]
        for w in adj[x]:
            if w not in on:
                on.add(w); path.append(w)
                if go(w):
                    return True
                on.discard(w); path.pop()
        return False
    return list(path) if go(s) else None


def magma(adj):
    return "{ " + ", ".join("{ " + ", ".join(str(w + 1) for w in nb) + " }" for nb in adj) + " }"


def graph6(adj):
    n = len(adj)
    bits = [1 if i in adj[j] else 0 for j in range(1, n) for i in range(j)]
    bits += [0] * (-len(bits) % 6)
    return chr(n + 63) + "".join(chr(63 + int("".join(map(str, bits[k:k + 6])), 2))
                                 for k in range(0, len(bits), 6))


def run(kind, adj, rid, wit):
    payload = graph6(adj) if kind == "hog" else (magma(adj), 6)
    return cw.check_one((kind, rid, payload, wit))[1]


def main():
    mk, hw = gp83(), heawood()
    c8, c16 = find_cycle(mk, 0, 8), find_cycle(mk, 0, 16)
    assert c8 and c16 and find_cycle(mk, 0, 4) is None
    cases = [
        ("valid witness accepted", run("psv", mk, "mk", ("mk", 16, 6, 8, c8)), None),
        ("valid Heawood witness accepted",
         run("psv", hw, "hw", ("hw", 14, 6, 8, find_cycle(hw, 0, 8))), None),
        ("shorter cycle exists (16 claimed, 8 present)", run("psv", mk, "mk", ("mk", 16, 6, 16, c16)), "x"),
        ("wrong length claimed", run("psv", mk, "mk", ("mk", 16, 6, 16, c8)), "x"),
        ("non-adjacent step", run("psv", mk, "mk", ("mk", 16, 6, 8, c8[:4] + c8[5:] + c8[4:5])), "x"),
        ("repeated vertex", run("psv", mk, "mk", ("mk", 16, 6, 8, c8[:7] + c8[:1])), "x"),
        ("wrong girth reported", run("psv", mk, "mk", ("mk", 16, 8, 8, c8)), "x"),
        ("census girth disagrees", cw.check_one(("psv", "mk", (magma(mk), 7), ("mk", 16, 6, 8, c8)))[1], "x"),
        ("wrong graph id", run("psv", mk, "mk", ("other", 16, 6, 8, c8)), "x"),
        ("NONE reported", run("psv", mk, "mk", ("mk", 16, 6, None, [])), "x"),
        ("girth-9 mode rejects girth 6", run("hog", mk, "1", ("1", 16, 6, 16, c16)), "x"),
        ("graph6 round trip", run("hog", mk, "1", ("1", 16, 6, 16, c16)) != "not simple cubic", True),
    ]
    bad = 0
    for name, got, want in cases:
        ok = (got is None) if want is None else (got is True if want is True else got is not None)
        bad += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {name}" + (f"  [{got}]" if got not in (None, True) else ""))
    print("ALL NEGATIVE CONTROLS PASSED" if not bad else f"{bad} FAILED")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
