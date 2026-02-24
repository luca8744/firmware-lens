import os
import json
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import networkx as nx
from collections import defaultdict

ANALYSIS_DIR = "analysis"
CALLGRAPH_PATH = os.path.join(ANALYSIS_DIR, "call_graph.json")
FUNCTIONS_INDEX_PATH = os.path.join(ANALYSIS_DIR, "functions_index.json")
TASKS_PATH = os.path.join(ANALYSIS_DIR, "tasks.json")

OUT_DIR = os.path.join(ANALYSIS_DIR, "architecture")
os.makedirs(OUT_DIR, exist_ok=True)


def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_function_to_task_map(tasks):
    fn_to_task = {}
    for task_name, data in tasks.items():
        for fn in data.get("functions", []):
            fn_to_task[fn] = task_name
    return fn_to_task


# ==========================================
# TASK HEATMAP
# ==========================================

def generate_task_heatmap(callgraph, tasks):

    fn_to_task = build_function_to_task_map(tasks)
    task_names = list(tasks.keys())

    matrix = pd.DataFrame(0, index=task_names, columns=task_names)

    for caller, callees in callgraph.items():
        caller_task = fn_to_task.get(caller)
        if not caller_task:
            continue

        for callee in callees:
            callee_task = fn_to_task.get(callee)
            if callee_task:
                matrix.loc[caller_task, callee_task] += 1

    plt.figure(figsize=(10, 8))
    sns.heatmap(matrix, annot=True, fmt="d", cmap="Reds")
    plt.title("Task Interaction Matrix")
    plt.tight_layout()

    heatmap_path = os.path.join(OUT_DIR, "task_interaction_heatmap.png")
    plt.savefig(heatmap_path, dpi=300)
    plt.close()

    return matrix, heatmap_path


# ==========================================
# MODULE COUPLING
# ==========================================

def generate_module_heatmap(callgraph, functions_index):

    modules = set()
    edges = defaultdict(int)

    for caller, callees in callgraph.items():
        caller_file = functions_index.get(caller, {}).get("file")
        if not caller_file:
            continue

        caller_mod = os.path.basename(caller_file)
        modules.add(caller_mod)

        for callee in callees:
            callee_file = functions_index.get(callee, {}).get("file")
            if not callee_file:
                continue

            callee_mod = os.path.basename(callee_file)
            modules.add(callee_mod)

            if caller_mod != callee_mod:
                edges[(caller_mod, callee_mod)] += 1

    modules = sorted(modules)
    matrix = pd.DataFrame(0, index=modules, columns=modules)

    for (a, b), count in edges.items():
        matrix.loc[a, b] = count

    matrix = matrix.loc[(matrix.sum(axis=1) > 0), (matrix.sum(axis=0) > 0)]

    plt.figure(figsize=(12, 10))
    sns.heatmap(matrix, cmap="Blues")
    plt.title("Module Coupling Heatmap")
    plt.tight_layout()

    heatmap_path = os.path.join(OUT_DIR, "module_coupling_heatmap.png")
    plt.savefig(heatmap_path, dpi=300)
    plt.close()

    return matrix, heatmap_path


# ==========================================
# CENTRALITY
# ==========================================

def compute_module_centrality(callgraph, functions_index):

    G = nx.DiGraph()

    for caller, callees in callgraph.items():
        caller_file = functions_index.get(caller, {}).get("file")
        if not caller_file:
            continue

        caller_mod = os.path.basename(caller_file)

        for callee in callees:
            callee_file = functions_index.get(callee, {}).get("file")
            if not callee_file:
                continue

            callee_mod = os.path.basename(callee_file)

            if caller_mod != callee_mod:
                G.add_edge(caller_mod, callee_mod)

    centrality = nx.betweenness_centrality(G)
    ranking = sorted(centrality.items(), key=lambda x: x[1], reverse=True)

    return ranking


# ==========================================
# REPORT GENERATION
# ==========================================

def generate_report(task_matrix, module_matrix, centrality_ranking,
                    task_img, module_img):

    report_path = os.path.join(OUT_DIR, "ARCHITECTURE_REPORT.md")

    with open(report_path, "w", encoding="utf-8") as f:

        f.write("# Firmware Architecture Report\n\n")

        f.write("## 1. Task Interaction Analysis\n\n")

        if task_matrix.values.sum() == 0:
            f.write("- No direct cross-task function calls detected.\n")
            f.write("- Tasks appear logically isolated.\n\n")
        else:
            f.write("- Cross-task interactions detected.\n")
            f.write(f"- Total cross-task calls: {task_matrix.values.sum()}\n\n")

        f.write(f"![Task Heatmap]({os.path.basename(task_img)})\n\n")

        f.write("## 2. Module Coupling Analysis\n\n")

        total_edges = module_matrix.values.sum()
        f.write(f"- Total cross-module calls: {int(total_edges)}\n")
        f.write(f"- Number of interacting modules: {len(module_matrix)}\n\n")

        f.write(f"![Module Coupling]({os.path.basename(module_img)})\n\n")

        f.write("## 3. Top Critical Modules (Betweenness Centrality)\n\n")

        f.write("| Rank | Module | Centrality |\n")
        f.write("|------|--------|------------|\n")

        for i, (mod, score) in enumerate(centrality_ranking[:10], 1):
            f.write(f"| {i} | {mod} | {score:.4f} |\n")

        f.write("\n")

        f.write("## 4. Interpretation\n\n")

        if centrality_ranking and centrality_ranking[0][1] > 0.2:
            f.write("- Highly centralized architecture detected.\n")
            f.write("- Consider reviewing high-centrality modules.\n")
        else:
            f.write("- No extreme centralization detected.\n")
            f.write("- Architecture appears relatively modular.\n")

    print(f"[✓] Generated {report_path}")


# ==========================================
# MAIN
# ==========================================

def main():

    print("\n=== GENERATE ARCHITECTURE REPORT ===\n")

    callgraph = load_json(CALLGRAPH_PATH)
    functions_index = load_json(FUNCTIONS_INDEX_PATH)
    tasks = load_json(TASKS_PATH)

    task_matrix, task_img = generate_task_heatmap(callgraph, tasks)
    module_matrix, module_img = generate_module_heatmap(callgraph, functions_index)
    centrality = compute_module_centrality(callgraph, functions_index)

    generate_report(task_matrix, module_matrix, centrality,
                    task_img, module_img)

    print("\n🎯 Done.\n")


if __name__ == "__main__":
    main()