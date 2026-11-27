#!/usr/bin/env python3
"""Extract the explicit construction data embedded in the Lean sources into JSON.

The Lean files are the single source of truth for every witness. This script
reads them as text (it does not run Lean) and writes
`results/small-graphs-power-of-two-cycles/data/constructions.json`, which the
independent checker `verify.py` consumes. Re-running it must reproduce the
committed JSON byte for byte; CI checks that.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEAN = ROOT / "lean" / "ErdosGyarfas"
OUT = ROOT / "results" / "small-graphs-power-of-two-cycles" / "data" / "constructions.json"


def lean_list(src: str, name: str) -> list:
    """Parse `def name : ... :=\n  [ ... ]` holding Nat / (Nat × Nat) / (Nat × Nat × Nat)."""
    m = re.search(r"def " + re.escape(name) + r"\b[^:]*:[^=]*:=\s*(\[[^\]]*\])", src, re.S)
    if not m:
        raise KeyError(name)
    body = m.group(1)
    return json.loads(body.replace("(", "[").replace(")", "]"))


# --- 4-ary lookup trees (`Q4`) used for the 702-vertex data --------------------

TOKEN = re.compile(r"Q4\.n|Q4\.l|\(|\)|true|false|\d+|,")


def parse_q4(text: str):
    toks = [t for t in TOKEN.findall(text)]
    pos = 0

    def value():
        nonlocal pos
        t = toks[pos]
        if t == "(":
            pos += 1
            if toks[pos] in ("Q4.n", "Q4.l"):
                v = tree()
                assert toks[pos] == ")"; pos += 1
                return v
            items = []
            while toks[pos] != ")":
                if toks[pos] != ",":
                    items.append(int(toks[pos]))
                pos += 1
            pos += 1
            return tuple(items)
        pos += 1
        if t in ("true", "false"):
            return t == "true"
        return int(t)

    def tree():
        nonlocal pos
        kind = toks[pos]; pos += 1
        kids = [value() for _ in range(4)]
        return (kind, kids)

    return tree()


def q4_get(t, i: int):
    kind, kids = t
    if kind == "Q4.l":
        return kids[i % 4]
    return q4_get(kids[i % 4], i // 4)


def q4_def(src: str, name: str, n: int) -> list:
    m = re.search(r"def " + name + r" : Q4 [^:]*:=\s*\n(.*?)\n\n", src + "\n\n", re.S)
    t = parse_q4(m.group(1))
    vals = [q4_get(t, i) for i in range(n)]
    return [list(v) if isinstance(v, tuple) else v for v in vals]


def main() -> None:
    ub = (LEAN / "UpperBounds.lean").read_text()
    con = (LEAN / "Connectivity.lean").read_text()
    gad = (LEAN / "Gadgets.lean").read_text()
    data16 = (LEAN / "Girth16Data.lean").read_text()
    f6 = (LEAN / "CubicF6.lean").read_text()

    out = {
        "_source": "extracted from lean/ErdosGyarfas/*.lean by scripts/extract_lean_data.py",
        "gadgets": {
            "H7": {"order": 7, "edges": lean_list(gad, "H7_edges"), "ports": [0, 1, 2]},
            "H8star": {"order": 8, "edges": lean_list(gad, "H8star_edges"), "ports": [2, 0, 1]},
            # H15 = two copies of H7 on {0..6}, {7..13} plus vertex 14 (see Gadgets.lean).
            "H15": {"order": 15,
                    "edges": lean_list(gad, "H7_edges")
                    + [[a + 7, b + 7] for a, b in lean_list(gad, "H7_edges")]
                    + [[14, 1], [14, 8], [2, 9]],
                    "ports": [14, 0, 7]},
        },
        "bases": {
            "petersen": lean_list(ub, "petersenTriples"),
            "tutte_coxeter": lean_list(ub, "tutteCoxeterTriples"),
            "k3_g16_n702": q4_def(data16, "adjTree", 702),
        },
        "lifts": {
            "pet73v1": {"base": "petersen",
                        "gadget": ["H8star" if v < 3 else "H7" for v in range(10)],
                        "choice": lean_list(ub, "pet73v1Choice")},
            "pet73v2": {"base": "petersen",
                        "gadget": ["U1" if v == 0 else "H8star" for v in range(10)],
                        "choice": lean_list(ub, "pet73v2Choice")},
            "pet78": {"base": "petersen",
                      "gadget": ["H15" if v == 0 else "H7" for v in range(10)],
                      "choice": lean_list(con, "pet78Choice")},
            "tc370": {"base": "tutte_coxeter",
                      "gadget": ["H15" if t == 2 else "H7" for t in lean_list(ub, "tc370Type")],
                      "choice": lean_list(ub, "tc370Choice")},
            "tc345": {"base": "tutte_coxeter",
                      "gadget": ["H15" if t == 2 else "H8star" for t in lean_list(ub, "tc345Type")],
                      "choice": lean_list(ub, "tc345Choice")},
        },
        "f6": {
            "chosen": q4_def(data16, "chosenTree", 702),
            "sources": [int(x) for x in re.findall(r"⟨(\d+), by omega⟩",
                        re.search(r"def S702[^=]*:=\s*\[(.*?)\]", f6, re.S).group(1))],
        },
    }
    # The per-vertex gadget assignments above mirror small Lean `if` expressions.
    # Fail loudly if those expressions ever change.
    expected = {
        (ub, "pet73v1Gadget"): "if v.val < 3 then H8star else H7",
        (ub, "pet73v2Gadget"): "if v.val == 0 then unitGadget else H8star",
        (con, "pet78Gadget"): "if v.val == 0 then H15 else H7",
        (ub, "tc370Gadget"): "if tc370Type.getD v.val 2 == 2 then H15 else H7",
        (ub, "tc345Gadget"): "if tc345Type.getD v.val 2 == 2 then H15 else H8star",
    }
    for (src, name), body in expected.items():
        m = re.search(r"def " + name + r" \(v : Fin \d+\) : Gadget3 :=\s*\n\s*(.*)", src)
        assert m and m.group(1).strip() == body, (name, m and m.group(1))
    # Gadget port maps mirror `H*_port` in Gadgets.lean.
    for name, ports in (("H7", [0, 1, 2]), ("H8star", [2, 0, 1]), ("H15", [14, 0, 7])):
        m = re.search(r"def " + name + r"_port : Fin 3 → Fin \d+\s*\n(.*?)\n\n", gad, re.S)
        got = [int(x) for x in re.findall(r"=> ⟨(\d+), by omega⟩", m.group(1))]
        assert got == ports, (name, got)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
