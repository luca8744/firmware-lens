import argparse

# ---------------------------
# SET LIBCLANG EARLY
# ---------------------------

LIBCLANG = r"C:\Program Files\LLVM\bin\libclang.dll"
# oppure usa os.environ.get("LIBCLANG_PATH")

if LIBCLANG:
    from clang.cindex import Config
    Config.set_library_file(LIBCLANG)
    
from pipeline.keil_to_compile import KeilToCompileCommands
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
# CONFIG (adatta qui)
# ---------------------------
CONFIG = {

    "uvprojx": r"C:\Work\GitPersonal\firmware-lens\sensor_logic_ecu_JD\Sensor_Logic_ECU\Sensor_Logic_ECU.uvprojx",
    "stub_dir": r"C:\Work\GitPersonal\firmware-lens\analysis_stubs",

    "armcc_stub_header": "keil_armcc_stubs.h",
    "target": "arm-none-eabi",
    "mcpu": "cortex-m3",

    "compile_commands": "analysis/compile_commands.json",
    "functions_index": "analysis/functions_index.json",
    "function_categories": "analysis/function_categories.json",
    "call_graph": "analysis/call_graph.json",
    "tasks": "analysis/tasks.json",
    "task_call_graph": "analysis/task_call_graph.json",
    "firmware_ir": "analysis/firmware_ir.json",

    "functions_detail_dir": "analysis/functions_detail",
    "architecture_overview_md": "analysis/ARCHITECTURE_OVERVIEW.md",
}

# ---------------------------
# PIPELINE
# ---------------------------
def build_steps(config, force: bool):
    return [
        KeilToCompileCommands(config, force=force),
        FunctionExtractor(config, force=force),
        FunctionClassifier(config, force=force),
        CallGraphBuilder(config, force=force),
        TaskExtractor(config, force=force),
        TaskCallGraphBuilder(config, force=force),
        IRBuilder(config, force=force),
        FunctionDetailBuilder(config, force=force),
        ArchitectureViewBuilder(config, force=force),
    ]

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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="run all steps ignoring up-to-date checks")
    ap.add_argument("--only", nargs="+", help="run only these step names (space separated)")
    ap.add_argument("--from", dest="start", help="run from this step name")
    ap.add_argument("--to", dest="end", help="run until this step name (inclusive)")
    args = ap.parse_args()

    ctx = PipelineContext()
    steps = build_steps(CONFIG, force=args.force)
    steps = filter_steps(steps, only=args.only, start=args.start, end=args.end)

    for step in steps:
        print(f"\n=== {step.name} ===")
        if step.should_skip(ctx):
            print(f"[{step.name}] SKIP (up-to-date)")
            continue
        step.run(ctx)

    print("\nDONE")

if __name__ == "__main__":
    main()


#python extractor/pipeline_runner.py
#python extractor/pipeline_runner.py --force
#python extractor/pipeline_runner.py --only 08_generate_function_detail
#python extractor/pipeline_runner.py --from 04_extract_call_graph
#python extractor/pipeline_runner.py --to 01_build_firmware_ir

