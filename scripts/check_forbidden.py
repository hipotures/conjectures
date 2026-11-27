#!/usr/bin/env python3
"""Fail if Lean *code* (comments stripped) uses sorry, admit, native_decide,
implemented_by, extern, unsafe, or declares an axiom."""
import re
import sys
from pathlib import Path

def segments(src: str):
    """Yield (kind, text) with kind in {'code', 'comment'}. Handles nested /- -/,
    line comments, and string literals (so '--' inside strings is not a comment)."""
    i, n = 0, len(src)
    buf = []
    while i < n:
        if src.startswith("/-", i):
            if buf:
                yield "code", "".join(buf); buf = []
            depth, j = 1, i + 2
            while j < n and depth:
                if src.startswith("/-", j):
                    depth += 1; j += 2
                elif src.startswith("-/", j):
                    depth -= 1; j += 2
                else:
                    j += 1
            yield "comment", src[i:j]
            i = j
        elif src.startswith("--", i):
            if buf:
                yield "code", "".join(buf); buf = []
            j = src.find("\n", i)
            j = n if j < 0 else j
            yield "comment", src[i:j]
            i = j
        elif src[i] == '"':
            j = i + 1
            while j < n and src[j] != '"':
                j += 2 if src[j] == "\\" else 1
            buf.append(src[i:j + 1]); i = j + 1
        else:
            buf.append(src[i]); i += 1
    if buf:
        yield "code", "".join(buf)


FORBIDDEN = re.compile(r"\b(sorry|admit|native_decide|implemented_by|extern|unsafe)\b|^\s*(private\s+)?axiom\b", re.M)

root = Path(__file__).resolve().parent.parent / "lean"
files = sorted(root.glob("ErdosGyarfas/**/*.lean")) + [root / "ErdosGyarfas.lean"]
hits = []
for f in files:
    code = "".join(t for k, t in segments(f.read_text(encoding="utf-8")) if k == "code")
    for m in FORBIDDEN.finditer(code):
        line = code.count("\n", 0, m.start()) + 1
        hits.append(f"{f.relative_to(root)}: code line ~{line}: {m.group(0).strip()}")
if hits:
    sys.exit("forbidden constructs:\n" + "\n".join(hits))
print(f"OK: {len(files)} files, no forbidden constructs in code.")
