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
