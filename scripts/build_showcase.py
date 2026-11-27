#!/usr/bin/env python3
"""Build the README showcase images for one result from its own paper and data.

Usage (from the repository root):

    uv run --no-project --with pymupdf --with matplotlib --with networkx \
        python scripts/build_showcase.py small-graphs-power-of-two-cycles

Every image is derived from committed sources, so it can be regenerated and
cannot drift from them:

- `page1.png`   first page of `paper.pdf`;
- `gadgets.svg` the gadgets H7 and H8* from `data/constructions.json`, drawn
                with the coordinates of Figure 1 of the paper;
- `lift73.svg`  the 73-vertex witness (Petersen graph, 3 x H8*, 7 x H7),
                rebuilt with the independent checker `verify.py`;
- `weights16.svg` the distribution of the weight w(D) over all 16-cycles D
                of the 702-vertex base, computed by `verify.py`.

Output goes to `assets/<result>/`.
"""
from __future__ import annotations

import importlib.util
import sys
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import networkx as nx  # noqa: E402
import pymupdf  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# Dark card style (reference dark palette, slots 1 and 2).
SURFACE = "#191919"
TEXT = "#efefef"
TEXT2 = "#9c9c9c"
GRID = "#383838"
BLUE = "#338ced"
ORANGE = "#e76624"
plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "text.color": TEXT, "axes.labelcolor": TEXT2, "xtick.color": TEXT2, "ytick.color": TEXT2,
    "axes.edgecolor": GRID, "font.family": "DejaVu Sans", "svg.fonttype": "path",
    "svg.hashsalt": "conjectures",
})


def load_verify(result: Path):
    spec = importlib.util.spec_from_file_location("verify", result / "verify.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def title(fig, main: str, sub: str) -> None:
    fig.text(0.04, 0.95, main, fontsize=15, family="DejaVu Serif", va="top")
    fig.text(0.04, 0.885, sub, fontsize=9.5, color=TEXT2, va="top")


def save(fig, path: Path) -> None:
    fig.savefig(path, metadata={"Date": None, "Creator": None})
    plt.close(fig)
    print("wrote", path.relative_to(ROOT))


def page1(result: Path, out: Path) -> None:
    doc = pymupdf.open(result / "paper.pdf")
    doc[0].get_pixmap(dpi=110).save(out / "page1.png")
    print("wrote", (out / "page1.png").relative_to(ROOT))


def draw_gadget(ax, edges, pos, ports, deg4=()):
    for a, b in edges:
        ax.plot(*zip(pos[a], pos[b]), color=TEXT2, lw=1.4, zorder=1)
    stubs = {ports[0]: (0, 0.7), ports[1]: (-0.6, -0.42), ports[2]: (0.6, -0.42)}
    for i, p in enumerate(ports):
        dx, dy = stubs[p]
        x, y = pos[p]
        ax.plot([x, x + dx], [y, y + dy], color=TEXT2, lw=1.4, zorder=1)
        ax.text(x + dx * 1.35, y + dy * 1.35, f"$p_{i}$", ha="center", va="center", fontsize=11)
    for v, (x, y) in pos.items():
        port = v in ports
        ax.scatter([x], [y], s=430, color=BLUE if port else SURFACE, edgecolors=BLUE if port else TEXT,
                   linewidths=1.4, zorder=2)
        if v in deg4:
            ax.scatter([x], [y], s=720, facecolors="none", edgecolors=ORANGE, linewidths=1.6, zorder=2)
        ax.text(x, y, str(v), ha="center", va="center", fontsize=10,
                color=SURFACE if port else TEXT, zorder=3, fontweight="bold" if port else None)
    ax.set_aspect("equal")
    ax.axis("off")


def gadgets(data, out: Path) -> None:
    g = data["gadgets"]
    pos7 = {0: (0, 2.5), 3: (-1.2, 1.3), 4: (1.2, 1.3), 1: (-2.3, -0.8), 5: (-0.8, -1.5),
            6: (0.8, -1.5), 2: (2.3, -0.8)}
    pos8 = {2: (0, 2.7), 5: (-1.6, 1.3), 7: (0.5, 1.3), 4: (-0.3, 0), 6: (1.2, 0), 0: (-2.2, -0.8),
            3: (0, -1.7), 1: (2.2, -0.8)}
    fig, axs = plt.subplots(1, 2, figsize=(8, 4.6))
    fig.subplots_adjust(left=0.03, right=0.97, bottom=0.1, top=0.8, wspace=0.15)
    title(fig, "Three-port gadgets", "ports filled blue · orange ring: the degree-4 vertex of $H_8^*$")
    draw_gadget(axs[0], g["H7"]["edges"], pos7, g["H7"]["ports"])
    draw_gadget(axs[1], g["H8star"]["edges"], pos8, g["H8star"]["ports"], deg4=(7,))
    for ax, name, d in ((axs[0], "$H_7$ (García)", "d(p0,·) = 2,  d(p1,p2) = 3"),
                        (axs[1], "$H_8^*$ (new)", "d(p0,·) = 3,  d(p1,p2) = 2")):
        ax.set_ylim(-2.9, 3.9)
        ax.set_xlim(-3.3, 3.3)
        ax.text(0, -2.45, name, ha="center", fontsize=12)
        ax.text(0, -2.95, d, ha="center", fontsize=9, color=TEXT2)
    save(fig, out / "gadgets.svg")


def lift73(V, data, out: Path) -> None:
    spec = data["lifts"]["pet73v1"]
    base = data["bases"]["petersen"]
    n, adj, _ = V.build_lift(base, spec["gadget"], spec["choice"])
    owner, ports = [], set()
    for v, name in enumerate(spec["gadget"]):
        k = len(owner)
        owner += [v] * V.GADGETS[name]["order"]
        ports |= {k + p for p in V.GADGETS[name]["ports"]}
    G = nx.Graph((a, b) for a in range(n) for b in adj[a] if a < b)
    import math
    bpos = {}
    for i in range(5):
        t = math.pi / 2 + 2 * math.pi * i / 5
        bpos[i] = (math.cos(t), math.sin(t))
        bpos[i + 5] = (0.45 * math.cos(t), 0.45 * math.sin(t))
    init = {x: (bpos[owner[x]][0] + 0.05 * math.cos(x), bpos[owner[x]][1] + 0.05 * math.sin(x))
            for x in range(n)}
    pos = nx.spring_layout(G, pos=init, k=0.075, iterations=200, seed=1)
    fig, ax = plt.subplots(figsize=(6.4, 6.4))
    fig.subplots_adjust(left=0.02, right=0.98, bottom=0.08, top=0.84)
    title(fig, "A 73-vertex graph without $C_4$, $C_8$, $C_{16}$",
          "Petersen graph with $H_8^*$ at 3 vertices and $H_7$ at 7 · 111 edges")
    for a, b in G.edges:
        inner = owner[a] == owner[b]
        ax.plot(*zip(pos[a], pos[b]), color=TEXT2 if inner else GRID, lw=1.0 if inner else 1.6, zorder=1)
    for x in range(n):
        col = ORANGE if spec["gadget"][owner[x]] == "H8star" else BLUE
        ax.scatter(*pos[x], s=46 if x not in ports else 30, color=col, edgecolors=SURFACE,
                   linewidths=1.2, zorder=2)
        if len(adj[x]) == 4:
            ax.scatter(*pos[x], s=150, facecolors="none", edgecolors=ORANGE, linewidths=1.3, zorder=2)
    ax.scatter([], [], color=ORANGE, s=46, label="$H_8^*$ gadget (ringed: degree 4)")
    ax.scatter([], [], color=BLUE, s=46, label="$H_7$ gadget")
    ax.plot([], [], color=GRID, lw=1.6, label="edge of the Petersen graph")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.1), ncol=3, frameon=False, fontsize=8.5,
              labelcolor=TEXT, handletextpad=0.4, columnspacing=1.2)
    ax.set_aspect("equal")
    ax.axis("off")
    save(fig, out / "lift73.svg")


def weights16(V, data, out: Path) -> None:
    base = data["bases"]["k3_g16_n702"]
    S = data["f6"]["sources"]
    chosen = data["f6"]["chosen"]
    gadget = ["H7" if v in S else "H15" for v in range(len(base))]
    choice = [base[v].index(chosen[v]) for v in range(len(base))]
    _, _, slot = V.build_lift(base, gadget, choice)
    cnt = Counter(V.base_weight(base, gadget, slot, c)
                  for c in V.simple_cycles_up_to([list(t) for t in base], 16))
    total = sum(cnt.values())
    lo = min(cnt)
    xs = list(range(60, max(cnt) + 2))
    fig, ax = plt.subplots(figsize=(7, 4.2))
    fig.subplots_adjust(left=0.1, right=0.97, bottom=0.15, top=0.8)
    title(fig, "Every base 16-cycle lifts to length > 64",
          f"weight w(D) over all {total:,} 16-cycles of the 702-vertex base · lifted cycles have length ≥ w(D)")
    ax.bar(xs, [cnt.get(x, 0) for x in xs], width=0.8, color=BLUE, zorder=2)
    top = max(cnt.values())
    ax.annotate(f"minimum {lo}\n({cnt[lo]} cycles)", xy=(lo, cnt[lo]), xytext=(lo + 0.2, top * 0.45),
                ha="center", fontsize=9, color=TEXT,
                arrowprops=dict(arrowstyle="-", color=TEXT2, lw=0.8))
    ax.axvline(64.5, color=TEXT2, lw=1.2, ls=(0, (4, 3)), zorder=1)
    ax.text(64.2, top * 0.97, "a 64-cycle\nneeds\nw(D) ≤ 64", ha="right", va="top", fontsize=8.5,
            color=TEXT2)
    ax.set_xticks([x for x in xs if x % 4 == 0])
    ax.set_xlabel("w(D)")
    ax.set_ylabel("number of 16-cycles")
    ax.grid(axis="y", color=GRID, lw=0.6, zorder=0)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    save(fig, out / "weights16.svg")


def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else "small-graphs-power-of-two-cycles"
    result = ROOT / "results" / name
    out = ROOT / "assets" / name
    out.mkdir(parents=True, exist_ok=True)
    V = load_verify(result)
    data = V.DATA
    page1(result, out)
    gadgets(data, out)
    lift73(V, data, out)
    weights16(V, data, out)


if __name__ == "__main__":
    main()
