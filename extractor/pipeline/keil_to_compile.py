import os
import xml.etree.ElementTree as ET
from .base import PipelineStep, save_json, StepIO


class KeilToCompileCommands(PipelineStep):
    name = "00_keil_to_compile"

    def io(self, context):
        return StepIO(
            inputs=[self.config["uvprojx"]],
            outputs=[self.config["compile_commands"]]
        )

    def run(self, context):

        uvprojx_path = self.config["uvprojx"]
        out_path = self.config["compile_commands"]

        tree = ET.parse(uvprojx_path)
        root = tree.getroot()

        def findall(tag):
            return root.findall(f".//{tag}")

        base_dir = os.path.dirname(os.path.abspath(uvprojx_path))

        print("BASE DIR:", base_dir)

        # -------------------------------------------------------
        # SOURCE FILES
        # -------------------------------------------------------
        sources = []
        for f in findall("File"):
            name = f.find("FileName")
            path = f.find("FilePath")

            if name is not None and path is not None:
                if name.text.lower().endswith((".c", ".cpp")):
                    sources.append(path.text.replace("\\", "/"))

        # -------------------------------------------------------
        # INCLUDE PATHS
        # -------------------------------------------------------
        include_paths = []
        for inc in findall("IncludePath"):
            if inc.text:
                for p in inc.text.split(";"):
                    p = p.strip().replace("\\", "/")
                    if p:
                        include_paths.append(p)

        # -------------------------------------------------------
        # DEFINE BLOCKS (⚠ NON SPLITTARE, NON DEDUPLICARE)
        # -------------------------------------------------------
        define_blocks = []
        for d in findall("Define"):
            if d.text:
                define_blocks.append(d.text.strip())

        # -------------------------------------------------------
        # STUB DIR
        # -------------------------------------------------------
        stub_dir = self.config["stub_dir"]

        commands = []

        for src in sources:

            abs_src = os.path.normpath(os.path.join(base_dir, src))
            if not os.path.isfile(abs_src):
                continue

            args = [
                "clang",
                "-fsyntax-only",
                "-target", "arm-none-eabi",
                "-mcpu=cortex-m3",  
                "-nostdinc",
                f"-I{stub_dir}",
                "-include", os.path.join(stub_dir, "keil_armcc_stubs.h"),
            ]

            # ---- INCLUDE PATHS (no dedupe) ----
            for inc in include_paths:
                inc_path = os.path.normpath(os.path.join(base_dir, inc))
                if os.path.isdir(inc_path):
                    args.append(f"-I{inc_path}")

            # ---- DEFINE BLOCKS (come in Keil) ----
            for block in define_blocks:
                args.append(f"-D{block}")

            # ---- SOURCE ----
            args.append(abs_src)

            commands.append({
                "directory": base_dir,
                "file": abs_src,
                "arguments": args
            })

        save_json(out_path, commands)
        context["compile_commands"] = out_path

        self.log(f"Generated compile_commands.json with {len(commands)} entries")
