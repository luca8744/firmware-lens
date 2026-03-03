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

# Firmware Lens - Documentation Generator
# Copyright (C) 2026 Luca Miliciani
# GPL-3.0

import json
import requests
import argparse
import fnmatch
from pathlib import Path
import sys

# -------------------------------------------------
# Configuration
# -------------------------------------------------

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mistral"

OUT_JSON = Path("analysis")
DETAILS_DIR = OUT_JSON / "functions_detail"

DOCS_DIR = Path("docs")
FUNCTIONS_DOC = DOCS_DIR / "functions"
MODULES_DOC = DOCS_DIR / "modules"


# -------------------------------------------------
# Utils
# -------------------------------------------------

def call_llm(prompt):
    try:
        r = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "prompt": prompt, "stream": False},
            timeout=180
        )
        r.raise_for_status()
        return r.json().get("response", "")
    except Exception as e:
        print("LLM ERROR:", e)
        return "LLM generation failed."


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


def load_function_details():
    details = {}
    if not DETAILS_DIR.exists():
        return details

    for file in DETAILS_DIR.glob("*.json"):
        with open(file, "r", encoding="utf-8") as f:
            details[file.stem] = json.load(f)

    return details


# -------------------------------------------------
# Documentation generation
# -------------------------------------------------

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


# -------------------------------------------------
# Main
# -------------------------------------------------

def main():

    print("=== Firmware Lens Documentation Generator ===")

    parser = argparse.ArgumentParser()
    parser.add_argument("--module", help="Generate docs only for this module (filename or full path)")
    parser.add_argument("--pattern", help="Generate docs only for functions matching pattern")
    parser.add_argument("--exclude-drivers", action="store_true",
                        help="Exclude drivers/cmsis/middleware")
    args = parser.parse_args()

    INCLUDE_MODULE = args.module.lower() if args.module else None
    INCLUDE_PATTERN = args.pattern
    EXCLUDE_PATTERNS = []

    if args.exclude_drivers:
        EXCLUDE_PATTERNS = ["drivers", "cmsis", "middleware"]

    print("Filters:")
    print("  Module:", INCLUDE_MODULE)
    print("  Pattern:", INCLUDE_PATTERN)
    print("  Exclude drivers:", args.exclude_drivers)

    # -------------------------------------------------
    # Load data
    # -------------------------------------------------

    functions_index = load_json(OUT_JSON / "functions_index.json")
    callgraph = load_json(OUT_JSON / "callgraph.json")
    function_details = load_function_details()

    print("Loaded functions:", len(functions_index))

    if not functions_index:
        print("ERROR: functions_index.json not found or empty.")
        sys.exit(1)

    # -------------------------------------------------
    # Prepare folders
    # -------------------------------------------------

    DOCS_DIR.mkdir(exist_ok=True)
    FUNCTIONS_DOC.mkdir(exist_ok=True)
    MODULES_DOC.mkdir(exist_ok=True)

    # Clean old docs
    for f in FUNCTIONS_DOC.glob("*.md"):
        f.unlink()

    for f in MODULES_DOC.glob("*.md"):
        f.unlink()

    file_map = {}
    generated_count = 0

    # -------------------------------------------------
    # Function level
    # -------------------------------------------------

    for name, meta in functions_index.items():

        file_path = meta.get("file", "")
        file_lower = file_path.lower()

        # ---- Module filter (match full path OR filename only)
        if INCLUDE_MODULE:
            if INCLUDE_MODULE not in file_lower and \
               INCLUDE_MODULE != Path(file_lower).name:
                continue

        # ---- Pattern filter
        if INCLUDE_PATTERN:
            if not fnmatch.fnmatch(name, INCLUDE_PATTERN):
                continue

        # ---- Exclude drivers
        if EXCLUDE_PATTERNS:
            if any(p in file_lower for p in EXCLUDE_PATTERNS):
                continue

        print(f"Generating function doc: {name}")

        detail = function_details.get(name, {})
        doc = generate_function_doc(name, meta, detail, callgraph)

        with open(FUNCTIONS_DOC / f"{name}.md", "w", encoding="utf-8") as f:
            f.write(doc)

        if file_path:
            file_map.setdefault(file_path, []).append(name)

        generated_count += 1

    print("Generated function docs:", generated_count)

    if generated_count == 0:
        print("WARNING: No functions matched filters.")

    # -------------------------------------------------
    # Module level
    # -------------------------------------------------

    for file_path, funcs in file_map.items():

        print(f"Generating module doc: {file_path}")

        doc = generate_module_doc(file_path, funcs)
        module_name = Path(file_path).stem

        with open(MODULES_DOC / f"{module_name}.md", "w", encoding="utf-8") as f:
            f.write(doc)

    # -------------------------------------------------
    # Master index
    # -------------------------------------------------

    readme = ["# Firmware Documentation\n"]

    arch_path = OUT_JSON / "architecture_overview.md"
    if arch_path.exists():
        readme.append("## Architecture")
        readme.append("- See: ../analysis/architecture_overview.md\n")

    readme.append("## Modules")
    for m in sorted(MODULES_DOC.glob("*.md")):
        readme.append(f"- [Module {m.stem}](modules/{m.name})")

    readme.append("\n## Functions")
    for f in sorted(FUNCTIONS_DOC.glob("*.md")):
        readme.append(f"- [{f.stem}](functions/{f.name})")

    with open(DOCS_DIR / "README_DOC.md", "w", encoding="utf-8") as f:
        f.write("\n".join(readme))

    print("Documentation generation complete.")

    # -------------------------------------------------
    # Full merged documentation
    # -------------------------------------------------

    full_doc_path = DOCS_DIR / "Firmware_Full_Documentation.md"

    with open(full_doc_path, "w", encoding="utf-8") as out:

        out.write("# Firmware Full Documentation\n\n")

        if arch_path.exists():
            out.write("## Architecture\n\n")
            out.write(arch_path.read_text(encoding="utf-8"))
            out.write("\n\n")

        out.write("## Modules\n\n")
        for module_file in sorted(MODULES_DOC.glob("*.md")):
            out.write(module_file.read_text(encoding="utf-8"))
            out.write("\n\n")

        out.write("## Functions\n\n")
        for function_file in sorted(FUNCTIONS_DOC.glob("*.md")):
            out.write(function_file.read_text(encoding="utf-8"))
            out.write("\n\n")

    print("Full documentation generated.")


if __name__ == "__main__":
    main()

#python generate_docs.py --module source/application/BLE_App.c