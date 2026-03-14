# Firmware Lens - A tool for firmware architecture analysis and documentation.
# Copyright (C) 2026 Luca Miliciani
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import json
import argparse
from collections import defaultdict

# ==========================================
# CONFIG SETUP
# ==========================================

parser = argparse.ArgumentParser()
parser.add_argument("--config", required=True, help="Path to project config JSON")
args = parser.parse_args()

with open(args.config, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

def get_path(key, default):
    return CONFIG.get(key, default)

CALLGRAPH_PATH = get_path("call_graph", "analysis/call_graph.json")
FUNCTIONS_INDEX_PATH = get_path("functions_index", "analysis/functions_index.json")
TASKS_PATH = get_path("tasks", "analysis/tasks.json")

OUT_DIR = get_path("architecture_dir", "analysis/architecture")
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
# 1ï¸âƒ£ LAYERED ARCHITECTURE
# ==========================================

def generate_layered_diagram(callgraph, functions_index, tasks):

    lines = []
    lines.append("graph TD\n")

    # Tasks â†’ Application
    for task_name, data in tasks.items():
        for fn in data.get("functions", []):
            file_path = functions_index.get(fn, {}).get("file")
            if not file_path:
                continue

            module = os.path.basename(file_path)
            lines.append(f"{task_name} --> {module}\n")

    # Application â†’ lower layers
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

    print(f"[âœ“] Generated {output_path}")


# ==========================================
# 2ï¸âƒ£ APPLICATION MODULE DEPENDENCIES
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

    print(f"[âœ“] Generated {output_path}")


# ==========================================
# 3ï¸âƒ£ APPLICATION FILE DEPENDENCIES
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

    print(f"[âœ“] Generated {output_path}")


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

    print("\nðŸŽ¯ Done.\n")


if __name__ == "__main__":
    main()
