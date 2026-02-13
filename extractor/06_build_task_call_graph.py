import json
from collections import deque

# --------------------------------
# Load inputs
# --------------------------------

with open("tasks.json") as f:
    tasks = json.load(f)

with open("call_graph.json") as f:
    call_graph = json.load(f)

# --------------------------------
# Build task call graph
# --------------------------------

task_call_graph = {}

def compute_reachable(entry):
    """
    BFS on the call graph starting from entry function
    """
    visited = set()
    queue = deque([entry])

    while queue:
        fn = queue.popleft()
        if fn in visited:
            continue
        visited.add(fn)

        for callee in call_graph.get(fn, []):
            if callee not in visited:
                queue.append(callee)

    return sorted(visited)

for task_name, info in tasks.items():
    entry = info["entry_function"]

    reachable = compute_reachable(entry)

    task_call_graph[task_name] = {
        "entry": entry,
        "reachable_functions": reachable
    }

# --------------------------------
# Write output
# --------------------------------

with open("task_call_graph.json", "w") as f:
    json.dump(task_call_graph, f, indent=2)

print(f"Generated task call graph for {len(task_call_graph)} tasks")
