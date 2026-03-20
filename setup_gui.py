import os
import sys
import subprocess
import threading
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Settings
APP_NAME = "Latif Background Remover v2.0.1"
AUTHOR = "OmniCode / Czan"
DEFAULT_INSTALL_DIR = os.path.join(os.environ.get("ProgramFiles", "C:\\"), "Latif Background Remover")
REQUIRED_FILES = ["GreenScreenRemover.exe", "app.py", "requirements.txt", "START.bat", "LICENSE"]
LICENSE_FILE = "LICENSE"

LICENSE_TEXT = """MIT License

Copyright (c) 2026 OmniCode / "Czan"

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

ATTRIBUTION:
- Original Repository: https://github.com/WhiteHagen
- Company: OmniCode
- Author: "Czan"

DEPENDENCIES:
This software uses the following libraries:
- Python (Programming Language)
- Pillow (Image processing)
- NumPy (Numerical processing)
- rembg (Background removal using AI)
- onnxruntime (Inference engine for AI)
- Tkinter (GUI Framework)

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

class SetupApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Setup - {APP_NAME}")
        self.geometry("600x450")
        self.resizable(False, False)
        self.configure(bg="#09090b")
        
        self.install_path = tk.StringVar(value=DEFAULT_INSTALL_DIR)
        self.current_step = 0
        
        # Styles
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure("TFrame", background="#09090b")
        style.configure("TLabel", background="#09090b", foreground="#f4f4f5", font=("Consolas", 10))
        style.configure("Title.TLabel", font=("Consolas", 18, "bold"), foreground="#39ff14")
        style.configure("TButton", font=("Consolas", 10, "bold"), padding=10)
        style.configure("TProgressbar", thickness=20)
        
        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.show_welcome()

    def clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def show_welcome(self):
        self.clear_container()
        ttk.Label(self.container, text=APP_NAME, style="Title.TLabel").pack(pady=(0, 10))
        ttk.Label(self.container, text=f"Welcome to the {APP_NAME} installer.\n\nThis program is used to remove backgrounds from images using Chroma Key and AI methods.\n\nAuthor: {AUTHOR}").pack(pady=10)
        
        # License box
        license_frame = ttk.Frame(self.container)
        license_frame.pack(fill="both", expand=True, pady=10)
        
        self.license_text = tk.Text(license_frame, height=10, bg="#111113", fg="#f4f4f5", font=("Consolas", 9), relief="flat")
        self.license_text.pack(side="left", fill="both", expand=True)
        
        # Use embedded license text
        self.license_text.insert("1.0", LICENSE_TEXT)
        self.license_text.config(state="disabled")
        
        scroll = ttk.Scrollbar(license_frame, command=self.license_text.yview)
        scroll.pack(side="right", fill="y")
        self.license_text.config(yscrollcommand=scroll.set)
        
        btn_frame = ttk.Frame(self.container)
        btn_frame.pack(fill="x", pady=(10, 0))
        ttk.Button(btn_frame, text="Next", command=self.show_path_selection).pack(side="right")


    def show_path_selection(self):
        self.clear_container()
        ttk.Label(self.container, text="Select Installation Location", style="Title.TLabel").pack(pady=(0, 20))
        ttk.Label(self.container, text="The program will be installed in the following folder:").pack(pady=5, anchor="w")
        
        path_frame = ttk.Frame(self.container)
        path_frame.pack(fill="x", pady=10)
        
        ttk.Entry(path_frame, textvariable=self.install_path).pack(side="left", fill="x", expand=True, padx=(0, 10))
        ttk.Button(path_frame, text="Browse...", command=self.browse_path).pack(side="right")
        
        btn_frame = ttk.Frame(self.container)
        btn_frame.pack(side="bottom", fill="x", pady=(20, 0))
        ttk.Button(btn_frame, text="Install", command=self.start_installation).pack(side="right")
        ttk.Button(btn_frame, text="Back", command=self.show_welcome).pack(side="left")

    def browse_path(self):
        path = filedialog.askdirectory(initialdir=self.install_path.get())
        if path:
            self.install_path.set(os.path.join(path, "Latif Background Remover"))

    def start_installation(self):
        self.clear_container()
        ttk.Label(self.container, text="Installation in progress...", style="Title.TLabel").pack(pady=(0, 20))
        
        self.progress_msg = tk.StringVar(value="Preparing...")
        ttk.Label(self.container, textvariable=self.progress_msg).pack(pady=5)
        
        self.progress = ttk.Progressbar(self.container, mode="determinate")
        self.progress.pack(fill="x", pady=10)
        
        self.log_text = tk.Text(self.container, height=10, bg="#111113", fg="#71717a", font=("Consolas", 8), relief="flat")
        self.log_text.pack(fill="both", expand=True, pady=10)
        self.log_text.config(state="disabled")

        threading.Thread(target=self.run_install, daemon=True).start()

    def log(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def run_install(self):
        try:
            # Check if Python is available in PATH
            try:
                subprocess.run(["python", "--version"], capture_output=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            except (subprocess.CalledProcessError, FileNotFoundError):
                self.log("ERROR: Python not found in PATH. Please install Python 3.x and ensure it's in your PATH.")
                messagebox.showerror("Installation Error", "Python not found. Please install Python 3.x from python.org before running this installer.")
                return

            # Determine source directory
            base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            
            dest = self.install_path.get()
            self.log(f"Creating folder: {dest}")
            os.makedirs(dest, exist_ok=True)
            os.makedirs(os.path.join(dest, "input"), exist_ok=True)
            os.makedirs(os.path.join(dest, "output"), exist_ok=True)
            
            # Copy files
            files_to_copy = REQUIRED_FILES
            total_steps = len(files_to_copy) + 4
            current_step = 1
            
            for file in files_to_copy:
                src_file = os.path.join(base_path, file)
                if os.path.exists(src_file):
                    self.progress_msg.set(f"Copying: {file}")
                    self.log(f"Copying {file}...")
                    shutil.copy2(src_file, os.path.join(dest, file))
                else:
                    self.log(f"ERROR: Source file {file} not found in {base_path}")
                
                current_step += 1
                self._update_progress(current_step, total_steps)

            # --- Pip Upgrade ---
            self.progress_msg.set("Upgrading pip...")
            self.log("Running: python -m pip install --upgrade pip")
            self._execute_with_log(["python", "-m", "pip", "install", "--upgrade", "pip", "--quiet"])
            
            current_step += 1
            self._update_progress(current_step, total_steps)
            
            # --- Requirements Installation ---
            self.progress_msg.set("Installing libraries (this may take a while)...")
            self.log("Running: pip install -r requirements.txt")
            self._execute_with_log(["python", "-m", "pip", "install", "-r", os.path.join(dest, "requirements.txt"), "--progress-bar", "on"])

            current_step += 1
            self._update_progress(current_step, total_steps)

            # --- AI Models Download ---
            self.progress_msg.set("Downloading AI Neural Networks (this may take several minutes)...")
            self.log("Initializing AI models download (approx. 500MB+)...")
            
            download_script = """
import rembg
import os
import time
import logging
import sys

# Force pooch (used by rembg) to update progress bars even without a TTY
os.environ['POOCH_PROGRESSBAR'] = '1'

models = ['u2net', 'u2netp', 'u2net_human_seg', 'isnet-general-use', 'silueta']
for model in models:
    try:
        print(f'\\n[MODEL: {model}]')
        start_t = time.time()
        # Triggering download via new_session. 
        # Pooch/tqdm will print progress bars to stderr/stdout which we capture.
        rembg.new_session(model)
        elapsed = time.time() - start_t
        print(f'DONE: {model} ready in {elapsed:.1f}s.')
    except Exception as e:
        print(f'ERROR: Could not download {model}: {e}')

print('\\nALL AI MODELS ARE READY.')
"""
            self._execute_with_log(["python", "-u", "-c", download_script])

            current_step += 1
            self._update_progress(current_step, total_steps)
            
            self.progress_msg.set("Installation completed successfully!")
            self.log("Installation ready.")
            self.after(500, self.show_finished)
            
        except Exception as e:
            self.log(f"CRITICAL ERROR: {str(e)}")
            messagebox.showerror("Installation Error", f"An error occurred: {str(e)}")

    def _update_progress(self, current, total):
        pct = (current / total) * 100
        self.after(0, lambda: self.progress.configure(value=pct))
        self.update_idletasks()

    def _execute_with_log(self, cmd):
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                       text=True, bufsize=1, creationflags=subprocess.CREATE_NO_WINDOW)
            
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    clean_line = line.strip()
                    if clean_line:
                        self.log(clean_line)
                        if "%" in clean_line and ("/" in clean_line or "it/s" in clean_line):
                            self.progress_msg.set(f"Working... {clean_line[:40]}")
            
            return process.poll()
        except Exception as e:
            self.log(f"Process error: {str(e)}")
            return -1

    def show_finished(self):
        self.clear_container()
        ttk.Label(self.container, text="Done!", style="Title.TLabel").pack(pady=(0, 20))
        ttk.Label(self.container, text=f"Program {APP_NAME} has been successfully installed.\n\nYou can now close the installer and run the program using the icon or GreenScreenRemover.exe.").pack(pady=10)
        
        btn_frame = ttk.Frame(self.container)
        btn_frame.pack(side="bottom", fill="x", pady=(20, 0))
        ttk.Button(btn_frame, text="Finish", command=self.destroy).pack(side="right")
        ttk.Button(btn_frame, text="Run Now", command=self.run_app).pack(side="left")

    def run_app(self):
        dest = self.install_path.get()
        exe_path = os.path.join(dest, "GreenScreenRemover.exe")
        if os.path.exists(exe_path):
            subprocess.Popen([exe_path], cwd=dest)
        self.destroy()

if __name__ == "__main__":
    app = SetupApp()
    app.mainloop()
