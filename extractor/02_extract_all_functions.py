from clang.cindex import Config
Config.set_library_file(r"C:\Program Files\LLVM\bin\libclang.dll")

from clang.cindex import Index, CursorKind, TranslationUnit
import json
import os
import sys

# -------------------------
# Load compile_commands.json
# -------------------------

with open("compile_commands.json") as f:
    compile_commands = json.load(f)

index = Index.create()

functions = {}

# -------------------------
# Helper: visit AST
# -------------------------

def visit(node, project_root):
    if node.kind == CursorKind.FUNCTION_DECL:
        # consider only real definitions
        if not node.is_definition():
            return

        if node.location.file is None:
            return

        file_path = os.path.normpath(node.location.file.name)

        # keep only project files (exclude stubs/system)
        if not file_path.startswith(project_root):
            return

        name = node.spelling

        functions[name] = {
            "file": file_path,
            "line": node.location.line,
            "return": node.result_type.spelling,
            "params": [
                {
                    "name": p.spelling,
                    "type": p.type.spelling
                }
                for p in node.get_arguments()
            ]
        }

    for c in node.get_children():
        visit(c, project_root)

# -------------------------
# Parse each translation unit
# -------------------------

for entry in compile_commands:
    src = entry["file"]
    workdir = os.path.normpath(entry["directory"])

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

    visit(tu.cursor, workdir)

# -------------------------
# Write output
# -------------------------

with open("functions_index.json", "w") as f:
    json.dump(functions, f, indent=2)

print(f"Extracted {len(functions)} functions")
