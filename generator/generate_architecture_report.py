import os
import json
import math
from collections import defaultdict, Counter

import pandas as pd
import networkx as nx


# ==============================
# CONFIG
# ==============================
ANALYSIS_DIR = "analysis"
CALLGRAPH_PATH = os.path.join(ANALYSIS_DIR, "call_graph.json")
FUNCTIONS_INDEX_PATH = os.path.join(ANALYSIS_DIR, "functions_index.json")
TASKS_PATH = os.path.join(ANALYSIS_DIR, "tasks.json")

OUT_DIR = os.path.join(ANALYSIS_DIR, "architecture")
os.makedirs(OUT_DIR, exist_ok=True)


# ==============================
# IO
# ==============================
def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ==============================
# GRAPH BUILDING
# ==============================
def function_to_module(functions_index, fn):
    fp = functions_index.get(fn, {}).get("file")
    return os.path.basename(fp) if fp else None


def build_module_dependency(callgraph, functions_index):
    edges = defaultdict(int)
    modules = set()

    for caller, callees in callgraph.items():
        src = function_to_module(functions_index, caller)
        if not src:
            continue

        modules.add(src)

        for callee in callees:
            dst = function_to_module(functions_index, callee)
            if not dst:
                continue

            modules.add(dst)

            if src != dst:
                edges[(src, dst)] += 1

    return edges, modules


def build_module_graph(edges, modules):
    G = nx.DiGraph()

    for m in modules:
        G.add_node(m)

    for (a, b), w in edges.items():
        G.add_edge(a, b, weight=float(w))

    return G


# ==============================
# METRICS
# ==============================
def compute_metrics(edges, modules):
    fan_in = Counter()
    fan_out = Counter()

    for (a, b), w in edges.items():
        fan_out[a] += w
        fan_in[b] += w

    G = build_module_graph(edges, modules)
    bet = nx.betweenness_centrality(G)

    rows = []

    for m in sorted(modules):
        fin = fan_in.get(m, 0)
        fout = fan_out.get(m, 0)
        denom = fin + fout
        instability = fout / denom if denom > 0 else 0.0

        rows.append({
            "module": m,
            "fanin": fin,
            "fanout": fout,
            "instability": instability,
            "betweenness": bet.get(m, 0.0),
        })

    df = pd.DataFrame(rows)
    return df, G


def compute_scc(G):
    sccs = [sorted(list(c)) for c in nx.strongly_connected_components(G) if len(c) > 1]
    sccs.sort(key=len, reverse=True)
    return sccs


def compute_task_sharing(tasks, functions_index):
    mod_task_count = Counter()

    for task, data in tasks.items():
        for fn in data.get("functions", []):
            mod = function_to_module(functions_index, fn)
            if mod:
                mod_task_count[mod] += 1

    return mod_task_count


def compute_hotspot_score(df, task_count, sccs):

    in_cycle = set()
    for comp in sccs:
        in_cycle.update(comp)

    df = df.copy()

    df["task_count"] = df["module"].map(lambda m: task_count.get(m, 0))
    df["in_cycle"] = df["module"].map(lambda m: 1 if m in in_cycle else 0)

    df["hotspot_score"] = (
        0.35 * df["betweenness"] * 100 +
        0.25 * df["fanin"].map(lambda x: math.log1p(x)) * 10 +
        0.20 * df["fanout"].map(lambda x: math.log1p(x)) * 10 +
        0.15 * df["task_count"] +
        0.05 * df["in_cycle"] * 20
    )

    return df.sort_values("hotspot_score", ascending=False)


# ==============================
# REPORT
# ==============================
def write_report(df, sccs):

    report_path = os.path.join(OUT_DIR, "ARCHITECTURE_HOTSPOTS.md")

    with open(report_path, "w", encoding="utf-8") as f:

        f.write("# Module-Level Architecture Hotspot Report\n\n")

        f.write(
            "This report identifies architectural hotspots at module (file) level "
            "using graph-theory-based metrics derived from the firmware call graph.\n\n"
        )

        f.write("---\n\n")

        f.write("## Metric Definitions\n\n")

        f.write("### Fan-In\n")
        f.write(
            "Number of incoming cross-module calls.\n\n"
            "- High Fan-In modules are widely reused.\n"
            "- Changes to these modules may impact large portions of the system.\n\n"
        )

        f.write("### Fan-Out\n")
        f.write(
            "Number of outgoing cross-module calls.\n\n"
            "- High Fan-Out modules depend on many other modules.\n"
            "- High Fan-Out increases fragility and change propagation risk.\n\n"
        )

        f.write("### Instability (I)\n")
        f.write(
            "Defined as:\n\n"
            "```\n"
            "I = FanOut / (FanIn + FanOut)\n"
            "```\n\n"
            "- I → 0 → Stable module\n"
            "- I → 1 → Highly dependent module\n\n"
        )

        f.write("### Betweenness Centrality\n")
        f.write(
            "Measures how often a module lies on shortest paths between other modules.\n\n"
            "- High centrality modules act as structural hubs or bottlenecks.\n\n"
        )

        f.write("### Task Sharing\n")
        f.write(
            "Number of RTOS tasks using the module.\n\n"
            "- Shared modules require careful synchronization.\n\n"
        )

        f.write("### Cyclic Dependency\n")
        f.write(
            "Module participates in a strongly connected component.\n\n"
            "- Indicates circular dependency.\n\n"
        )

        f.write("### Hotspot Score\n")
        f.write(
            "Composite ranking score combining coupling, centrality, instability, "
            "task sharing and cycle participation.\n\n"
        )

        f.write("---\n\n")

        f.write("## Top 15 Architectural Hotspots\n\n")

        top = df.head(15)

        f.write("| Rank | Module | Score | Fan-In | Fan-Out | Centrality | Instability | Tasks | In Cycle |\n")
        f.write("|------|--------|-------|--------|---------|------------|-------------|-------|----------|\n")

        for i, row in enumerate(top.itertuples(index=False), 1):
            f.write(
                f"| {i} | {row.module} | {row.hotspot_score:.1f} | "
                f"{row.fanin} | {row.fanout} | "
                f"{row.betweenness:.3f} | {row.instability:.2f} | "
                f"{row.task_count} | {row.in_cycle} |\n"
            )

        f.write("\n---\n\n")

        f.write("## Cyclic Module Dependencies\n\n")

        if not sccs:
            f.write("No cyclic module dependencies detected.\n")
        else:
            for comp in sccs:
                f.write(f"- Cycle ({len(comp)} modules): " + " → ".join(comp) + "\n")

        f.write("\n\nReport generated automatically by Firmware Lens.\n")

    print(f"[✓] Generated report: {report_path}")


# ==============================
# MAIN
# ==============================
def main():

    print("\n=== MODULE HOTSPOT DETECTION ===\n")

    callgraph = load_json(CALLGRAPH_PATH)
    functions_index = load_json(FUNCTIONS_INDEX_PATH)
    tasks = load_json(TASKS_PATH)

    if not callgraph or not functions_index:
        raise RuntimeError("Missing required analysis JSON files.")

    edges, modules = build_module_dependency(callgraph, functions_index)

    df_metrics, G = compute_metrics(edges, modules)

    sccs = compute_scc(G)

    task_count = compute_task_sharing(tasks, functions_index)

    df_hotspots = compute_hotspot_score(df_metrics, task_count, sccs)

    hotspots_csv = os.path.join(OUT_DIR, "module_hotspots.csv")
    df_hotspots.to_csv(hotspots_csv, index=False)

    print(f"[✓] Saved CSV: {hotspots_csv}")

    write_report(df_hotspots, sccs)

    print("\n🎯 Done.\n")


if __name__ == "__main__":
    main()