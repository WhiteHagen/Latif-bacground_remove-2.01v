"""
╔══════════════════════════════════════════════════╗
║         GREEN SCREEN REMOVER  v2.0               ║
║   CHROMA KEY (HSV) Mode + AI (rembg) Mode        ║
╚══════════════════════════════════════════════════╝
Requirements: pip install pillow numpy rembg onnxruntime
"""

import os
import sys
import threading
import multiprocessing
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageFilter
import numpy as np
import io
import time

# Redirection for EXE (no console) to avoid 'NoneType' object has no attribute 'write'
class NullWriter:
    def write(self, text): pass
    def flush(self): pass

if sys.stdout is None: sys.stdout = NullWriter()
if sys.stderr is None: sys.stderr = NullWriter()

# Robust path handling
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Import rembg late or handle session carefully
try:
    from rembg import remove, new_session
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False

# ─── Colors / Theme ──────────────────────────────────────────────────────────
C = {
    "bg0":    "#09090b",   # Main background
    "bg1":    "#111113",   # Panels
    "bg2":    "#1c1c20",   # Cards
    "bg3":    "#26262c",   # Hover / Active
    "border": "#2e2e36",   # Borders
    "green":  "#39ff14",   # Neon accent
    "green2": "#22c55e",   # Darker green
    "green3": "#14532d",   # Active mode background
    "amber":  "#f59e0b",   # Warnings
    "red":    "#ef4444",   # Errors
    "text":   "#f4f4f5",   # Main text
    "muted":  "#71717a",   # Secondary text
    "dim":    "#3f3f46",   # Very dimmed text
}

FONT_TITLE  = ("Consolas", 22, "bold")
FONT_LABEL  = ("Consolas", 10)
FONT_SMALL  = ("Consolas",  9)
FONT_BADGE  = ("Consolas",  8, "bold")
FONT_BTN    = ("Consolas", 12, "bold")
FONT_LOG    = ("Consolas",  9)

EXTENSIONS = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff')

# ─── Logic: HSV Chroma-Key ──────────────────────────────────────────────────
def _remove_chroma(img: Image.Image) -> Image.Image:
    rgba = img.convert("RGBA")
    arr  = np.array(rgba, dtype=np.float32)
    r, g, b = arr[...,0], arr[...,1], arr[...,2]

    cmax  = np.maximum(np.maximum(r, g), b)
    cmin  = np.minimum(np.minimum(r, g), b)
    delta = cmax - cmin + 1e-6

    hue = np.zeros_like(r)
    mg  = (cmax == g);  mb = (cmax == b);  mr = ~mg & ~mb
    hue[mr] = (60 * ((g[mr]-b[mr])/delta[mr]) % 360) / 2
    hue[mg] = (60 * ((b[mg]-r[mg])/delta[mg] + 2)) / 2
    hue[mb] = (60 * ((r[mb]-g[mb])/delta[mb] + 4)) / 2

    sat = np.where(cmax == 0, 0, (delta/cmax)*100)
    val = cmax / 255 * 100

    # Standard green screen masking
    mask = ((hue >= 35)&(hue <= 85)&(sat >= 40)&(val >= 35))

    m_img = Image.fromarray((mask*255).astype(np.uint8))
    for _ in range(4):
        m_img = m_img.filter(ImageFilter.SMOOTH)
    mask = np.array(m_img) > 128

    alpha = arr[...,3].copy()
    alpha[mask] = 0
    out = arr.copy(); out[...,3] = alpha
    return Image.fromarray(out.astype(np.uint8), "RGBA")


def _remove_rembg(img: Image.Image, session=None) -> Image.Image:
    if not REMBG_AVAILABLE:
        raise ImportError("Library 'rembg' is not available.")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    result_bytes = remove(buf.getvalue(), session=session)
    return Image.open(io.BytesIO(result_bytes)).convert("RGBA")


# ─── Custom Canvas Widgets ───────────────────────────────────────────────────
def _rounded_rect(canvas, x1, y1, x2, y2, r, **kw):
    pts = [x1+r,y1, x2-r,y1, x2,y1, x2,y1+r, x2,y2-r, x2,y2,
           x2-r,y2, x1+r,y2, x1,y2, x1,y2-r, x1,y1+r, x1,y1]
    return canvas.create_polygon(pts, smooth=True, **kw)


class NeonButton(tk.Button):
    def __init__(self, parent, text, command, width=340, height=52, **kw):
        super().__init__(parent, text=text, command=command,
                         font=FONT_BTN,
                         bg=C["green"], fg="#000",
                         activebackground=C["green2"], activeforeground="#000",
                         relief="flat", bd=0,
                         padx=20, pady=14,
                         cursor="hand2")

    def set_text(self, t):
        self.config(text=t)

    def set_enabled(self, enabled: bool):
        if enabled:
            self.config(state=tk.NORMAL, bg=C["green"], fg="#000")
        else:
            self.config(state=tk.DISABLED, bg=C["bg3"], fg=C["muted"])


class ProgressBar(tk.Canvas):
    def __init__(self, parent, width=380, height=10, **kw):
        super().__init__(parent, width=width, height=height,
                         bg=C["bg0"], highlightthickness=0, **kw)
        self.p_width = width; self.p_height = height
        self._pct = 0.0
        self._draw()

    def _draw(self):
        self.delete("all")
        _rounded_rect(self, 0, 0, self.p_width, self.p_height, 5,
                      fill=C["bg3"], outline="")
        if self._pct > 0:
            fw = max(10, int(self.p_width * self._pct))
            _rounded_rect(self, 0, 0, fw, self.p_height, 5,
                          fill=C["green"], outline="")

    def set(self, value, maximum):
        self._pct = value / maximum if maximum else 0
        self._draw()

    def reset(self):
        self._pct = 0; self._draw()


# ─── Translations ─────────────────────────────────────────────
TEXTS = {
    "en": {
        "main_title": "Latif Background Remover v2.0",
        "header_title": "LATIF REMOVER",
        "header_subtitle": "background remover v2.0",
        "badge": " AI + CHROMA ",
        "mode_title": "REMOVAL MODE",
        "mode_chroma_title": "⚡  CHROMA KEY",
        "mode_chroma_desc": "HSV masking · ultra fast",
        "mode_ai_title": "🧠  AI  REMBG",
        "mode_ai_desc": "Neural Network · precise",
        "folders_title": "FOLDERS",
        "input_label": "📥  INPUT",
        "output_label": "📤  OUTPUT",
        "files_count": "{} files",
        "btn_run": "▶   REMOVE BG",
        "btn_processing": "⏳  PROCESSING…",
        "status_ready": "Ready to work",
        "status_error_folder": "Folder access error: {}",
        "status_no_files": "No files",
        "status_no_files_msg": "In folder:\n{}\nthere are no images.",
        "log_title": "LOG",
        "log_clear": "clear",
        "log_start": "── START  [{}]  {} file(s) ──",
        "log_ai_loading": "Loading AI model (may take a while)...",
        "log_ai_ok": "AI model loaded successfully.",
        "log_ai_err": "AI model load error: {}",
        "log_fallback": "Trying to switch to CHROMA KEY mode...",
        "log_processing": "Processing: {}...",
        "log_saved": "  ✓  {} - saved",
        "log_error": "  ✗  {}  →  {}",
        "log_end_err": "── END  {}/{} OK  ·  {} errors ──",
        "log_end_ok": "── END  {}/{} files OK ──",
        "msg_err_title": "Finished with errors",
        "msg_err_body": "Processed: {}/{}\nErrors ({}): {}",
        "msg_ok_title": "✅  Done!",
        "msg_ok_body": "Successfully processed {} file(s).",
        "status_done_err": "Finished with {} error(s)",
        "status_done_ok": "Done! Saved {} file(s)",
    }
}

# ─── Main Application Class ───────────────────────────────────────────────────
class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.lang = tk.StringVar(value="en")
        self.root.title(self.t("main_title"))
        self.root.geometry("480x720")
        self.root.resizable(False, False)
        self.root.configure(bg=C["bg0"])
        try:
            self.root.iconbitmap(default="")
        except Exception:
            pass

        # ── State ──
        self.mode     = tk.StringVar(value="chroma")   # "chroma" | "ai"
        self.folder_in = tk.StringVar(value=os.path.join(BASE_DIR, "input"))
        self.folder_out = tk.StringVar(value=os.path.join(BASE_DIR, "output"))
        self._processing = False

        for f in [self.folder_in.get(), self.folder_out.get()]:
            os.makedirs(f, exist_ok=True)

        self._build_ui()
        self._refresh_counter()

    def t(self, key, *args):
        txt = TEXTS["en"].get(key, key)
        if args:
            return txt.format(*args)
        return txt

    # ═══════════════════════════ BUILDING UI ════════════════════════════════

    def _build_ui(self):
        # Clear existing UI
        for widget in self.root.winfo_children():
            widget.destroy()

        outer = tk.Frame(self.root, bg=C["bg0"])
        outer.pack(fill="both", expand=True, padx=20, pady=20)

        self._header(outer)
        self._separator(outer, top=12, bottom=14)
        self._mode_toggle(outer)
        self._separator(outer, top=14, bottom=14)
        self._folders(outer)
        self._separator(outer, top=14, bottom=14)
        self._action_section(outer)
        self._separator(outer, top=14, bottom=10)
        self._log_area(outer)

    # ── Header ─────────────────────────────────────────────────────────────
    def _header(self, parent):
        f = tk.Frame(parent, bg=C["bg0"])
        f.pack(fill="x")

        # Icon — green square with square icon
        ico = tk.Canvas(f, width=40, height=40, bg=C["bg0"],
                        highlightthickness=0)
        ico.pack(side="left", padx=(0,12))
        _rounded_rect(ico, 2, 2, 38, 38, 6, fill=C["green3"], outline=C["green2"])
        ico.create_text(20, 20, text="⬜", font=("Segoe UI Emoji",16), fill=C["green"])

        title_f = tk.Frame(f, bg=C["bg0"])
        title_f.pack(side="left")
        tk.Label(title_f, text="LATIF", font=("Consolas",18,"bold"),
                 bg=C["bg0"], fg=C["green"]).pack(anchor="w")
        tk.Label(title_f, text="background remover v2.0", font=("Consolas",10),
                 bg=C["bg0"], fg=C["muted"]).pack(anchor="w")

        # Badge
        right_f = tk.Frame(f, bg=C["bg0"])
        right_f.pack(side="right")

        badge = tk.Frame(right_f, bg=C["bg3"])
        badge.pack(side="right", padx=(0,2))
        tk.Label(badge, text=self.t("badge"), font=FONT_BADGE,
                 bg=C["bg3"], fg=C["green2"], padx=6, pady=3).pack()

    # ── Separator ────────────────────────────────────────────────────────────
    def _separator(self, parent, top=8, bottom=8):
        f = tk.Frame(parent, bg=C["bg0"])
        f.pack(fill="x", pady=(top, bottom))
        tk.Frame(f, height=1, bg=C["border"]).pack(fill="x")

    # ── Mode Toggle ─────────────────────────────────────────────────────────
    def _mode_toggle(self, parent):
        tk.Label(parent, text=self.t("mode_title"),
                 font=FONT_SMALL, bg=C["bg0"], fg=C["muted"]).pack(anchor="w")

        f = tk.Frame(parent, bg=C["bg2"], pady=4)
        f.pack(fill="x", pady=(6,0))

        # Left Panel — CHROMA
        self._btn_chroma = self._mode_card(
            f, "chroma",
            self.t("mode_chroma_title"),
            self.t("mode_chroma_desc"),
            side="left"
        )
        # Right Panel — AI
        self._btn_ai = self._mode_card(
            f, "ai",
            self.t("mode_ai_title"),
            self.t("mode_ai_desc"),
            side="left"
        )
        self._update_mode_ui()

    def _mode_card(self, parent, value, title, desc, side):
        f = tk.Frame(parent, bg=C["bg2"], cursor="hand2",
                     pady=10, padx=16)
        f.pack(side=side, expand=True, fill="both", padx=4)

        t = tk.Label(f, text=title, font=("Consolas",10,"bold"),
                     bg=C["bg2"], fg=C["text"])
        t.pack(anchor="w")
        d = tk.Label(f, text=desc, font=FONT_SMALL,
                     bg=C["bg2"], fg=C["muted"])
        d.pack(anchor="w")

        for w in [f, t, d]:
            w.bind("<Button-1>", lambda _, v=value: self._select_mode(v))

        return {"frame": f, "title": t, "desc": d}

    def _select_mode(self, v):
        self.mode.set(v)
        self._update_mode_ui()

    def _update_mode_ui(self):
        for key, cfg in [("chroma", self._btn_chroma), ("ai", self._btn_ai)]:
            active = self.mode.get() == key
            bg   = C["green3"]  if active else C["bg2"]
            fg_t = C["green"]   if active else C["text"]
            fg_d = C["green2"]  if active else C["muted"]
            cfg["frame"].configure(bg=bg)
            cfg["title"].configure(bg=bg, fg=fg_t)
            cfg["desc"].configure(bg=bg,  fg=fg_d)

    # ── Folders ───────────────────────────────────────────────────────────────
    def _folders(self, parent):
        tk.Label(parent, text=self.t("folders_title"),
                 font=FONT_SMALL, bg=C["bg0"], fg=C["muted"]).pack(anchor="w")

        self._folder_row(parent, self.t("input_label"), self.folder_in, "in", top=6)
        self._folder_row(parent, self.t("output_label"), self.folder_out, "out", top=6)

    def _folder_row(self, parent, label, variable, tag, top=4):
        row = tk.Frame(parent, bg=C["bg2"])
        row.pack(fill="x", pady=(top,0))

        # Label
        lbl = tk.Label(row, text=label, font=FONT_SMALL,
                       bg=C["bg2"], fg=C["muted"], width=15, anchor="w",
                       padx=8, pady=8)
        lbl.pack(side="left")

        # Path
        path_lbl = tk.Label(row, textvariable=variable, font=FONT_SMALL,
                            bg=C["bg2"], fg=C["text"], anchor="w")
        path_lbl.pack(side="left", fill="x", expand=True)

        # Change Button
        btn = tk.Label(row, text=" … ", font=FONT_BADGE,
                       bg=C["bg3"], fg=C["green2"], padx=6, cursor="hand2")
        btn.pack(side="right", padx=6, pady=6)
        btn.bind("<Button-1>", lambda _, z=variable, t=tag: self._select_folder(z, t))

        # File Counter (Input only)
        if tag == "in":
            self._lbl_counter = tk.Label(row, text=self.t("files_count", 0),
                                         font=FONT_BADGE, bg=C["bg2"],
                                         fg=C["muted"], padx=8)
            self._lbl_counter.pack(side="right")

    def _select_folder(self, variable, tag):
        path = filedialog.askdirectory(initialdir=variable.get())
        if path:
            variable.set(os.path.abspath(path))
            if tag == "in":
                self._refresh_counter()

    def _refresh_counter(self):
        try:
            files = [f for f in os.listdir(self.folder_in.get())
                     if f.lower().endswith(EXTENSIONS)]
            n = len(files)
            color = C["green2"] if n > 0 else C["muted"]
            self._lbl_counter.config(text=self.t("files_count", n), fg=color)
        except Exception:
            if hasattr(self, "_lbl_counter"):
                self._lbl_counter.config(text="—", fg=C["muted"])

    # ── Action Section ─────────────────────────────────────────────────────────
    def _action_section(self, parent):
        # Big Button
        self._btn_main = NeonButton(
            parent,
            text=self.t("btn_run"),
            command=self._start_processing
        )
        self._btn_main.pack(pady=(0, 12))

        # Progress Bar
        prog_f = tk.Frame(parent, bg=C["bg0"])
        prog_f.pack(fill="x")
        self._progress_bar = ProgressBar(prog_f, width=440, height=8)
        self._progress_bar.pack()

        # Status
        status_f = tk.Frame(parent, bg=C["bg0"])
        status_f.pack(fill="x", pady=(6,0))
        self._lbl_status = tk.Label(
            status_f, text=self.t("status_ready"),
            font=FONT_SMALL, bg=C["bg0"], fg=C["muted"], anchor="w"
        )
        self._lbl_status.pack(side="left")
        self._lbl_counter2 = tk.Label(
            status_f, text="",
            font=FONT_SMALL, bg=C["bg0"], fg=C["green2"], anchor="e"
        )
        self._lbl_counter2.pack(side="right")

    # ── Log Area ─────────────────────────────────────────────────────────────
    def _log_area(self, parent):
        header = tk.Frame(parent, bg=C["bg0"])
        header.pack(fill="x")
        tk.Label(header, text=self.t("log_title"), font=FONT_SMALL,
                 bg=C["bg0"], fg=C["muted"]).pack(side="left")
        clr = tk.Label(header, text=self.t("log_clear"), font=FONT_SMALL,
                       bg=C["bg0"], fg=C["dim"], cursor="hand2")
        clr.pack(side="right")
        clr.bind("<Button-1>", lambda _: self._clear_log())

        log_frame = tk.Frame(parent, bg=C["bg1"], pady=2)
        log_frame.pack(fill="both", expand=True, pady=(6,0))

        sb = tk.Scrollbar(log_frame, bg=C["bg1"],
                          troughcolor=C["bg1"], bd=0)
        sb.pack(side="right", fill="y")

        self._log = tk.Text(
            log_frame,
            font=FONT_LOG, bg=C["bg1"], fg=C["muted"],
            insertbackground=C["text"],
            relief="flat", bd=0, padx=10, pady=8,
            state="disabled", height=8,
            yscrollcommand=sb.set
        )
        self._log.pack(fill="both", expand=True)
        sb.config(command=self._log.yview)

        # Color tags
        self._log.tag_config("ok",    foreground=C["green2"])
        self._log.tag_config("err",   foreground=C["red"])
        self._log.tag_config("info",  foreground=C["muted"])
        self._log.tag_config("head",  foreground=C["green"])

    def _log_add(self, text, tag="info"):
        def _append():
            self._log.configure(state="normal")
            self._log.insert("end", text + "\n", tag)
            self._log.see("end")
            self._log.configure(state="disabled")
        self.root.after(0, _append)

    def _clear_log(self):
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")

    # ═══════════════════════════ MAIN LOGIC ════════════════════════════════

    def _start_processing(self):
        if self._processing:
            return
        t = threading.Thread(target=self._worker_thread, daemon=True)
        t.start()

    def _worker_thread(self):
        folder_in = self.folder_in.get()
        folder_out = self.folder_out.get()
        mode      = self.mode.get()

        try:
            files = [f for f in os.listdir(folder_in)
                     if f.lower().endswith(EXTENSIONS)]
        except Exception as e:
            self._log_add(self.t("status_error_folder", str(e)), "err")
            return

        if not files:
            messagebox.showinfo(
                self.t("status_no_files"),
                self.t("status_no_files_msg", folder_in)
            )
            return

        # UI Lock
        self._processing = True
        self.root.after(0, lambda: self._btn_main.set_enabled(False))
        self.root.after(0, lambda: self._btn_main.set_text(self.t("btn_processing")))

        os.makedirs(folder_out, exist_ok=True)

        mode_label = "CHROMA KEY" if mode == "chroma" else "AI · rembg"
        self._log_add(self.t("log_start", mode_label, len(files)), "head")

        session = None
        if mode == "ai" and REMBG_AVAILABLE:
            self._log_add(self.t("log_ai_loading"), "info")
            try:
                session = new_session()
                self._log_add(self.t("log_ai_ok"), "ok")
            except Exception as e:
                self._log_add(self.t("log_ai_err", str(e)), "err")
                mode = "chroma" # Fallback
                self._log_add(self.t("log_fallback"), "amber")

        errors = []
        for i, file_name in enumerate(files, 1):
            # UI Update
            self.root.after(0, lambda i=i, fn=file_name: self._lbl_status.config(
                text=f"[{i}/{len(files)}]  {fn}", fg=C["text"]
            ))
            self.root.after(0, lambda i=i: self._lbl_counter2.config(text=f"{i}/{len(files)}"))
            self.root.after(0, lambda i=i: self._progress_bar.set(i-1, len(files)))

            path_in = os.path.join(folder_in, file_name)
            path_out = os.path.join(folder_out,
                                      os.path.splitext(file_name)[0] + ".png")
            try:
                self._log_add(self.t("log_processing", file_name), "info")
                img = Image.open(path_in)

                if mode == "chroma":
                    result = _remove_chroma(img)
                else:
                    result = _remove_rembg(img, session=session)

                result.save(path_out, "PNG")
                self._log_add(self.t("log_saved", file_name), "ok")

            except Exception as e:
                errors.append(file_name)
                self._log_add(self.t("log_error", file_name, str(e)), "err")

            self.root.after(0, lambda i=i: self._progress_bar.set(i, len(files)))

        # UI Unlock
        self._processing = False
        self.root.after(0, lambda: self._btn_main.set_enabled(True))
        self.root.after(0, lambda: self._btn_main.set_text(self.t("btn_run")))
        self.root.after(0, self._refresh_counter)
        self.root.after(0, lambda: self._lbl_counter2.config(text=""))

        ok_count = len(files) - len(errors)
        if errors:
            self.root.after(0, lambda: self._lbl_status.config(
                text=self.t("status_done_err", len(errors)), fg=C["amber"]
            ))
            self._log_add(
                self.t("log_end_err", ok_count, len(files), len(errors)),
                "err"
            )
            messagebox.showwarning(
                self.t("msg_err_title"),
                self.t("msg_err_body", ok_count, len(files), len(errors), ', '.join(errors))
            )
        else:
            self.root.after(0, lambda: self._lbl_status.config(
                text=self.t("status_done_ok", ok_count), fg=C["green2"]
            ))
            self._log_add(
                self.t("log_end_ok", ok_count, len(files)), "head"
            )
            messagebox.showinfo(self.t("msg_ok_title"), self.t("msg_ok_body", ok_count))


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    multiprocessing.freeze_support()
    root = tk.Tk()
    App(root)
    root.mainloop()
