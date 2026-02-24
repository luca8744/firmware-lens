import os
import re
from clang.cindex import Index, CursorKind, TranslationUnit
from .base import PipelineStep, load_json, save_json, StepIO


class TaskExtractor(PipelineStep):
    name = "05_extract_task"

    def io(self, context):
        return StepIO(
            inputs=[self.config["compile_commands"]],
            outputs=[self.config["tasks"]]
        )

    def run(self, context):
        compile_commands = load_json(self.config["compile_commands"])
        out_path = self.config["tasks"]

        index = Index.create()
        tasks = {}

        # -----------------------------
        # helpers
        # -----------------------------
        def is_inside_project(project_root, file_path):
            project_root = os.path.normpath(project_root)
            file_path = os.path.normpath(file_path)
            try:
                return os.path.commonpath([project_root, file_path]) == project_root
            except ValueError:
                return False

        def read_file_text(fp):
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            except Exception:
                return ""

        def get_obj_name_from_start_call(call_node):
            """
            Try to extract object name from `obj.start()`.
            Works on many clang builds:
              - MEMBER_REF_EXPR child spelling often is 'start' (method),
                and object may be UNEXPOSED_EXPR / DECL_REF_EXPR / MEMBER_REF_EXPR.
            We do a token fallback.
            """
            # Token-based (robust): look for pattern "<obj> . start"
            try:
                toks = [t.spelling for t in call_node.get_tokens()]
            except Exception:
                toks = []

            # example tokens: ["m_thread", ".", "start", "(", ")"]
            for i in range(len(toks) - 2):
                if toks[i + 1] == "." and toks[i + 2] == "start":
                    return toks[i]

            # Fallback: sometimes tokens are like ["start", "(", ")"] (rare)
            return None

        def extract_entry_from_initializer_text(obj_name, window_text):
            """
            Given a snippet of code around the constructor area, extract:
              obj_name{ [this]() { entry(); }, ... }
            or
              obj_name( [this]() { entry(); }, ... )

            Returns entry function name or None.
            """
            # Allow whitespace/newlines between everything; keep window small to avoid slow regex.
            # Capture first called symbol inside lambda body.
            pattern = re.compile(
                rf"{re.escape(obj_name)}\s*[\{{(]\s*"
                rf"\[[^\]]*\]\s*\(\s*\)\s*\{{\s*"
                rf"([A-Za-z_]\w*)\s*\(",
                re.DOTALL
            )
            m = pattern.search(window_text)
            if m:
                return m.group(1)
            return None

        def extract_cpp_thread_entry_from_file(fp, start_line, obj_name):
            """
            Strategy:
              - We see obj_name.start() at start_line
              - We look UP a bit in the file for the constructor initializer list region
              - Extract entry from obj_name initializer lambda
            """
            text = read_file_text(fp)
            if not text:
                return None, None

            lines = text.splitlines()
            if start_line < 1 or start_line > len(lines):
                start_line = max(1, min(start_line, len(lines)))

            # Take a window from some lines ABOVE start() to include initializer list.
            # In your code it’s usually within ~5-60 lines above.
            lo = max(0, start_line - 1 - 120)
            hi = min(len(lines), start_line - 1 + 5)
            window = "\n".join(lines[lo:hi])

            entry = extract_entry_from_initializer_text(obj_name, window)
            if entry:
                # try to estimate line of lambda (best effort): find where obj initializer starts
                # If not found, return start_line
                idx = window.find(obj_name)
                lam_line = start_line
                if idx >= 0:
                    prefix = window[:idx]
                    lam_line = lo + prefix.count("\n") + 1
                return entry, lam_line

            return None, None

        # -----------------------------
        # AST traversal
        # -----------------------------
        def visit(node, project_root):
            file_path = node.location.file.name if node.location.file else None

            # =========================
            # 1) CMSIS v1: osThreadDef
            # =========================
            if node.kind == CursorKind.MACRO_INSTANTIATION and node.spelling == "osThreadDef":
                if file_path and is_inside_project(project_root, file_path):
                    tokens = list(node.get_tokens())
                    entry = None
                    for i, t in enumerate(tokens):
                        if t.spelling == "(" and i + 1 < len(tokens):
                            entry = tokens[i + 1].spelling
                            break

                    if entry and entry not in tasks:
                        tasks[entry] = {
                            "entry_function": entry,
                            "file": os.path.normpath(file_path),
                            "line": node.location.line,
                            "type": "CMSIS_v1"
                        }
                        self.log(f"[TASK][CMSIS_v1] {entry}")

            # =========================
            # 2) CMSIS v2: osThreadNew
            # =========================
            if node.kind == CursorKind.CALL_EXPR and node.spelling == "osThreadNew":
                if file_path and is_inside_project(project_root, file_path):
                    args = list(node.get_arguments())
                    if args:
                        entry_cursor = args[0]
                        entry_name = entry_cursor.referenced.spelling if entry_cursor.referenced else entry_cursor.spelling

                        if entry_name and entry_name not in tasks:
                            tasks[entry_name] = {
                                "entry_function": entry_name,
                                "file": os.path.normpath(file_path),
                                "line": node.location.line,
                                "type": "CMSIS_v2"
                            }
                            self.log(f"[TASK][CMSIS_v2] {entry_name}")

            # ==========================================
            # 3) C++ wrapper: detect member .start()
            #    then parse initializer list from source
            # ==========================================
            if node.kind == CursorKind.CALL_EXPR and node.spelling == "start":
                if file_path and is_inside_project(project_root, file_path):
                    obj_name = get_obj_name_from_start_call(node)

                    # Filter out local threads like `os::Thread thread(...); thread.start();`
                    # We only want member threads (in your code they are m_*)
                    if not obj_name or not obj_name.startswith("m_"):
                        pass
                    else:
                        entry_name, lam_line = extract_cpp_thread_entry_from_file(
                            file_path,
                            node.location.line,
                            obj_name
                        )

                        if entry_name and entry_name not in tasks:
                            tasks[entry_name] = {
                                "entry_function": entry_name,
                                "file": os.path.normpath(file_path),
                                "line": lam_line if lam_line else node.location.line,
                                "type": "CPP_ThreadWrapper"
                            }
                            self.log(f"[TASK][CPP_THREAD] {entry_name} ({obj_name})")

            for c in node.get_children():
                visit(c, project_root)

        # -----------------------------
        # parse all TUs
        # -----------------------------
        for entry in compile_commands:
            src = entry["file"]
            project_root = os.path.normpath(entry["directory"])

            args = [a for a in entry.get("arguments", []) if a not in (src,)]

            try:
                tu = index.parse(
                    src,
                    args=args,
                    options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
                )
            except Exception as e:
                self.log(f"[WARN] Failed parsing {src}: {e}")
                continue

            visit(tu.cursor, project_root)

        save_json(out_path, tasks)
        context["tasks"] = out_path
        self.log(f"Extracted {len(tasks)} tasks")
