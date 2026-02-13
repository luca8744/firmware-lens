import json
import requests
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mistral"

# =========================
# Utility
# =========================

def call_llm(prompt):
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        }
    )
    return response.json()["response"]


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# =========================
# Extract function body
# =========================

def extract_function_body(file_path, start_line):
    lines = Path(file_path).read_text(
        encoding="utf-8",
        errors="ignore"
    ).splitlines()

    body = []
    brace_count = 0
    started = False

    for i in range(start_line - 1, len(lines)):
        line = lines[i]

        if "{" in line:
            brace_count += line.count("{")
            started = True

        if "}" in line:
            brace_count -= line.count("}")

        body.append(line)

        if started and brace_count == 0:
            break

    return "\n".join(body)


# =========================
# Function documentation
# =========================

def document_function(name, meta, callgraph):
    body = extract_function_body(meta["file"], meta["line"])
    calls = callgraph.get(name, [])

    prompt = f"""
You are an embedded firmware documentation assistant.

Generate professional Markdown documentation.

Function: {name}
Return type: {meta["return"]}
Parameters: {meta["params"]}
Calls: {calls}

Code:
{body}

Structure:
# {name}
## Purpose
## Parameters
## Return Value
## Internal Logic
## Interactions
## Possible Improvements
"""

    return call_llm(prompt)


# =========================
# File documentation
# =========================

def document_file(file_path, functions):
    prompt = f"""
You are documenting a firmware module.

File: {file_path}

Functions contained:
{functions}

Generate a Markdown module-level documentation:
- Module purpose
- Responsibilities
- Internal structure
- Design considerations
"""

    return call_llm(prompt)


# =========================
# Architecture documentation
# =========================

def document_architecture(callgraph):
    prompt = f"""
You are documenting firmware architecture.

Callgraph:
{callgraph}

Generate:
- High level architecture description
- Functional domains
- Execution flow assumptions
- Possible task separation
"""

    return call_llm(prompt)


# =========================
# Main
# =========================

def main():

    functions_index = load_json("analysis/functions_index.json")
    callgraph = load_json("analysis/call_graph.json")

    docs_root = Path("generated_docs")
    docs_root.mkdir(exist_ok=True)

    # -------- Function level --------
    func_dir = docs_root / "functions"
    func_dir.mkdir(exist_ok=True)

    for name, meta in functions_index.items():
        print(f"Documenting function: {name}")
        doc = document_function(name, meta, callgraph)

        with open(func_dir / f"{name}.md", "w", encoding="utf-8") as f:
            f.write(doc)

    # -------- File level --------
    file_dir = docs_root / "modules"
    file_dir.mkdir(exist_ok=True)

    files_map = {}

    for name, meta in functions_index.items():
        files_map.setdefault(meta["file"], []).append(name)

    for file_path, funcs in files_map.items():
        print(f"Documenting module: {file_path}")
        doc = document_file(file_path, funcs)

        safe_name = Path(file_path).stem
        with open(file_dir / f"{safe_name}.md", "w", encoding="utf-8") as f:
            f.write(doc)

    # -------- Architecture --------
    print("Generating architecture documentation...")
    arch_doc = document_architecture(callgraph)

    with open(docs_root / "architecture.md", "w", encoding="utf-8") as f:
        f.write(arch_doc)

    print("Done.")


if __name__ == "__main__":
    main()
