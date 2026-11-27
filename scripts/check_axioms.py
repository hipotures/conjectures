#!/usr/bin/env python3
"""Axiom gate for the Lean library.

Runs `lake env lean lean/Audit.lean` and fails unless every `#print axioms`
line reports only Lean's three standard axioms (propext, Classical.choice,
Quot.sound) or no axioms at all. In particular `sorryAx` and
`Lean.ofReduceBool` (from `native_decide`) are rejected.
"""
import re
import subprocess
import sys
from pathlib import Path

ALLOWED = {"propext", "Classical.choice", "Quot.sound"}
root = Path(__file__).resolve().parent.parent
lean_dir = root / "lean"
audit = lean_dir / "Audit.lean"

expected = [m.group(1) for m in re.finditer(r"^#print axioms (\S+)", audit.read_text(), re.M)]
proc = subprocess.run(["lake", "env", "lean", str(audit)], cwd=lean_dir,
                      capture_output=True, text=True)
out = proc.stdout + proc.stderr
if proc.returncode != 0:
    sys.exit(f"lean failed on Audit.lean:\n{out}")

seen, bad = {}, []
for line in out.splitlines():
    m = re.match(r"'(\S+)' depends on axioms: \[(.*)\]", line)
    if m:
        axioms = {a.strip() for a in m.group(2).split(",") if a.strip()}
        seen[m.group(1)] = axioms
        if not axioms <= ALLOWED:
            bad.append((m.group(1), sorted(axioms - ALLOWED)))
        continue
    m = re.match(r"'(\S+)' does not depend on any axioms", line)
    if m:
        seen[m.group(1)] = set()

missing = [e for e in expected if e not in seen]
for name in expected:
    if name in seen:
        print(f"{name}: [{', '.join(sorted(seen[name]))}]")
if missing:
    sys.exit(f"no axiom report for: {missing}")
if bad:
    sys.exit(f"non-standard axioms: {bad}")
print(f"OK: {len(expected)} theorems use only standard axioms.")
