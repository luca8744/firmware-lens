import os
import json
from collections import defaultdict


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


def classify_layer(file_path):
    if not file_path:
        return "unknown"

    p = file_path.lower()

    if "cmsis" in p:
        return "CMSIS"
    if "hal" in p:
        return "HAL"
    if "driver" in p:
        return "Drivers"
    if "middleware" in p:
        return "Middleware"
    if "application" in p:
        return "Application"

    return "Other"


# ==========================================
# 1️⃣ LAYERED ARCHITECTURE
# ==========================================

def generate_layered_diagram(callgraph, functions_index, tasks):

    lines = []
    lines.append("graph TD\n")

    # Tasks → Application
    for task_name, data in tasks.items():
        for fn in data.get("functions", []):
            file_path = functions_index.get(fn, {}).get("file")
            if not file_path:
                continue

            module = os.path.basename(file_path)
            lines.append(f"{task_name} --> {module}\n")

    # Application → lower layers
    for caller, callees in callgraph.items():
        caller_file = functions_index.get(caller, {}).get("file")
        if not caller_file:
            continue

        caller_module = os.path.basename(caller_file)
        caller_layer = classify_layer(caller_file)

        for callee in callees:
            callee_file = functions_index.get(callee, {}).get("file")
            if not callee_file:
                continue

            callee_module = os.path.basename(callee_file)
            callee_layer = classify_layer(callee_file)

            if caller_layer != callee_layer:
                lines.append(f"{caller_module} --> {callee_module}\n")

    output_path = os.path.join(OUT_DIR, "layered_architecture.mmd")
    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"[✓] Generated {output_path}")


# ==========================================
# 2️⃣ APPLICATION MODULE DEPENDENCIES
# ==========================================

def generate_application_module_diagram(callgraph, functions_index):

    lines = []
    lines.append("graph TD\n")

    edges = set()

    for caller, callees in callgraph.items():
        caller_file = functions_index.get(caller, {}).get("file")
        if not caller_file or "application" not in caller_file.lower():
            continue

        caller_module = os.path.basename(caller_file)

        for callee in callees:
            callee_file = functions_index.get(callee, {}).get("file")
            if not callee_file or "application" not in callee_file.lower():
                continue

            callee_module = os.path.basename(callee_file)

            if caller_module != callee_module:
                edges.add((caller_module, callee_module))

    for a, b in edges:
        lines.append(f"{a} --> {b}\n")

    output_path = os.path.join(OUT_DIR, "application_modules.mmd")
    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"[✓] Generated {output_path}")


# ==========================================
# 3️⃣ APPLICATION FILE DEPENDENCIES
# ==========================================

def generate_file_dependency_diagram(callgraph, functions_index):

    lines = []
    lines.append("graph TD\n")

    edges = set()

    for caller, callees in callgraph.items():
        caller_file = functions_index.get(caller, {}).get("file")
        if not caller_file:
            continue

        caller_module = os.path.basename(caller_file)

        for callee in callees:
            callee_file = functions_index.get(callee, {}).get("file")
            if not callee_file:
                continue

            callee_module = os.path.basename(callee_file)

            if caller_module != callee_module:
                edges.add((caller_module, callee_module))

    for a, b in edges:
        lines.append(f"{a} --> {b}\n")

    output_path = os.path.join(OUT_DIR, "file_dependencies.mmd")
    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"[✓] Generated {output_path}")


# ==========================================
# MAIN
# ==========================================

def main():
    print("\n=== GENERATE MERMAID ARCHITECTURE DIAGRAMS ===\n")

    callgraph = load_json(CALLGRAPH_PATH)
    functions_index = load_json(FUNCTIONS_INDEX_PATH)
    tasks = load_json(TASKS_PATH)

    generate_layered_diagram(callgraph, functions_index, tasks)
    generate_application_module_diagram(callgraph, functions_index)
    generate_file_dependency_diagram(callgraph, functions_index)

    print("\n🎯 Done.\n")


if __name__ == "__main__":
    main()