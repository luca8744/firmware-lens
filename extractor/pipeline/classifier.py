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

from .base import PipelineStep, load_json, save_json, StepIO

class FunctionClassifier(PipelineStep):
    name = "03_classify_functions"

    def io(self, context):
        return StepIO(
            inputs=[self.config["functions_index"]],
            outputs=[self.config["function_categories"]]
        )

    def run(self, context):
        functions = load_json(self.config["functions_index"])
        out_path = self.config["function_categories"]

        def classify_function(name, file_path):
            p = (file_path or "").lower()

            if ("cmsis_os" in p or "rtos" in p or name.startswith("os")):
                return "rtos"

            if ("driver" in p or "hwlib" in p or "baselib" in p or name.startswith("Driver_") or name.startswith("BSP_")):
                return "driver"

            if ("utils" in p or "common" in p or "helper" in p or name.endswith("_Init")):
                return "utility"

            return "application"

        categories = {}
        for fn, info in functions.items():
            categories[fn] = classify_function(fn, info.get("file"))

        save_json(out_path, categories)
        context["function_categories"] = out_path
        self.log(f"Classified {len(categories)} functions")

