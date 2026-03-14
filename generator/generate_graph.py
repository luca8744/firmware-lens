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
from graphviz import Digraph

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

OUTPUT_FILE = os.path.join(OUT_DIR, "architecture_final")


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


def module_from_file(path):
    return os.path.basename(path)


# ==========================================
# BUILD ARCHITECTURE GRAPH
# ==========================================

def build_architecture_graph(callgraph, functions_index, tasks):

    dot = Digraph("FirmwareArchitecture")
    dot.attr(rankdir="TB")  # top -> bottom
    dot.attr("node", shape="box", style="filled", fontname="Helvetica")

    # --------------------------------------
    # 1ï¸âƒ£ Collect module dependencies
    # --------------------------------------

    edge_weights = defaultdict(int)
    modules = set()

    for caller, callees in callgraph.items():
        caller_file = functions_index.get(caller, {}).get("file")
        if not is_application_file(caller_file):
            continue

        caller_mod = module_from_file(caller_file)
        modules.add(caller_mod)

        for callee in callees:
            callee_file = functions_index.get(callee, {}).get("file")
            if not is_application_file(callee_file):
                continue

            callee_mod = module_from_file(callee_file)
            modules.add(callee_mod)

            if caller_mod != callee_mod:
                edge_weights[(caller_mod, callee_mod)] += 1

    # --------------------------------------
    # 2ï¸âƒ£ TASK LAYER
    # --------------------------------------

    with dot.subgraph(name="cluster_tasks") as c:
        c.attr(label="RTOS Tasks", color="red")
        for task_name in tasks.keys():
            c.node(task_name, fillcolor="#ffcccc")

    # --------------------------------------
    # 3ï¸âƒ£ APPLICATION MODULE LAYER
    # --------------------------------------

    with dot.subgraph(name="cluster_app") as c:
        c.attr(label="Application Modules", color="blue")
        for mod in sorted(modules):
            c.node(mod, fillcolor="#cce5ff")

    # --------------------------------------
    # 4ï¸âƒ£ TASK â†’ MODULE edges
    # --------------------------------------

    for task_name, data in tasks.items():
        for fn in data.get("functions", []):
            file_path = functions_index.get(fn, {}).get("file")
            if not is_application_file(file_path):
                continue

            module = module_from_file(file_path)
            dot.edge(task_name, module, color="red")

    # --------------------------------------
    # 5ï¸âƒ£ MODULE â†’ MODULE dependencies
    # --------------------------------------

    for (src, dst), weight in edge_weights.items():

        if weight < 3:  # filtro rumore
            continue

        penwidth = str(min(1 + weight * 0.3, 5))
        dot.edge(src, dst, label=str(weight), penwidth=penwidth)

    # --------------------------------------
    # RENDER PNG
    # --------------------------------------

    dot.render(OUTPUT_FILE, format="png", cleanup=True)
    print(f"[âœ“] Generated {OUTPUT_FILE}.png")


# ==========================================
# MAIN
# ==========================================

def main():
    print("\n=== GENERATE FINAL FIRMWARE ARCHITECTURE PNG ===\n")

    callgraph = load_json(CALLGRAPH_PATH)
    functions_index = load_json(FUNCTIONS_INDEX_PATH)
    tasks = load_json(TASKS_PATH)

    build_architecture_graph(callgraph, functions_index, tasks)

    print("\nðŸŽ¯ Done.\n")


if __name__ == "__main__":
    main()
