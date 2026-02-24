import os
import json
import networkx as nx
import matplotlib.pyplot as plt


ANALYSIS_DIR = "analysis"
CALLGRAPH_PATH = os.path.join(ANALYSIS_DIR, "call_graph.json")
FUNCTIONS_INDEX_PATH = os.path.join(ANALYSIS_DIR, "functions_index.json")
TASKS_PATH = os.path.join(ANALYSIS_DIR, "tasks.json")

OUT_DIR = os.path.join(ANALYSIS_DIR, "architecture")
os.makedirs(OUT_DIR, exist_ok=True)


# ==========================================
# UTIL
# ==========================================

def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def is_application_file(path):
    if not path:
        return False
    path = path.lower()
    return (
        "application" in path
        and "drivers" not in path
        and "cmsis" not in path
        and "middleware" not in path
    )


# ==========================================
# 1️⃣ CALLGRAPH (FILTERED)
# ==========================================

def generate_callgraph(callgraph, functions_index):
    G = nx.DiGraph()

    for caller, callees in callgraph.items():
        caller_file = functions_index.get(caller, {}).get("file")
        if not is_application_file(caller_file):
            continue

        for callee in callees:
            callee_file = functions_index.get(callee, {}).get("file")
            if not is_application_file(callee_file):
                continue

            G.add_edge(caller, callee)

    if G.number_of_nodes() == 0:
        print("[!] No application-level callgraph found")
        return

    plt.figure(figsize=(18, 18))
    pos = nx.spring_layout(G, k=0.5)
    nx.draw(
        G,
        pos,
        node_size=300,
        arrows=True,
        with_labels=True,
        font_size=6
    )

    output = os.path.join(OUT_DIR, "callgraph_filtered.png")
    plt.savefig(output, dpi=300)
    plt.close()

    print(f"[✓] Generated {output}")


# ==========================================
# 2️⃣ TASK GRAPH
# ==========================================

def generate_task_graph(tasks):
    if not tasks:
        print("[i] No tasks.json found")
        return

    G = nx.DiGraph()

    for task_name, data in tasks.items():
        for fn in data.get("functions", []):
            G.add_edge(task_name, fn)

    plt.figure(figsize=(14, 14))
    pos = nx.spring_layout(G, k=0.7)

    colors = []
    for node in G.nodes():
        if node in tasks:
            colors.append("red")
        else:
            colors.append("skyblue")

    nx.draw(
        G,
        pos,
        node_color=colors,
        node_size=800,
        with_labels=True,
        font_size=8
    )

    output = os.path.join(OUT_DIR, "task_graph.png")
    plt.savefig(output, dpi=300)
    plt.close()

    print(f"[✓] Generated {output}")


# ==========================================
# 3️⃣ FILE DEPENDENCY GRAPH
# ==========================================

def generate_file_dependency(callgraph, functions_index):
    G = nx.DiGraph()

    for caller, callees in callgraph.items():
        caller_file = functions_index.get(caller, {}).get("file")
        if not is_application_file(caller_file):
            continue

        caller_file = os.path.basename(caller_file)

        for callee in callees:
            callee_file = functions_index.get(callee, {}).get("file")
            if not is_application_file(callee_file):
                continue

            callee_file = os.path.basename(callee_file)

            if caller_file != callee_file:
                G.add_edge(caller_file, callee_file)

    if G.number_of_nodes() == 0:
        print("[!] No file dependencies found")
        return

    plt.figure(figsize=(16, 16))
    pos = nx.spring_layout(G, k=0.6)

    nx.draw(
        G,
        pos,
        node_size=1500,
        with_labels=True,
        font_size=8,
        arrows=True
    )

    output = os.path.join(OUT_DIR, "file_dependency.png")
    plt.savefig(output, dpi=300)
    plt.close()

    print(f"[✓] Generated {output}")


# ==========================================
# MAIN
# ==========================================

def main():
    print("\n=== GENERATE ARCHITECTURE GRAPHS (Filtered Embedded) ===\n")

    callgraph = load_json(CALLGRAPH_PATH)
    functions_index = load_json(FUNCTIONS_INDEX_PATH)
    tasks = load_json(TASKS_PATH)

    generate_callgraph(callgraph, functions_index)
    generate_task_graph(tasks)
    generate_file_dependency(callgraph, functions_index)

    print("\n🎯 Done.\n")


if __name__ == "__main__":
    main()