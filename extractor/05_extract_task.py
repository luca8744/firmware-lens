from clang.cindex import Config
Config.set_library_file(r"C:\Program Files\LLVM\bin\libclang.dll")

from clang.cindex import Index, CursorKind, TranslationUnit
import json
import os

with open("compile_commands.json") as f:
    compile_commands = json.load(f)

index = Index.create()
tasks = {}

def visit(node, project_root):
    # ---- CMSIS-RTOS v1: osThreadDef macro ----
    if node.kind == CursorKind.MACRO_INSTANTIATION and node.spelling == "osThreadDef":
        location = node.location
        file_path = location.file.name if location.file else None
        if not file_path:
            return

        file_path = os.path.normpath(file_path)
        if not file_path.startswith(project_root):
            return

        # Extract macro arguments from tokens
        tokens = list(node.get_tokens())

        # tokens example: osThreadDef ( ADConvTask , osPriorityNormal , 1 , 512 )
        # entry function is the first identifier after '('
        entry = None
        for i, t in enumerate(tokens):
            if t.spelling == "(" and i + 1 < len(tokens):
                entry = tokens[i + 1].spelling
                break

        if entry:
            tasks[entry] = {
                "entry_function": entry,
                "file": file_path,
                "line": location.line
            }

    for c in node.get_children():
        visit(c, project_root)

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

with open("tasks.json", "w") as f:
    json.dump(tasks, f, indent=2)

print(f"Extracted {len(tasks)} RTOS tasks")
