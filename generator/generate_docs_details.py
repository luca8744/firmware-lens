import json
import requests
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mistral"

OUT_JSON = Path("analysis")
DETAILS_DIR = OUT_JSON / "functions_detail"

DOCS_DIR = Path("docs")
FUNCTIONS_DOC = DOCS_DIR / "functions"
MODULES_DOC = DOCS_DIR / "modules"


# -----------------------------
# Utils
# -----------------------------

def call_llm(prompt):
    r = requests.post(
        OLLAMA_URL,
        json={"model": MODEL, "prompt": prompt, "stream": False}
    )
    return r.json()["response"]


def load_json(path):
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_function_body(file_path, start_line):
    p = Path(file_path)
    if not p.exists():
        return "// file not found"

    lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()

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


# -----------------------------
# Load everything
# -----------------------------

def load_function_details():
    details = {}
    if not DETAILS_DIR.exists():
        return details

    for file in DETAILS_DIR.glob("*.json"):
        with open(file, "r", encoding="utf-8") as f:
            details[file.stem] = json.load(f)

    return details


# -----------------------------
# Documentation
# -----------------------------

def generate_function_doc(name, index_meta, detail_meta, callgraph):

    body = ""
    if index_meta.get("file") and index_meta.get("line"):
        body = extract_function_body(
            index_meta["file"],
            index_meta["line"]
        )

    calls = callgraph.get(name, [])

    prompt = f"""
You are an embedded firmware documentation assistant.
Write professional Markdown documentation.

Function: {name}
Return type: {index_meta.get("return")}
Parameters: {index_meta.get("params")}
Calls: {calls}

Static analysis details (authoritative, do NOT invent missing data):
{json.dumps(detail_meta, indent=2)}

Code:
{body}

Output structure:
# {name}
## Purpose
## Parameters
## Return Value
## Dependencies
## Internal Logic
## Global interactions (if present)
## Edge cases
"""

    return call_llm(prompt)


def generate_module_doc(file_path, functions):

    prompt = f"""
You are documenting a firmware module.

File: {file_path}

Functions:
{functions}

Generate Markdown:
# Module: {Path(file_path).name}
## Responsibility
## Contained Functions
## Data interactions
## Design considerations
"""

    return call_llm(prompt)


# -----------------------------
# Main orchestrator
# -----------------------------

def main():

    DOCS_DIR.mkdir(exist_ok=True)
    FUNCTIONS_DOC.mkdir(exist_ok=True)
    MODULES_DOC.mkdir(exist_ok=True)

    functions_index = load_json(OUT_JSON / "functions_index.json")
    callgraph = load_json(OUT_JSON / "callgraph.json")
    function_details = load_function_details()

    file_map = {}

    # ---- Function level
    for name, meta in functions_index.items():

        print(f"Generating function doc: {name}")

        detail = function_details.get(name, {})
        doc = generate_function_doc(name, meta, detail, callgraph)

        with open(FUNCTIONS_DOC / f"{name}.md", "w", encoding="utf-8") as f:
            f.write(doc)

        file_map.setdefault(meta["file"], []).append(name)

    # ---- Module level
    for file_path, funcs in file_map.items():

        print(f"Generating module doc: {file_path}")

        doc = generate_module_doc(file_path, funcs)

        module_name = Path(file_path).stem

        with open(MODULES_DOC / f"{module_name}.md", "w", encoding="utf-8") as f:
            f.write(doc)

    # ---- Master index
    readme = []

    readme.append("# Firmware Documentation\n")

    if (OUT_JSON / "architecture_overview.md").exists():
        readme.append("## Architecture")
        readme.append("- See: ../out_json/architecture_overview.md\n")

    readme.append("## Modules")
    for m in MODULES_DOC.glob("*.md"):
        readme.append(f"- [Module {m.stem}](modules/{m.name})")

    readme.append("\n## Functions")
    for f in FUNCTIONS_DOC.glob("*.md"):
        readme.append(f"- [{f.stem}](functions/{f.name})")

    with open(DOCS_DIR / "README_DOC.md", "w", encoding="utf-8") as f:
        f.write("\n".join(readme))

    print("Documentation generation complete.")

        # ---- Full merged documentation
    full_doc_path = DOCS_DIR / "Firmware_Full_Documentation.md"

    with open(full_doc_path, "w", encoding="utf-8") as out:

        out.write("# Firmware Full Documentation\n\n")

        # Architecture
        arch_path = OUT_JSON / "architecture_overview.md"
        if arch_path.exists():
            out.write("## Architecture\n\n")
            out.write(arch_path.read_text(encoding="utf-8"))
            out.write("\n\n")

        # Modules
        out.write("## Modules\n\n")
        for module_file in sorted(MODULES_DOC.glob("*.md")):
            out.write(module_file.read_text(encoding="utf-8"))
            out.write("\n\n")

        # Functions
        out.write("## Functions\n\n")
        for function_file in sorted(FUNCTIONS_DOC.glob("*.md")):
            out.write(function_file.read_text(encoding="utf-8"))
            out.write("\n\n")

    print("Full documentation generated.")


if __name__ == "__main__":
    main()
