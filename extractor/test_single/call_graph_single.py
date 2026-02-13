from clang.cindex import Config
Config.set_library_file(r"C:\Program Files\LLVM\bin\libclang.dll")

from clang.cindex import Index, CursorKind, TranslationUnit
import json
import os

# --------------------------------
# Load compile_commands.json
# --------------------------------

cc = json.load(open("compile_commands.json"))

# ⚠️ scegliamo UNA translation unit
entry = cc[0]

src = entry["file"]
workdir = os.path.normpath(entry["directory"])

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

call_graph = {}

# --------------------------------
# AST traversal
# --------------------------------

def visit(node, current_function=None):
    # se entriamo in una funzione
    if node.kind == CursorKind.FUNCTION_DECL and node.is_definition():
        current_function = node.spelling
        call_graph.setdefault(current_function, [])

    # se troviamo una chiamata
    elif node.kind == CursorKind.CALL_EXPR and current_function:
        callee = node.spelling
        if callee:
            call_graph[current_function].append(callee)

    for c in node.get_children():
        visit(c, current_function)

visit(tu.cursor)

# rimuove duplicati
for fn in call_graph:
    call_graph[fn] = sorted(set(call_graph[fn]))

print(json.dumps(call_graph, indent=2))
