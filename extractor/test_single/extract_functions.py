from clang.cindex import Config
Config.set_library_file(r"C:\Program Files\LLVM\bin\libclang.dll")

from clang.cindex import Index, CursorKind, TranslationUnit
import json
import os

# carica compile_commands.json
cc = json.load(open("compile_commands.json"))

entry = cc[0]

src = entry["file"]
workdir = entry["directory"]

# 🔑 args corretti per libclang:
# - togli "clang"
# - togli il file sorgente
args = [
    a for a in entry["arguments"]
    if a != "clang" and a != src
]

index = Index.create()

tu = index.parse(
    src,
    args=args,
    options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
)

functions = []

def visit(node):
    if node.kind == CursorKind.FUNCTION_DECL:
        # solo funzioni del progetto (non stub)
        if node.location.file and node.location.file.name.startswith(workdir):
            functions.append({
                "name": node.spelling,
                "return": node.result_type.spelling,
                "params": [
                    {"name": p.spelling, "type": p.type.spelling}
                    for p in node.get_arguments()
                ],
                "file": node.location.file.name,
                "line": node.location.line
            })
    for c in node.get_children():
        visit(c)

visit(tu.cursor)

print(json.dumps(functions, indent=2))
