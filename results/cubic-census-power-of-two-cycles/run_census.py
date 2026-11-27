#!/usr/bin/env python3
"""Run the census scans end to end and write the summaries in data/.

    python3 run_census.py [--cache DIR] [--workers W]

1. Fetch the six input files listed in data/sources.json into the cache directory
   (default: $CENSUS_CACHE or ~/.cache/conjectures-census), unless a file with the
   right SHA-256 is already there. About 2.6 GB in total.
2. Convert each census to the scanner's input format (`id<TAB>graph`).
3. Compile src/census_scan.cpp and scan: the cubic graphs of girth at least 9 in
   general mode (cycles through every vertex), the vertex-transitive and symmetric
   censuses in vertex-transitive mode (cycles through vertex 0).
4. Run check_witnesses.py, which re-reads the original files with its own parsers,
   checks every witness cycle, and for the vertex-transitive censuses confirms by a
   separate search that no shorter power-of-two cycle passes through vertex 0.
5. Write data/summary.json (counts by girth and by order) and data/shortest32.tsv.

Takes about 3.5 minutes on 16 cores once the files are downloaded.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCES = json.loads((HERE / "data" / "sources.json").read_text())["files"]
HOG = ["cub58g9.g6", "cub60g9.g6", "cub62g9.g6.gz", "cub64g9.g6.gz"]
PSV = "main_Graph.txt"
CONDER = "AllSymmCubic-OrderUpTo10000-ByEdgeSets.txt.gz"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(cache: Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    for name, meta in SOURCES.items():
        path = cache / name
        if not path.exists():
            print(f"downloading {meta['url']}", flush=True)
            req = urllib.request.Request(meta["url"], headers={"User-Agent": "census-check"})
            with urllib.request.urlopen(req) as r, open(path, "wb") as f:
                shutil.copyfileobj(r, f)
        got = sha256(path)
        if got != meta["sha256"]:
            sys.exit(f"{name}: SHA-256 {got} differs from data/sources.json")
        print(f"ok   {name}", flush=True)


def open_text(path: Path):
    return gzip.open(path, "rt") if path.suffix == ".gz" else open(path)


def psv_rows(path: Path):
    """Yield (psv_id, adjacency lists 0-based) for the PSV census rows. Fields are
    split from the right because the sparse6 columns may contain '|'."""
    with open(path) as f:
        f.readline()
        for line in f:
            head, *tail = line.rstrip("\n").rsplit("|", 22)
            cvt, magma = tail[19], tail[20]
            if not cvt:
                continue
            rid = head.split("|", 1)[0]
            lists = re.findall(r"\{([^{}]*)\}", magma)
            yield rid, [[int(x) - 1 for x in l.split(",")] for l in lists]


def conder_graphs(path: Path):
    """Yield (name, n, edges 0-based) from Conder's Magma file. Whitespace is removed
    first, because some edge pairs and closing brackets are broken across lines."""
    text = re.sub(r"\s+", "", open_text(path).read())
    names = re.findall(r"//(C\d+\.\d+):", text)
    graphs = re.findall(r"CubicAT\[\d+,\d+\]:=Graph<(\d+)\|\{(.*?)\}>;", text)
    if len(names) != len(graphs):
        sys.exit(f"{path.name}: {len(names)} headers but {len(graphs)} graphs")
    for name, (n, body) in zip(names, graphs):
        edges = [(int(a) - 1, int(b) - 1) for a, b in re.findall(r"\{(\d+),(\d+)\}", body)]
        yield name, int(n), edges


def prepare(cache: Path, work: Path) -> dict[str, Path]:
    out = {}
    for name in HOG:
        tsv = work / (name.split(".")[0] + ".tsv")
        with open_text(cache / name) as f, open(tsv, "w") as g:
            for i, line in enumerate(f, 1):
                if line.strip():
                    g.write(f"{i}\t{line.strip()}\n")
        out[name] = tsv
    tsv = work / "psv.tsv"
    with open(tsv, "w") as g:
        for rid, adj in psv_rows(cache / PSV):
            edges = ",".join(f"{u}-{v}" for u, nb in enumerate(adj) for v in nb if u < v)
            g.write(f"psv:{rid}\tE{len(adj)}:{edges}\n")
    out[PSV] = tsv
    tsv = work / "conder.tsv"
    with open(tsv, "w") as g:
        for name, n, edges in conder_graphs(cache / CONDER):
            g.write(f"{name}\tE{n}:" + ",".join(f"{u}-{v}" for u, v in edges) + "\n")
    out[CONDER] = tsv
    return out


def scan(exe: Path, tsv: Path, mode: str, workers: int, out: Path) -> None:
    with open(tsv) as fin, open(out, "w") as fout:
        subprocess.run([str(exe), "--mode", mode, "--girth", "--workers", str(workers)],
                       stdin=fin, stdout=fout, check=True)


def read_witnesses(path: Path):
    for line in open(path):
        rid, n, g, L, *rest = line.rstrip("\n").split("\t")
        yield rid, int(n), int(g), (None if L == "NONE" else int(L)), (rest[0] if rest else "")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=os.environ.get("CENSUS_CACHE",
                                                     str(Path.home() / ".cache" / "conjectures-census")))
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    args = ap.parse_args()
    cache = Path(args.cache)
    work = cache / "work"
    work.mkdir(parents=True, exist_ok=True)

    fetch(cache)
    tsvs = prepare(cache, work)
    exe = work / "census_scan"
    subprocess.run([os.environ.get("CXX", "g++"), "-O3", "-std=c++17", "-pthread",
                    str(HERE / "src" / "census_scan.cpp"), "-o", str(exe)], check=True)
    wit = {}
    for name, tsv in tsvs.items():
        mode = "general" if name in HOG else "vt"
        wit[name] = work / (tsv.stem + ".witnesses.tsv")
        print(f"scan {name} ({mode})", flush=True)
        scan(exe, tsv, mode, args.workers, wit[name])

    res = subprocess.run([sys.executable, str(HERE / "check_witnesses.py"), "--cache", str(cache),
                          "--workers", str(args.workers)])
    if res.returncode != 0:
        return 1

    summary = {}
    long_rows = []
    for name, path in wit.items():
        rows = list(read_witnesses(path))
        by_len = Counter("none" if L is None else str(L) for _, _, _, L, _ in rows)
        by_girth = defaultdict(Counter)
        by_order = defaultdict(Counter)
        for _, n, g, L, _ in rows:
            by_girth[str(g)]["none" if L is None else str(L)] += 1
            by_order[str(n)]["none" if L is None else str(L)] += 1
        key = lambda kv: (kv[0] == "none", int(kv[0]) if kv[0] != "none" else 0)
        entry = {"graphs": len(rows), "min_order": min(r[1] for r in rows),
                 "max_order": max(r[1] for r in rows),
                 "shortest_power_of_two_cycle": dict(sorted(by_len.items(), key=key)),
                 "by_girth": {g: dict(sorted(c.items(), key=key))
                              for g, c in sorted(by_girth.items(), key=lambda kv: int(kv[0]))},
                 "by_order": {o: dict(sorted(c.items(), key=key))
                              for o, c in sorted(by_order.items(), key=lambda kv: int(kv[0]))}}
        summary[name] = entry
        for rid, n, g, L, cyc in rows:
            if L is None or L >= 32:
                long_rows.append(f"{name}\t{rid}\t{n}\t{g}\t{L}\t{cyc}")
    (HERE / "data" / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    (HERE / "data" / "shortest32.tsv").write_text(
        "# source\tid\torder\tgirth\tshortest power-of-two cycle\twitness (vertices, 0-based)\n"
        + "\n".join(long_rows) + "\n")
    print(json.dumps({k: v["shortest_power_of_two_cycle"] for k, v in summary.items()}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
