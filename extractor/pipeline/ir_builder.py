from datetime import datetime
from .base import PipelineStep, load_json, save_json, StepIO

class IRBuilder(PipelineStep):
    name = "01_build_firmware_ir"

    def io(self, context):
        return StepIO(
            inputs=[
                self.config["tasks"],
                self.config["task_call_graph"],
                self.config["functions_index"],
                self.config["function_categories"],
                self.config["call_graph"],
            ],
            outputs=[self.config["firmware_ir"]]
        )

    def run(self, context):
        tasks = load_json(self.config["tasks"])
        task_call_graph = load_json(self.config["task_call_graph"])
        functions_index = load_json(self.config["functions_index"])
        function_categories = load_json(self.config["function_categories"])
        call_graph = load_json(self.config["call_graph"])

        ir = {
            "metadata": {
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "source": "static analysis (clang + heuristics)",
                "language": "C / C++",
                "target": "embedded firmware",
                "notes": "IR generated automatically; semantics inferred statically"
            },
            "tasks": {},
            "functions": {},
            "call_graph": call_graph
        }

        for fn, info in functions_index.items():
            ir["functions"][fn] = {
                "file": info.get("file"),
                "line": info.get("line"),
                "category": function_categories.get(fn, "unknown")
            }

        for task_name, task_info in tasks.items():
            entry = task_info["entry_function"]
            reachable = task_call_graph.get(task_name, {}).get("reachable_functions", [])

            ir["tasks"][task_name] = {
                "entry_function": entry,
                "defined_in": {"file": task_info.get("file"), "line": task_info.get("line")},
                "reachable_functions": reachable,
                "function_categories": {
                    "application": [],
                    "driver": [],
                    "rtos": [],
                    "utility": [],
                    "unknown": []
                }
            }

            for fn in reachable:
                cat = function_categories.get(fn, "unknown")
                ir["tasks"][task_name]["function_categories"][cat].append(fn)

        save_json(self.config["firmware_ir"], ir)
        context["firmware_ir"] = self.config["firmware_ir"]
        self.log("Generated firmware_ir.json")
