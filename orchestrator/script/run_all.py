import os
import argparse
import subprocess
import sys
import datetime
from pathlib import Path

import json

def setup_logger(config_path):
    # Try to read log directory from config, otherwise default to "logs"
    log_dir_name = "logs"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)
            if "log_dir" in config_data:
                log_dir_name = str(config_data["log_dir"])
    except Exception as e:
        print(f"⚠️ Warning: Could not read log_dir from config, using default 'logs'. Error: {e}")

    logs_dir = Path(log_dir_name)
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    config_name = Path(config_path).stem
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"{timestamp}_{config_name}.log"
    return log_file

class LoggerWriter:
    def __init__(self, original_stream, log_file_path):
        self.original_stream = original_stream
        self.log_file = open(log_file_path, "a", encoding="utf-8")

    def write(self, message):
        self.original_stream.write(message)
        self.log_file.write(message)
        self.flush()

    def __getattr__(self, attr):
        # Delega attributi mancanti (come isatty()) allo stream originale
        return getattr(self.original_stream, attr)

    def flush(self):
        self.original_stream.flush()
        self.log_file.flush()

    def close(self):
        self.log_file.close()

def run_command(command, description):
    print(f"\n{'='*60}")
    print(f"🚀 RUNNING: {description}")
    print(f"➜ {' '.join(command)}")
    print(f"{'='*60}\n")
    
    # Use Popen to capture stdout and stderr and print it line by line
    # so that our LoggerWriter can intercept it and save it to the log file.
    process = subprocess.Popen(
        command, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT, 
        text=True,
        bufsize=1  # Line buffered
    )
    
    # Read output line by line as it is generated
    if process.stdout:
        for line in process.stdout:
            print(line, end="")
        
    process.wait()
    
    if process.returncode != 0:
        print(f"\n❌ ERROR: Step '{description}' failed with code {process.returncode}")
        # non facciamo sys.exit prima di chiudere i log, usiamo un'eccezione o usciamo puliti
        raise SystemExit(process.returncode)

def main():
    # Force UTF-8 encoding for standard output on Windows to support emojis
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            pass
            
    parser = argparse.ArgumentParser(description="Run the entire Firmware Lens pipeline.")
    parser.add_argument("--config", required=True, help="Path to project config JSON")
    
    # Optional flags to skip parts of the pipeline
    parser.add_argument("--skip-extractor", action="store_true", help="Skip the extraction phase")
    parser.add_argument("--skip-generator", action="store_true", help="Skip the documentation generation phase")
    parser.add_argument("--skip-graphs", action="store_true", help="Skip the graph generation phase")
    parser.add_argument("--skip-merge", action="store_true", help="Skip the final merge phase")
    
    args = parser.parse_args()
    config_path = args.config

    if not os.path.exists(config_path):
        print(f"❌ ERROR: Config file not found at '{config_path}'")
        sys.exit(1)

    # Pre-flight Checks
    print("\n" + "="*60)
    print("🔍 RUNNING PRE-FLIGHT CHECKS")
    print("="*60)
    
    missing_reqs = []
    warnings_reqs = []
    
    import shutil
    # 1. Check CMake
    if shutil.which("cmake") is None:
        warnings_reqs.append("cmake (Not found in PATH, might fail if your project needs it to build a compile database)")
    else:
        print("✅ cmake: Installed")

    # 2. Check Ollama
    if shutil.which("ollama") is None:
        warnings_reqs.append("ollama (Not found in PATH, might fail if you use local LLM generation without an external URL)")
    else:
        print("✅ ollama: Installed")
        
    # 3. Check config-specific requirements (like libclang)
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)
            libclang_path = config_data.get("libclang")
            if libclang_path and not os.path.exists(libclang_path):
                 missing_reqs.append(f"libclang (Path not found: {libclang_path})")
            elif libclang_path:
                 print("✅ libclang: Found in config")
    except Exception as e:
        print(f"⚠️ Warning: Could not read config for libclang check: {e}")

    if warnings_reqs:
        print("\n⚠️ PRE-FLIGHT WARNINGS (Process will continue):")
        for w in warnings_reqs:
            print(f"  - Missing: {w}")

    if missing_reqs:
        print("\n❌ PRE-FLIGHT CHECKS FAILED:")
        for req in missing_reqs:
            print(f"  - Missing: {req}")
        print("\nPlease install the missing requirements before running the pipeline.\n")
        sys.exit(1)
    
    if not missing_reqs and not warnings_reqs:
        print("✅ All pre-flight checks passed!\n")
    else:
        print("\nPre-flight checks passed with warnings.\n")

    log_file_path = setup_logger(config_path)
    print(f"📝 Logging output to: {log_file_path}")
    
    # Redirect stdout and stderr
    sys.stdout = LoggerWriter(sys.stdout, log_file_path)
    sys.stderr = LoggerWriter(sys.stderr, log_file_path)

    # Resolve project root dynamically so we can run this from anywhere
    project_root = Path(__file__).resolve().parent.parent.parent
    
    # Helper per costruire i comandi con path assoluti
    def get_script_path(*parts):
        return str(project_root.joinpath(*parts))

    # 1. Extractor Pipeline
    if not args.skip_extractor:
        run_command(
            [sys.executable, get_script_path("extractor", "pipeline_runner.py"), "--config", config_path],
            "Pipeline Extractor"
        )
    else:
        print("\n⏭️  SKIPPING Pipeline Extractor")

    # 2. Document Generators
    if not args.skip_generator:
        base_gen_cmd = [sys.executable, get_script_path("generator", "generate_docs_smart.py"), "--config", config_path]
        
        run_command(base_gen_cmd + ["--mode", "architecture"], "Generate Architecture Docs")
        run_command(base_gen_cmd + ["--mode", "modules"], "Generate Module Docs")
        run_command(base_gen_cmd + ["--mode", "functions", "--batch-size", "30"], "Generate Function Docs")
    else:
        print("\n⏭️  SKIPPING Document Generation")

    # 3. Graph Generators
    if not args.skip_graphs:
        run_command(
            [sys.executable, get_script_path("generator", "generate_architecture_report.py"), "--config", config_path],
            "Generate Architecture Report (CSV/Metadata)"
        )
        run_command(
            [sys.executable, get_script_path("generator", "generate_graph.py"), "--config", config_path],
            "Generate Architecture Graph (Graphviz)"
        )
        run_command(
            [sys.executable, get_script_path("generator", "generate_graph_mermaid.py"), "--config", config_path],
            "Generate Architecture Graphs (Mermaid)"
        )
    else:
        print("\n⏭️  SKIPPING Graph Generation")

    # 4. Merge
    if not args.skip_merge:
        run_command(
            [sys.executable, get_script_path("merge", "merge_docs.py"), "--config", config_path],
            "Merge Documentation into Final Output"
        )
    else:
        print("\n⏭️  SKIPPING Merge Step")

    print(f"\n{'='*60}")
    print("✅ Firmware Lens Pipeline Completed Successfully! ✅")
    print(f"{'='*60}\n")

    # Clean up loggers
    if hasattr(sys.stdout, "close"):
        sys.stdout.close()
    if hasattr(sys.stderr, "close"):
        sys.stderr.close()

if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        # Assicura la pulizia dei file se c'è un exit
        if hasattr(sys.stdout, "close"):
            sys.stdout.close()
        if hasattr(sys.stderr, "close"):
            sys.stderr.close()
        sys.exit(e.code)
