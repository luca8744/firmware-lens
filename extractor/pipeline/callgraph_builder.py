import os
from clang.cindex import Config, Index, CursorKind, TranslationUnit
from .base import PipelineStep, load_json, save_json, StepIO

def _setup_libclang(config):
    lib = config.get("libclang") or os.environ.get("LIBCLANG_PATH")
    if lib:
        Config.set_library_file(lib)

class CallGraphBuilder(PipelineStep):
    name = "04_extract_call_graph"

    def io(self, context):
        return StepIO(
            inputs=[self.config["compile_commands"]],
            outputs=[self.config["call_graph"]]
        )

    def run(self, context):
        _setup_libclang(self.config)

        compile_commands = load_json(self.config["compile_commands"])
        out_path = self.config["call_graph"]

        index = Index.create()
        call_graph = {}

        def visit(node, project_root, current_function=None):
            if node.kind == CursorKind.FUNCTION_DECL and node.is_definition():
                if node.location.file is None:
                    return

                file_path = os.path.normpath(node.location.file.name)
                if not file_path.startswith(project_root):
                    return

                current_function = node.spelling
                call_graph.setdefault(current_function, [])

            elif node.kind == CursorKind.CALL_EXPR and current_function:
                callee = node.spelling
                if callee:
                    call_graph[current_function].append(callee)

            for c in node.get_children():
                visit(c, project_root, current_function)

        for entry in compile_commands:
            src = entry["file"]
            project_root = os.path.normpath(entry["directory"])
            args = [a for a in entry["arguments"] if a not in ("clang", src)]

            try:
                tu = index.parse(
                    src,
                    args=args,
                    options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
                )
            except Exception as e:
                self.log(f"[WARN] Failed parsing {src}: {e}")
                continue

            visit(tu.cursor, project_root)

        for fn in call_graph:
            call_graph[fn] = sorted(set(call_graph[fn]))

        save_json(out_path, call_graph)
        context["call_graph"] = out_path
        self.log(f"Call graph generated for {len(call_graph)} functions")
