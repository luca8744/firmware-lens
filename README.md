# 🧩 Firmware Lens: Static Analysis Pipeline for C/C++, C#, and Firmware Projects

A robust **static analysis pipeline** for in-depth analysis of software projects. Originally designed for embedded firmware (primarily **Keil/STM32** and **VisualGDB** using **Clang / libclang**), it now also supports standard C/C++ projects (via `compile_commands.json` or loose files) and **C# projects** (parsing `.sln` or `.csproj` directly). 

It is designed to reconstruct the **Abstract Syntax Tree (AST), symbols, functions, and dependencies** directly from existing project files **without requiring code modification or compilation**.

---

## 🎯 Core Philosophy: Analyze the Code *As-Is*

Firmware Lens is designed to analyze your code exactly as it exists in your development environment, removing the friction often associated with static analysis tools.

**Key Advantages:**
- **No Source Code Modification:** Analyzes code without altering a single line.
- **Multi-Language & Multi-Environment:** Supports Keil, VisualGDB, standard `compile_commands.json`, loose C/C++ files, and C# projects.
- **Static Analysis Only:** No runtime simulation, linking, or binary generation is required.
- **Simulated Environment (C/C++):** The tool meticulously simulates the project's compilation environment (include paths, macros, etc.) to ensure accurate AST reconstruction via libclang.
- **Lightweight Alternative (C#):** Uses direct regex-based parsing to extract methods and build an index without needing heavy compiler dependencies.

---

## ✨ Features and Capabilities

This pipeline offers advanced analysis capabilities, comparable to commercial tools, while remaining **Transparent, Extendable, and LLM-Integrable**.

### 1. Deep Static Analysis
The main pipeline processes the project in structured stages, building a rich Intermediate Representation (IR). The execution dynamically adapts based on the target language and project type.

| Step | Component | Description |
| :--- | :--- | :--- |
| **Project Parsing** | Pluggable Extractors | Extracts project configurations based on the `toolchain` field (Keil, VisualGDB, C#, loose C/C++, or generic `compile_commands.json`). |
| **IR Construction** | `function_extractor.py` <br> `csharp_to_compile.py` | Generates the core function metadata. For C/C++, uses `libclang` to generate the AST. For C#, extracts methods directly bypassing libclang. |
| **Call Graph & RTOS** | `callgraph_builder.py` | Builds a comprehensive function call graph. For firmware projects, it identifies RTOS tasks (CMSIS-RTOS v1/v2 support) to generate a task-centric call graph. *(Skipped for C# and non-firmware projects)* |
| **Function Details** | `function_detail_builder.py` | Performs in-depth classification (e.g., Application vs. Driver) and extracts metrics like cyclomatic complexity, global variable usage, and potential side effects. |

### 2. LLM-Powered Documentation

Leverages the resulting static analysis artifacts (`firmware_ir.json` / `functions_index.json`) with local Large Language Models (LLMs) to generate high-quality, contextual documentation.

- **Tools:** `generator/generate_docs_smart.py`, `merge/merge_docs.py` (via Ollama).
- **Output:** Detailed documentation for individual functions, code modules, and high-level architectural overview.

### Stub Environment (C/C++ Firmware)

The `analysis_stubs_keil5/` directory provides the necessary mock headers (minimal libc, BSP, RTOS) used with the Clang `-nostdinc` flag. This ensures symbol resolution without interference from host system standard headers.

---

## ⚙️ Configuration Settings (`.json`)

The pipeline execution is driven by a `.json` configuration file. Recent updates introduced new fields to flexibly handle diverse projects:

- **`toolchain`**: Specifies how the project should be processed. Supported values:
  - `"keil"`: Parses a Keil `.uvprojx` file.
  - `"visualgdb"`: Parses a VisualGDB `.vcxproj` file.
  - `"csharp"`: Parses a `.sln` or `.csproj` directly for basic C# method extraction (skips Clang phases).
  - `"compile_commands"`: Directly accesses a pre-existing `compile_commands.json` database.
  - `"loose_cpp"`: Extracts data from loose C/C++ files without relying on strict compilation commands.
- **`project_type`**: Influences the pipeline logic. If set to `"firmware"`, task-centric extractions (like RTOS task identification and task callgraphs) are executed. For other values, these firmware-specific steps are bypassed.

**Example Configuration Snippet:**
```json
{
  "project_type": "firmware",
  "toolchain": "keil",
  "uvprojx": "projects/sensor_app/sensor_app.uvprojx",
  "functions_index": "output/functions.json"
}
```

---

## 🚀 Usage

### 1. Graphical Interface (UI - Recommended)
You can use the built-in graphical interface to easily select your project folder, toolchain, and generate the configuration file. It also provides a one-click execution of the pipeline.

**Using the Python Script:**
```bash
python orchestrator/artifact/run_ui.py
```

**Using the Standalone Executable:**
A portable executable is available to run the UI without launching Python manually. It is located at `orchestrator/artifact/dist/OrchestratorUI.exe`.
*(Note: the executable must remain in its dist folder or the repository root to find the underlying python pipeline scripts).*

To build or rebuild the executable yourself, run:
```bash
cd orchestrator/artifact
pip install pyinstaller
pyinstaller --onefile --noconsole --name OrchestratorUI run_ui.py
```

### 2. Command Line Automated Pipeline
You can run the entire pipeline—from extraction to generation and final documentation merging—using the orchestrator script via CLI. Note that the UI does exactly this under the hood.

Before starting the pipeline, the orchestrator runs **Pre-flight Checks** to ensure your environment has the necessary tools installed:
- **`cmake`**: Required for parsing C/C++ projects.
- **`ollama`**: Required for generating documentation using LLMs.
- **`libclang`**: Validates that the path specified in your `.json` config physically exists.

```bash
# Run everything automatically using your configuration file
python orchestrator/script/run_all.py --config config.json
```

You can also skip specific phases if required:
```bash
python orchestrator/script/run_all.py --config config.json --skip-extractor
python orchestrator/script/run_all.py --config config.json --skip-generator
python orchestrator/script/run_all.py --config config.json --skip-graphs
python orchestrator/script/run_all.py --config config.json --skip-merge
```

_Note: When using `run_all.py`, the console output (both `stdout` and `stderr`) is automatically captured and saved in a `.log` file. The output directory is determined by the `log_dir` field in your `config.json` (defaults to `logs/`), with files named in the format `YYYYMMDD_HHMMSS_config_name.log`._

### 2. Manual Execution: Analysis Pipeline (Extractor)
If you prefer to run steps manually, execute the main runner script first:

```bash
# Run the analysis using a configuration file
python extractor/pipeline_runner.py --config config.json

# Run specific steps or force re-execution
python extractor/pipeline_runner.py --config config.json --force
python extractor/pipeline_runner.py --config config.json --only 02_extract_all_functions
```
_Note: For C/C++ firmware parsing, the generated `compile_commands.json` file is meant for static analysis only and cannot compile the project target directly._

### 3. Manual Execution: Generating Documentation (LLM Generator)
Once the analysis is complete, use the generator tools to create Markdown documentation via local LLMs (like Ollama).

**Smart Generation (Filtered for relevance):**
```bash
# Generate high-level architecture overview
python generator/generate_docs_smart.py --config config.json --mode architecture

# Generate module-level documentation
python generator/generate_docs_smart.py --config config.json --mode modules

# Generate detailed documentation for interesting functions
python generator/generate_docs_smart.py --config config.json --mode functions --batch-size 30
```

**Detailed Generation (Custom filtering):**
```bash
# Generate docs for a specific module
python generator/generate_docs_details.py --config config.json --module source/application/file.c

# Generate docs only for functions matching a pattern
python generator/generate_docs_details.py --config config.json --pattern "*Init*"

# Exclude driver and middleware files from generation
python generator/generate_docs_details.py --config config.json --exclude-drivers
```

---

## ✅ Current Status

The infrastructure is stable and operational. Firmware Lens is ready for:

- **Automated Documentation Generation**
- **In-Depth Code Auditing**
- **Reverse Engineering Support**
- **Seamless Local LLM Integration**
- **Multi-Domain Targeting** (Firmware, Desktop/Backend C/C++, C# Apps)

---

## ⚠️ Caveats and Limitations (By Design)

Because the emphasis is on *static analysis without requiring buildability*:

- No compilation, linking, or binary output is ever produced.
- No code execution or functional correctness verification is performed.
- C# extraction currently employs lightweight regex matching instead of deep AST analysis, so complex language features may not map seamlessly.

---

## 📝 Application Domain

You can customize this section for the specific project being analyzed:

- **Functional Purpose:** What the software/firmware aims to do.
- **Domain:** Motor Control, CAN bus, Desktop Client, Backend Service, etc.
- **Target Platform:** STM32, Windows, Linux, etc.
- **Main Flows:** High-level interactions, task loops, scheduling.
