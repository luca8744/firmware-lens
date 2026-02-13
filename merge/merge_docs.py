from pathlib import Path

DOCS_DIR = Path("docs")
FUNCTIONS_DIR = DOCS_DIR / "functions"
MODULES_DIR = DOCS_DIR / "modules"

OUTPUT_FILE = DOCS_DIR / "Firmware_Full_Documentation.md"


def read_file(path):
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def main():

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:

        out.write("# Firmware Full Documentation\n\n")

        # ---------------------------------
        # 1️⃣ Architecture
        # ---------------------------------
        arch_path = DOCS_DIR / "Architecture.md"

        if arch_path.exists():
            out.write("## Architecture\n\n")
            out.write(read_file(arch_path))
            out.write("\n\n")

        # ---------------------------------
        # 2️⃣ Modules
        # ---------------------------------
        out.write("## Modules\n\n")

        module_files = sorted(MODULES_DIR.glob("*.md"))

        for module_file in module_files:
            out.write(read_file(module_file))
            out.write("\n\n")

        # ---------------------------------
        # 3️⃣ Functions
        # ---------------------------------
        out.write("## Functions\n\n")

        function_files = sorted(FUNCTIONS_DIR.glob("*.md"))

        for function_file in function_files:
            out.write(read_file(function_file))
            out.write("\n\n")

    print("Merged documentation created.")


if __name__ == "__main__":
    main()
