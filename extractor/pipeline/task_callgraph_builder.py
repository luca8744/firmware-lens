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

from collections import deque
from .base import PipelineStep, load_json, save_json, StepIO

class TaskCallGraphBuilder(PipelineStep):
    name = "06_build_task_call_graph"

    def io(self, context):
        return StepIO(
            inputs=[self.config["tasks"], self.config["call_graph"]],
            outputs=[self.config["task_call_graph"]]
        )

    def run(self, context):
        tasks = load_json(self.config["tasks"])
        call_graph = load_json(self.config["call_graph"])
        out_path = self.config["task_call_graph"]

        task_call_graph = {}

        def compute_reachable(entry):
            visited = set()
            queue = deque([entry])

            while queue:
                fn = queue.popleft()
                if fn in visited:
                    continue
                visited.add(fn)

                for callee in call_graph.get(fn, []):
                    if callee not in visited:
                        queue.append(callee)

            return sorted(visited)

        for task_name, info in tasks.items():
            entry = info["entry_function"]
            reachable = compute_reachable(entry)
            task_call_graph[task_name] = {
                "entry": entry,
                "reachable_functions": reachable
            }

        save_json(out_path, task_call_graph)
        context["task_call_graph"] = out_path
        self.log(f"Generated task call graph for {len(task_call_graph)} tasks")

