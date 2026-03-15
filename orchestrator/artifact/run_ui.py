import os
import sys
import json
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

class OrchestratorUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Firmware Lens - Orchestrator UI")
        self.root.geometry("600x700")
        self.root.minsize(500, 600)
        
        self.project_path = tk.StringVar()
        self.toolchain = tk.StringVar(value="keil")
        self.project_type = tk.StringVar(value="firmware")
        
        self.config_path = None
        
        self._build_ui()

    def _build_ui(self):
        # --- Project Selection ---
        frame_project = ttk.LabelFrame(self.root, text=" 1. Project Selection ")
        frame_project.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(frame_project, text="Project Folder:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(frame_project, textvariable=self.project_path, state="readonly", width=40).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(frame_project, text="Browse...", command=self.browse_project).grid(row=0, column=2, padx=5, pady=5)
        
        frame_project.columnconfigure(1, weight=1)

        # --- Settings ---
        frame_settings = ttk.LabelFrame(self.root, text=" 2. Settings ")
        frame_settings.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(frame_settings, text="Toolchain:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        toolchain_combo = ttk.Combobox(frame_settings, textvariable=self.toolchain, values=["keil", "cmake"], state="readonly")
        toolchain_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(frame_settings, text="Project Type:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        type_combo = ttk.Combobox(frame_settings, textvariable=self.project_type, values=["firmware", "software", "library"], state="readonly")
        type_combo.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        frame_settings.columnconfigure(1, weight=1)

        # --- Generate Config ---
        frame_config = ttk.LabelFrame(self.root, text=" 3. Configuration ")
        frame_config.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(frame_config, text="Generate config.json", command=self.generate_config).pack(pady=10)

        # --- Execution ---
        frame_exec = ttk.LabelFrame(self.root, text=" 4. Execution ")
        frame_exec.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.run_btn = ttk.Button(frame_exec, text="Run Pipeline", command=self.run_pipeline, state="disabled")
        self.run_btn.pack(pady=5)
        
        # Log Output Console
        self.log_text = tk.Text(frame_exec, wrap="word", state="disabled", bg="#1e1e1e", fg="#d4d4d4", font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(self.log_text, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

    def browse_project(self):
        folder = filedialog.askdirectory(title="Select Project Root Folder")
        if folder:
            self.project_path.set(folder)
            self.log_message(f"Selected project: {folder}")
            self.run_btn.config(state="disabled")

    def find_uvprojx(self, root_dir):
        for file in Path(root_dir).rglob("*.uvprojx"):
            return str(file.resolve().as_posix())
        return None

    def find_compile_commands(self, root_dir):
        for file in Path(root_dir).rglob("compile_commands.json"):
            # skip docs folder if it already exists
            if "docs" in file.parts:
                continue
            return str(file.resolve().as_posix())
        return None

    def generate_config(self):
        proj_dir = self.project_path.get()
        if not proj_dir:
            messagebox.showwarning("Warning", "Please select a project folder first.")
            return

        proj_path = Path(proj_dir)
        docs_dir = proj_path / "docs"
        logs_dir = proj_path / "logs"

        config = {
            "toolchain": self.toolchain.get(),
            "project_type": self.project_type.get(),
            "log_dir": logs_dir.as_posix(),
            
            # Standard docs paths
            "functions_index": (docs_dir / "functions_index.json").as_posix(),
            "function_categories": (docs_dir / "function_categories.json").as_posix(),
            "call_graph": (docs_dir / "call_graph.json").as_posix(),
            "tasks": (docs_dir / "tasks.json").as_posix(),
            "task_call_graph": (docs_dir / "task_call_graph.json").as_posix(),
            "firmware_ir": (docs_dir / "firmware_ir.json").as_posix(),
            "functions_detail_dir": (docs_dir / "functions_detail").as_posix(),
            "architecture_overview_md": (docs_dir / "ARCHITECTURE_OVERVIEW.md").as_posix()
        }

        # Toolchain specifics
        if self.toolchain.get() == "keil":
            uvprojx = self.find_uvprojx(proj_path)
            if uvprojx:
                config["uvprojx"] = uvprojx
                self.log_message(f"Found .uvprojx: {uvprojx}")
            else:
                config["uvprojx"] = (proj_path / "UNKNOWN.uvprojx").as_posix()
                self.log_message("Warning: No .uvprojx file found.")
        
        elif self.toolchain.get() == "cmake":
            cc_path = self.find_compile_commands(proj_path)
            if cc_path:
                config["compile_commands"] = cc_path
                self.log_message(f"Found compile_commands.json: {cc_path}")
            else:
                config["compile_commands"] = (proj_path / "compile_commands.json").as_posix()
                self.log_message("Warning: No compile_commands.json file found. Firmware Lens graph extraction may fail.")

        # Save config
        self.config_path = proj_path / "config.json"
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
            self.log_message(f"Configuration saved to: {self.config_path}")
            self.run_btn.config(state="normal")
            messagebox.showinfo("Success", "Configuration generated successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config: {e}")
            self.log_message(f"Error saving config: {e}")

    def log_message(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")
        self.root.update_idletasks()

    def run_pipeline(self):
        if not self.config_path or not self.config_path.exists():
            messagebox.showerror("Error", "Config file is missing. Please generate it first.")
            return

        self.run_btn.config(state="disabled")
        self.log_message("\n--- Starting Pipeline ---")
        
        # Determine paths and Python interpreter
        # Se siamo in un eseguibile compilato (PyInstaller)
        is_frozen = getattr(sys, 'frozen', False)
        if is_frozen:
            # sys.executable punterà a run_ui.exe
            exe_path = Path(sys.executable).resolve()
            # Assumiamo che l'exe venga tenuto nella root "firmware-lens" o in "orchestrator/artifact"
            if (exe_path.parent / "orchestrator" / "script" / "run_all.py").exists():
                run_all_script = exe_path.parent / "orchestrator" / "script" / "run_all.py"
            else:
                run_all_script = exe_path.parent.parent / "script" / "run_all.py"
            
            python_exe = "python" # Dobbiamo chiamare python di sistema, non l'exe compilato
        else:
            ui_script_path = Path(__file__).resolve()
            orchestrator_dir = ui_script_path.parent.parent
            run_all_script = orchestrator_dir / "script" / "run_all.py"
            python_exe = sys.executable

        if not run_all_script.exists():
            self.log_message(f"Error: Could not find {run_all_script}")
            self.run_btn.config(state="normal")
            return

        def run_thread():
            cmd = [python_exe, str(run_all_script), "--config", str(self.config_path)]
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )

                for line in iter(process.stdout.readline, ""):
                    # Clean up VT100 escape codes (colors) if any
                    clean_line = line.replace('\x1b', '').replace('[0m', '')
                    self.root.after(0, self.log_message, clean_line.strip())

                process.stdout.close()
                return_code = process.wait()

                if return_code == 0:
                    self.root.after(0, self.log_message, "\n--- Pipeline Finished Successfully ---")
                else:
                    self.root.after(0, self.log_message, f"\n--- Pipeline Failed with code {return_code} ---")

            except Exception as e:
                self.root.after(0, self.log_message, f"\nPipeline exception: {e}")
            finally:
                self.root.after(0, lambda: self.run_btn.config(state="normal"))

        thread = threading.Thread(target=run_thread, daemon=True)
        thread.start()

if __name__ == "__main__":
    root = tk.Tk()
    app = OrchestratorUI(root)
    root.mainloop()
