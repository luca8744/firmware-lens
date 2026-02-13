import json
from collections import defaultdict

# --------------------------------
# Load inputs
# --------------------------------

with open("analysis/task_call_graph.json") as f:
    task_graph = json.load(f)

with open("analysis/function_categories.json") as f:
    categories = json.load(f)

# --------------------------------
# Helpers
# --------------------------------

def group_by_category(functions):
    grouped = defaultdict(list)
    for fn in functions:
        cat = categories.get(fn, "unknown")
        grouped[cat].append(fn)
    return grouped

# --------------------------------
# Generate markdown
# --------------------------------

lines = []
lines.append("# Firmware Architecture Overview\n")
lines.append("This document provides a **task-centric architectural view** of the firmware.\n")
lines.append("Each section describes a runtime task, its responsibilities, and the modules it interacts with.\n")

for task, info in task_graph.items():
    entry = info["entry"]
    functions = info["reachable_functions"]

    grouped = group_by_category(functions)

    lines.append(f"\n---\n")
    lines.append(f"## Task `{task}`\n")
    lines.append(f"**Entry function:** `{entry}`\n")

    for category in ["application", "driver", "rtos", "utility", "unknown"]:
        items = sorted(grouped.get(category, []))
        if not items:
            continue

        lines.append(f"\n### {category.capitalize()} functions\n")
        for fn in items:
            lines.append(f"- `{fn}`")

    # Summary paragraph
    app_count = len(grouped.get("application", []))
    drv_count = len(grouped.get("driver", []))
    rtos_count = len(grouped.get("rtos", []))

    lines.append("\n**Summary:**\n")
    lines.append(
        f"This task executes **{app_count} application-level functions**, "
        f"interacts with **{drv_count} driver-level functions**, "
        f"and relies on **{rtos_count} RTOS primitives** for scheduling and synchronization.\n"
    )

# --------------------------------
# Write output
# --------------------------------

with open("ARCHITECTURE_OVERVIEW.md", "w") as f:
    f.write("\n".join(lines))

print("Generated ARCHITECTURE_OVERVIEW.md")
