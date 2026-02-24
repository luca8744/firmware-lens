import os
import json
import math
from collections import defaultdict, Counter

import pandas as pd
import matplotlib.pyplot as plt

# seaborn is optional but recommended for nicer heatmaps
try:
    import seaborn as sns
    _HAS_SEABORN = True
except Exception:
    _HAS_SEABORN = False

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
# LAYER MODEL
# ==============================
# You can tune these rules for your repos.
# The idea: classify file paths into architectural layers.
def classify_layer(file_path: str) -> str:
    if not file_path:
        return "Unknown"

    p = file_path.replace("\\", "/").lower()

    # Common STM32 + embedded patterns
    if "/cmsis/" in p or "cmsis" in p:
        return "CMSIS"
    if "/drivers/" in p and "cmsis" not in p:
        # ST projects often keep HAL inside Drivers/STM32xx_HAL_Driver
        if "hal" in p or "stm32" in p and "hal" in p:
            return "HAL"
        return "Drivers"
    if "stm32" in p and "hal" in p:
        return "HAL"
    if "/middleware/" in p or "middleware" in p:
        return "Middleware"
    if "/application/" in p or "/app/" in p or "application" in p:
        return "Application"

    # Some projects put app in root folders like "src", "core", etc.
    if "/src/" in p or "/core/" in p:
        return "Application"

    return "Other"


# Define allowed dependency direction (top -> bottom)
LAYER_ORDER = ["Application", "Middleware", "Drivers", "HAL", "CMSIS", "Other", "Unknown"]
LAYER_RANK = {name: i for i, name in enumerate(LAYER_ORDER)}

def is_violation(src_layer: str, dst_layer: str) -> bool:
    """
    A "violation" is when a lower layer depends on a higher layer.
    Example: HAL -> Application.
    We treat Unknown/Other as weakly ordered (still ranked, but you can tune).
    """
    rs = LAYER_RANK.get(src_layer, LAYER_RANK["Unknown"])
    rd = LAYER_RANK.get(dst_layer, LAYER_RANK["Unknown"])
    return rs > rd  # lower layer calling "up"


# ==============================
# CORE DERIVATIONS
# ==============================
def function_to_module(functions_index: dict, fn: str) -> str | None:
    fp = functions_index.get(fn, {}).get("file")
    if not fp:
        return None
    return os.path.basename(fp)

def function_to_layer(functions_index: dict, fn: str) -> str:
    fp = functions_index.get(fn, {}).get("file")
    return classify_layer(fp) if fp else "Unknown"

def build_fn_to_task(tasks: dict) -> dict:
    fn_to_task = {}
    for task_name, data in tasks.items():
        for fn in data.get("functions", []):
            fn_to_task[fn] = task_name
    return fn_to_task

def build_module_dependency(callgraph: dict, functions_index: dict):
    """
    Returns:
      edges_count[(src_mod, dst_mod)] = number of function-level cross-module calls
      modules_set
    """
    edges_count = defaultdict(int)
    modules = set()

    for caller, callees in callgraph.items():
        src_mod = function_to_module(functions_index, caller)
        if not src_mod:
            continue
        modules.add(src_mod)

        for callee in callees:
            dst_mod = function_to_module(functions_index, callee)
            if not dst_mod:
                continue
            modules.add(dst_mod)

            if src_mod != dst_mod:
                edges_count[(src_mod, dst_mod)] += 1

    return edges_count, modules

def build_layer_violations(callgraph: dict, functions_index: dict):
    """
    Violations computed at function-call granularity but aggregated per module pair.
    """
    violations = defaultdict(int)

    for caller, callees in callgraph.items():
        src_mod = function_to_module(functions_index, caller)
        if not src_mod:
            continue
        src_layer = function_to_layer(functions_index, caller)

        for callee in callees:
            dst_mod = function_to_module(functions_index, callee)
            if not dst_mod or src_mod == dst_mod:
                continue
            dst_layer = function_to_layer(functions_index, callee)

            if is_violation(src_layer, dst_layer):
                violations[(src_mod, src_layer, dst_mod, dst_layer)] += 1

    return violations

def compute_task_interaction_matrix(callgraph: dict, tasks: dict):
    fn_to_task = build_fn_to_task(tasks)
    task_names = list(tasks.keys())
    m = pd.DataFrame(0, index=task_names, columns=task_names, dtype=int)

    for caller, callees in callgraph.items():
        t_src = fn_to_task.get(caller)
        if not t_src:
            continue
        for callee in callees:
            t_dst = fn_to_task.get(callee)
            if t_dst:
                m.loc[t_src, t_dst] += 1

    return m, fn_to_task

def compute_shared_modules_by_task(tasks: dict, functions_index: dict):

    task_to_modules = {}

    for task, data in tasks.items():

        mods = set()

        functions = data.get("functions", [])
        if not isinstance(functions, list):
            continue

        for fn in functions:
            fp = functions_index.get(fn, {}).get("file")
            if fp:
                mods.add(os.path.basename(fp))

        task_to_modules[task] = mods

    module_to_tasks = defaultdict(set)

    for task, mods in task_to_modules.items():
        for mod in mods:
            module_to_tasks[mod].add(task)

    rows = []

    for mod, tset in module_to_tasks.items():
        rows.append({
            "module": mod,
            "task_count": len(tset),
            "tasks": ", ".join(sorted(tset)),
        })

    if not rows:
        # Return empty dataframe with correct columns
        df = pd.DataFrame(columns=["module", "task_count", "tasks"])
    else:
        df = pd.DataFrame(rows).sort_values(
            ["task_count", "module"],
            ascending=[False, True]
        )

    return df, task_to_modules

# ==============================
# VISUALS
# ==============================
def save_heatmap(df: pd.DataFrame, title: str, out_path: str, annotate: bool = False):
    # For large matrices, annotations become unreadable, keep off by default
    figsize = (max(10, int(df.shape[1] * 0.25)), max(8, int(df.shape[0] * 0.25)))
    plt.figure(figsize=figsize)

    if _HAS_SEABORN:
        sns.heatmap(df, cmap="Blues", annot=annotate, fmt="d" if annotate else "")
    else:
        plt.imshow(df.values, aspect="auto")
        plt.title(title)
        plt.colorbar()

    plt.title(title)
    plt.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close()

def build_module_coupling_matrix(edges_count: dict, modules: set):
    modules = sorted(modules)
    mat = pd.DataFrame(0, index=modules, columns=modules, dtype=int)
    for (a, b), w in edges_count.items():
        mat.loc[a, b] = int(w)

    # remove fully isolated rows/cols to make it readable
    mat = mat.loc[(mat.sum(axis=1) > 0), (mat.sum(axis=0) > 0)]
    return mat


# ==============================
# METRICS
# ==============================
def compute_module_metrics(edges_count: dict, modules: set):
    """
    Fan-in / Fan-out on module graph (unweighted and weighted),
    instability I = fanout / (fanin + fanout) using weighted counts.
    Also computes betweenness centrality on directed module graph.
    """
    # Weighted fan-in/out
    fan_out_w = Counter()
    fan_in_w = Counter()

    # Unweighted fan-in/out (unique dependencies)
    fan_out_u = Counter()
    fan_in_u = Counter()

    for (a, b), w in edges_count.items():
        fan_out_w[a] += w
        fan_in_w[b] += w
        fan_out_u[a] += 1
        fan_in_u[b] += 1

    # Build directed module graph (unweighted for centrality)
    G = nx.DiGraph()
    for m in modules:
        G.add_node(m)
    for (a, b), w in edges_count.items():
        G.add_edge(a, b, weight=float(w))

    # Betweenness centrality: unweighted edges is usually enough for "hub-ness"
    bet = nx.betweenness_centrality(G)

    rows = []
    for m in sorted(modules):
        fin = int(fan_in_w.get(m, 0))
        fout = int(fan_out_w.get(m, 0))
        denom = fin + fout
        instability = (fout / denom) if denom > 0 else 0.0

        rows.append({
            "module": m,
            "fanin_weighted": fin,
            "fanout_weighted": fout,
            "fanin_unique": int(fan_in_u.get(m, 0)),
            "fanout_unique": int(fan_out_u.get(m, 0)),
            "instability": float(instability),
            "betweenness": float(bet.get(m, 0.0)),
        })

    df = pd.DataFrame(rows)
    return df, bet, G


def compute_density_stats(edges_count: dict, modules: set):
    # directed possible edges = N*(N-1)
    n = len(modules)
    possible = n * (n - 1) if n > 1 else 1
    actual = len(edges_count)
    density = actual / possible
    total_cross_calls = int(sum(edges_count.values()))
    return {
        "module_count": n,
        "edge_count": actual,
        "possible_edges": possible,
        "density": density,
        "total_cross_module_calls": total_cross_calls,
    }


# ==============================
# REPORT (MD)
# ==============================
def md_escape(text: str) -> str:
    return text.replace("|", "\\|")

def write_report(
    *,
    out_path: str,
    task_matrix: pd.DataFrame,
    task_heatmap_png: str,
    module_matrix: pd.DataFrame,
    module_heatmap_png: str,
    module_metrics: pd.DataFrame,
    centrality_top20_csv: str,
    module_metrics_csv: str,
    layer_violations_csv: str,
    task_shared_modules_csv: str,
    stats: dict,
    tasks_coverage: dict
):

    total_task_calls = int(task_matrix.values.sum())
    n_tasks = task_matrix.shape[0]

    density = stats["density"]
    module_count = stats["module_count"]
    edge_count = stats["edge_count"]

    # Simple architecture risk heuristic
    top_bet = float(module_metrics["betweenness"].max()) if len(module_metrics) else 0.0
    top_fanin = int(module_metrics["fanin_weighted"].max()) if len(module_metrics) else 0

    risk_score = min(
        100,
        int(density * 2000) +
        int(top_bet * 200) +
        int(top_fanin / 20)
    )

    if risk_score < 35:
        risk_label = "LOW"
    elif risk_score < 70:
        risk_label = "MEDIUM"
    else:
        risk_label = "HIGH"

    mapped_fns = tasks_coverage["functions_mapped_to_task"]
    total_fns = tasks_coverage["functions_present_in_callgraph"]
    coverage_pct = (mapped_fns / total_fns * 100.0) if total_fns else 0.0

    with open(out_path, "w", encoding="utf-8") as f:

        f.write("# Firmware Architecture Analysis Report\n\n")

        f.write("This report has been automatically generated from the extracted firmware call graph, task model and module structure.\n\n")

        f.write("## Executive Summary\n\n")
        f.write(f"- Tasks detected: **{n_tasks}**\n")
        f.write(f"- Modules (file-level): **{module_count}**\n")
        f.write(f"- Cross-module dependencies: **{edge_count}**\n")
        f.write(f"- Architecture density: **{density:.4f}**\n")
        f.write(f"- Architecture Risk Score (heuristic): **{risk_score}/100 → {risk_label}**\n\n")

        f.write("---\n\n")

        f.write("## 1. Task Interaction Matrix\n\n")
        f.write("The matrix represents function-level calls between tasks.\n\n")
        f.write(f"![Task Interaction]({os.path.basename(task_heatmap_png)})\n\n")

        if total_task_calls == 0:
            f.write("No direct cross-task function calls were detected.\n")
            f.write("This may indicate good task isolation or incomplete task-function mapping.\n\n")
        else:
            f.write(f"Total cross-task interactions detected: **{total_task_calls}**\n\n")

        f.write("### Task Mapping Coverage\n\n")
        f.write(f"- Functions in call graph: **{total_fns}**\n")
        f.write(f"- Functions mapped to tasks: **{mapped_fns} ({coverage_pct:.1f}%)**\n\n")

        if coverage_pct < 30:
            f.write("> ⚠ Low coverage: task-level analysis may be incomplete.\n\n")

        f.write("---\n\n")

        f.write("## 2. Module Coupling Analysis\n\n")
        f.write("This heatmap shows file-level dependencies.\n\n")
        f.write(f"![Module Coupling]({os.path.basename(module_heatmap_png)})\n\n")

        f.write("Interpretation:\n\n")
        f.write("- Dark rows → modules that depend on many others (high fan-out)\n")
        f.write("- Dark columns → highly reused modules (high fan-in)\n\n")

        f.write("---\n\n")

        f.write("## 3. Module Centrality\n\n")
        f.write("Betweenness centrality identifies architectural hubs.\n")
        f.write("Modules with high centrality often represent critical coordination points.\n\n")

        top10 = module_metrics.sort_values("betweenness", ascending=False).head(10)

        f.write("| Rank | Module | Centrality | Fan-In | Fan-Out | Instability |\n")
        f.write("|------|--------|------------|--------|---------|-------------|\n")

        for i, row in enumerate(top10.itertuples(index=False), 1):
            f.write(
                f"| {i} | {row.module} | {row.betweenness:.4f} | "
                f"{int(row.fanin_weighted)} | {int(row.fanout_weighted)} | "
                f"{row.instability:.2f} |\n"
            )

        f.write("\n---\n\n")

        f.write("## 4. Instability Metric\n\n")
        f.write("Instability is defined as:\n\n")
        f.write("```\n")
        f.write("I = FanOut / (FanIn + FanOut)\n")
        f.write("```\n\n")
        f.write("- I → 0 → stable module (widely reused)\n")
        f.write("- I → 1 → highly dependent module\n\n")

        unstable = module_metrics.sort_values("instability", ascending=False).head(5)

        f.write("### Most Unstable Modules\n\n")
        f.write("| Module | Instability |\n")
        f.write("|--------|------------|\n")
        for row in unstable.itertuples(index=False):
            f.write(f"| {row.module} | {row.instability:.2f} |\n")

        f.write("\n---\n\n")

        f.write("## 5. Layer Violations\n\n")
        f.write("Layering rules assumed:\n")
        f.write("Application → Middleware → Drivers → HAL → CMSIS\n\n")
        f.write("Lower layers depending on upper layers are considered violations.\n\n")
        f.write(f"See CSV: `{os.path.basename(layer_violations_csv)}`\n\n")

        f.write("---\n\n")

        f.write("## 6. Task Shared Modules\n\n")
        f.write("Modules used by multiple tasks may represent shared infrastructure.\n")
        f.write("Such modules should be carefully reviewed for synchronization and global state usage.\n\n")
        f.write(f"See CSV: `{os.path.basename(task_shared_modules_csv)}`\n\n")

        f.write("---\n\n")

        f.write("## Final Assessment\n\n")

        if risk_label == "LOW":
            f.write("The architecture appears modular and reasonably well structured.\n")
        elif risk_label == "MEDIUM":
            f.write("Moderate architectural coupling detected. Review high-centrality modules.\n")
        else:
            f.write("High architectural risk detected. Significant centralization or coupling present.\n")

        f.write("\nReport generated automatically by Firmware Lens.\n")

    print(f"[✓] Generated report: {out_path}")


# ==============================
# MAIN PIPELINE
# ==============================
def main():
    print("\n=== GENERATE ARCHITECTURE METRICS + REPORT ===\n")

    callgraph = load_json(CALLGRAPH_PATH)
    functions_index = load_json(FUNCTIONS_INDEX_PATH)
    tasks = load_json(TASKS_PATH)

    if not callgraph:
        raise RuntimeError(f"Missing or empty: {CALLGRAPH_PATH}")
    if not functions_index:
        raise RuntimeError(f"Missing or empty: {FUNCTIONS_INDEX_PATH}")
    if not tasks:
        raise RuntimeError(f"Missing or empty: {TASKS_PATH}")

    # --- Task interaction matrix + heatmap
    task_matrix, fn_to_task = compute_task_interaction_matrix(callgraph, tasks)
    task_png = os.path.join(OUT_DIR, "task_interaction_heatmap.png")
    # annotate only for small task counts
    annotate = task_matrix.shape[0] <= 22
    save_heatmap(task_matrix, "Task Interaction Matrix", task_png, annotate=annotate)

    # coverage stats
    fn_present = set(callgraph.keys())
    for _, callees in callgraph.items():
        fn_present.update(callees)
    mapped_fns = sum(1 for fn in fn_present if fn in fn_to_task)
    tasks_coverage = {
        "functions_present_in_callgraph": len(fn_present),
        "functions_mapped_to_task": mapped_fns,
    }

    # --- Module coupling
    edges_count, modules = build_module_dependency(callgraph, functions_index)
    module_matrix = build_module_coupling_matrix(edges_count, modules)
    module_png = os.path.join(OUT_DIR, "module_coupling_heatmap.png")
    # no annotation for large matrices
    save_heatmap(module_matrix, "Module Coupling Heatmap", module_png, annotate=False)

    # --- Module metrics: fan-in/out, instability, centrality
    module_metrics, bet_map, Gmod = compute_module_metrics(edges_count, modules)
    module_metrics_csv = os.path.join(OUT_DIR, "module_metrics.csv")
    module_metrics.to_csv(module_metrics_csv, index=False)

    # centrality top20
    top20 = module_metrics.sort_values("betweenness", ascending=False).head(20)[["module", "betweenness"]]
    centrality_csv = os.path.join(OUT_DIR, "module_centrality_top20.csv")
    top20.to_csv(centrality_csv, index=False)

    # --- Layer violations
    violations = build_layer_violations(callgraph, functions_index)
    viol_rows = []
    for (src_mod, src_layer, dst_mod, dst_layer), c in violations.items():
        viol_rows.append({
            "src_module": src_mod,
            "src_layer": src_layer,
            "dst_module": dst_mod,
            "dst_layer": dst_layer,
            "count": int(c),
        })
    viol_df = pd.DataFrame(viol_rows).sort_values("count", ascending=False) if viol_rows else pd.DataFrame(
        columns=["src_module", "src_layer", "dst_module", "dst_layer", "count"]
    )
    violations_csv = os.path.join(OUT_DIR, "layer_violations.csv")
    viol_df.to_csv(violations_csv, index=False)

    # --- Shared modules by task
    shared_df, task_to_modules = compute_shared_modules_by_task(tasks, functions_index)
    shared_csv = os.path.join(OUT_DIR, "task_shared_modules.csv")
    shared_df.to_csv(shared_csv, index=False)

    # --- Density stats
    stats = compute_density_stats(edges_count, modules)

    # --- Write markdown report
    report_md = os.path.join(OUT_DIR, "ARCHITECTURE_REPORT.md")
    write_report(
        out_path=report_md,
        task_matrix=task_matrix,
        task_heatmap_png=task_png,
        module_matrix=module_matrix,
        module_heatmap_png=module_png,
        module_metrics=module_metrics,
        centrality_top20_csv=centrality_csv,
        module_metrics_csv=module_metrics_csv,
        layer_violations_csv=violations_csv,
        task_shared_modules_csv=shared_csv,
        stats=stats,
        tasks_coverage=tasks_coverage,
    )

    print("\n🎯 Done.")
    print(f"- {task_png}")
    print(f"- {module_png}")
    print(f"- {centrality_csv}")
    print(f"- {module_metrics_csv}")
    print(f"- {violations_csv}")
    print(f"- {shared_csv}")
    print(f"- {report_md}\n")


if __name__ == "__main__":
    main()