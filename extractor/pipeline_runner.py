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

import argparse
import json
import os

# ---------------------------
# ARGUMENT PARSING EARLY
# ---------------------------

ap = argparse.ArgumentParser()
ap.add_argument("--config", required=True, help="Path to project config JSON")
ap.add_argument("--force", action="store_true", help="Run all steps ignoring up-to-date checks")
ap.add_argument("--only", nargs="+", help="Run only these step names (space separated)")
ap.add_argument("--from", dest="start", help="Run from this step name")
ap.add_argument("--to", dest="end", help="Run until this step name (inclusive)")
args = ap.parse_args()

# ---------------------------
# LOAD CONFIG
# ---------------------------

with open(args.config, "r") as f:
    CONFIG = json.load(f)

project_root = os.getcwd()

def normalize_path(path):
    if not path:
        return path
    if os.path.isabs(path):
        return path
    return os.path.normpath(os.path.join(project_root, path))


for key in CONFIG:
    if isinstance(CONFIG[key], str) and (
        key.endswith("_dir")
        or key.endswith("_md")
        or key.endswith("_json")
        or key.endswith("_commands")
        or key in ["uvprojx", "vcxproj", "stub_dir", "project_root"]
    ):
        CONFIG[key] = normalize_path(CONFIG[key])
    
    print(f"key: {CONFIG[key]}")

# ---------------------------
# SET LIBCLANG EARLY
# ---------------------------

libclang_path = CONFIG.get("libclang") or os.environ.get("LIBCLANG_PATH")

if libclang_path:
    from clang.cindex import Config
    Config.set_library_file(libclang_path)

# ---------------------------
# IMPORT COMMON PIPELINE STEPS
# ---------------------------

from pipeline.function_extractor import FunctionExtractor
from pipeline.classifier import FunctionClassifier
from pipeline.callgraph_builder import CallGraphBuilder
from pipeline.task_extractor import TaskExtractor
from pipeline.task_callgraph_builder import TaskCallGraphBuilder
from pipeline.ir_builder import IRBuilder
from pipeline.function_detail_builder import FunctionDetailBuilder
from pipeline.architecture_view_builder import ArchitectureViewBuilder
from pipeline.base import PipelineContext

# ---------------------------
# TOOLCHAIN FACTORY
# ---------------------------

def build_compile_step(config, force):
    toolchain = config.get("toolchain", "keil").lower()

    if toolchain == "keil":
        from pipeline.keil_to_compile import KeilToCompileCommands
        return KeilToCompileCommands(config, force=force)

    elif toolchain == "visualgdb":
        from pipeline.visualgdb_to_compile import VisualGDBToCompileCommands
        return VisualGDBToCompileCommands(config, force=force)

    elif toolchain == "csharp":
        from pipeline.csharp_to_compile import CSharpToCompileCommands
        return CSharpToCompileCommands(config, force=force)

    elif toolchain == "compile_commands":
        from pipeline.commands_to_compile import CompileCommandsLoader
        return CompileCommandsLoader(config, force=force)

    elif toolchain == "loose_cpp":
        # 🔥 Loose mode does not need a compile step
        return None

    else:
        raise ValueError(f"Unsupported toolchain: {toolchain}")

# ---------------------------
# PIPELINE BUILD
# ---------------------------

def build_steps(config, force: bool):

    compile_step = build_compile_step(config, force)

    steps = []

    if compile_step is not None:
        steps.append(compile_step)

    steps.extend([
        FunctionExtractor(config, force=force),
        FunctionClassifier(config, force=force),
        CallGraphBuilder(config, force=force),
        TaskExtractor(config, force=force),
        TaskCallGraphBuilder(config, force=force),
        IRBuilder(config, force=force),
        FunctionDetailBuilder(config, force=force),
        ArchitectureViewBuilder(config, force=force),
    ])

    return steps

# ---------------------------
# STEP FILTERING
# ---------------------------

def filter_steps(steps, only=None, start=None, end=None):
    names = [s.name for s in steps]

    if only:
        only_set = set(only)
        return [s for s in steps if s.name in only_set]

    if start:
        if start not in names:
            raise SystemExit(f"--from '{start}' not found. Available: {names}")
        idx = names.index(start)
        steps = steps[idx:]

    if end:
        names2 = [s.name for s in steps]
        if end not in names2:
            raise SystemExit(f"--to '{end}' not found in remaining. Available: {names2}")
        idx = names2.index(end)
        steps = steps[: idx + 1]

    return steps

# ---------------------------
# MAIN EXECUTION
# ---------------------------

def main():
    ctx = PipelineContext()

    steps = build_steps(CONFIG, force=args.force)
    steps = filter_steps(steps, only=args.only, start=args.start, end=args.end)

    for step in steps:
        print(f"\n=== {step.name} ===")

        # ----------------------------------------
        # Skip clang-based steps if C# extractor ran
        # ----------------------------------------
        if ctx.get("skip_clang") and step.name in [
            "02_extract_all_functions",
            "03_classify_functions",
            "04_build_callgraph",
            "05_extract_task",
            "06_build_task_callgraph",
        ]:
            print(f"[{step.name}] SKIP (not applicable for C#)")
            continue

        # ----------------------------------------
        # Skip firmware-only steps in loose mode
        # ----------------------------------------
        if CONFIG.get("toolchain") == "loose_cpp" and step.name in [
            "05_extract_task",
            "06_build_task_callgraph",
        ]:
            print(f"[{step.name}] SKIP (not supported in loose_cpp mode)")
            continue

        # ----------------------------------------
        # Skip task-related steps if not firmware
        # ----------------------------------------
        if CONFIG.get("project_type") != "firmware" and step.name in [
            "05_extract_task",
            "06_build_task_callgraph",
        ]:
            print(f"[{step.name}] SKIP (not a firmware project)")
            continue

        if step.should_skip(ctx):
            print(f"[{step.name}] SKIP (up-to-date)")
            continue

        step.run(ctx)

    print("\nDONE")


if __name__ == "__main__":
    main()

#python extractor/pipeline_runner.py --config extractor/configs/config.json 