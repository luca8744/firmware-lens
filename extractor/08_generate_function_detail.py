import json
import os
import hashlib
import re

from clang.cindex import Config
Config.set_library_file(r"C:\Program Files\LLVM\bin\libclang.dll")

FUNCTION_INDEX = "analysis/functions_index.json"
OUTPUT_DIR = "analysis/functions_detail"


# -------------------------------------------------------
# Utility
# -------------------------------------------------------

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def sha1(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def find_function_end(lines, start_line):
    """
    Trova la fine della funzione contando le graffe.
    start_line è 1-based.
    """
    brace_count = 0
    started = False

    for i in range(start_line - 1, len(lines)):
        line = lines[i]

        if "{" in line:
            brace_count += line.count("{")
            started = True

        if "}" in line:
            brace_count -= line.count("}")

        if started and brace_count == 0:
            return i + 1

    return len(lines)


# -------------------------------------------------------
# Metriche
# -------------------------------------------------------

def compute_cyclomatic_complexity(body):
    """
    Calcolo semplice (euristico).
    """
    keywords = [
        r"\bif\b",
        r"\bfor\b",
        r"\bwhile\b",
        r"\bcase\b",
        r"\bcatch\b",
        r"\?\s*",
        r"&&",
        r"\|\|"
    ]

    complexity = 1
    for k in keywords:
        complexity += len(re.findall(k, body))

    return complexity


def extract_calls(body, all_function_names, current_name):
    """
    Cerca chiamate funzione nel body.
    """
    calls = set()

    for fname in all_function_names:
        if fname == current_name:
            continue

        pattern = rf"\b{re.escape(fname)}\s*\("
        if re.search(pattern, body):
            calls.add(fname)

    return list(calls)


def detect_interrupt(name, body):
    if "__irq" in body:
        return True
    if "IRQHandler" in name:
        return True
    if "Interrupt" in name:
        return True
    return False


def detect_task(name, body):
    if "Task" in name:
        return True
    if "osThread" in body:
        return True
    if "xTaskCreate" in body:
        return True
    return False


def detect_global_writes(body):
    """
    Euristica base:
    Se troviamo assegnazioni fuori da dichiarazioni locali.
    Non è perfetta, ma è un buon inizio.
    """
    assignment_pattern = r"[a-zA-Z_][a-zA-Z0-9_]*\s*="
    matches = re.findall(assignment_pattern, body)

    if len(matches) > 0:
        return True

    return False


# -------------------------------------------------------
# Main
# -------------------------------------------------------

def main():
    ensure_dir(OUTPUT_DIR)

    with open(FUNCTION_INDEX, "r", encoding="utf-8") as f:
        functions = json.load(f)

    all_function_names = list(functions.keys())

    generated = 0
    skipped = 0

    for name, meta in functions.items():

        src_file = os.path.normpath(meta["file"])
        start_line = meta["line"]

        if not os.path.exists(src_file):
            print(f"⚠ file non trovato: {src_file}")
            continue

        with open(src_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        end_line = find_function_end(lines, start_line)
        body = "".join(lines[start_line - 1: end_line])
        body_hash = sha1(body)

        out_file = os.path.join(OUTPUT_DIR, f"{name}.json")

        # ---- CACHE CHECK ----
        if os.path.exists(out_file):
            with open(out_file, "r", encoding="utf-8") as f:
                old = json.load(f)
            if old.get("body_hash") == body_hash:
                skipped += 1
                continue

        # ---- METRICHE ----
        complexity = compute_cyclomatic_complexity(body)
        calls = extract_calls(body, all_function_names, name)
        is_interrupt = detect_interrupt(name, body)
        is_task = detect_task(name, body)
        writes_globals = detect_global_writes(body)

        detail = {
            "name": name,
            "file": src_file,
            "line_start": start_line,
            "line_end": end_line,
            "return": meta.get("return"),
            "params": meta.get("params"),

            "cyclomatic_complexity": complexity,
            "calls": calls,
            "fan_out": len(calls),

            "writes_globals": writes_globals,
            "is_interrupt": is_interrupt,
            "is_task": is_task,

            "body_hash": body_hash,
            "raw_body": body.strip()
        }

        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(detail, f, indent=2)

        generated += 1

    print(f"✔ Generated: {generated}, skipped: {skipped}")


if __name__ == "__main__":
    main()
