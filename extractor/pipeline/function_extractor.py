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
from clang.cindex import Config, Index, CursorKind, TranslationUnit
from .base import PipelineStep, load_json, save_json, StepIO

class FunctionExtractor(PipelineStep):
    name = "02_extract_all_functions"

    def io(self, context):
        return StepIO(
            inputs=[self.config["compile_commands"]],
            outputs=[self.config["functions_index"]]
        )

    def run(self, context):

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
                    "params": [{"name": p.spelling, "type": p.type.spelling} for p in node.get_arguments()],
                }

            for c in node.get_children():
                visit(c, project_root)

        for entry in compile_commands:
            src = entry["file"]
            workdir = os.path.normpath(entry["directory"])
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

            visit(tu.cursor, workdir)

        save_json(out_path, functions)
        context["functions_index"] = out_path
        self.log(f"Extracted {len(functions)} functions")

