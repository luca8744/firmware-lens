import json
from datetime import datetime

# --------------------------------
# Load inputs
# --------------------------------

with open("tasks.json") as f:
    tasks = json.load(f)

with open("task_call_graph.json") as f:
    task_call_graph = json.load(f)

with open("functions_index.json") as f:
    functions_index = json.load(f)

with open("function_categories.json") as f:
    function_categories = json.load(f)

with open("call_graph.json") as f:
    call_graph = json.load(f)

# --------------------------------
# Build IR
# --------------------------------

ir = {
    "metadata": {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source": "static analysis (clang + heuristics)",
        "language": "C / C++",
        "target": "embedded firmware",
        "notes": "IR generated automatically; semantics inferred statically"
    },
    "tasks": {},
    "functions": {},
    "call_graph": call_graph
}

# --------------------------------
# Functions section
# --------------------------------

for fn, info in functions_index.items():
    ir["functions"][fn] = {
        "file": info.get("file"),
        "line": info.get("line"),
        "category": function_categories.get(fn, "unknown")
    }

# --------------------------------
# Tasks section
# --------------------------------

for task_name, task_info in tasks.items():
    entry = task_info["entry_function"]
    reachable = task_call_graph.get(task_name, {}).get("reachable_functions", [])

    ir["tasks"][task_name] = {
        "entry_function": entry,
        "defined_in": {
            "file": task_info.get("file"),
            "line": task_info.get("line")
        },
        "reachable_functions": reachable,
        "function_categories": {
            "application": [],
            "driver": [],
            "rtos": [],
            "utility": [],
            "unknown": []
        }
    }

    for fn in reachable:
        cat = function_categories.get(fn, "unknown")
        ir["tasks"][task_name]["function_categories"][cat].append(fn)

# --------------------------------
# Write output
# --------------------------------

with open("firmware_ir.json", "w") as f:
    json.dump(ir, f, indent=2)

print("Generated firmware_ir.json")
