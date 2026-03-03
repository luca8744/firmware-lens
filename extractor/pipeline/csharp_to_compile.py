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

import json
import os
import re
from pathlib import Path

from pipeline.base import PipelineStep

class CSharpToCompileCommands(PipelineStep):
    """
    Questo step estrae direttamente i metodi dai file .cs usando regex per 
    generare un `functions_index.json` di base, scavalcando libclang.
    Genera anche file mock per call_graph e tasks così il resto della pipeline può proseguire.
    """
    name = "csharp_to_compile"

    def __init__(self, config, force=False):
        super().__init__(config, force)
        self.sln_or_csproj = config.get("sln") or config.get("csproj")
        self.output_index = config.get("functions_index")
        self.output_call_graph = config.get("call_graph")
        self.output_tasks = config.get("tasks")
        self.output_task_call_graph = config.get("task_call_graph")

        if not self.sln_or_csproj:
            raise ValueError("Missing 'sln' or 'csproj' in config")

    def should_skip(self, ctx):
        if self.force:
            return False
        return os.path.exists(self.output_index)

    def run(self, ctx):
        project_dir = Path(self.sln_or_csproj).parent.resolve()
        
        print(f"[{self.name}] Scanning {project_dir} for .cs files...")
        
        cs_files = list(project_dir.rglob("*.cs"))
        print(f"[{self.name}] Found {len(cs_files)} C# files")

        # Cerca firme di metodi banali: public/private/protected [static] TipoRitorno NomeMetodo(arg1, arg2)
        # Ignora le proprietà, i costruttori e altre finezze per ora
        method_pattern = re.compile(
            r'^\s*(?:public|private|protected|internal|protected internal|private protected)?\s*'
            r'(?:static\s+|virtual\s+|override\s+|abstract\s+|async\s+)*'
            r'([a-zA-Z0-9_<>, \[\]]+)\s+'     # Return type (group 1)
            r'([a-zA-Z0-9_]+)\s*'           # Method name (group 2)
            r'\((.*?)\)\s*'                 # Parameters (group 3)
            r'(?:where\s+.*?)?'             # Generic constraints (optional)
            r'\{?',                          # Opening brace (optional on same line)
            re.MULTILINE
        )

        functions = {}

        for cs_file in cs_files:
            if "obj" in cs_file.parts or "bin" in cs_file.parts:
                continue

            try:
                with open(cs_file, "r", encoding="utf-8-sig") as f:
                    content = f.read()

                # Calcola i numeri di riga in modo grezzo
                lines = content.split('\n')
                
                for lineno, line in enumerate(lines, 1):
                    # Salta commenti e classi/namespace
                    if line.strip().startswith("//") or "class " in line or "namespace " in line or "interface " in line:
                        continue

                    match = method_pattern.search(line)
                    if match:
                        ret_type = match.group(1).strip()
                        name = match.group(2).strip()
                        params_raw = match.group(3).strip()

                        # Salta le keyword del linguaggio e i costrutti standard
                        if name in ["if", "for", "foreach", "while", "catch", "using", "lock", "switch"]:
                            continue

                        # Costruisci params (molto basic)
                        params = []
                        if params_raw:
                            for p in params_raw.split(','):
                                parts = p.strip().split()
                                if len(parts) >= 2:
                                    params.append({"type": " ".join(parts[:-1]), "name": parts[-1]})
                                else:
                                    params.append({"type": "unknown", "name": p.strip()})

                        
                        file_path_str = str(cs_file.resolve()).replace('\\', '/')
                        functions[name] = {
                            "file": file_path_str,
                            "line": lineno,
                            "return": ret_type,
                            "params": params
                        }

            except Exception as e:
                print(f"[{self.name}] Warning: Could not parse {cs_file.name}: {e}")

        os.makedirs(os.path.dirname(self.output_index), exist_ok=True)

        with open(self.output_index, "w", encoding="utf-8") as f:
            json.dump(functions, f, indent=2)
        print(f"[{self.name}] Extracted {len(functions)} functions to {self.output_index}")

        # Crea dummy per callgraph e tasks
        with open(self.output_call_graph, "w", encoding="utf-8") as f:
            json.dump({}, f)
        
        with open(self.output_tasks, "w", encoding="utf-8") as f:
            json.dump({}, f)
            
        with open(self.output_task_call_graph, "w", encoding="utf-8") as f:
            json.dump({}, f)

        # Skip clang extraction/classifier/callgraph per C#
        ctx["skip_clang"] = True
