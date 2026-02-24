import os
import json
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


def build_task_tree(tasks, functions_index, callgraph):

    tree_lines = []

    for task_name, data in tasks.items():
        tree_lines.append(f"{task_name}\n")

        visited = set()

        for fn in data.get("functions", []):
            build_function_branch(
                fn,
                functions_index,
                callgraph,
                tree_lines,
                indent=" ├── ",
                visited=visited
            )

        tree_lines.append("\n")

    return tree_lines


def build_function_branch(fn, functions_index, callgraph, tree_lines, indent, visited):

    if fn in visited:
        return
    visited.add(fn)

    file_path = functions_index.get(fn, {}).get("file")
    module = os.path.basename(file_path) if file_path else "unknown"

    tree_lines.append(f"{indent}{module} :: {fn}\n")

    callees = callgraph.get(fn, [])

    for callee in callees:
        build_function_branch(
            callee,
            functions_index,
            callgraph,
            tree_lines,
            indent=" " * len(indent) + " └── ",
            visited=visited
        )


def main():
    print("\n=== GENERATE TREE VIEW ===\n")

    callgraph = load_json(CALLGRAPH_PATH)
    functions_index = load_json(FUNCTIONS_INDEX_PATH)
    tasks = load_json(TASKS_PATH)

    if not tasks:
        print("[!] No tasks.json found")
        return

    tree = build_task_tree(tasks, functions_index, callgraph)

    output_path = os.path.join(OUT_DIR, "architecture_tree.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(tree)

    print(f"[✓] Generated {output_path}")
    print("\n🎯 Done.\n")


if __name__ == "__main__":
    main()