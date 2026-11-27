// SPDX-License-Identifier: CC0-1.0
//
// For each graph of a census, find the shortest power-of-two cycle length L in
// {4, 8, 16, 32} and print one explicit cycle of that length as a witness.
//
// Input (stdin): one graph per line, "<id>\t<graph>", where <graph> is graph6, sparse6
// (leading ':'), or an edge list "E<n>:<u>-<v>,<u>-<v>,..." with 0-based vertices.
// Output (stdout): "<id>\t<n>\t<girth or 0>\t<L>\t<v0,v1,...,v_{L-1}>", or "<id>\t<n>\t<g>\tNONE"
// if there is no cycle of length 4, 8, 16 or 32 (in the scanned set of
// start vertices). Graphs that are not simple, cubic and connected abort the run.
//
// Modes:
//   --mode general  cycles through every start vertex (exact for any graph);
//   --mode vt       cycles through vertex 0 only. For a vertex-transitive graph this is
//                   exact, since every vertex lies on a cycle of each length that occurs.
//
// Method: a cycle of length L = 2h through v0 consists of two paths of length h from v0
// to a common far vertex w, with disjoint interiors. All simple paths of length h from v0
// are enumerated (at most 3 * 2^(h-1)), grouped by end vertex, and pairs with disjoint
// interiors are searched. This is complete: every L-cycle through v0 is found.
//
// Build: g++ -O3 -std=c++17 -pthread census_scan.cpp -o census_scan
// Usage: census_scan --mode general|vt [--girth] [--workers W] < graphs.tsv > witnesses.tsv

#include <algorithm>
#include <atomic>
#include <cstdint>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

namespace {

using Adj = std::vector<std::vector<int>>;

Adj decode_graph6(const std::string& s) {
    std::size_t pos = 0;
    auto byte = [&](std::size_t i) {
        if (i >= s.size()) throw std::runtime_error("graph6: truncated");
        const int v = static_cast<unsigned char>(s[i]) - 63;
        if (v < 0 || v > 63) throw std::runtime_error("graph6: bad character");
        return v;
    };
    long n;
    if (byte(0) == 63) {
        if (byte(1) == 63) throw std::runtime_error("graph6: n too large");
        n = (static_cast<long>(byte(1)) << 12) | (byte(2) << 6) | byte(3);
        pos = 4;
    } else {
        n = byte(0);
        pos = 1;
    }
    Adj adj(n);
    int bit = 6, cur = 0;
    for (long j = 1; j < n; ++j) {
        for (long i = 0; i < j; ++i) {
            if (bit == 6) { cur = byte(pos++); bit = 0; }
            if ((cur >> (5 - bit)) & 1) { adj[i].push_back(j); adj[j].push_back(i); }
            ++bit;
        }
    }
    return adj;
}

Adj decode_sparse6(const std::string& s) {
    // Format reference: nauty's formats.txt (sparse6).
    std::size_t pos = 1;  // skip ':'
    auto byte = [&](std::size_t i) {
        if (i >= s.size()) throw std::runtime_error("sparse6: truncated");
        const int v = static_cast<unsigned char>(s[i]) - 63;
        if (v < 0 || v > 63) throw std::runtime_error("sparse6: bad character");
        return v;
    };
    long n;
    if (byte(1) == 63) {
        if (byte(2) == 63) {
            n = 0;
            for (int i = 3; i < 9; ++i) n = (n << 6) | byte(i);
            pos = 9;
        } else {
            n = (static_cast<long>(byte(2)) << 12) | (byte(3) << 6) | byte(4);
            pos = 5;
        }
    } else {
        n = byte(1);
        pos = 2;
    }
    int k = 0;
    while ((1L << k) < n) ++k;
    Adj adj(n);
    std::vector<int> bits;
    for (std::size_t i = pos; i < s.size(); ++i) {
        const int v = byte(i);
        for (int b = 5; b >= 0; --b) bits.push_back((v >> b) & 1);
    }
    std::size_t p = 0;
    long v = 0;
    while (p < bits.size()) {
        const int b = bits[p++];
        if (p + static_cast<std::size_t>(k) > bits.size()) break;
        long x = 0;
        for (int i = 0; i < k; ++i) x = (x << 1) | bits[p++];
        if (b == 1) ++v;
        if (v >= n) break;
        if (x > v) {
            v = x;
        } else {
            adj[x].push_back(v);
            if (x != v) adj[v].push_back(x);
        }
    }
    return adj;
}

Adj decode_edges(const std::string& s) {
    // "E<n>:<u>-<v>,<u>-<v>,..."
    const std::size_t colon = s.find(':');
    const long n = std::stol(s.substr(1, colon - 1));
    Adj adj(n);
    std::stringstream ss(s.substr(colon + 1));
    std::string tok;
    while (std::getline(ss, tok, ',')) {
        const std::size_t dash = tok.find('-');
        const int u = std::stoi(tok.substr(0, dash)), w = std::stoi(tok.substr(dash + 1));
        if (dash == std::string::npos || u < 0 || w < 0 || u >= n || w >= n)
            throw std::runtime_error("edge list: vertex out of range");
        adj[u].push_back(w);
        adj[w].push_back(u);
    }
    return adj;
}

Adj decode(const std::string& g) {
    if (g.empty()) throw std::runtime_error("empty graph string");
    if (g[0] == ':') return decode_sparse6(g);
    if (g[0] == 'E') return decode_edges(g);
    return decode_graph6(g);
}

void check_simple_cubic_connected(const Adj& adj) {
    const int n = static_cast<int>(adj.size());
    for (int v = 0; v < n; ++v) {
        if (adj[v].size() != 3) throw std::runtime_error("not cubic");
        for (int w : adj[v]) {
            if (w == v) throw std::runtime_error("loop");
            if (std::count(adj[v].begin(), adj[v].end(), w) != 1) throw std::runtime_error("multi-edge");
        }
    }
    std::vector<char> seen(n, 0);
    std::vector<int> stack{0};
    seen[0] = 1;
    int cnt = 1;
    while (!stack.empty()) {
        const int v = stack.back();
        stack.pop_back();
        for (int w : adj[v])
            if (!seen[w]) { seen[w] = 1; ++cnt; stack.push_back(w); }
    }
    if (cnt != n) throw std::runtime_error("not connected");
}

int girth(const Adj& adj, bool vt) {
    const int n = static_cast<int>(adj.size());
    int best = 0;
    std::vector<int> dist(n), par(n), q(n);
    for (int s = 0; s < (vt ? 1 : n); ++s) {
        std::fill(dist.begin(), dist.end(), -1);
        dist[s] = 0; par[s] = -1;
        int head = 0, tail = 0;
        q[tail++] = s;
        while (head < tail) {
            const int v = q[head++];
            if (best && 2 * dist[v] + 1 >= best) break;
            for (int w : adj[v]) {
                if (dist[w] < 0) { dist[w] = dist[v] + 1; par[w] = v; q[tail++] = w; }
                else if (w != par[v]) {
                    const int len = dist[v] + dist[w] + 1;
                    if (!best || len < best) best = len;
                }
            }
        }
    }
    return best;
}

// Cycle of length 2h through v0, or empty.
std::vector<int> cycle_through(const Adj& adj, int v0, int h, std::vector<int>& stamp, int& epoch) {
    const int n = static_cast<int>(adj.size());
    if (2 * h > n) return {};
    std::vector<std::vector<int>> paths;
    std::vector<int> cur{v0};
    std::vector<char> on(n, 0);
    on[v0] = 1;
    // iterative DFS over simple paths of length h
    std::vector<std::size_t> it{0};
    while (!it.empty()) {
        const int v = cur.back();
        if (static_cast<int>(cur.size()) == h + 1) {
            paths.push_back(cur);
            on[v] = 0; cur.pop_back(); it.pop_back();
            continue;
        }
        std::size_t& i = it.back();
        if (i == adj[v].size()) {
            on[v] = 0; cur.pop_back(); it.pop_back();
            continue;
        }
        const int w = adj[v][i++];
        if (on[w]) continue;
        on[w] = 1; cur.push_back(w); it.push_back(0);
    }
    if (on[v0]) on[v0] = 0;
    std::sort(paths.begin(), paths.end(), [](const std::vector<int>& a, const std::vector<int>& b) {
        return a.back() != b.back() ? a.back() < b.back() : a < b;
    });
    for (std::size_t lo = 0; lo < paths.size();) {
        std::size_t hi = lo;
        while (hi < paths.size() && paths[hi].back() == paths[lo].back()) ++hi;
        for (std::size_t a = lo; a < hi; ++a) {
            ++epoch;
            for (int k = 1; k < h; ++k) stamp[paths[a][k]] = epoch;
            for (std::size_t b = a + 1; b < hi; ++b) {
                bool ok = true;
                for (int k = 1; k < h && ok; ++k) ok = stamp[paths[b][k]] != epoch;
                if (!ok) continue;
                std::vector<int> cyc(paths[a].begin(), paths[a].end());
                for (int k = h - 1; k >= 1; --k) cyc.push_back(paths[b][k]);
                return cyc;
            }
        }
        lo = hi;
    }
    return {};
}

struct Result {
    std::string line;
    std::string error;
};

}  // namespace

int main(int argc, char** argv) {
    std::string mode;
    bool want_girth = false;
    int workers = static_cast<int>(std::max(1u, std::thread::hardware_concurrency()));
    for (int i = 1; i < argc; ++i) {
        const std::string a = argv[i];
        if (a == "--mode" && i + 1 < argc) mode = argv[++i];
        else if (a == "--girth") want_girth = true;
        else if (a == "--workers" && i + 1 < argc) workers = std::max(1, std::stoi(argv[++i]));
        else { std::cerr << "usage: census_scan --mode general|vt [--girth] [--workers W]\n"; return 64; }
    }
    if (mode != "general" && mode != "vt") { std::cerr << "--mode general|vt required\n"; return 64; }
    const bool vt = mode == "vt";

    std::vector<std::string> ids, graphs;
    std::string line;
    while (std::getline(std::cin, line)) {
        if (line.empty()) continue;
        const std::size_t tab = line.find('\t');
        if (tab == std::string::npos) { std::cerr << "bad input line\n"; return 65; }
        ids.push_back(line.substr(0, tab));
        graphs.push_back(line.substr(tab + 1));
    }
    std::vector<Result> out(ids.size());
    std::atomic<std::size_t> next{0};
    auto work = [&]() {
        std::vector<int> stamp;
        int epoch = 0;
        for (std::size_t i; (i = next.fetch_add(1)) < ids.size();) {
            try {
                const Adj adj = decode(graphs[i]);
                check_simple_cubic_connected(adj);
                const int n = static_cast<int>(adj.size());
                if (static_cast<int>(stamp.size()) < n) { stamp.assign(n, 0); epoch = 0; }
                const int g = want_girth ? girth(adj, vt) : 0;
                std::vector<int> cyc;
                int L = 0;
                for (int h = 2; h <= 16 && cyc.empty(); h *= 2) {
                    for (int v0 = 0; v0 < (vt ? 1 : n) && cyc.empty(); ++v0)
                        cyc = cycle_through(adj, v0, h, stamp, epoch);
                    if (!cyc.empty()) L = 2 * h;
                }
                std::ostringstream os;
                os << ids[i] << '\t' << n << '\t' << g << '\t';
                if (cyc.empty()) os << "NONE";
                else {
                    os << L << '\t';
                    for (std::size_t k = 0; k < cyc.size(); ++k) os << (k ? "," : "") << cyc[k];
                }
                out[i].line = os.str();
            } catch (const std::exception& e) {
                out[i].error = ids[i] + ": " + e.what();
            }
        }
    };
    std::vector<std::thread> pool;
    for (int w = 0; w < workers; ++w) pool.emplace_back(work);
    for (auto& t : pool) t.join();
    int bad = 0;
    for (const auto& r : out) {
        if (!r.error.empty()) { std::cerr << "ERROR " << r.error << '\n'; ++bad; continue; }
        std::cout << r.line << '\n';
    }
    return bad ? 1 : 0;
}
