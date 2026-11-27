#!/usr/bin/env python3
"""Independent re-implementation of both searches, for small caps.

This file shares no code with `src/`. It implements the restricted-growth schedule
from its description in the paper (Section 3) and decides every cycle test with a
different method: instead of enumerating Berge cycles, it asks whether the Levi
graph of the current configuration has a simple path of length L - 2 between two
points of the candidate block (adding the block closes an L-cycle exactly then).

It checks three things, using only the Python standard library:

1. Branch A (Berge triangle, root orbits 1 and 2) for caps 20, 22, 24, 26: the
   counters must equal those printed by `src/triangle_search.cpp`, which in turn
   agree with Tranquilli's program (recorded in `data/expected_counts.json`).
2. Branch B (girth >= 10 root) for caps 31, 32, 33: same comparison with
   `src/girth10_search.cpp`.
3. Coverage on known graphs: each of the three (3,10)-cages (70 vertices,
   `data/cagesk3g10.g6`) is relabelled as in the coverage argument of the paper,
   for every choice of root block, and replayed through the Branch B schedule
   with the C16 test switched off. Every replay must be accepted and end in a
   completed configuration. With the C16 test on, every replay must instead be
   stopped by a 16-cycle (the cages contain 16-cycles).

Run: python3 independent_check.py   (about two minutes)
"""
from __future__ import annotations

import json
import sys
from itertools import permutations
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPECTED = json.loads((HERE / "data" / "expected_counts.json").read_text())


class Config:
    """A partial linear 3-uniform configuration; Levi graph vertices are
    ('p', i) for points and ('b', j) for blocks."""

    def __init__(self, cap: int):
        self.cap = cap
        self.blocks: list[tuple[int, int, int]] = []
        self.pt_blocks: dict[int, list[int]] = {}
        self.pairs: set[frozenset] = set()
        self.introduced = 0

    def deg(self, p: int) -> int:
        return len(self.pt_blocks.get(p, ()))

    def add(self, blk: tuple[int, int, int]) -> None:
        j = len(self.blocks)
        self.blocks.append(blk)
        for p in blk:
            self.pt_blocks.setdefault(p, []).append(j)
        for a in blk:
            for b in blk:
                if a < b:
                    self.pairs.add(frozenset((a, b)))

    def remove(self) -> None:
        blk = self.blocks.pop()
        for p in blk:
            self.pt_blocks[p].pop()
        for a in blk:
            for b in blk:
                if a < b:
                    self.pairs.discard(frozenset((a, b)))

    # --- cycle test: simple path of exact length in the Levi graph ----------------
    def nbrs(self, v):
        kind, i = v
        if kind == "p":
            return [("b", j) for j in self.pt_blocks.get(i, ())]
        return [("p", p) for p in self.blocks[i]]

    def dist_from(self, t):
        dist = {t: 0}
        frontier = [t]
        while frontier:
            nxt = []
            for v in frontier:
                for w in self.nbrs(v):
                    if w not in dist:
                        dist[w] = dist[v] + 1
                        nxt.append(w)
            frontier = nxt
        return dist

    def has_path(self, s: int, t: int, length: int) -> bool:
        """Is there a simple s-t path with exactly `length` edges?"""
        S, T = ("p", s), ("p", t)
        dist = self.dist_from(T)
        if S not in dist or dist[S] > length:
            return False
        seen = {S}

        def dfs(v, left):
            if left == 0:
                return v == T
            for w in self.nbrs(v):
                if w in seen or w not in dist or dist[w] > left - 1:
                    continue
                if w == T and left != 1:
                    continue
                seen.add(w)
                ok = dfs(w, left - 1)
                seen.discard(w)
                if ok:
                    return True
            return False

        return dfs(S, length)

    def closes_cycle(self, blk, length: int) -> bool:
        a, b, c = blk
        return any(self.has_path(x, y, length - 2) for x, y in ((a, b), (a, c), (b, c)))


def run(cfg: Config, start_point: int, tests: tuple[int, ...], deficit_bound: bool,
        replay=None):
    """Restricted-growth search. `tests` are the cycle lengths tested in order
    (e.g. (8, 16) or (6, 8, 16)). Returns the counters. If `replay` is given it is a
    function choosing the single block to follow at each state (coverage replay)."""
    cnt = dict(states=0, attempted=0, structural=0, completions=0)
    for L in tests:
        cnt[f"c{L}"] = 0

    def rec(point, last):
        cnt["states"] += 1
        while point < cfg.introduced and cfg.deg(point) == 3:
            point += 1
            last = None
        if point >= cfg.introduced:
            if len(cfg.blocks) == cfg.introduced:
                cnt["completions"] += 1
            return
        if len(cfg.blocks) >= cfg.cap:
            return
        if deficit_bound:
            deficit = sum(3 - cfg.deg(u) for u in range(point, cfg.introduced))
            if deficit > 3 * (cfg.cap - len(cfg.blocks)):
                return
        old = cfg.introduced
        cands = [q for q in range(point + 1, old)
                 if cfg.deg(q) < 3 and frozenset((point, q)) not in cfg.pairs]
        if old < cfg.cap:
            cands.append(old)
        if old + 1 < cfg.cap:
            cands.append(old + 1)
        proposals = []
        for i in range(len(cands)):
            for j in range(i + 1, len(cands)):
                q, r = cands[i], cands[j]
                if r == old + 1 and q != old:
                    continue
                if last is not None and (q, r) <= last:
                    continue
                proposals.append((q, r))
        want = replay(cfg, point, old, proposals) if replay else None
        if want is not None and want not in proposals:
            raise AssertionError(f"replay block {(point, *want)} is not a proposal")
        for q, r in proposals:
            if want is not None and (q, r) != want:
                continue
            cnt["attempted"] += 1
            blk = (point, q, r)
            olds = [x for x in blk if x < old]
            if any(cfg.deg(x) >= 3 for x in olds) or any(
                    frozenset((x, y)) in cfg.pairs for x in olds for y in olds if x < y):
                cnt["structural"] += 1
                continue
            hit = next((L for L in tests if cfg.closes_cycle(blk, L)), None)
            if hit is not None:
                cnt[f"c{hit}"] += 1
                continue
            nxt = old + (1 if old in (q, r) else 0) + (1 if r == old + 1 else 0)
            cfg.introduced = nxt
            cfg.add(blk)
            rec(point, (q, r))
            cfg.remove()
            cfg.introduced = old

    return cnt, rec


TRIANGLE_ROOT = [(0, 1, 3), (1, 2, 4), (0, 2, 5)]
ORBIT_BLOCK = {1: ((0, 4, 6), 7), 2: ((0, 6, 7), 8)}
GIRTH10_ROOT = [(0, 1, 2), (0, 3, 4), (0, 5, 6), (1, 7, 8), (1, 9, 10), (2, 11, 12), (2, 13, 14),
                (3, 15, 16), (3, 17, 18), (4, 19, 20), (4, 21, 22), (5, 23, 24), (5, 25, 26),
                (6, 27, 28), (6, 29, 30)]


def branch_a(cap: int) -> dict:
    total = {}
    for orbit in (1, 2):
        cfg = Config(cap)
        blk, intro = ORBIT_BLOCK[orbit]
        for b in TRIANGLE_ROOT + [blk]:
            cfg.add(b)
        cfg.introduced = intro
        cnt, rec = run(cfg, 1, (8, 16), deficit_bound=False)
        rec(1, (2, 4))
        for k, v in cnt.items():
            total[k] = total.get(k, 0) + v
    return total


def branch_b(cap: int) -> dict:
    cfg = Config(cap)
    for b in GIRTH10_ROOT:
        cfg.add(b)
    cfg.introduced = 31
    cnt, rec = run(cfg, 7, (6, 8, 16), deficit_bound=True)
    rec(7, None)
    return cnt


# --- coverage replay on the (3,10)-cages ------------------------------------------

def decode_g6(line: str) -> list[set[int]]:
    data = [ord(c) - 63 for c in line.strip()]
    if data[0] == 63:
        n = (data[1] << 12) | (data[2] << 6) | data[3]
        data = data[4:]
    else:
        n = data[0]
        data = data[1:]
    bits = [(x >> (5 - i)) & 1 for x in data for i in range(6)]
    adj = [set() for _ in range(n)]
    k = 0
    for j in range(1, n):
        for i in range(j):
            if bits[k]:
                adj[i].add(j)
                adj[j].add(i)
            k += 1
    return adj


def two_colour(adj):
    col = {0: 0}
    stack = [0]
    while stack:
        v = stack.pop()
        for w in adj[v]:
            if w not in col:
                col[w] = 1 - col[v]
                stack.append(w)
            elif col[w] == col[v]:
                raise AssertionError("not bipartite")
    return col


def replay_cage(adj, root_block, flip, tests=(6, 8)):
    """Relabel the cage from `root_block` as in the coverage argument and follow it
    through the Branch B schedule with the C16 test off. `flip` picks the colour
    class used as points."""
    col = two_colour(adj)
    side = [v for v in range(len(adj)) if col[v] == flip]
    blocks_t = [frozenset(adj[y]) for y in range(len(adj)) if col[y] != flip]
    label: dict[int, int] = {}
    # Root: block {0,1,2}; two more blocks through each of 0, 1, 2 (points 3..14);
    # two more blocks through each of 3, 4, 5, 6 (points 15..30).
    B0 = blocks_t[root_block]
    for i, x in enumerate(sorted(B0)):
        label[x] = i
    used = {B0}
    nxt = 3

    def blocks_through(x):
        return [B for B in blocks_t if x in B and B not in used]

    inv = {}
    for lab in range(7):
        x = next(k for k, v in label.items() if v == lab)
        for B in sorted(blocks_through(x), key=sorted):
            for y in sorted(B - {x}):
                assert y not in label, "root points not distinct (girth < 10?)"
                label[y] = nxt
                nxt += 1
            used.add(B)
    assert nxt == 31
    target = {tuple(sorted(label[x] for x in B)) for B in used}
    assert target == set(GIRTH10_ROOT), "root does not match the normal form"
    remaining = [B for B in blocks_t if B not in used]

    def chooser(cfg, point, old, proposals):
        x = next(k for k, v in label.items() if v == point)
        todo = [B for B in remaining if x in B and B not in used]
        assert todo, "unsaturated point with no remaining target block"

        def key(B):
            labs = sorted(label.get(y, 10**6) for y in B - {x})
            return labs
        B = min(todo, key=key)
        fresh = sorted((y for y in B - {x} if y not in label), key=lambda y: y)
        for k, y in enumerate(fresh):
            label[y] = old + k
        used.add(B)
        q, r = sorted(label[y] for y in B - {x})
        return (q, r)

    cfg = Config(len(side))
    for b in GIRTH10_ROOT:
        cfg.add(b)
    cfg.introduced = 31
    cnt, rec = run(cfg, 7, tests, deficit_bound=True, replay=chooser)
    rec(7, None)
    return cnt


def main() -> int:
    ok = True

    def report(name, got, want):
        nonlocal ok
        good = all(got.get(k) == v for k, v in want.items())
        ok &= good
        print(f"{'ok  ' if good else 'FAIL'} {name}: {got}")

    for cap, want in EXPECTED["branch_a_small"].items():
        report(f"branch A cap {cap}", branch_a(int(cap)), want)
    for cap, want in EXPECTED["branch_b_small"].items():
        report(f"branch B cap {cap}", branch_b(int(cap)), want)

    cages = (HERE / "data" / "cagesk3g10.g6").read_text().split()
    for gi, line in enumerate(cages):
        adj = decode_g6(line)
        assert len(adj) == 70 and all(len(a) == 3 for a in adj)
        runs = 0
        for flip in (0, 1):
            for rb in range(35):
                cnt = replay_cage(adj, rb, flip)
                if cnt["completions"] != 1 or cnt["c6"] or cnt["c8"] or cnt["structural"]:
                    ok = False
                    print(f"FAIL cage {gi} root {rb} side {flip}: {cnt}")
                # Negative control: with the 16-cycle test on, the same replay must be
                # stopped by a 16-cycle (Theorem 1.3), so the replay is not vacuous.
                cnt16 = replay_cage(adj, rb, flip, tests=(6, 8, 16))
                if cnt16["completions"] != 0 or cnt16["c16"] != 1 or cnt16["c6"] or cnt16["c8"]:
                    ok = False
                    print(f"FAIL cage {gi} root {rb} side {flip} with C16 test: {cnt16}")
                runs += 1
        print(f"ok   (3,10)-cage {gi}: reached as a completion from all {runs} roots;"
              " with the C16 test on, every replay is stopped by a 16-cycle")
    print("ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
