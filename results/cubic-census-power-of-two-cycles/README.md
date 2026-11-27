# Cycles of length 4, 8, 16 and 32 in censuses of cubic graphs

**Category C** (census computation with independently checked witnesses). Paper:
[`paper.pdf`](paper.pdf) ([TeX](paper.tex)).

> **Theorem.** Every connected cubic graph of girth at least 9 on at most 64
> vertices contains a 16-cycle. Hence every cubic graph of girth at least 8 on
> at most 64 vertices contains a cycle of length 8 or 16.
>
> **Theorem.** Every connected cubic vertex-transitive graph on at most 1280
> vertices (Potočnik–Spiga–Verret census) contains a cycle of length 4, 8, 16
> or 32.
>
> **Theorem.** Every connected cubic symmetric graph on at most 10,000 vertices
> (Conder's list) contains a cycle of length 4, 8, 16 or 32.

The first theorem assumes that the House of Graphs lists are complete. The
other two are statements about the published censuses.

## Shortest power-of-two cycle

| Census | Graphs | 4 | 8 | 16 | 32 |
|---|--:|--:|--:|--:|--:|
| cubic, girth ≥ 9, 58–64 vertices ([House of Graphs](https://houseofgraphs.org/meta-directory/cubic)) | 1,436,474 | – | – | 1,436,474 | – |
| cubic vertex-transitive, ≤ 1280 vertices ([doi:10.5281/zenodo.6576526](https://doi.org/10.5281/zenodo.6576526)) | 111,360 | 5,756 | 16,624 | 88,880 | 100 |
| cubic symmetric, ≤ 10,000 vertices ([Conder](https://www.math.auckland.ac.nz/~conder/)) | 3,815 | 3 | 111 | 3,012 | 689 |

The smallest vertex-transitive graph that needs a 32-cycle has 180 vertices
(CVT(180,50), girth 3). The smallest symmetric one is C1050.1 (1050 vertices,
girth 12). [`data/shortest32.tsv`](data/shortest32.tsv) lists all 789 graphs
that need a 32-cycle, each with one. [`data/summary.json`](data/summary.json)
breaks the counts down by girth. No graph needs a 64-cycle.

## What is checked, and by what

| Claim | Checked by |
|---|---|
| The input files are the published ones | SHA-256 hashes in [`data/sources.json`](data/sources.json) |
| Each graph has a cycle of the reported length | [`check_witnesses.py`](check_witnesses.py) checks every reported cycle edge by edge, after reading the census files with its own parsers |
| The reported length is the shortest power of two | girth ≥ 9 censuses: girth recomputed from every vertex; vertex-transitive and symmetric censuses: a second, different search through vertex 0 for every shorter length |
| The girth | recomputed, and compared with the girth stored in the vertex-transitive and symmetric censuses (all 115,175 agree) |
| The checker rejects wrong results | [`test_checker.py`](test_checker.py), nine corrupted results that must fail |

For a vertex-transitive graph, a cycle of length L through vertex 0 exists if
and only if the graph has a cycle of length L at all, so these censuses are
searched through vertex 0 only. Vertex-transitivity is taken from the census.

## Reproduce

```bash
python3 test_checker.py      # negative controls, < 1 s, standard library only
python3 run_census.py        # everything: ~3.5 min on 16 cores after a 2.6 GB download
```

`run_census.py` needs a C++17 compiler. It downloads the six input files into
`~/.cache/conjectures-census` (or `$CENSUS_CACHE`), checks their hashes,
compiles [`src/census_scan.cpp`](src/census_scan.cpp), scans every graph, runs
`check_witnesses.py`, and rewrites `data/summary.json` and
`data/shortest32.tsv`.

## Licence

CC0. The census files are not redistributed here; they are downloaded from
their publishers.
