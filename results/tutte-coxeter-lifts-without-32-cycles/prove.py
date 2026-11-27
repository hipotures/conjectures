#!/usr/bin/env python3
"""Reproduce every computation of the paper.

  1. download CaDiCaL 2.1.3 and drat-trim (pinned, SHA-256 checked) and build
     them, unless --cadical and --drat-trim point to existing binaries;
  2. write the CNF instances with encode.py;
  3. solve every instance with CaDiCaL, writing a DRAT proof;
  4. check every UNSAT answer with drat-trim, then delete the proof;
  5. decode the two satisfiable controls and check the lifts they describe
     as graphs (order, and shortest cycle through an edge between gadgets);
  6. write data/results.json.

Needs a C/C++ compiler and make; about 30 minutes on 16 cores.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import platform
import subprocess
import sys
import tarfile
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import encode  # noqa: E402
import test_encoding as te  # noqa: E402

SOURCES = {
    "cadical": {
        "url": "https://github.com/arminbiere/cadical/archive/refs/tags/rel-2.1.3.tar.gz",
        "sha256": "abfe890aa4ccda7b8449c7ad41acb113cfb8e7e8fbf5e49369075f9b00d70465",
        "version": "CaDiCaL 2.1.3",
    },
    "drat-trim": {
        "url": "https://github.com/marijnheule/drat-trim/archive/"
               "2e3b2dc0ecf938addbd779d42877b6ed69d9a985.tar.gz",
        "sha256": "a75e5a2072fa5a5493ee8504067661c6b452d45a32f889ac5b2c9470c227b58c",
        "version": "drat-trim commit 2e3b2dc (2024-11-25)",
    },
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def build_solvers(cache: Path) -> tuple[Path, Path]:
    cache.mkdir(parents=True, exist_ok=True)
    out = {}
    for name, src in SOURCES.items():
        binary = cache / name
        if binary.exists():
            out[name] = binary
            continue
        tgz = cache / f"{name}.tar.gz"
        if not tgz.exists():
            print(f"download {src['url']}")
            urllib.request.urlretrieve(src["url"], tgz)
        if sha256(tgz) != src["sha256"]:
            raise SystemExit(f"{tgz}: SHA-256 mismatch")
        with tarfile.open(tgz) as t:
            top = t.getnames()[0].split("/")[0]
            t.extractall(cache, filter="data")
        d = cache / top
        print(f"build {name}")
        if name == "cadical":
            subprocess.run(["./configure"], cwd=d, check=True, stdout=subprocess.DEVNULL)
            subprocess.run(["make", f"-j{os.cpu_count()}"], cwd=d, check=True, stdout=subprocess.DEVNULL)
            (d / "build" / "cadical").rename(binary)
        else:
            subprocess.run(["gcc", "-O3", "-std=gnu99", "drat-trim.c", "-o", str(binary)],
                           cwd=d, check=True)
        out[name] = binary
    return out["cadical"], out["drat-trim"]


def decode_model(text: str, x: dict) -> dict:
    true = set()
    for line in text.splitlines():
        if line.startswith("v "):
            true.update(int(t) for t in line[2:].split() if int(t) > 0)
    states = {}
    for (v, g, p), var in x.items():
        if var in true:
            assert v not in states
            states[v] = (g, p)
    assert len(states) == 30
    return states


def check_model(states: dict) -> dict:
    """Build the lift as a graph and measure it (independent of the CNF)."""
    G = encode.load_gadgets()
    base = encode.tutte_coxeter()
    gad = [states[v][0] for v in range(30)]
    perm = [[(k - states[v][1]) % 3 for k in range(3)] for v in range(30)]
    lift = te.Lift(base, gad, perm, G)
    counts = {g: gad.count(g) for g in G}
    return {"order": lift.n, "counts": counts, "cross_girth": lift.cross_girth(),
            "gadget": gad, "choice": [states[v][1] for v in range(30)]}


def run(job, cadical, drat_trim, keep):
    cnf = Path(job["path"])
    proof = cnf.with_suffix(".drat")
    t0 = time.time()
    r = subprocess.run([str(cadical), "-q", str(cnf), str(proof)], capture_output=True, text=True)
    job["solve_s"] = round(time.time() - t0, 1)
    job["result"] = {10: "SAT", 20: "UNSAT"}.get(r.returncode, f"rc={r.returncode}")
    if job["result"] == "SAT":
        job["model"] = r.stdout
    if job["result"] == "UNSAT":
        job["proof_bytes"] = proof.stat().st_size
        t1 = time.time()
        v = subprocess.run([str(drat_trim), str(cnf), str(proof), "-t", "200000"],
                           capture_output=True, text=True)
        job["verify_s"] = round(time.time() - t1, 1)
        job["drat_trim"] = "VERIFIED" if (v.returncode == 0 and "s VERIFIED" in v.stdout) else "FAILED"
        for line in v.stdout.splitlines():
            if "lemmas in core" in line:
                job["core"] = line[2:].strip()
    if not keep:
        proof.unlink(missing_ok=True)
    return job


def cpu_name() -> str:
    try:
        for line in open("/proc/cpuinfo"):
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or platform.machine()


def table_tex(res: dict) -> str:
    """The results table of the paper, from data/results.json."""
    rows = []
    label = {"delta3_a14": r"\textsf{A}", "delta3_a15_c1": r"\textsf{B}", "cubic_a19": r"\textsf{C}",
             "control_delta3_a15": r"control \textsf{A}, $a\le 15$",
             "control_cubic_a20": r"control \textsf{C}, $a\le 20$"}
    for name in encode.INSTANCES:
        js = [j for j in res["jobs"] if j["instance"] == name]
        if not js:
            continue
        solve = sum(j["solve_s"] for j in js)
        ver = sum(j.get("verify_s", 0) for j in js)
        checked = js[0]["result"] == "UNSAT" and all(j.get("drat_trim") == "VERIFIED" for j in js)
        res_ = js[0]["result"] + ((", all checked" if len(js) > 1 else ", checked") if checked else "")
        num = lambda v: f"{v:,.0f}".replace(",", "{,}") if v >= 10000 else f"{v:.0f}"
        span = lambda k: "--".join(num(v) for v in sorted({min(j[k] for j in js), max(j[k] for j in js)}))
        S = encode.encode(**encode.INSTANCES[name])[2]["slack"]
        rows.append(f"{label[name]} & {len(js)} & {span('vars')} & {span('clauses')} & "
                    f"{S} & {num(solve)} & {num(ver) if ver else '--'} & {res_}" + r"\\")
    body = "\n".join(rows)
    return (r"""\begin{table}[ht]
\centering
\caption{The SAT instances. $S$ is the bound of \cref{cor:counting}(a). Times
are the running times of the single-threaded CaDiCaL runs and of
\code{drat-trim} on their proofs, summed over the files of a case; variables
and clauses are per file (the cube clauses of case \textsf{C} add one clause
to some files). Machine: """ + res["machine"].replace("_", r"\_") + r""", """ +
            f"{res['wall_seconds'] / 60:.0f}" + r""" minutes of wall time.}
\label{tab:results}
\small
\begin{tabular}{@{}lrrrrrrl@{}}
\toprule
case & files & variables & clauses & $S$ & solve (s) & check (s) & result\\
\midrule
""" + body + r"""
\bottomrule
\end{tabular}
\end{table}
""")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache", type=Path,
                    default=Path(os.environ.get("TC_LIFT_CACHE", Path.home() / ".cache" / "conjectures-tc-lifts")))
    ap.add_argument("--cadical", type=Path)
    ap.add_argument("--drat-trim", type=Path)
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    ap.add_argument("--keep-proofs", action="store_true")
    ap.add_argument("--only", nargs="*", help="instance names (default: all)")
    a = ap.parse_args()

    if a.cadical and a.drat_trim:
        cadical, drat_trim = a.cadical, a.drat_trim
    else:
        cadical, drat_trim = build_solvers(a.cache / "solvers")
    work = a.cache / "cnf"
    jobs = []
    xmaps = {}
    for name in (a.only or list(encode.INSTANCES)):
        for row in encode.write_instance(name, work):
            row["path"] = str(work / row["file"])
            jobs.append(row)
        xmaps[name] = encode.encode(**encode.INSTANCES[name])[1]
    print(f"{len(jobs)} CNF files in {work}; solving with {a.workers} workers")

    # cube leaves where vertices 1 and 29 are both H15 off adj[.][0] are the slowest
    jobs.sort(key=lambda j: (j["cube"].count("_") != 3, j["instance"] != "delta3_a15_c1"))
    t0 = time.time()
    done = []
    with cf.ThreadPoolExecutor(a.workers) as ex:
        for j in ex.map(lambda j: run(j, cadical, drat_trim, a.keep_proofs), jobs):
            done.append(j)
            print(f"[{len(done):2d}/{len(jobs)}] {j['instance']} {j['cube']}: {j['result']} "
                  f"{j.get('drat_trim', '')} solve {j['solve_s']} s verify {j.get('verify_s', '-')} s",
                  flush=True)
    wall = round(time.time() - t0, 1)

    ok = True
    controls = {}
    for j in done:
        want = encode.EXPECT[j["instance"]]
        if j["result"] != want or (want == "UNSAT" and j.get("drat_trim") != "VERIFIED"):
            ok = False
            print(f"FAIL {j['instance']} {j['cube']}: {j['result']} {j.get('drat_trim')}")
        if j["result"] == "SAT":
            m = check_model(decode_model(j.pop("model"), xmaps[j["instance"]]))
            controls[j["instance"]] = m
            good = m["cross_girth"] >= 33 and m["order"] == j["max_order"]
            ok &= good
            print(("ok   " if good else "FAIL ") +
                  f"{j['instance']}: lift on {m['order']} vertices, {m['counts']}, "
                  f"shortest cycle between gadgets {m['cross_girth']}")
        j.pop("path", None)

    for j in done:
        for k in ("gadgets", "max_h15", "min_h7", "slack", "symmetry", "cycles", "max_order"):
            j.pop(k, None)
    out = {
        "solvers": {k: v["version"] for k, v in SOURCES.items()},
        "machine": f"{cpu_name()}, {os.cpu_count()} threads, {a.workers} parallel runs",
        "wall_seconds": wall,
        "instances": {n: {k: (list(v) if isinstance(v, tuple) else v) for k, v in spec.items()}
                      | {"expect": encode.EXPECT[n]} for n, spec in encode.INSTANCES.items()},
        "controls": controls,
        "jobs": sorted(done, key=lambda j: (j["instance"], j["cube"])),
        "all_verified": ok,
    }
    if not a.only:
        (HERE / "data").mkdir(exist_ok=True)
        (HERE / "data" / "results.json").write_text(json.dumps(out, indent=1) + "\n")
        (HERE / "results_table.tex").write_text(table_tex(out))
    print("ALL INSTANCES VERIFIED" if ok else "VERIFICATION FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
