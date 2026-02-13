import json
import os

# --------------------------------
# Load inputs
# --------------------------------

with open("functions_index.json") as f:
    functions = json.load(f)

# --------------------------------
# Classification rules
# --------------------------------

def classify_function(name, file_path):
    p = file_path.lower()

    # --- RTOS ---
    if (
        "cmsis_os" in p or
        "rtos" in p or
        name.startswith("os")
    ):
        return "rtos"

    # --- Driver ---
    if (
        "driver" in p or
        "hwlib" in p or
        "baselib" in p or
        name.startswith("Driver_") or
        name.startswith("BSP_")
    ):
        return "driver"

    # --- Utility ---
    if (
        "utils" in p or
        "common" in p or
        "helper" in p or
        name.endswith("_Init")
    ):
        return "utility"

    # --- Application (default) ---
    return "application"

# --------------------------------
# Classify all functions
# --------------------------------

categories = {}

for fn, info in functions.items():
    file_path = info["file"]
    categories[fn] = classify_function(fn, file_path)

# --------------------------------
# Write output
# --------------------------------

with open("function_categories.json", "w") as f:
    json.dump(categories, f, indent=2)

print(f"Classified {len(categories)} functions")
