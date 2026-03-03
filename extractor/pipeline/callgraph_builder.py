# Firmware Lens - A tool for firmware architecture analysis and documentation.
# Copyright (C) 2026 Luca Miliciani
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
from clang.cindex import Index, CursorKind, TranslationUnit
from .base import PipelineStep, load_json, save_json, StepIO


class CallGraphBuilder(PipelineStep):
    name = "04_extract_call_graph"

    # ============================================================
    # IO
    # ============================================================

    def io(self, context):

        if self.config.get("toolchain") == "loose_cpp":
            return StepIO(
                inputs=[self.config["functions_index"]],
                outputs=[self.config["call_graph"]],
            )

        return StepIO(
            inputs=[self.config["compile_commands"]],
            outputs=[self.config["call_graph"]],
        )

    # ============================================================
    # RUN
    # ============================================================

    def run(self, context):

        if self.config.get("toolchain") == "loose_cpp":
            return self._run_loose_cpp(context)

        # ----------------------------
        # NORMAL compile_commands mode
        # ----------------------------

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

        import shlex

        for entry in compile_commands:

            src = entry["file"]
            project_root = os.path.normpath(entry["directory"])

            # ---- Recupero args corretto ----
            if "arguments" in entry:
                args = entry["arguments"]
            else:
                args = shlex.split(entry["command"])

            # ---- Rimuovi compilatore ----
            if args and args[0].endswith(("gcc", "g++", "clang", "arm-none-eabi-gcc", "armcc")):
                args = args[1:]

            # ---- Rimuovi il file sorgente dagli args ----
            args = [a for a in args if os.path.normpath(a) != os.path.normpath(src)]

            prev_cwd = os.getcwd()
            try:
                os.chdir(project_root)

                tu = index.parse(
                    src,
                    args=args,
                    options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD,
                )

            except Exception as e:
                self.log(f"[WARN] Failed parsing {src}: {e}")
                continue

            finally:
                os.chdir(prev_cwd)

            if tu is None:
                self.log(f"[NULL TU] {src}")
                continue

            for d in tu.diagnostics:
                self.log(f"[CLANG] {src}: {d}")

            visit(tu.cursor, project_root)

        for fn in call_graph:
            call_graph[fn] = sorted(set(call_graph[fn]))

        save_json(out_path, call_graph)
        context["call_graph"] = out_path
        self.log(f"Call graph generated for {len(call_graph)} functions")

    # ============================================================
    # 🔥 LOOSE MODE
    # ============================================================

    def _run_loose_cpp(self, context):

        project_root = os.path.normpath(self.config["project_root"])
        source_dir = os.path.normpath(
            os.path.join(project_root, self.config["source_dir"])
        )

        out_path = self.config["call_graph"]

        index = Index.create()
        call_graph = {}

        def visit(node, current_function=None):

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
                visit(c, current_function)

        for root, _, files in os.walk(source_dir):
            for f in files:

                if not f.endswith((".cpp", ".cc", ".c")):
                    continue

                if f.startswith(("moc_", "qrc_", "ui_")):
                    continue

                file_path = os.path.join(root, f)
                self.log(f"[loose_cpp] Parsing {file_path}")

                try:
                    tu = index.parse(
                        file_path,
                        args=[
                            "-std=c++17",
                            "-I" + project_root,
                        ],
                        options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD,
                    )
                except Exception as e:
                    self.log(f"[WARN] Failed parsing {file_path}: {e}")
                    continue

                visit(tu.cursor)

        for fn in call_graph:
            call_graph[fn] = sorted(set(call_graph[fn]))

        save_json(out_path, call_graph)
        context["call_graph"] = out_path
        self.log(f"[loose_cpp] Call graph generated for {len(call_graph)} functions")