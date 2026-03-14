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

import argparse
import json
from pathlib import Path

# ==========================================
# CONFIG SETUP
# ==========================================
parser = argparse.ArgumentParser()
parser.add_argument("--config", required=True, help="Path to project config JSON")
args = parser.parse_args()

with open(args.config, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

DOCS_DIR = Path(CONFIG.get("docs_dir", "docs"))
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
        # 1ï¸âƒ£ Architecture
        # ---------------------------------
        arch_path = DOCS_DIR / "Architecture.md"

        if arch_path.exists():
            out.write("## Architecture\n\n")
            out.write(read_file(arch_path))
            out.write("\n\n")

        # ---------------------------------
        # 2ï¸âƒ£ Modules
        # ---------------------------------
        out.write("## Modules\n\n")

        module_files = sorted(MODULES_DIR.glob("*.md"))

        for module_file in module_files:
            out.write(read_file(module_file))
            out.write("\n\n")

        # ---------------------------------
        # 3ï¸âƒ£ Functions
        # ---------------------------------
        out.write("## Functions\n\n")

        function_files = sorted(FUNCTIONS_DIR.glob("*.md"))

        for function_file in function_files:
            out.write(read_file(function_file))
            out.write("\n\n")

    print("Merged documentation created.")


if __name__ == "__main__":
    main()

