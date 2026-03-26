"""
pip_manager.py  —  A sleek CustomTkinter pip GUI
Includes a pre-flight checker that auto-installs customtkinter if missing.
"""

# ── Pre-flight checker ───────────────────────────────────────────────────────
import sys
import subprocess


def _precheck():
    """Ensure all required packages are present before launching the GUI."""
    required = {"customtkinter": "customtkinter"}
    missing = []

    for import_name, pip_name in required.items():
        try:
            __import__(import_name)
        except ImportError:
            missing.append((import_name, pip_name))

    if missing:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        names = ", ".join(p for _, p in missing)
        ok = messagebox.askyesno(
            "Missing Dependencies",
            f"The following package(s) are required but not installed:\n\n"
            f"  {names}\n\n"
            f"Install them now using pip?",
            parent=root,
        )
        root.destroy()

        if not ok:
            print("Aborted — missing dependencies.")
            sys.exit(1)

        print(f"Installing: {names} ...")
        for _, pip_name in missing:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", pip_name],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                import tkinter as tk
                from tkinter import messagebox
                r2 = tk.Tk()
                r2.withdraw()
                messagebox.showerror(
                    "Install Failed",
                    f"Failed to install '{pip_name}'.\n\n{result.stderr[:400]}",
                )
                r2.destroy()
                sys.exit(1)
            print(f"  installed: {pip_name}")

    if sys.version_info < (3, 8):
        import tkinter as tk
        from tkinter import messagebox
        r = tk.Tk()
        r.withdraw()
        messagebox.showerror(
            "Python Too Old",
            f"Python 3.8+ is required.\nYou have {sys.version}",
        )
        r.destroy()
        sys.exit(1)


_precheck()

# ── Main app ─────────────────────────────────────────────────────────────────
import json
import threading
import urllib.request
import urllib.parse
import urllib.error

import customtkinter as ctk
from tkinter import messagebox

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BG       = "#0b0d12"
SURFACE  = "#13161f"
SURFACE2 = "#1a1e2e"
SURFACE3 = "#222640"
ACCENT   = "#4f8ef7"
ACCENT_H = "#6fa8ff"
MINT     = "#56d9a0"
DANGER   = "#f87171"
TEXT     = "#dde4f5"
TEXT_DIM = "#5a6180"
BORDER   = "#252a3a"


def run_pip(*args):
    cmd = [sys.executable, "-m", "pip", *args, "--no-color"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


class PackageCard(ctk.CTkFrame):
    def __init__(self, parent, name, version, manager, **kw):
        super().__init__(parent, fg_color=SURFACE2, corner_radius=8, **kw)
        self.name = name
        self.version = version
        self.manager = manager
        self._build()

    def _build(self):
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text="◆", text_color=ACCENT,
                     font=ctk.CTkFont(size=9), width=20
                     ).grid(row=0, column=0, padx=(12, 6), pady=10)

        ctk.CTkLabel(self, text=self.name, text_color=TEXT,
                     font=ctk.CTkFont(size=13, weight="bold"), anchor="w"
                     ).grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(self, text=self.version, text_color=TEXT_DIM,
                     font=ctk.CTkFont(family="Consolas", size=11),
                     width=90, anchor="w"
                     ).grid(row=0, column=2, padx=8)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=0, column=3, padx=(0, 10))

        ctk.CTkButton(btn_frame, text="Update", width=80, height=28,
                      fg_color=SURFACE3, hover_color=ACCENT,
                      text_color=ACCENT, font=ctk.CTkFont(size=11),
                      corner_radius=6,
                      command=lambda: self.manager.update_pkg(self.name)
                      ).pack(side="left", padx=3)

        ctk.CTkButton(btn_frame, text="Remove", width=80, height=28,
                      fg_color=SURFACE3, hover_color="#7f2020",
                      text_color=DANGER, font=ctk.CTkFont(size=11),
                      corner_radius=6,
                      command=lambda: self.manager.remove_pkg(self.name)
                      ).pack(side="left", padx=3)


class SearchCard(ctk.CTkFrame):
    def __init__(self, parent, pkg, installed_names, manager, **kw):
        super().__init__(parent, fg_color=SURFACE2, corner_radius=8, **kw)
        self.manager = manager
        self._build(pkg, installed_names)

    def _build(self, pkg, installed_names):
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text=pkg["name"], text_color=TEXT,
                     font=ctk.CTkFont(size=13, weight="bold"), anchor="w"
                     ).grid(row=0, column=0, padx=(14, 6), pady=(10, 2), sticky="w")

        ctk.CTkLabel(self, text=f"v{pkg['version']}", text_color=TEXT_DIM,
                     font=ctk.CTkFont(family="Consolas", size=11)
                     ).grid(row=0, column=1, sticky="w", padx=4, pady=(10, 2))

        already = pkg["name"].lower() in installed_names
        if already:
            ctk.CTkLabel(self, text="installed", text_color=MINT,
                         font=ctk.CTkFont(size=11)
                         ).grid(row=0, column=2, padx=12, pady=(10, 2))
        else:
            ctk.CTkButton(self, text="Install", width=90, height=28,
                          fg_color=ACCENT, hover_color=ACCENT_H,
                          text_color="#0b0d12",
                          font=ctk.CTkFont(size=11, weight="bold"),
                          corner_radius=6,
                          command=lambda n=pkg["name"]: self.manager.install_pkg(n)
                          ).grid(row=0, column=2, padx=12, pady=(10, 2))

        summary = pkg["summary"]
        if len(summary) > 100:
            summary = summary[:100] + "..."
        ctk.CTkLabel(self, text=summary, text_color=TEXT_DIM,
                     font=ctk.CTkFont(size=11), anchor="w",
                     wraplength=580, justify="left"
                     ).grid(row=1, column=0, columnspan=3,
                            padx=14, pady=(0, 10), sticky="w")


class PipManager(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("pip manager")
        self.geometry("980x700")
        self.minsize(740, 520)
        self.configure(fg_color=BG)
        self._packages = []
        self._build_ui()
        self.after(120, self.refresh_packages)

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        sidebar = ctk.CTkFrame(self, fg_color=SURFACE, width=210, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(8, weight=1)

        ctk.CTkLabel(sidebar, text="pip",
                     font=ctk.CTkFont(family="Consolas", size=32, weight="bold"),
                     text_color=ACCENT
                     ).grid(row=0, column=0, padx=24, pady=(28, 0), sticky="w")

        ctk.CTkLabel(sidebar, text="package manager",
                     font=ctk.CTkFont(size=11), text_color=TEXT_DIM
                     ).grid(row=1, column=0, padx=24, sticky="w")

        ctk.CTkFrame(sidebar, height=1, fg_color=BORDER
                     ).grid(row=2, column=0, padx=18, pady=20, sticky="ew")

        self._nav_btns = {}
        nav_items = [("Installed", "installed"),
                     ("Search",    "search"),
                     ("Console",   "console")]

        for i, (label, tab) in enumerate(nav_items, start=3):
            btn = ctk.CTkButton(
                sidebar, text=label, anchor="w",
                font=ctk.CTkFont(size=13),
                fg_color="transparent", hover_color=SURFACE3,
                text_color=TEXT_DIM, corner_radius=8, height=42,
                command=lambda t=tab: self._show_tab(t)
            )
            btn.grid(row=i, column=0, padx=10, pady=2, sticky="ew")
            self._nav_btns[tab] = btn

        ctk.CTkFrame(sidebar, height=1, fg_color=BORDER
                     ).grid(row=8, column=0, padx=18, pady=10, sticky="ew")

        ver_str = f"Python {sys.version.split()[0]}"
        ctk.CTkLabel(sidebar, text=ver_str,
                     font=ctk.CTkFont(family="Consolas", size=10),
                     text_color=TEXT_DIM
                     ).grid(row=9, column=0, padx=24, pady=(0, 4), sticky="w")

        exe = sys.executable
        short_exe = ("..." + exe[-26:]) if len(exe) > 28 else exe
        ctk.CTkLabel(sidebar, text=short_exe,
                     font=ctk.CTkFont(family="Consolas", size=9),
                     text_color=TEXT_DIM, wraplength=185
                     ).grid(row=10, column=0, padx=24, pady=(0, 16), sticky="w")

        # Main content area
        main = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(main, fg_color=SURFACE, height=58, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        header.grid_propagate(False)

        self._header_lbl = ctk.CTkLabel(
            header, text="Installed Packages",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=TEXT, anchor="w"
        )
        self._header_lbl.grid(row=0, column=0, padx=20, pady=14, sticky="w")

        ctk.CTkButton(
            header, text="Refresh", width=100, height=32,
            fg_color=SURFACE2, hover_color=SURFACE3,
            text_color=ACCENT, font=ctk.CTkFont(size=12),
            corner_radius=8, command=self.refresh_packages
        ).grid(row=0, column=1, padx=12, pady=12)

        # Tab container
        self._tab_container = ctk.CTkFrame(main, fg_color=BG, corner_radius=0)
        self._tab_container.grid(row=1, column=0, sticky="nsew")
        self._tab_container.grid_rowconfigure(0, weight=1)
        self._tab_container.grid_columnconfigure(0, weight=1)

        # Status bar
        status_bar = ctk.CTkFrame(main, fg_color=SURFACE, height=30, corner_radius=0)
        status_bar.grid(row=2, column=0, sticky="ew")
        status_bar.grid_columnconfigure(0, weight=1)
        status_bar.grid_propagate(False)

        self._status_var = ctk.StringVar(value="Ready")
        ctk.CTkLabel(status_bar, textvariable=self._status_var,
                     font=ctk.CTkFont(size=11), text_color=TEXT_DIM, anchor="w"
                     ).grid(row=0, column=0, padx=14, sticky="w")

        self._count_var = ctk.StringVar(value="")
        ctk.CTkLabel(status_bar, textvariable=self._count_var,
                     font=ctk.CTkFont(size=11), text_color=TEXT_DIM, anchor="e"
                     ).grid(row=0, column=1, padx=14, sticky="e")

        # Build tabs
        self._tabs = {}
        self._tabs["installed"] = self._build_installed_tab(self._tab_container)
        self._tabs["search"]    = self._build_search_tab(self._tab_container)
        self._tabs["console"]   = self._build_console_tab(self._tab_container)

        self._active_tab = None
        self._show_tab("installed")

    # ── Installed tab ─────────────────────────────────────────────────────────
    def _build_installed_tab(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=BG, corner_radius=0)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        filter_row = ctk.CTkFrame(frame, fg_color=BG)
        filter_row.grid(row=0, column=0, sticky="ew", padx=16, pady=12)
        filter_row.grid_columnconfigure(0, weight=1)

        self._filter_var = ctk.StringVar()
        self._filter_var.trace_add("write", lambda *a: self._filter_packages())
        ctk.CTkEntry(filter_row, textvariable=self._filter_var,
                     placeholder_text="Filter installed packages...",
                     font=ctk.CTkFont(size=13), height=38,
                     fg_color=SURFACE2, border_color=BORDER,
                     border_width=1, corner_radius=8, text_color=TEXT
                     ).grid(row=0, column=0, sticky="ew")

        self._pkg_scroll = ctk.CTkScrollableFrame(
            frame, fg_color=BG, corner_radius=0,
            scrollbar_button_color=SURFACE3,
            scrollbar_button_hover_color=ACCENT
        )
        self._pkg_scroll.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 8))
        self._pkg_scroll.grid_columnconfigure(0, weight=1)

        return frame

    # ── Search tab ────────────────────────────────────────────────────────────
    def _build_search_tab(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=BG, corner_radius=0)
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        search_row = ctk.CTkFrame(frame, fg_color=BG)
        search_row.grid(row=0, column=0, sticky="ew", padx=16, pady=12)
        search_row.grid_columnconfigure(0, weight=1)

        self._search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(
            search_row, textvariable=self._search_var,
            placeholder_text="Search PyPI for a package...",
            font=ctk.CTkFont(size=14), height=42,
            fg_color=SURFACE2, border_color=BORDER,
            border_width=1, corner_radius=8, text_color=TEXT
        )
        search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        search_entry.bind("<Return>", lambda e: self._do_search())

        ctk.CTkButton(
            search_row, text="Search", width=100, height=42,
            fg_color=ACCENT, hover_color=ACCENT_H,
            text_color="#0b0d12", font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=8, command=self._do_search
        ).grid(row=0, column=1)

        hint = ctk.CTkFrame(frame, fg_color=SURFACE2, corner_radius=10)
        hint.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))
        ctk.CTkLabel(hint,
                     text="Search by exact package name for best results (e.g. requests, numpy, flask)",
                     font=ctk.CTkFont(size=12), text_color=TEXT_DIM
                     ).pack(padx=16, pady=10)

        self._search_scroll = ctk.CTkScrollableFrame(
            frame, fg_color=BG, corner_radius=0,
            scrollbar_button_color=SURFACE3,
            scrollbar_button_hover_color=ACCENT
        )
        self._search_scroll.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 8))
        self._search_scroll.grid_columnconfigure(0, weight=1)

        return frame

    # ── Console tab ───────────────────────────────────────────────────────────
    def _build_console_tab(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=BG, corner_radius=0)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        cmd_row = ctk.CTkFrame(frame, fg_color=BG)
        cmd_row.grid(row=0, column=0, sticky="ew", padx=16, pady=12)
        cmd_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(cmd_row, text="pip",
                     font=ctk.CTkFont(family="Consolas", size=15, weight="bold"),
                     text_color=ACCENT, width=36
                     ).grid(row=0, column=0, padx=(0, 8))

        self._cmd_var = ctk.StringVar()
        cmd_entry = ctk.CTkEntry(
            cmd_row, textvariable=self._cmd_var,
            placeholder_text="install requests   |   show numpy   |   list --outdated",
            font=ctk.CTkFont(family="Consolas", size=13), height=38,
            fg_color=SURFACE2, border_color=BORDER, border_width=1,
            corner_radius=8, text_color=TEXT
        )
        cmd_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        cmd_entry.bind("<Return>", lambda e: self._run_custom_cmd())

        ctk.CTkButton(cmd_row, text="Run", width=80, height=38,
                      fg_color=MINT, hover_color="#3fbf88",
                      text_color="#0b0d12",
                      font=ctk.CTkFont(size=12, weight="bold"),
                      corner_radius=8, command=self._run_custom_cmd
                      ).grid(row=0, column=2, padx=(0, 6))

        ctk.CTkButton(cmd_row, text="Clear", width=70, height=38,
                      fg_color=SURFACE2, hover_color=SURFACE3,
                      text_color=TEXT_DIM, font=ctk.CTkFont(size=12),
                      corner_radius=8, command=self._console_clear
                      ).grid(row=0, column=3)

        self._console_out = ctk.CTkTextbox(
            frame, font=ctk.CTkFont(family="Consolas", size=12),
            fg_color="#080a0f", text_color=MINT,
            corner_radius=8, border_width=1, border_color=BORDER,
            wrap="word", state="disabled"
        )
        self._console_out.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 10))

        self._console_write(
            "pip manager console\n"
            "--------------------------------------\n"
            "Type any pip arguments above, e.g.:\n"
            "  install requests\n"
            "  uninstall numpy\n"
            "  list --outdated\n"
            "  show flask\n\n"
        )
        return frame

    # ── Navigation ────────────────────────────────────────────────────────────
    def _show_tab(self, tab_name):
        titles = {
            "installed": "Installed Packages",
            "search":    "Search & Install",
            "console":   "Console"
        }
        if self._active_tab == tab_name:
            return
        self._active_tab = tab_name
        self._header_lbl.configure(text=titles[tab_name])

        for name, btn in self._nav_btns.items():
            if name == tab_name:
                btn.configure(fg_color=SURFACE3, text_color=TEXT)
            else:
                btn.configure(fg_color="transparent", text_color=TEXT_DIM)

        for name, frame in self._tabs.items():
            if name == tab_name:
                frame.grid(row=0, column=0, sticky="nsew")
            else:
                frame.grid_remove()

    # ── Package loading ───────────────────────────────────────────────────────
    def refresh_packages(self):
        self._status("Loading packages...")
        threading.Thread(target=self._load_packages, daemon=True).start()

    def _load_packages(self):
        rc, out, err = run_pip("list", "--format=json")
        if rc == 0:
            try:
                pkgs = sorted(json.loads(out), key=lambda p: p["name"].lower())
                self._packages = pkgs
                self.after(0, self._render_packages, pkgs)
                self.after(0, self._status, f"Loaded {len(pkgs)} packages")
                self.after(0, self._count_var.set, f"{len(pkgs)} packages")
            except Exception as ex:
                self.after(0, self._status, f"Parse error: {ex}")
        else:
            self.after(0, self._status, "Failed to list packages")

    def _render_packages(self, pkgs):
        for w in self._pkg_scroll.winfo_children():
            w.destroy()
        for p in pkgs:
            card = PackageCard(self._pkg_scroll, p["name"], p["version"], self)
            card.pack(fill="x", pady=2)

    def _filter_packages(self):
        q = self._filter_var.get().lower().strip()
        filtered = [p for p in self._packages if q in p["name"].lower()] \
                   if q else self._packages
        self._render_packages(filtered)

    # ── Search ────────────────────────────────────────────────────────────────
    def _do_search(self):
        query = self._search_var.get().strip()
        if not query:
            return
        for w in self._search_scroll.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._search_scroll, text="Searching PyPI...",
                     text_color=TEXT_DIM, font=ctk.CTkFont(size=13)
                     ).pack(pady=20)
        self._status(f'Searching PyPI for "{query}"...')
        threading.Thread(target=self._pypi_search, args=(query,),
                         daemon=True).start()

    def _pypi_search(self, query):
        results = []
        url = f"https://pypi.org/pypi/{urllib.parse.quote(query)}/json"
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "pip-manager-gui/2.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read())
            info = data["info"]
            results.append({
                "name":    info["name"],
                "version": info["version"],
                "summary": info.get("summary") or "No description available.",
            })
        except Exception:
            pass

        if not results:
            results.append({
                "name":    query,
                "version": "latest",
                "summary": f"Package '{query}' — click Install to try.",
            })

        self.after(0, self._show_search_results, query, results)

    def _show_search_results(self, query, results):
        for w in self._search_scroll.winfo_children():
            w.destroy()
        installed = {p["name"].lower() for p in self._packages}
        for r in results:
            card = SearchCard(self._search_scroll, r, installed, self)
            card.pack(fill="x", pady=3)
        self._status(f'Search complete for "{query}"')

    # ── Package ops ───────────────────────────────────────────────────────────
    def install_pkg(self, name):
        if not messagebox.askyesno("Install", f"Install '{name}'?", parent=self):
            return
        self._show_tab("console")
        self._console_write(f"\n$ pip install {name}\n")
        self._status(f"Installing {name}...")
        threading.Thread(target=self._pkg_op,
                         args=(["install", name], name, "installed"),
                         daemon=True).start()

    def remove_pkg(self, name):
        if not messagebox.askyesno(
                "Remove", f"Uninstall '{name}'? This cannot be undone.",
                parent=self):
            return
        self._show_tab("console")
        self._console_write(f"\n$ pip uninstall -y {name}\n")
        self._status(f"Removing {name}...")
        threading.Thread(target=self._pkg_op,
                         args=(["uninstall", "-y", name], name, "removed"),
                         daemon=True).start()

    def update_pkg(self, name):
        self._show_tab("console")
        self._console_write(f"\n$ pip install --upgrade {name}\n")
        self._status(f"Updating {name}...")
        threading.Thread(target=self._pkg_op,
                         args=(["install", "--upgrade", name], name, "updated"),
                         daemon=True).start()

    def _pkg_op(self, args, name, action):
        rc, out, err = run_pip(*args)
        self.after(0, self._console_write, out + err)
        if rc == 0:
            self.after(0, self._status, f"{name} {action} successfully")
            self.after(0, self.refresh_packages)
        else:
            self.after(0, self._status, f"Failed to {action[:-1]} {name}")

    # ── Console ───────────────────────────────────────────────────────────────
    def _run_custom_cmd(self):
        raw = self._cmd_var.get().strip()
        if not raw:
            return
        self._cmd_var.set("")
        self._console_write(f"\n$ pip {raw}\n")
        self._status(f"Running: pip {raw}")
        threading.Thread(target=self._custom_pip,
                         args=(raw.split(),), daemon=True).start()

    def _custom_pip(self, args):
        rc, out, err = run_pip(*args)
        self.after(0, self._console_write, out + err)
        self.after(0, self._status,
                   "Done" if rc == 0 else f"Exit code {rc}")
        if any(a in args for a in ("install", "uninstall", "upgrade")):
            self.after(0, self.refresh_packages)

    def _console_write(self, text):
        self._console_out.configure(state="normal")
        self._console_out.insert("end", text)
        self._console_out.see("end")
        self._console_out.configure(state="disabled")

    def _console_clear(self):
        self._console_out.configure(state="normal")
        self._console_out.delete("1.0", "end")
        self._console_out.configure(state="disabled")

    def _status(self, msg):
        self._status_var.set(msg)


if __name__ == "__main__":
    app = PipManager()
    app.mainloop()
