# 🧩 Firmware Lens: Static Analysis Pipeline for C/C++ Firmware

A robust **static analysis pipeline** based on **Clang / libclang** for in-depth analysis of embedded firmware projects (primarily **Keil/STM32** and **VisualGDB**). It is designed to reconstruct the entire **Abstract Syntax Tree (AST), symbols, and dependencies** directly from existing project files ([`.uvprojx`](.uvprojx) or [`.vcxproj`](.vcxproj)) **without requiring code modification or compilation**.

---

## 🎯 Core Philosophy: Analyze the Code *As-Is*

Firmware Lens is designed to analyze your embedded C/C++ code exactly as it exists in your development environment, removing the friction often associated with static analysis tools.

**Key Advantages:**
- **No Source Code Modification:** Analyzes code without altering a single line.
- **Toolchain Independent:** Does not rely on proprietary toolchains (ARMCC, GCC ARM) for the analysis phase.
- **Static Analysis Only:** No runtime simulation, linking, or binary generation is required.
- **Simulated Environment:** The tool meticulously simulates the project's compilation environment (include paths, macros, etc.) to ensure accurate AST reconstruction.

---

## ✨ Features and Capabilities

This pipeline offers advanced analysis capabilities, comparable to commercial embedded tools, while remaining **Transparent, Extendable, and LLM-Integrable**.

### 1. Deep Static Analysis
The main pipeline processes the project in structured stages, building a rich Intermediate Representation (IR).

| Step | Component | Description |
| :--- | :--- | :--- |
| **Project Parsing** | [`extractor/pipeline/keil_to_compile.py`](extractor/pipeline/keil_to_compile.py:1) | Converts `.uvprojx` or `.vcxproj` into a `compile_commands.json` database, capturing all necessary include paths and macro definitions (`-D`). |
| **IR Construction** | [`extractor/pipeline/function_extractor.py`](extractor/pipeline/function_extractor.py:1) | Uses `libclang` to generate the AST and extract core function metadata (signatures, locations) for the initial IR. |
| **Call Graph & RTOS** | [`extractor/pipeline/callgraph_builder.py`](extractor/pipeline/callgraph_builder.py:1) | Builds a comprehensive function call graph, and critically, identifies RTOS tasks (CMSIS-RTOS v1/v2 support) to generate a task-centric call graph. |
| **Function Details** | [`extractor/pipeline/function_detail_builder.py`](extractor/pipeline/function_detail_builder.py:1) | Performs in-depth classification (e.g., Application vs. Driver) and extracts metrics like cyclomatic complexity, global variable usage, and potential side effects. |

### 2. LLM-Powered Documentation

Leverages the resulting static analysis artifacts (`firmware_ir.json`) with local Large Language Models (LLMs) to generate high-quality, contextual documentation.

- **Tools:** [`generator/generate_docs_smart.py`](generator/generate_docs_smart.py:1), [`merge/merge_docs.py`](merge/merge_docs.py:1) (via Ollama).
- **Output:** Detailed documentation for individual functions, code modules, and high-level architectural overview.

### Stub Environment

The [`analysis_stubs_keil5/`](analysis_stubs_keil5/:1) directory provides the necessary mock headers (minimal libc, BSP, RTOS) used with the Clang `-nostdinc` flag. This ensures symbol resolution without interference from host system standard headers.

---

## 🚀 Usage

The pipeline is executed via the main runner script using a JSON configuration file that defines the project path and analysis targets.

```bash
# Example: Run the analysis using a configuration file
python extractor/pipeline_runner.py extractor/configs/sensor_logic.json
```
_Note: The generated `compile_commands.json` file is for static analysis only and is not suitable for direct project compilation._

---

## ✅ Current Status

The infrastructure is stable and fully operational for static analysis. Firmware Lens is ready to support advanced tasks:

- **Automated Documentation Generation**
- **In-Depth Code Auditing**
- **Reverse Engineering Support**
- **Seamless Local LLM Integration**

---

## ⚠️ Caveats and Limitations (By Design)

The focus on *analysis only* leads to the following intentional design constraints:

- No compilation, linking, or binary output.
- No code execution or functional correctness verification.
- Clang warnings (e.g., `macro redefined`) are accepted as they do not impede structural analysis.

---

## 📝 Application Domain

This section can be customized to document the specific firmware under analysis:

- Functional purpose of the firmware.
- Application domain (e.g., Motor control, CAN bus management).
- Target device (e.g., STM32F205VC).
- Main logical flows (e.g., Sampling cycle, Isobus message handling).
