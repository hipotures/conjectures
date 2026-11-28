#!/usr/bin/env python3
"""Rebuild the search programs, rerun the proof, and compare every counter.

    python3 reproduce.py           # full proof: n <= 88 (about 80 min on 16 cores)
    python3 reproduce.py --quick   # small caps only (about 1 min; used by CI)

Needs a C++17 compiler (g++ or clang++). Branch B witness streams (up to 1.3 GiB at
cap 44) are written to a temporary directory and deleted after checking.

Each run must end with zero completed configurations, the C++ witness checkers must
accept every stream, and all counters must equal `data/expected_counts.json`. The
counters for caps 29 to 44 of Branch A also equal those of Tranquilli's original
program (see `data/upstream_crosscheck.json`).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPECTED = json.loads((HERE / "data" / "expected_counts.json").read_text())

FULL_A = [29, 34, 35, 40, 41, 42, 43, 44]
FULL_B = list(range(35, 45))
QUICK_A = [29]
QUICK_B = [35]


def compiler() -> str:
    for cxx in (os.environ.get("CXX"), "g++", "clang++"):
        if cxx and shutil.which(cxx):
            return cxx
    sys.exit("no C++ compiler found (set CXX)")


def build(tmp: Path) -> dict[str, Path]:
    cxx = compiler()
    out = {}
    for name in ("triangle_search", "girth10_search", "girth10_verify"):
        exe = tmp / name
        subprocess.run([cxx, "-O3", "-std=c++17", "-pthread", str(HERE / "src" / f"{name}.cpp"),
                        "-o", str(exe)], check=True)
        out[name] = exe
    return out


def fields(line: str) -> dict[str, int]:
    return {k: int(v) for k, v in re.findall(r"(\w+)=(\d+)(?=\s|$)", line)}


KEYS_A = ("states", "attempted", "structural", "c8", "c16", "completions")
KEYS_B = ("states", "attempted", "structural", "c6", "c8", "c16", "completions")


def main() -> int:
    quick = "--quick" in sys.argv
    caps_a, caps_b = (QUICK_A, QUICK_B) if quick else (FULL_A, FULL_B)
    ok = True

    def compare(label, got, want, keys):
        nonlocal ok
        bad = [k for k in keys if got.get(k) != want.get(k)]
        ok &= not bad
        print(f"{'ok  ' if not bad else 'FAIL'} {label}: "
              + " ".join(f"{k}={got.get(k)}" for k in keys)
              + (f"   (mismatch: {bad})" if bad else ""), flush=True)

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        exe = build(tmp)
        for cap in caps_a:
            res = subprocess.run([str(exe["triangle_search"]), "--side", str(cap)],
                                 capture_output=True, text=True)
            if res.returncode != 0 or "witnesses_checked=true" not in res.stdout:
                ok = False
                print(f"FAIL branch A cap {cap}: exit {res.returncode}\n{res.stdout}{res.stderr}")
                continue
            for line in res.stdout.splitlines():
                if line.startswith("ORBIT"):
                    orbit = line.split()[1]
                    want = EXPECTED["branch_a"][str(cap)][f"orbit{orbit}"]
                    compare(f"branch A cap {cap} (n <= {2 * cap}) orbit {orbit}", fields(line), want, KEYS_A)
        for cap in caps_b:
            cert = tmp / f"g10_{cap}.cert"
            gen = subprocess.run([str(exe["girth10_search"]), "--side", str(cap), "--out", str(cert)],
                                 capture_output=True, text=True)
            ver = subprocess.run([str(exe["girth10_verify"]), str(cert)], capture_output=True, text=True)
            cert.unlink(missing_ok=True)
            if gen.returncode != 0 or ver.returncode != 0 or "G10_VERIFIED_OK" not in ver.stdout:
                ok = False
                print(f"FAIL branch B cap {cap}:\n{gen.stdout}{gen.stderr}{ver.stdout}{ver.stderr}")
                continue
            compare(f"branch B cap {cap} (n <= {2 * cap}) checked", fields(ver.stdout),
                    EXPECTED["branch_b"][str(cap)], KEYS_B)
    print("ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
