import json
import requests
import hashlib
import argparse
from pathlib import Path

# ==============================
# CONFIG
# ==============================

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mistral"

OUT_JSON = Path("analysis")
DETAILS_DIR = OUT_JSON / "functions_detail"

DOCS_DIR = Path("docs")
FUNCTIONS_DOC = DOCS_DIR / "functions"
MODULES_DOC = DOCS_DIR / "modules"

CACHE_FILE = Path("docs/doc_cache.json")


# ==============================
# UTILITIES
# ==============================

def call_llm(prompt):

    print(f"Prompt length: {len(prompt)}")

    r = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 600,     # limite output
                "temperature": 0.2
            }
        },
        timeout=600
    )

    r.raise_for_status()
    return r.json()["response"]



def compute_hash(content):
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def load_json(path):
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_cache():
    return load_json(CACHE_FILE) if CACHE_FILE.exists() else {}


def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def load_function_details():
    details = {}
    if DETAILS_DIR.exists():
        for file in DETAILS_DIR.glob("*.json"):
            details[file.stem] = load_json(file)
    return details


def extract_function_body(file_path, start_line):
    p = Path(file_path)
    if not p.exists():
        return ""
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


# ==============================
# INTELLIGENT FILTERING
# ==============================

def compute_fan_in(callgraph):
    fan_in = {}
    for caller, callees in callgraph.items():
        for callee in callees:
            fan_in[callee] = fan_in.get(callee, 0) + 1
    return fan_in


def is_interesting_function(name, detail, callgraph, fan_in):

    if len(callgraph.get(name, [])) > 5:
        return True

    if fan_in.get(name, 0) > 5:
        return True

    if detail.get("cyclomatic_complexity", 0) > 8:
        return True

    if detail.get("writes_globals"):
        return True

    if detail.get("is_interrupt") or detail.get("is_task"):
        return True

    print(f"{name}: {len(callgraph.get(name, []))} - {fan_in.get(name, 0)} - {detail.get("cyclomatic_complexity", 0)} - {detail.get("writes_globals")} - {detail.get("is_interrupt")} - {detail.get("is_task")}")

    return False


# ==============================
# DOC GENERATORS
# ==============================

def generate_function_doc(name, meta, detail, callgraph):

    body = ""
    if meta.get("file") and meta.get("line"):
        body = extract_function_body(meta["file"], meta["line"])

    # ⚠ Rimuoviamo raw_body e body_hash dal JSON passato al LLM
    detail_for_llm = dict(detail)
    detail_for_llm.pop("raw_body", None)
    detail_for_llm.pop("body_hash", None)

    prompt = f"""
You are an embedded firmware documentation assistant.
Write professional Markdown.

Function: {name}
Return type: {meta.get("return")}
Parameters: {meta.get("params")}
Calls: {callgraph.get(name, [])}

Static analysis details:
{json.dumps(detail_for_llm, indent=2)}

Code:
{body}

Output:
# {name}
## Purpose
## Parameters
## Return
## Dependencies
## Internal Logic
## Side Effects
"""

    return call_llm(prompt)



def generate_module_doc(file_path, functions):

    prompt = f"""
Document firmware module.

File: {file_path}
Functions:
{functions}

Output:
# Module {Path(file_path).name}
## Responsibility
## Key Functions
## Design Notes
"""

    return call_llm(prompt)


def generate_architecture_doc(callgraph):

    prompt = f"""
Document firmware architecture from callgraph.

Callgraph:
{json.dumps(callgraph, indent=2)[:15000]}

Output:
# Architecture
## Overview
## Main Subsystems
## Call Flow Highlights
"""

    return call_llm(prompt)


# ==============================
# MAIN
# ==============================

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["architecture", "modules", "functions"], required=True)
    parser.add_argument("--batch-size", type=int, default=30)
    args = parser.parse_args()

    DOCS_DIR.mkdir(exist_ok=True)
    FUNCTIONS_DOC.mkdir(exist_ok=True)
    MODULES_DOC.mkdir(exist_ok=True)

    functions_index = load_json(OUT_JSON / "functions_index.json")
    callgraph = load_json(OUT_JSON / "callgraph.json")
    function_details = load_function_details()

    fan_in = compute_fan_in(callgraph)
    cache = load_cache()

    # ---------------- ARCHITECTURE ----------------

    if args.mode == "architecture":
        print("Generating architecture...")
        doc = generate_architecture_doc(callgraph)
        (DOCS_DIR / "Architecture.md").write_text(doc, encoding="utf-8")
        print("Done.")
        return

    # ---------------- MODULES ----------------

    if args.mode == "modules":
        file_map = {}
        for name, meta in functions_index.items():
            file_map.setdefault(meta["file"], []).append(name)

        for file_path, funcs in file_map.items():
            print(f"Module: {file_path}")
            doc = generate_module_doc(file_path, funcs)
            (MODULES_DOC / f"{Path(file_path).stem}.md").write_text(doc, encoding="utf-8")

        print("Done.")
        return

    # ---------------- FUNCTIONS ----------------

    if args.mode == "functions":

        all_functions = sorted(functions_index.keys())

        interesting = [
            f for f in all_functions
            if is_interesting_function(
                f,
                function_details.get(f, {}),
                callgraph,
                fan_in
            )
        ]

        total = len(interesting)
        batch_size = args.batch_size

        print(f"Total interesting functions: {total}")

        for start in range(0, total, batch_size):

            batch = interesting[start:start + batch_size]
            print(f"\n=== Processing functions {start} to {start + len(batch)} ===")

            for name in batch:

                meta = functions_index[name]
                detail = function_details.get(name, {})
                calls = callgraph.get(name, [])

                body = ""
                if meta.get("file") and meta.get("line"):
                    body = extract_function_body(meta["file"], meta["line"])

                hash_input = json.dumps(meta, sort_keys=True) + \
                             json.dumps(detail, sort_keys=True) + \
                             json.dumps(calls, sort_keys=True) + \
                             body

                current_hash = compute_hash(hash_input)

                if cache.get(name) == current_hash:
                    print(f"SKIP {name}")
                    continue

                print(f"Generating {name}")

                doc = generate_function_doc(name, meta, detail, callgraph)
                (FUNCTIONS_DOC / f"{name}.md").write_text(doc, encoding="utf-8")

                cache[name] = current_hash

            save_cache(cache)

        print("All batches completed.")
        return


if __name__ == "__main__":
    main()



#python generator/generate_docs_smart.py --mode architecture
#python generator/generate_docs_smart.py --mode modules
#python generator/generate_docs_smart.py --mode functions --batch-size 30



