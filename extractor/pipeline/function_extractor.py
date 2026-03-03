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


class FunctionExtractor(PipelineStep):
    name = "02_extract_all_functions"

    # ============================================================
    # IO DEFINITION
    # ============================================================

    def io(self, context):

        # Loose mode does NOT depend on compile_commands
        if self.config.get("toolchain") == "loose_cpp":
            return StepIO(
                inputs=[],
                outputs=[self.config["functions_index"]],
            )

        # Normal compile_commands mode
        return StepIO(
            inputs=[self.config["compile_commands"]],
            outputs=[self.config["functions_index"]],
        )

    # ============================================================
    # MAIN RUN
    # ============================================================

    def run(self, context):

        # 🔥 LOOSE MODE
        if self.config.get("toolchain") == "loose_cpp":
            return self._run_loose_cpp(context)

        # 🔵 NORMAL MODE (compile_commands)
        compile_commands = load_json(self.config["compile_commands"])
        out_path = self.config["functions_index"]

        index = Index.create()
        functions = {}

        def visit(node, project_root):
            if node.kind == CursorKind.FUNCTION_DECL:
                if not node.is_definition():
                    return
                if node.location.file is None:
                    return

                file_path = os.path.normpath(node.location.file.name)

                if not file_path.startswith(project_root):
                    return

                name = node.spelling

                functions[name] = {
                    "file": file_path,
                    "line": node.location.line,
                    "return": node.result_type.spelling,
                    "params": [
                        {"name": p.spelling, "type": p.type.spelling}
                        for p in node.get_arguments()
                    ],
                }

            for c in node.get_children():
                visit(c, project_root)

        import shlex

        for entry in compile_commands:

            src = entry["file"]
            workdir = os.path.normpath(entry["directory"])

            if "arguments" in entry:
                args = entry["arguments"]
            else:
                args = shlex.split(entry["command"])

            # Rimuovi compilatore
            if args and args[0].endswith(("gcc", "g++", "clang", "arm-none-eabi-gcc", "armcc")):
                args = args[1:]

            # Rimuovi il file sorgente dagli argomenti
            args = [a for a in args if os.path.normpath(a) != os.path.normpath(src)]

            prev_cwd = os.getcwd()
            try:
                os.chdir(workdir)

                tu = index.parse(
                    src,
                    args=args,
                    options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD,
                )

            except Exception as e:
                self.log(f"[EXCEPTION] {src}: {e}")
                continue

            finally:
                os.chdir(prev_cwd)

            if tu is None:
                self.log(f"[NULL TU] {src}")
                continue

            for d in tu.diagnostics:
                self.log(f"[CLANG] {src}: {d}")

            visit(tu.cursor, workdir)

        save_json(out_path, functions)
        context["functions_index"] = out_path
        self.log(f"Extracted {len(functions)} functions")

    # ============================================================
    # 🔥 LOOSE CPP MODE
    # ============================================================

    def _run_loose_cpp(self, context):

        project_root = os.path.normpath(self.config["project_root"])
        source_dir = os.path.normpath(
            os.path.join(project_root, self.config["source_dir"])
        )

        out_path = self.config["functions_index"]

        if not os.path.exists(source_dir):
            raise FileNotFoundError(f"Source directory not found: {source_dir}")

        index = Index.create()
        functions = {}

        def visit(node):
            if node.kind == CursorKind.FUNCTION_DECL:
                if not node.is_definition():
                    return
                if node.location.file is None:
                    return

                file_path = os.path.normpath(node.location.file.name)

                if not file_path.startswith(project_root):
                    return

                name = node.spelling

                functions[name] = {
                    "file": file_path,
                    "line": node.location.line,
                    "return": node.result_type.spelling,
                    "params": [
                        {"name": p.spelling, "type": p.type.spelling}
                        for p in node.get_arguments()
                    ],
                }

            for c in node.get_children():
                visit(c)

        for root, _, files in os.walk(source_dir):
            for f in files:

                if not f.endswith((".cpp", ".cc", ".c")):
                    continue

                # Skip Qt generated files
                if f.startswith(("moc_", "qrc_", "ui_")):
                    continue

                file_path = os.path.join(root, f)
                self.log(f"[loose_cpp] Parsing {file_path}")

                try:
                    include_args = [
                        "-std=c++17",
                        "-ferror-limit=0",          # non fermarti ai primi errori
                        "-Wno-everything",          # riduci rumore
                        "-D__clang_analyzer__",     # modalità analisi
                    ]

                    # Neutralizza macro Qt (fondamentale)
                    qt_macro_neutralizers = [
                        "-DQ_OBJECT=",
                        "-Dsignals=public",
                        "-Dslots=",
                        "-Demit=",
                        "-DQ_INVOKABLE=",
                        "-DQ_ENUM(...)=",
                        "-DQ_PROPERTY(...)=",
                        "-DQ_GADGET=",
                    ]

                    include_args.extend(qt_macro_neutralizers)

                    # Include project root
                    include_args.append("-I" + project_root)

                    # Include stub dir (se presente)
                    stub_dir = self.config.get("loose_stub_dir")
                    if stub_dir:
                        include_args.append("-I" + stub_dir)

                    # Include tutte le sottocartelle sotto source
                    for root_dir, _, _ in os.walk(source_dir):
                        include_args.append("-I" + root_dir)

                    # Forza include di uno stub globale se esiste
                    if stub_dir:
                        global_stub = os.path.join(stub_dir, "qt_global_stub.h")
                        if os.path.exists(global_stub):
                            include_args.extend(["-include", global_stub])

                    tu = index.parse(
                        file_path,
                        args=include_args,
                        options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD,
                    )

                    # 🔎 DEBUG (temporaneo)
                    for d in tu.diagnostics:
                        self.log(f"[CLANG] {d}")

                except Exception as e:
                    self.log(f"[WARN] Failed parsing {file_path}: {e}")
                    continue

                visit(tu.cursor)

        save_json(out_path, functions)
        context["functions_index"] = out_path
        self.log(f"[loose_cpp] Extracted {len(functions)} functions")