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
import json
from dataclasses import dataclass
from typing import Dict, List, Optional

def ensure_dir(path: str) -> None:
    if path:
        os.makedirs(path, exist_ok=True)

def load_json(path: str):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: str, data) -> None:
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def write_text(path: str, text: str) -> None:
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

def newest_mtime(paths: List[str]) -> float:
    mt = 0.0
    for p in paths:
        if p and os.path.exists(p):
            mt = max(mt, os.path.getmtime(p))
    return mt

def oldest_mtime(paths: List[str]) -> float:
    mts = []
    for p in paths:
        if p and os.path.exists(p):
            mts.append(os.path.getmtime(p))
    return min(mts) if mts else 0.0

def outputs_up_to_date(inputs: List[str], outputs: List[str]) -> bool:
    # if any output missing => not up to date
    for o in outputs:
        if not o or not os.path.exists(o):
            return False
    # outputs must be newer than all inputs
    in_newest = newest_mtime(inputs)
    out_oldest = oldest_mtime(outputs)
    return out_oldest >= in_newest

class PipelineContext(dict):
    """Shared context across steps."""
    pass

@dataclass
class StepIO:
    inputs: List[str]
    outputs: List[str]

class PipelineStep:
    name: str = "base"

    def __init__(self, config: Dict, force: bool = False):
        self.config = config
        self.force = force

    def io(self, context: PipelineContext) -> StepIO:
        return StepIO(inputs=[], outputs=[])

    def run(self, context: PipelineContext) -> None:
        raise NotImplementedError

    def should_skip(self, context: PipelineContext) -> bool:
        if self.force:
            return False
        sio = self.io(context)
        return outputs_up_to_date(sio.inputs, sio.outputs)

    def log(self, msg: str) -> None:
        print(f"[{self.name}] {msg}")
