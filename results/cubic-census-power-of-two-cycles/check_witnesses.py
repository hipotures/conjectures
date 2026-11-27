#!/usr/bin/env python3
"""Independent check of the census scan (standard library only).

    python3 check_witnesses.py [--cache DIR] [--workers W]

Reads the original census files from the cache directory with its own parsers (it
does not use the scanner's input files) and the witness files written by
run_census.py, and checks for every graph:

  * the graph is simple, cubic and connected;
  * the witness is a cycle of the claimed length L in {4, 8, 16, 32};
  * the girth reported by the scanner is right and, for the vertex-transitive and
    symmetric censuses, equals the girth recorded in the census itself;
  * L is the shortest power-of-two cycle length:
      - girth >= 9 censuses: L = 16 and the girth (computed here from every vertex)
        is at least 9, so there is no 4-cycle and no 8-cycle;
      - vertex-transitive and symmetric censuses: for every power of two l < L, a
        depth-first search with distance pruning (a different algorithm from the
        scanner's) finds no l-cycle through vertex 0. By vertex-transitivity, then,
        the graph has no l-cycle at all.

It also checks that every graph of each census has exactly one witness line and that
the graph counts agree with data/sources.json. Vertex-transitivity itself is taken
from the census, not checked.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
from collections import Counter
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCES = json.loads((HERE / "data" / "sources.json").read_text())["files"]
HOG = ["cub58g9.g6", "cub60g9.g6", "cub62g9.g6.gz", "cub64g9.g6.gz"]
PSV = "main_Graph.txt"
CONDER = "AllSymmCubic-OrderUpTo10000-ByEdgeSets.txt.gz"
WITNESS_FILE = {"cub58g9.g6": "cub58g9", "cub60g9.g6": "cub60g9", "cub62g9.g6.gz": "cub62g9",
                "cub64g9.g6.gz": "cub64g9", PSV: "psv", CONDER: "conder"}


# ---------------------------------------------------------------- parsers

def graph6_edges(s: str):
    data = s.encode()
    if data[0] == 126:
        n = ((data[1] - 63) << 12) | ((data[2] - 63) << 6) | (data[3] - 63)
        body = data[4:]
    else:
        n = data[0] - 63
        body = data[1:]
    x = 0
    for c in body:
        x = (x << 6) | (c - 63)
    nbits = 6 * len(body)
    edges = []
    k = 0
    for j in range(1, n):
        for i in range(j):
            if (x >> (nbits - 1 - k)) & 1:
                edges.append((i, j))
            k += 1
    return n, edges


def magma_lists(code: str):
    """'{ { 2, 3, 4 }, { 1, 3, 4 }, ... }' -> 0-based adjacency lists (character scan)."""
    lists, cur, num, depth = [], None, "", 0
    for ch in code:
        if ch == "{":
            depth += 1
            if depth == 2:
                cur = []
        elif ch == "}":
            if depth == 2:
                if num:
                    cur.append(int(num) - 1)
                    num = ""
                lists.append(cur)
            depth -= 1
        elif ch.isdigit():
            num += ch
        elif ch == "," and depth == 2 and num:
            cur.append(int(num) - 1)
            num = ""
    return lists


def hog_graphs(path: Path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if line:
                yield str(i), line


def psv_graphs(path: Path):
    with open(path) as f:
        header = f.readline().rstrip("\n").split("|")
        ncols = len(header)
        i_girth = header.index("girth")
        i_cvt, i_magma = header.index("cvt_index"), header.index("raw_magma_code")
        for line in f:
            cols = line.rstrip("\n").split("|")
            # The two graph6/sparse6 columns (1 and 3) may contain '|'; all later
            # columns may not, so anchor the indices at the right end.
            tail = cols[len(cols) - (ncols - i_girth):]
            if tail[i_cvt - i_girth]:
                yield "psv:" + cols[0], tail[i_magma - i_girth], int(tail[0])


def conder_graphs(path: Path):
    with gzip.open(path, "rt") as f:
        name, n, buf, girth = None, None, None, None
        for line in f:
            if line.startswith("// C") and " : " in line:
                name = line[3:line.index(" : ")]
                girth = int(line.split(": Girth ", 1)[1].split()[0])
            elif line.startswith("CubicAT["):
                n = int(line.split("Graph<", 1)[1].split("|", 1)[0])
                buf = [line.split("|", 1)[1]]
                if ">;" in line:
                    yield name, n, "".join(buf), girth
                    buf = None
            elif buf is not None:
                buf.append(line)
                if ">;" in line:
                    yield name, n, "".join(buf), girth
                    buf = None


def conder_edges(text: str):
    edges = []
    for chunk in text.split("{")[2:]:
        a, b = chunk.split("}", 1)[0].split(",")
        edges.append((int(a) - 1, int(b) - 1))
    return edges


# ---------------------------------------------------------------- checks

def adjacency(n, edges):
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    return adj


def check_cubic_simple_connected(adj):
    n = len(adj)
    for v, nb in enumerate(adj):
        if len(nb) != 3 or len(set(nb)) != 3 or v in nb:
            return "not simple cubic"
        if any(not 0 <= w < n or v not in adj[w] for w in nb):
            return "adjacency lists out of range or not symmetric"
    seen = {0}
    stack = [0]
    while stack:
        for w in adj[stack.pop()]:
            if w not in seen:
                seen.add(w)
                stack.append(w)
    return None if len(seen) == len(adj) else "not connected"


def check_cycle(adj, cyc, L):
    if len(cyc) != L or len(set(cyc)) != L:
        return False
    if any(not 0 <= v < len(adj) for v in cyc):
        return False
    return all(cyc[(i + 1) % L] in adj[cyc[i]] for i in range(L))


def bfs(adj, s):
    dist = [-1] * len(adj)
    dist[s] = 0
    order = [s]
    for v in order:
        for w in adj[v]:
            if dist[w] < 0:
                dist[w] = dist[v] + 1
                order.append(w)
    return dist


def shortest_cycle_through(adj, s):
    """Length of a shortest cycle through s: the least dist(a)+dist(b)+1 over edges ab
    whose endpoints lie in different branches of the BFS tree at s, or 2*dist(a) over
    vertices a reached from two different branches."""
    n = len(adj)
    dist, branch = [-1] * n, [-1] * n
    dist[s] = 0
    order = []
    for i, w in enumerate(adj[s]):
        dist[w], branch[w] = 1, i
        order.append(w)
    best = None
    for v in order:
        for w in adj[v]:
            if w == s:
                continue
            if dist[w] < 0:
                dist[w], branch[w] = dist[v] + 1, branch[v]
                order.append(w)
            elif branch[w] != branch[v]:
                cand = dist[v] + dist[w] + 1
                if best is None or cand < best:
                    best = cand
    return best


def girth_all(adj):
    best = None
    for s in range(len(adj)):
        g = shortest_cycle_through(adj, s)
        if g is not None and (best is None or g < best):
            best = g
    return best


def has_cycle_through(adj, s, L, dist):
    """Is there a cycle of length L through s? Depth-first search over simple paths
    s = x0, x1, ..., x_{L-1}, pruned by dist(x_d, s) <= L - d."""
    on = [False] * len(adj)
    on[s] = True

    def go(x, d):
        if d == L - 1:
            return s in adj[x]
        for w in adj[x]:
            if not on[w] and dist[w] <= L - d - 1:
                on[w] = True
                if go(w, d + 1):
                    return True
                on[w] = False
        return False

    return go(s, 0)


def check_one(task):
    kind, rid, payload, wit = task
    meta_girth = None
    if kind == "hog":
        n, edges = graph6_edges(payload)
        adj = adjacency(n, edges)
    elif kind == "psv":
        code, meta_girth = payload
        adj = magma_lists(code)
        n = len(adj)
    else:
        n, text, meta_girth = payload
        adj = adjacency(n, conder_edges(text))
    err = check_cubic_simple_connected(adj)
    if err:
        return rid, err, None
    w_id, w_n, w_g, w_L, w_cyc = wit
    if w_id != rid or w_n != n:
        return rid, "witness line does not match the graph", None
    if w_L is None:
        return rid, "no power-of-two cycle up to 32 reported", None
    if w_L not in (4, 8, 16, 32) or not check_cycle(adj, w_cyc, w_L):
        return rid, "witness is not a cycle of the claimed length", None
    if kind == "hog":
        g = girth_all(adj)
        if g != w_g or g < 9 or w_L != 16:
            return rid, f"girth {g} / length {w_L} inconsistent", None
    else:
        g = shortest_cycle_through(adj, 0)
        if g != w_g or g != meta_girth:
            return rid, f"girth {g} differs from scanner's {w_g} or the census's {meta_girth}", None
        dist = bfs(adj, 0)
        for l in (4, 8, 16):
            if l < w_L and has_cycle_through(adj, 0, l, dist):
                return rid, f"has a {l}-cycle through vertex 0 but the scanner reported {w_L}", None
        if not has_cycle_through(adj, 0, w_L, dist):
            return rid, f"own search finds no {w_L}-cycle through vertex 0", None
    return rid, None, (n, g, w_L)


# ---------------------------------------------------------------- driver

def read_witnesses(path: Path):
    for line in open(path):
        rid, n, g, L, *rest = line.rstrip("\n").split("\t")
        cyc = [int(x) for x in rest[0].split(",")] if rest else []
        yield rid, int(n), int(g), (None if L == "NONE" else int(L)), cyc


def tasks(name, cache: Path, work: Path):
    wits = read_witnesses(work / (WITNESS_FILE[name] + ".witnesses.tsv"))
    if name in HOG:
        graphs = (("hog", rid, s) for rid, s in hog_graphs(cache / name))
    elif name == PSV:
        graphs = (("psv", rid, (code, g)) for rid, code, g in psv_graphs(cache / name))
    else:
        graphs = (("conder", nm, (n, text, g)) for nm, n, text, g in conder_graphs(cache / name))
    sentinel = object()
    for g in graphs:
        w = next(wits, sentinel)
        if w is sentinel:
            raise SystemExit(f"{name}: fewer witness lines than graphs")
        yield (*g, w)
    if next(wits, sentinel) is not sentinel:
        raise SystemExit(f"{name}: more witness lines than graphs")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=os.environ.get("CENSUS_CACHE",
                                                     str(Path.home() / ".cache" / "conjectures-census")))
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    ap.add_argument("--only", nargs="*", help="check only these source files")
    args = ap.parse_args()
    cache = Path(args.cache)
    work = cache / "work"
    failures = 0
    with Pool(args.workers) as pool:
        for name in args.only or list(WITNESS_FILE):
            cnt = Counter()
            total = 0
            for rid, err, info in pool.imap(check_one, tasks(name, cache, work), chunksize=256):
                total += 1
                if err:
                    failures += 1
                    if failures <= 20:
                        print(f"FAIL {name} {rid}: {err}", flush=True)
                else:
                    cnt[info[2]] += 1
            expected = SOURCES[name]["graphs"]
            if total != expected:
                failures += 1
                print(f"FAIL {name}: {total} graphs, data/sources.json says {expected}")
            print(f"{'ok  ' if total == expected else 'FAIL'} {name}: {total} graphs, "
                  f"shortest power-of-two cycle {dict(sorted(cnt.items()))}", flush=True)
    print("ALL WITNESSES CHECKED" if failures == 0 else f"{failures} FAILURES")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
