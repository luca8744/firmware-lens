from collections import defaultdict
from .base import PipelineStep, load_json, write_text, StepIO

class ArchitectureViewBuilder(PipelineStep):
    name = "07_generate_architecture_view"

    def io(self, context):
        return StepIO(
            inputs=[self.config["task_call_graph"], self.config["function_categories"]],
            outputs=[self.config["architecture_overview_md"]]
        )

    def run(self, context):
        task_graph = load_json(self.config["task_call_graph"])
        categories = load_json(self.config["function_categories"])
        out_path = self.config["architecture_overview_md"]

        def group_by_category(functions):
            grouped = defaultdict(list)
            for fn in functions:
                cat = categories.get(fn, "unknown")
                grouped[cat].append(fn)
            return grouped

        lines = []
        lines.append("# Firmware Architecture Overview\n")
        lines.append("This document provides a **task-centric architectural view** of the firmware.\n")
        lines.append("Each section describes a runtime task, its responsibilities, and the modules it interacts with.\n")

        for task, info in task_graph.items():
            entry = info["entry"]
            functions = info["reachable_functions"]
            grouped = group_by_category(functions)

            lines.append("\n---\n")
            lines.append(f"## Task `{task}`\n")
            lines.append(f"**Entry function:** `{entry}`\n")

            for category in ["application", "driver", "rtos", "utility", "unknown"]:
                items = sorted(grouped.get(category, []))
                if not items:
                    continue

                lines.append(f"\n### {category.capitalize()} functions\n")
                for fn in items:
                    lines.append(f"- `{fn}`")

            app_count = len(grouped.get("application", []))
            drv_count = len(grouped.get("driver", []))
            rtos_count = len(grouped.get("rtos", []))

            lines.append("\n**Summary:**\n")
            lines.append(
                f"This task executes **{app_count} application-level functions**, "
                f"interacts with **{drv_count} driver-level functions**, "
                f"and relies on **{rtos_count} RTOS primitives** for scheduling and synchronization.\n"
            )

        write_text(out_path, "\n".join(lines))
        context["architecture_overview_md"] = out_path
        self.log("Generated ARCHITECTURE_OVERVIEW.md")
