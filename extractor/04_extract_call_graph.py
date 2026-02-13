from clang.cindex import Config
Config.set_library_file(r"C:\Program Files\LLVM\bin\libclang.dll")

from clang.cindex import Index, CursorKind, TranslationUnit
import json
import os

# --------------------------------
# Load compile_commands.json
# --------------------------------

with open("compile_commands.json") as f:
    compile_commands = json.load(f)

index = Index.create()

call_graph = {}

# --------------------------------
# AST traversal
# --------------------------------

def visit(node, project_root, current_function=None):
    # enter function definition
    if node.kind == CursorKind.FUNCTION_DECL and node.is_definition():
        if node.location.file is None:
            return

        file_path = os.path.normpath(node.location.file.name)

        # keep only project files
        if not file_path.startswith(project_root):
            return

        current_function = node.spelling
        call_graph.setdefault(current_function, [])

    # function call
    elif node.kind == CursorKind.CALL_EXPR and current_function:
        callee = node.spelling
        if callee:
            call_graph[current_function].append(callee)

    for c in node.get_children():
        visit(c, project_root, current_function)

# --------------------------------
# Parse all translation units
# --------------------------------

for entry in compile_commands:
    src = entry["file"]
    project_root = os.path.normpath(entry["directory"])

    args = [
        a for a in entry["arguments"]
        if a != "clang" and a != src
    ]

    try:
        tu = index.parse(
            src,
            args=args,
            options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
        )
    except Exception as e:
        print(f"[WARN] Failed parsing {src}: {e}")
        continue

    visit(tu.cursor, project_root)

# --------------------------------
# Normalize output (remove duplicates)
# --------------------------------

for fn in call_graph:
    call_graph[fn] = sorted(set(call_graph[fn]))

# --------------------------------
# Write output
# --------------------------------

with open("call_graph.json", "w") as f:
    json.dump(call_graph, f, indent=2)

print(f"Call graph generated for {len(call_graph)} functions")
