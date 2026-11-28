#!/usr/bin/env python3
"""Build the README showcase images for one result from its own paper and data.

Usage (from the repository root):

    uv run --no-project --with pymupdf --with matplotlib --with networkx \
        python scripts/build_showcase.py small-graphs-power-of-two-cycles

Every image is derived from committed sources, so it can be regenerated and
cannot drift from them. Every result gets `page1.png`.

small-graphs-power-of-two-cycles:

- `page1.png`   first page of `paper.pdf`;
- `gadgets.svg` the gadgets H7 and H8* from `data/constructions.json`, drawn
                with the coordinates of Figure 1 of the paper;
- `lift73.svg`  the 73-vertex witness (Petersen graph, 3 x H8*, 7 x H7),
                rebuilt with the independent checker `verify.py`;
- `weights16.svg` the distribution of the weight w(D) over all 16-cycles D
                of the 702-vertex base, computed by `verify.py`.

cubic-bipartite-power-of-two-cycles:

- `root_branch_b.svg` the forced 15-block root of Branch B (Figure 1 of the paper);
- `search_growth.svg` candidate blocks per cap, from `data/expected_counts.json`;
- `cages16.svg`  the three (3,10)-cages from `data/cagesk3g10.g6`, each with a
                16-cycle found here.

cubic-census-power-of-two-cycles:

- `share32.svg`  share of symmetric graphs with shortest power-of-two cycle 32,
                by order, from `data/summary.json` and `data/shortest32.tsv`;
- `girth_vt.svg`, `girth_sym.svg` counts by girth and shortest power-of-two
                cycle, from `data/summary.json`.

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


# ---------------------------------------------------------------- cubic bipartite (paper 2)

def _cycle_dfs(adj, start, length):
    """One cycle of the given length through `start` (vertex list), or None. Neighbours
    with fewer free neighbours are tried first (Warnsdorff), which finds Hamiltonian
    cycles of the cages at once."""
    path, on = [start], {start}

    def go(x):
        if len(path) == length:
            return start in adj[x]
        for w in sorted(adj[x], key=lambda y: (sum(z not in on for z in adj[y]), y)):
            if w not in on:
                on.add(w)
                path.append(w)
                if go(w):
                    return True
                on.discard(w)
                path.pop()
        return False

    return list(path) if go(start) else None


def cages16(result: Path, out: Path) -> None:
    """The three (3,10)-cages, each drawn on a Hamiltonian cycle, with one 16-cycle."""
    import math
    lines = (result / "data" / "cagesk3g10.g6").read_text().split()
    fig, axs = plt.subplots(1, 3, figsize=(10.5, 4.3))
    fig.subplots_adjust(left=0.01, right=0.99, bottom=0.04, top=0.8, wspace=0.04)
    title(fig, "The three (3,10)-cages have 16-cycles",
          "70 vertices, girth 10, bipartite · drawn on a Hamiltonian cycle · a 16-cycle in orange")
    for ax, line in zip(axs, lines):
        G = nx.from_graph6_bytes(line.encode())
        adj = {v: sorted(G[v]) for v in G}
        ham = _cycle_dfs(adj, 0, len(adj))
        c16 = _cycle_dfs(adj, 0, 16)
        pos = {v: (math.cos(2 * math.pi * i / len(ham)), math.sin(2 * math.pi * i / len(ham)))
               for i, v in enumerate(ham)}
        on16 = {frozenset((c16[i], c16[(i + 1) % 16])) for i in range(16)}
        side = nx.bipartite.color(G)
        rim = {frozenset((ham[i], ham[(i + 1) % len(ham)])) for i in range(len(ham))}
        for a, b in G.edges:
            e = frozenset((a, b))
            if e in on16:
                ax.plot(*zip(pos[a], pos[b]), color=ORANGE, lw=3.0, zorder=2, solid_capstyle="round")
            else:
                ax.plot(*zip(pos[a], pos[b]), color=TEXT2 if e in rim else GRID,
                        lw=1.1 if e in rim else 0.7, zorder=1)
        for v, (x, y) in pos.items():
            hot = v in c16
            ax.scatter([x], [y], s=22 if hot else 9, color=ORANGE if hot else (TEXT if side[v] else SURFACE),
                       edgecolors=ORANGE if hot else TEXT, linewidths=0.7, zorder=3)
        ax.set_aspect("equal")
        ax.set_xlim(-1.12, 1.12)
        ax.set_ylim(-1.12, 1.12)
        ax.axis("off")
    save(fig, out / "cages16.svg")


def search_growth(result: Path, out: Path) -> None:
    """Number of proposals per cap in both branches (from data/expected_counts.json)."""
    import json
    exp = json.loads((result / "data" / "expected_counts.json").read_text())
    a = {int(c): sum(o["attempted"] for o in v.values()) for c, v in exp["branch_a"].items()}
    a.update({int(c): v["attempted"] for c, v in exp.get("branch_a_small", {}).items()})
    b = {int(c): v["attempted"] for c, v in exp["branch_b"].items()}
    fig, ax = plt.subplots(figsize=(7, 4.2))
    fig.subplots_adjust(left=0.1, right=0.83, bottom=0.15, top=0.8)
    title(fig, "Size of the two searches",
          "candidate blocks examined at point cap v (graphs with n ≤ 2v) · 0 completions up to v = 44")
    for data, col, name in ((a, BLUE, "Branch A\n(6-cycle)"), (b, ORANGE, "Branch B\n(girth ≥ 10)")):
        xs = sorted(data)
        ax.plot(xs, [data[x] for x in xs], color=col, lw=2, marker="o", ms=5, zorder=3,
                markeredgecolor=SURFACE, markeredgewidth=1.2)
        ax.text(xs[-1] + 0.4, data[xs[-1]], name, color=TEXT, fontsize=9, va="center")
    ax.set_yscale("log")
    ax.set_xlabel("point cap v")
    ax.set_ylabel("candidate blocks")
    ax.grid(axis="y", color=GRID, lw=0.6, zorder=0)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.tick_params(length=0)
    save(fig, out / "search_growth.svg")


def root_branch_b(out: Path) -> None:
    """The forced 15-block root of Branch B (Figure 1 of the paper)."""
    fig, ax = plt.subplots(figsize=(8.6, 4.0))
    fig.subplots_adjust(left=0.01, right=0.99, bottom=0.02, top=0.8)
    title(fig, "The root of the girth-10 search",
          "girth ≥ 10 forces 15 blocks (squares) on 31 points (circles) around any block · depth 5 not drawn")
    def pt(x, y, label):
        ax.scatter([x], [y], s=210, color=SURFACE, edgecolors=TEXT, linewidths=1.1, zorder=3)
        ax.text(x, y, label, ha="center", va="center", fontsize=7.5, zorder=4)
    def bl(x, y, col=BLUE):
        ax.scatter([x], [y], s=70, marker="s", color=col, edgecolors=SURFACE, linewidths=0.8, zorder=3)
    def ln(p, q):
        ax.plot(*zip(p, q), color=TEXT2, lw=0.9, zorder=1)
    root = (0, 4)
    bl(*root, ORANGE)
    ax.text(0.7, 4, r"$\beta=\{0,1,2\}$", fontsize=9, va="center")
    P = {0: (-10, 3), 1: (0, 3), 2: (10, 3)}
    for p, xy in P.items():
        ln(root, xy)
        pt(*xy, str(p))
    for a, b, c, x in ((0, 3, 4, -12.5), (0, 5, 6, -7.5), (1, 7, 8, -2.5), (1, 9, 10, 2.5),
                       (2, 11, 12, 7.5), (2, 13, 14, 12.5)):
        ln(P[a], (x, 2))
        bl(x, 2)
        for q, dx in ((b, -1.1), (c, 1.1)):
            ln((x, 2), (x + dx, 1))
            pt(x + dx, 1, str(q))
            P[q] = (x + dx, 1)
    for q in (3, 4, 5, 6):
        x = P[q][0]
        for dx in (-0.55, 0.55):
            ln(P[q], (x + dx, 0.1))
            bl(x + dx, 0.1)
    for d, y in enumerate((4, 3, 2, 1, 0.1)):
        ax.text(-16.2, y, f"depth {d}", fontsize=8, color=TEXT2, va="center")
    ax.set_xlim(-16.5, 14.2)
    ax.set_ylim(-0.5, 4.5)
    ax.axis("off")
    save(fig, out / "root_branch_b.svg")


# ---------------------------------------------------------------- cubic censuses (paper 3)

def share32(result: Path, out: Path) -> None:
    """Share of symmetric graphs whose shortest power-of-two cycle is 32, by order."""
    import json
    summ = json.loads((result / "data" / "summary.json").read_text())
    by_order = summ["AllSymmCubic-OrderUpTo10000-ByEdgeSets.txt.gz"]["by_order"]
    rows = [r.split("\t") for r in (result / "data" / "shortest32.tsv").read_text().splitlines()
            if r and not r.startswith("#") and r.startswith("AllSymm")]
    width = 1000
    bands = range(0, 10000, width)
    tot = Counter()
    for o, c in by_order.items():
        tot[(int(o) - 1) // width] += sum(c.values())
    lo16, hi17 = Counter(), Counter()
    for r in rows:
        k = (int(r[2]) - 1) // width
        (hi17 if int(r[3]) >= 17 else lo16)[k] += 1
    xs = list(range(len(bands)))
    y1 = [100 * lo16[k] / tot[k] for k in xs]
    y2 = [100 * hi17[k] / tot[k] for k in xs]
    fig, ax = plt.subplots(figsize=(7, 4.2))
    fig.subplots_adjust(left=0.1, right=0.97, bottom=0.2, top=0.78)
    title(fig, "Symmetric graphs that need a 32-cycle",
          "share of Conder's cubic symmetric graphs with no cycle of length 4, 8 or 16, by order")
    ax.bar(xs, y1, width=0.72, color=BLUE, zorder=2, label="girth ≤ 16")
    ax.bar(xs, y2, width=0.72, bottom=y1, color=ORANGE, zorder=2, label="girth 17–20 (forced)",
           edgecolor=SURFACE, linewidth=2)
    for k in xs:
        ax.text(k, y1[k] + y2[k] + 0.6, f"{lo16[k] + hi17[k]}/{tot[k]}", ha="center", fontsize=7.5,
                color=TEXT2)
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{b // 1000}–{(b + width) // 1000}k" if b else "≤1k" for b in bands], fontsize=8)
    ax.set_xlabel("order (vertices)")
    ax.set_ylabel("% of graphs")
    ax.grid(axis="y", color=GRID, lw=0.6, zorder=0)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.tick_params(length=0)
    ax.legend(loc="upper left", frameon=False, fontsize=8.5, labelcolor=TEXT)
    save(fig, out / "share32.svg")


def girth_table(result: Path, out: Path, key: str, fname: str, main: str, sub: str) -> None:
    """Heat table: number of graphs by girth (rows) and shortest power-of-two cycle (columns)."""
    import json
    import math
    from matplotlib.colors import LinearSegmentedColormap, to_rgb
    summ = json.loads((result / "data" / "summary.json").read_text())[key]["by_girth"]
    girths = sorted(summ, key=int)
    cols = ["4", "8", "16", "32"]
    cmap = LinearSegmentedColormap.from_list("seq", ["#0e3d7e", "#1b64be", "#338ced", "#84b9f3", "#cce3fd"])
    vmax = math.log10(max(max(c.values()) for c in summ.values()))
    height = 0.3 * len(girths) + 1.45
    fig, ax = plt.subplots(figsize=(4.6, height))
    fig.subplots_adjust(left=0.14, right=0.97, bottom=0.02, top=1 - 1.0 / height)
    fig.text(0.04, 1 - 0.12 / height, main, fontsize=13, family="DejaVu Serif", va="top")
    fig.text(0.04, 1 - 0.45 / height, sub, fontsize=8.5, color=TEXT2, va="top")
    for i, g in enumerate(girths):
        for j, L in enumerate(cols):
            n = summ[g].get(L, 0)
            if not n:
                continue
            col = cmap(math.log10(n) / vmax if vmax else 1)
            ax.add_patch(plt.Rectangle((j + 0.04, i + 0.06), 0.92, 0.88, color=col, zorder=1))
            lum = sum(w * c for w, c in zip((0.2126, 0.7152, 0.0722), to_rgb(col)))
            ax.text(j + 0.5, i + 0.5, f"{n:,}", ha="center", va="center", fontsize=8,
                    color=SURFACE if lum > 0.45 else TEXT, zorder=2)
    ax.set_xlim(0, 4)
    ax.set_ylim(len(girths), 0)
    ax.set_xticks([j + 0.5 for j in range(4)])
    ax.set_xticklabels([f"ℓ₂ = {L}" for L in cols], fontsize=8.5)
    ax.xaxis.tick_top()
    ax.set_yticks([i + 0.5 for i in range(len(girths))])
    ax.set_yticklabels([f"g = {g}" for g in girths], fontsize=8)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(length=0)
    save(fig, out / fname)


def _tc_module(result: Path):
    spec = importlib.util.spec_from_file_location("encode", result / "encode.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def case_map(out: Path) -> None:
    """Gadget counts (a copies of H15, c of H7): what excludes each pair."""
    from matplotlib.patches import Rectangle
    fig, ax = plt.subplots(figsize=(7, 5.4))
    fig.subplots_adjust(left=0.1, right=0.97, bottom=0.2, top=0.84)
    title(fig, "Where the small lifts go",
          "a copies of H15, c of H7, the rest H8*; cell label = number of vertices 240 + 7a − c")
    A, C = range(10, 23), range(0, 16)
    for a in A:
        for c in C:
            if a + c > 30:
                continue
            n = 240 + 7 * a - c
            if 3 * a - c < 42:
                fc, tc, lab = "#262626", "#555555", ""
            elif (a + c == 30 and n < 370) or n < 345:
                fc, tc, lab = BLUE, SURFACE, str(n)
            else:
                fc, tc, lab = "#2f2f2f", TEXT2, str(n)
            if (a, c) in ((15, 0), (20, 10)):
                fc, tc = ORANGE, SURFACE
            ax.add_patch(Rectangle((a - 0.46, c - 0.46), 0.92, 0.92, color=fc, lw=0))
            if lab:
                ax.text(a, c, lab, ha="center", va="center", fontsize=6.3, color=tc)
    ax.plot([10 - 0.5, 22.5], [20.5, 7.5], color=TEXT2, lw=0.8, ls=":")
    ax.text(20.6, 13.2, "cubic lifts: a + c = 30", ha="left", fontsize=7.5, color=TEXT2)
    ax.set_xlim(9.4, 22.6)
    ax.set_ylim(-0.6, 15.6)
    ax.set_xlabel("a (copies of H15)")
    ax.set_ylabel("c (copies of H7)")
    ax.set_xticks(list(A))
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(length=0)
    fig.text(0.1, 0.07, "■", color="#262626", fontsize=11)
    fig.text(0.125, 0.07, "excluded by counting (3a − c < 42)", fontsize=8, color=TEXT2)
    fig.text(0.47, 0.07, "■", color=BLUE, fontsize=11)
    fig.text(0.495, 0.07, "refuted by SAT (cases A, B, C)", fontsize=8, color=TEXT2)
    fig.text(0.79, 0.07, "■", color=ORANGE, fontsize=11)
    fig.text(0.815, 0.07, "optimum", fontsize=8, color=TEXT2)
    save(fig, out / "case_map.svg")


def tc_weights(result: Path, out: Path) -> None:
    """Weights of the 90 eight-cycles in the two optimal lifts."""
    import json
    E = _tc_module(result)
    adj = E.tutte_coxeter()
    G = E.load_gadgets()
    dist = {g: E.port_distances(G[g]) for g in G}
    lifts = json.loads((ROOT / "results" / "small-graphs-power-of-two-cycles" / "data" /
                        "constructions.json").read_text())["lifts"]
    c8 = [E.off_edges(adj, c) for c in E.cycles(adj, (8,))]

    def weights(L):
        return [8 + sum(dist[L["gadget"][v]][1] if L["choice"][v] == o else dist[L["gadget"][v]][0]
                        for v, o in c) for c in c8]
    w345, w370 = weights(lifts["tc345"]), weights(lifts["tc370"])
    xs = list(range(33, max(w345 + w370) + 1))
    fig, ax = plt.subplots(figsize=(7, 4.2))
    fig.subplots_adjust(left=0.1, right=0.97, bottom=0.16, top=0.78)
    title(fig, "Most eight-cycles are exactly at the limit",
          "weight w(D) of the 90 eight-cycles in the two optimal lifts; w ≤ 32 would give a 32-cycle")
    for off, ws, col, lab in ((-0.2, w345, BLUE, "345 vertices (H15, H8*)"),
                              (0.2, w370, ORANGE, "370 vertices (H15, H7, cubic)")):
        ys = [ws.count(x) for x in xs]
        ax.bar([x + off for x in xs], ys, width=0.38, color=col, label=lab, zorder=2)
        for x, y in zip(xs, ys):
            if y:
                ax.text(x + off, y + 0.8, str(y), ha="center", fontsize=7.5, color=TEXT2)
    ax.set_xticks(xs)
    ax.set_xlabel("w(D)")
    ax.set_ylabel("eight-cycles")
    ax.grid(axis="y", color=GRID, lw=0.6, zorder=0)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.tick_params(length=0)
    ax.legend(loc="upper right", frameon=False, fontsize=8.5, labelcolor=TEXT)
    save(fig, out / "weights8.svg")


def port_paths(result: Path, out: Path) -> None:
    """Lengths of port-to-port paths in the three gadgets."""
    E = _tc_module(result)
    G = E.load_gadgets()
    rows = []
    for g, name in (("H7", "H7"), ("H8star", "H8*"), ("H15", "H15")):
        gr = G[g]
        adj = [[] for _ in range(gr["order"])]
        for u, v in gr["edges"]:
            adj[u].append(v)
            adj[v].append(u)
        P = gr["ports"]
        for i, j in ((0, 1), (1, 2)):
            got = set()

            def go(x, seen, d):
                if x == P[j]:
                    got.add(d)
                    return
                for y in adj[x]:
                    if y not in seen:
                        go(y, seen | {y}, d + 1)
            go(P[i], {P[i]}, 0)
            rows.append((f"{name}  ports {i},{j}", sorted(got)))
    fig, ax = plt.subplots(figsize=(7, 3.9))
    fig.subplots_adjust(left=0.2, right=0.97, bottom=0.16, top=0.76)
    title(fig, "No gaps in the path lengths",
          "lengths of paths between two ports; the shortest (orange) enters the weight w(D)")
    for k, (lab, ls) in enumerate(rows):
        y = len(rows) - 1 - k
        for L in ls:
            ax.add_patch(plt.Rectangle((L - 0.42, y - 0.32), 0.84, 0.64,
                                       color=ORANGE if L == ls[0] else BLUE, lw=0, zorder=2))
        ax.text(1.2, y, lab, ha="right", va="center", fontsize=8.5, color=TEXT)
    ax.set_xlim(1.3, 14.7)
    ax.set_ylim(-0.7, len(rows) - 0.3)
    ax.set_yticks([])
    ax.set_xticks(range(2, 15))
    ax.set_xlabel("path length")
    ax.grid(axis="x", color=GRID, lw=0.6, zorder=0)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.tick_params(length=0)
    save(fig, out / "port_paths.svg")


def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else "small-graphs-power-of-two-cycles"
    result = ROOT / "results" / name
    out = ROOT / "assets" / name
    out.mkdir(parents=True, exist_ok=True)
    page1(result, out)
    if name == "cubic-bipartite-power-of-two-cycles":
        root_branch_b(out)
        search_growth(result, out)
        cages16(result, out)
        return
    if name == "cubic-census-power-of-two-cycles":
        share32(result, out)
        girth_table(result, out, "main_Graph.txt", "girth_vt.svg", "Vertex-transitive, n ≤ 1280",
                    "graphs by girth g and shortest power-of-two cycle ℓ₂")
        girth_table(result, out, "AllSymmCubic-OrderUpTo10000-ByEdgeSets.txt.gz", "girth_sym.svg",
                    "Symmetric, n ≤ 10,000", "graphs by girth g and shortest power-of-two cycle ℓ₂")
        return
    if name == "tutte-coxeter-lifts-without-32-cycles":
        case_map(out)
        tc_weights(result, out)
        port_paths(result, out)
        return
    if not (result / "verify.py").exists():
        return  # results without construction data get only the first-page card
    V = load_verify(result)
    data = V.DATA
    gadgets(data, out)
    lift73(V, data, out)
    weights16(V, data, out)


if __name__ == "__main__":
    main()
