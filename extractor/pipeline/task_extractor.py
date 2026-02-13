import os
from clang.cindex import Index, CursorKind, TranslationUnit
from .base import PipelineStep, load_json, save_json, StepIO


class TaskExtractor(PipelineStep):
    name = "05_extract_task"

    def io(self, context):
        return StepIO(
            inputs=[self.config["compile_commands"]],
            outputs=[self.config["tasks"]]
        )

    def run(self, context):

        compile_commands = load_json(self.config["compile_commands"])
        out_path = self.config["tasks"]

        index = Index.create()
        tasks = {}

        def is_inside_project(project_root, file_path):
            """
            Robust project root check (Windows-safe)
            """
            project_root = os.path.normpath(project_root)
            file_path = os.path.normpath(file_path)

            try:
                return os.path.commonpath([project_root, file_path]) == project_root
            except ValueError:
                return False

        def visit(node, project_root):

            # ---- CMSIS-RTOS v1: osThreadDef macro ----
            if node.kind == CursorKind.MACRO_INSTANTIATION and node.spelling == "osThreadDef":

                location = node.location
                file_path = location.file.name if location.file else None
                if not file_path:
                    return

                if not is_inside_project(project_root, file_path):
                    return

                tokens = list(node.get_tokens())

                # tokens example:
                # osThreadDef ( ADConvTask , osPriorityNormal , 1 , 512 )
                entry = None
                for i, t in enumerate(tokens):
                    if t.spelling == "(" and i + 1 < len(tokens):
                        entry = tokens[i + 1].spelling
                        break

                if entry:
                    tasks[entry] = {
                        "entry_function": entry,
                        "file": os.path.normpath(file_path),
                        "line": location.line
                    }

            # continua traversal
            for c in node.get_children():
                visit(c, project_root)

        # ---- Parse tutte le translation unit ----
        for entry in compile_commands:
            src = entry["file"]
            project_root = os.path.normpath(entry["directory"])

            args = [
                a for a in entry["arguments"]
                if a not in ("clang", src)
            ]

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

        save_json(out_path, tasks)
        context["tasks"] = out_path
        self.log(f"Extracted {len(tasks)} RTOS tasks")
