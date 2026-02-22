"""
Mouse Trail Launcher - GUI to configure and start the mouse trail server.
Double-click this file to open. (.pyw = no console window)
"""

import tkinter as tk
from tkinter import ttk, colorchooser
import subprocess
import sys
import os
from urllib.parse import urlparse, parse_qs

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OVERLAY_PATH = os.path.join(SCRIPT_DIR, "overlay.html")
SERVER_PATH = os.path.join(SCRIPT_DIR, "mouse_server.py")


class LauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Mouse Trail")
        self.root.resizable(False, False)
        self.root.configure(bg="#1a1a2e")
        self.server_proc = None

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#1a1a2e")
        style.configure("TLabel", background="#1a1a2e", foreground="#e0e0e0", font=("Segoe UI", 10))
        style.configure("Header.TLabel", background="#1a1a2e", foreground="#00ffaa", font=("Segoe UI", 14, "bold"))
        style.configure("Sub.TLabel", background="#1a1a2e", foreground="#888", font=("Segoe UI", 8))
        style.configure("TButton", font=("Segoe UI", 10))
        style.configure("Start.TButton", font=("Segoe UI", 12, "bold"))
        style.configure("TCombobox", font=("Segoe UI", 10))
        style.configure("TLabelframe", background="#1a1a2e", foreground="#00ffaa", font=("Segoe UI", 10, "bold"))
        style.configure("TLabelframe.Label", background="#1a1a2e", foreground="#00ffaa")

        pad = {"padx": 8, "pady": 3}
        main = ttk.Frame(root)
        main.pack(padx=16, pady=12)

        # --- Header ---
        ttk.Label(main, text="Mouse Trail for OBS", style="Header.TLabel").pack(anchor="w")
        ttk.Label(main, text="Uses Raw Input API \u2014 works in all games, no configuration needed",
                  style="Sub.TLabel").pack(anchor="w", pady=(0, 8))

        # --- Server settings ---
        srv = ttk.LabelFrame(main, text="Server")
        srv.pack(fill="x", **pad)

        ttk.Label(srv, text="Port:").grid(row=0, column=0, sticky="w", **pad)
        self.port_var = tk.StringVar(value="8765")
        ttk.Entry(srv, textvariable=self.port_var, width=8).grid(row=0, column=1, sticky="w", **pad)

        # --- Overlay settings ---
        ovl = ttk.LabelFrame(main, text="Overlay Appearance")
        ovl.pack(fill="x", **pad)

        r = 0
        ttk.Label(ovl, text="Color:").grid(row=r, column=0, sticky="w", **pad)
        self.color_var = tk.StringVar(value="#00ffaa")
        self.color_btn = tk.Button(ovl, bg="#00ffaa", width=4, relief="solid", bd=1,
                                   command=self._pick_color)
        self.color_btn.grid(row=r, column=1, sticky="w", **pad)

        ttk.Label(ovl, text="Width:").grid(row=r, column=2, sticky="w", **pad)
        self.width_var = tk.IntVar(value=3)
        ttk.Scale(ovl, from_=1, to=20, variable=self.width_var, orient="horizontal",
                  length=100).grid(row=r, column=3, sticky="w", **pad)

        r += 1
        ttk.Label(ovl, text="Opacity:").grid(row=r, column=0, sticky="w", **pad)
        self.opacity_var = tk.IntVar(value=80)
        ttk.Scale(ovl, from_=1, to=100, variable=self.opacity_var, orient="horizontal",
                  length=100).grid(row=r, column=1, sticky="w", **pad)

        ttk.Label(ovl, text="Glow:").grid(row=r, column=2, sticky="w", **pad)
        self.glow_var = tk.IntVar(value=6)
        ttk.Scale(ovl, from_=0, to=30, variable=self.glow_var, orient="horizontal",
                  length=100).grid(row=r, column=3, sticky="w", **pad)

        r += 1
        ttk.Label(ovl, text="Fade (s):").grid(row=r, column=0, sticky="w", **pad)
        self.fade_var = tk.IntVar(value=5)
        ttk.Scale(ovl, from_=0, to=30, variable=self.fade_var, orient="horizontal",
                  length=100).grid(row=r, column=1, sticky="w", **pad)

        ttk.Label(ovl, text="Scale:").grid(row=r, column=2, sticky="w", **pad)
        self.scale_var = tk.IntVar(value=100)
        ttk.Scale(ovl, from_=10, to=300, variable=self.scale_var, orient="horizontal",
                  length=100).grid(row=r, column=3, sticky="w", **pad)

        r += 1
        ttk.Label(ovl, text="Camera:").grid(row=r, column=0, sticky="w", **pad)
        self.cam_var = tk.IntVar(value=40)
        ttk.Scale(ovl, from_=1, to=100, variable=self.cam_var, orient="horizontal",
                  length=100).grid(row=r, column=1, sticky="w", **pad)

        r += 1
        ttk.Label(ovl, text="Preset:").grid(row=r, column=0, sticky="w", **pad)
        self.preset_var = tk.StringVar(value="neon")
        preset_cb = ttk.Combobox(ovl, textvariable=self.preset_var, values=["neon", "pen"],
                                 state="readonly", width=8)
        preset_cb.grid(row=r, column=1, sticky="w", **pad)

        r += 1
        self.dim_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(ovl, text="Dim Trail", variable=self.dim_var).grid(
            row=r, column=0, columnspan=2, sticky="w", **pad)
        self.instafade_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(ovl, text="Instafade", variable=self.instafade_var).grid(
            row=r, column=2, columnspan=2, sticky="w", **pad)

        r += 1
        self.cursor_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(ovl, text="Cursor Only", variable=self.cursor_var).grid(
            row=r, column=0, columnspan=2, sticky="w", **pad)
        self.endpts_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(ovl, text="Endpoints", variable=self.endpts_var).grid(
            row=r, column=2, columnspan=2, sticky="w", **pad)

        r += 1
        self.arrow_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(ovl, text="Arrow", variable=self.arrow_var).grid(
            row=r, column=0, columnspan=2, sticky="w", **pad)

        # --- OBS Path ---
        obs = ttk.LabelFrame(main, text="OBS Browser Source URL  (click to copy)")
        obs.pack(fill="x", **pad)

        self.obs_path_var = tk.StringVar()
        self.obs_entry = tk.Entry(obs, textvariable=self.obs_path_var, font=("Consolas", 9),
                                  fg="#00ffaa", bg="#111", readonlybackground="#111",
                                  relief="flat", state="readonly", cursor="hand2")
        self.obs_entry.pack(fill="x", padx=8, pady=6, ipady=4)
        self.obs_entry.bind("<Button-1>", self._copy_obs_path)

        self.copy_label = ttk.Label(obs, text="", style="Sub.TLabel")
        self.copy_label.pack(anchor="e", padx=8)

        self._update_obs_path()

        # Rebuild OBS path when any setting changes
        for var in [self.port_var, self.color_var, self.width_var, self.opacity_var,
                    self.glow_var, self.fade_var, self.scale_var, self.cam_var,
                    self.preset_var, self.dim_var, self.instafade_var,
                    self.cursor_var, self.endpts_var, self.arrow_var]:
            var.trace_add("write", lambda *_: self._update_obs_path())

        # --- Buttons ---
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill="x", pady=(8, 0))

        self.start_btn = ttk.Button(btn_frame, text="Start Server", style="Start.TButton",
                                    command=self._toggle_server)
        self.start_btn.pack(side="left", padx=4)

        ttk.Button(btn_frame, text="Import URL", command=self._import_url).pack(side="left", padx=4)

        self.status_label = ttk.Label(btn_frame, text="stopped", foreground="#ff5555")
        self.status_label.pack(side="left", padx=12)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _pick_color(self):
        color = colorchooser.askcolor(color=self.color_var.get(), title="Trail Color")
        if color[1]:
            self.color_var.set(color[1])
            self.color_btn.configure(bg=color[1])

    def _build_overlay_url(self):
        path = OVERLAY_PATH.replace("\\", "/")
        base = f"file:///{path}"

        params = [
            f"port={self.port_var.get()}",
            f"color={self.color_var.get().lstrip('#')}",
            f"width={self.width_var.get()}",
            f"opacity={self.opacity_var.get()}",
            f"fade={self.fade_var.get()}",
            f"glow={self.glow_var.get()}",
            f"scale={self.scale_var.get()}",
            f"cam={self.cam_var.get()}",
            f"preset={self.preset_var.get()}",
        ]
        if self.dim_var.get():       params.append("dim=1")
        if self.instafade_var.get(): params.append("instafade=1")
        if self.cursor_var.get():    params.append("cursor=1")
        if self.endpts_var.get():    params.append("endpts=1")
        if self.arrow_var.get():     params.append("arrow=1")
        params.append("hideui=1")
        return base + "?" + "&".join(params)

    def _update_obs_path(self):
        self.obs_path_var.set(self._build_overlay_url())

    def _copy_obs_path(self, event=None):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.obs_path_var.get())
        self.copy_label.configure(text="Copied!", foreground="#00ffaa")
        self.root.after(1500, lambda: self.copy_label.configure(text=""))

    def _import_url(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Import URL")
        dlg.configure(bg="#1a1a2e")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        ttk.Label(dlg, text="Paste an OBS Browser Source URL:").pack(padx=12, pady=(12, 4), anchor="w")

        url_entry = tk.Entry(dlg, font=("Consolas", 9), fg="#00ffaa", bg="#111",
                             insertbackground="#00ffaa", width=70)
        url_entry.pack(padx=12, pady=4, fill="x")

        # Pre-fill from clipboard if it looks like a relevant URL
        try:
            clip = self.root.clipboard_get()
            if "overlay.html" in clip:
                url_entry.insert(0, clip)
        except Exception:
            pass

        status = ttk.Label(dlg, text="", style="Sub.TLabel")
        status.pack(padx=12, anchor="w")

        def apply():
            url = url_entry.get().strip()
            if not url:
                return
            try:
                self._apply_url_params(url)
                dlg.destroy()
            except Exception as e:
                status.configure(text=f"Error: {e}", foreground="#ff5555")

        bf = ttk.Frame(dlg)
        bf.pack(padx=12, pady=(4, 12), fill="x")
        ttk.Button(bf, text="Import", command=apply).pack(side="right", padx=4)
        ttk.Button(bf, text="Cancel", command=dlg.destroy).pack(side="right", padx=4)

        url_entry.focus_set()
        dlg.bind("<Return>", lambda e: apply())
        dlg.bind("<Escape>", lambda e: dlg.destroy())

    def _apply_url_params(self, url):
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=True)

        def get(key):
            vals = params.get(key)
            return vals[0] if vals else None

        if get("port"):
            self.port_var.set(get("port"))
        if get("color"):
            color = "#" + get("color").lstrip("#")
            self.color_var.set(color)
            self.color_btn.configure(bg=color)
        if get("width"):
            self.width_var.set(int(get("width")))
        if get("opacity"):
            self.opacity_var.set(int(get("opacity")))
        if get("glow"):
            self.glow_var.set(int(get("glow")))
        if get("fade"):
            self.fade_var.set(int(get("fade")))
        if get("scale"):
            self.scale_var.set(int(get("scale")))
        if get("cam"):
            self.cam_var.set(int(get("cam")))
        if get("preset"):
            self.preset_var.set(get("preset"))

        # Boolean flags: present with "1" = true, otherwise false
        self.dim_var.set(get("dim") == "1")
        self.instafade_var.set(get("instafade") == "1")
        self.cursor_var.set(get("cursor") == "1")
        self.endpts_var.set(get("endpts") == "1")
        self.arrow_var.set(get("arrow") == "1")

    def _toggle_server(self):
        if self.server_proc and self.server_proc.poll() is None:
            self.server_proc.terminate()
            self.server_proc = None
            self.start_btn.configure(text="Start Server")
            self.status_label.configure(text="stopped", foreground="#ff5555")
            return

        cmd = [sys.executable, SERVER_PATH, "--port", self.port_var.get()]

        try:
            self.server_proc = subprocess.Popen(
                cmd, creationflags=subprocess.CREATE_NO_WINDOW
            )
            self.start_btn.configure(text="Stop Server")
            self.status_label.configure(
                text=f"running on :{self.port_var.get()}", foreground="#00ffaa"
            )
        except Exception as e:
            self.status_label.configure(text=f"error: {e}", foreground="#ff5555")

    def _on_close(self):
        if self.server_proc and self.server_proc.poll() is None:
            self.server_proc.terminate()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = LauncherApp(root)
    root.mainloop()
