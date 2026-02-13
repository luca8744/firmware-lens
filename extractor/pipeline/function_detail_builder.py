import os
import re
import json
import hashlib
from .base import PipelineStep, load_json, save_json, ensure_dir, StepIO


class FunctionDetailBuilder(PipelineStep):
    name = "08_generate_function_detail"

    # -----------------------------------------------------
    # IO
    # -----------------------------------------------------

    def io(self, context):
        fn_index = self.config["functions_index"]
        inputs = [fn_index]
        functions = load_json(fn_index) if os.path.exists(fn_index) else {}
        for _, meta in functions.items():
            fp = meta.get("file")
            if fp and os.path.exists(fp):
                inputs.append(fp)
        return StepIO(inputs=inputs, outputs=[self.config["functions_detail_dir"]])

    # -----------------------------------------------------
    # Helpers
    # -----------------------------------------------------

    @staticmethod
    def sanitize_filename(name: str) -> str:
        """
        Safe for Windows filesystem.
        Avoid illegal chars and collisions.
        """
        # Replace illegal Windows chars
        safe = re.sub(r'[<>:"/\\|?*]', "_", name)

        # Replace namespace separators
        safe = safe.replace("::", "__")

        # Trim spaces
        safe = safe.strip()

        # Avoid empty filename
        if not safe:
            safe = "unnamed"

        # Avoid Windows reserved names
        reserved = {"CON", "PRN", "AUX", "NUL"}
        if safe.upper() in reserved:
            safe += "_fn"

        # Add short hash to avoid collisions
        short_hash = hashlib.sha1(name.encode("utf-8")).hexdigest()[:8]

        return f"{safe}_{short_hash}"

    @staticmethod
    def sha1(text: str) -> str:
        return hashlib.sha1(text.encode("utf-8")).hexdigest()

    # -----------------------------------------------------

    def run(self, context):
        fn_index_path = self.config["functions_index"]
        out_dir = self.config["functions_detail_dir"]
        ensure_dir(out_dir)

        functions = load_json(fn_index_path)
        all_function_names = list(functions.keys())

        def find_function_end(lines, start_line):
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

        def compute_cyclomatic_complexity(body):
            keywords = [
                r"\bif\b", r"\bfor\b", r"\bwhile\b", r"\bcase\b",
                r"\bcatch\b", r"\?\s*", r"&&", r"\|\|"
            ]
            complexity = 1
            for k in keywords:
                complexity += len(re.findall(k, body))
            return complexity

        def extract_calls(body, all_names, current_name):
            calls = set()
            for fname in all_names:
                if fname == current_name:
                    continue
                pattern = rf"\b{re.escape(fname)}\s*\("
                if re.search(pattern, body):
                    calls.add(fname)
            return list(calls)

        def detect_interrupt(name, body):
            return ("__irq" in body) or ("IRQHandler" in name) or ("Interrupt" in name)

        def detect_task(name, body):
            rtos_patterns = [
                r"\bxTaskCreate\b",
                r"\bosThreadNew\b",
                r"\bosThreadCreate\b",
                r"\bTaskCreate\b",
                r"\bCreateTask\b",
                r"\bTaskManager::create\b"
            ]

            for p in rtos_patterns:
                if re.search(p, body):
                    return True

            return False


        def detect_global_writes(body):
            assignment_pattern = r"[a-zA-Z_][a-zA-Z0-9_]*\s*="
            return len(re.findall(assignment_pattern, body)) > 0

        generated = 0
        skipped = 0

        for name, meta in functions.items():
            src_file = os.path.normpath(meta["file"])
            start_line = meta["line"]

            if not os.path.exists(src_file):
                self.log(f"⚠ file non trovato: {src_file}")
                continue

            with open(src_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            end_line = find_function_end(lines, start_line)
            body = "".join(lines[start_line - 1: end_line])
            body_hash = self.sha1(body)

            safe_name = self.sanitize_filename(name)
            out_file = os.path.join(out_dir, f"{safe_name}.json")

            # Incremental skip
            if os.path.exists(out_file):
                try:
                    old = load_json(out_file)
                    if old.get("body_hash") == body_hash:
                        skipped += 1
                        continue
                except Exception:
                    pass

            complexity = compute_cyclomatic_complexity(body)
            calls = extract_calls(body, all_function_names, name)

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
                "writes_globals": detect_global_writes(body),
                "is_interrupt": detect_interrupt(name, body),
                "is_task": detect_task(name, body),
                "body_hash": body_hash,
                "raw_body": body.strip()
            }

            save_json(out_file, detail)
            generated += 1

        context["functions_detail_dir"] = out_dir
        self.log(f"✔ Generated: {generated}, skipped: {skipped}")
