import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path

from pipeline.base import PipelineStep


class VisualGDBToCompileCommands(PipelineStep):
    name = "visualgdb_to_compile"

    def __init__(self, config, force=False):
        super().__init__(config, force)
        self.vcxproj = config.get("vcxproj")
        self.output = config.get("compile_commands")

        if not self.vcxproj:
            raise ValueError("Missing 'vcxproj' in config")
        if not self.output:
            raise ValueError("Missing 'compile_commands' in config")

    # -----------------------------------------------------

    def should_skip(self, ctx):
        if self.force:
            return False
        return os.path.exists(self.output)

    # -----------------------------------------------------

    def run(self, ctx):
        print(f"[{self.name}] Parsing {self.vcxproj}")

        tree = ET.parse(self.vcxproj)
        root = tree.getroot()

        ns = {"msb": "http://schemas.microsoft.com/developer/msbuild/2003"}

        # -------------------------------------------------
        # Collect source files
        # -------------------------------------------------

        sources = []
        for item in root.findall(".//msb:ClCompile", ns):
            include = item.attrib.get("Include")
            if include and include.lower().endswith((".c", ".cpp", ".cc", ".cxx")):
                sources.append(include)

        print(f"[{self.name}] Found {len(sources)} source files")

        # -------------------------------------------------
        # Collect include directories
        # -------------------------------------------------

        includes = set()
        for inc in root.findall(".//msb:AdditionalIncludeDirectories", ns):
            if inc.text:
                parts = inc.text.split(";")
                for p in parts:
                    p = p.strip()
                    if p and "%(" not in p:
                        includes.add(p)

        # -------------------------------------------------
        # Collect defines
        # -------------------------------------------------

        defines = set()
        for define in root.findall(".//msb:PreprocessorDefinitions", ns):
            if define.text:
                parts = define.text.split(";")
                for d in parts:
                    d = d.strip()
                    if d and "%(" not in d:
                        defines.add(d)

        # -------------------------------------------------
        # Build compile_commands entries
        # -------------------------------------------------

        project_dir = Path(self.vcxproj).parent.resolve()
        compile_commands = []

        std_c = self.config.get("c_standard", "gnu11")
        std_cpp = self.config.get("cpp_standard", "gnu++17")

        target = self.config.get("target")
        mcpu = self.config.get("mcpu")

        for src in sources:
            full_path = (project_dir / src).resolve()

            is_cpp = full_path.suffix.lower() in [".cpp", ".cc", ".cxx"]

            arguments = [
                "clang",   # importante per clang parser
                "-c",
                str(full_path),
            ]

            # Linguaggio + standard
            if is_cpp:
                arguments.extend(["-x", "c++", f"-std={std_cpp}"])
            else:
                arguments.extend(["-x", "c", f"-std={std_c}"])

            # Includes
            for inc in includes:
                inc_path = (project_dir / inc).resolve()
                arguments.append(f"-I{inc_path}")

            # Defines
            for d in defines:
                arguments.append(f"-D{d}")

            # Target / MCU
            if target:
                arguments.append(f"--target={target}")
            if mcpu:
                arguments.append(f"-mcpu={mcpu}")

            compile_commands.append({
                "directory": str(project_dir),
                "file": str(full_path),
                "arguments": arguments
            })

        # -------------------------------------------------
        # Write output
        # -------------------------------------------------

        os.makedirs(os.path.dirname(self.output), exist_ok=True)

        with open(self.output, "w", encoding="utf-8") as f:
            json.dump(compile_commands, f, indent=2)

        print(f"[{self.name}] Generated {self.output}")
