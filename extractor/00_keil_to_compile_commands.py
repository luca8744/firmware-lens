import xml.etree.ElementTree as ET
import json
import os
import sys


def parse_uvprojx(uvprojx_path):
    tree = ET.parse(uvprojx_path)
    root = tree.getroot()

    def findall(tag):
        return root.findall(f".//{tag}")

    # --- Source files ---
    sources = []
    for f in findall("File"):
        name = f.find("FileName")
        path = f.find("FilePath")
        if name is not None and path is not None:
            if name.text.lower().endswith((".c", ".cpp")):
                sources.append(path.text.replace("\\", "/"))

    # --- Include paths ---
    includes = set()
    for inc in findall("IncludePath"):
        if inc.text:
            for p in inc.text.split(";"):
                p = p.strip().replace("\\", "/")
                if p:
                    includes.add(p)

    # --- Defines (flat, deduplicated) ---
    defines = set()
    for d in findall("Define"):
        if not d.text:
            continue
        for macro in d.text.split(";"):
            macro = macro.strip()
            if macro:
                defines.add(macro)

    return sources, includes, sorted(defines)


def generate_compile_commands(uvprojx_path):
    base_dir = os.path.dirname(os.path.abspath(uvprojx_path))

    sources, includes, defines = parse_uvprojx(uvprojx_path)

    # Stub headers (absolute paths)
    armcc_stub = os.path.join(base_dir, "keil_armcc_stubs.h")
    fake_libc = os.path.join(base_dir, "fake_libc.h")
    fake_stdlib = os.path.join(base_dir, "fake_stdlib.h")

    commands = []

    for src in sources:
        abs_src = os.path.normpath(os.path.join(base_dir, src))
        if not os.path.isfile(abs_src):
            continue

        stub_dir = os.path.join(base_dir, "analysis_stubs")

        args = [
            "clang",
            "-fsyntax-only",
            "-target", "arm-none-eabi",
            "-mcpu=cortex-m3",

            # 🔑 fondamentale
            "-nostdinc",

            # 🔑 qui clang troverà stdio.h / stdlib.h fake
            f"-I{stub_dir}",

            # Stub ARMCC (macro / attributi)
            "-include", os.path.join(stub_dir, "keil_armcc_stubs.h"),
        ]

        # Include paths (only existing dirs)
        for inc in includes:
            inc_path = os.path.normpath(os.path.join(base_dir, inc))
            if os.path.isdir(inc_path):
                args.append(f"-I{inc_path}")

        # Defines (ONE -D per macro)
        for d in defines:
            args.append(f"-D{d}")

        # Source file
        args.append(abs_src)

        commands.append({
            "directory": base_dir,
            "file": abs_src,
            "arguments": args
        })

    return commands


def main(uvprojx_path):
    cc = generate_compile_commands(uvprojx_path)

    if not cc:
        print("ERROR: no source files found")
        return 1

    with open("compile_commands.json", "w", encoding="utf-8") as f:
        json.dump(cc, f, indent=2)

    print(f"Generated compile_commands.json with {len(cc)} entries")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python keil_to_compile_commands.py project.uvprojx")
        sys.exit(1)

    sys.exit(main(sys.argv[1]))
