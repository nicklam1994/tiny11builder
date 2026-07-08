"""
tiny11 Builder GUI — CustomTkinter application.
A visual interface for building trimmed Windows 11 images.
"""
import customtkinter as ctk
import sys
import os
import threading
import subprocess
import ctypes
from pathlib import Path
from tkinter import filedialog, messagebox

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from core.ps_parser import get_all_packages, get_all_tweaks
from core.script_gen import BuildConfig, generate_command
from core.git_ops import get_status, pull_upstream, get_log, get_diff_summary

# ─── Theme ────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

SCRIPT_DIR = Path(__file__).resolve().parent.parent  # repo root
GUI_DIR = Path(__file__).resolve().parent


class Sidebar(ctk.CTkFrame):
    """Left navigation sidebar."""

    NAV_ITEMS = [
        ("🏠", "首頁", "home"),
        ("🔧", "構建", "build"),
        ("📦", "包管理", "packages"),
        ("⚙️", "調整", "tweaks"),
        ("🔄", "同步", "sync"),
    ]

    def __init__(self, master, on_navigate):
        super().__init__(master, width=180, corner_radius=0)
        self.on_navigate = on_navigate
        self.buttons: dict[str, ctk.CTkButton] = {}
        self._build()

    def _build(self):
        # Logo
        ctk.CTkLabel(
            self, text="tiny11 Builder",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(pady=(20, 30), padx=10)

        for icon, label, key in self.NAV_ITEMS:
            btn = ctk.CTkButton(
                self,
                text=f"  {icon}  {label}",
                anchor="w",
                font=ctk.CTkFont(size=14),
                height=40,
                corner_radius=8,
                fg_color="transparent",
                hover_color=("gray75", "gray25"),
                command=lambda k=key: self._select(k),
            )
            btn.pack(fill="x", padx=10, pady=3)
            self.buttons[key] = btn

        # Version at bottom
        ctk.CTkLabel(
            self, text="v1.0 · upstream sync",
            font=ctk.CTkFont(size=11),
            text_color="gray60",
        ).pack(side="bottom", pady=10)

    def _select(self, key: str):
        for k, btn in self.buttons.items():
            btn.configure(fg_color="transparent")
        self.buttons[key].configure(fg_color=("gray75", "gray25"))
        self.on_navigate(key)


class HomePage(ctk.CTkFrame):
    """Home / overview page."""

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._build()

    def _build(self):
        ctk.CTkLabel(
            self, text="tiny11 Builder",
            font=ctk.CTkFont(size=32, weight="bold"),
        ).pack(pady=(40, 10))

        ctk.CTkLabel(
            self,
            text="建立精簡 Windows 11 映像檔的圖形化工具",
            font=ctk.CTkFont(size=16),
            text_color="gray70",
        ).pack(pady=(0, 30))

        # Steps
        steps = [
            ("1", "選擇 ISO", "掛載 Windows 11 ISO 並選擇磁碟機"),
            ("2", "選擇模式", "Regular（推薦）或 Core（極簡）"),
            ("3", "自定義", "勾選要移除的應用和調整"),
            ("4", "構建", "以管理員權限執行，等待完成"),
        ]
        for num, title, desc in steps:
            frame = ctk.CTkFrame(self, fg_color=("gray90", "gray17"), corner_radius=10)
            frame.pack(fill="x", padx=60, pady=5)
            ctk.CTkLabel(
                frame, text=num,
                font=ctk.CTkFont(size=24, weight="bold"),
                text_color="#3B82F6",
                width=40,
            ).pack(side="left", padx=(15, 5), pady=10)
            ctk.CTkLabel(
                frame, text=title,
                font=ctk.CTkFont(size=14, weight="bold"),
            ).pack(side="left", padx=5)
            ctk.CTkLabel(
                frame, text=desc,
                font=ctk.CTkFont(size=12),
                text_color="gray60",
            ).pack(side="left", padx=10)


class BuildPage(ctk.CTkFrame):
    """Build configuration page."""

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.config = BuildConfig()
        self._build()

    def _build(self):
        ctk.CTkLabel(
            self, text="構建配置",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(20, 10))

        # Mode selector
        mode_frame = ctk.CTkFrame(self, fg_color="transparent")
        mode_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(mode_frame, text="構建模式：",
                     font=ctk.CTkFont(size=14)).pack(side="left")

        self.mode_var = ctk.StringVar(value="regular")
        ctk.CTkRadioButton(
            mode_frame, text="Regular（推薦）",
            variable=self.mode_var, value="regular",
            font=ctk.CTkFont(size=13),
        ).pack(side="left", padx=15)
        ctk.CTkRadioButton(
            mode_frame, text="Core（極簡，不可維護）",
            variable=self.mode_var, value="core",
            font=ctk.CTkFont(size=13),
        ).pack(side="left", padx=15)

        # Drive selectors
        drive_frame = ctk.CTkFrame(self, fg_color="transparent")
        drive_frame.pack(fill="x", padx=20, pady=10)

        # ISO drive
        iso_frame = ctk.CTkFrame(drive_frame, fg_color="transparent")
        iso_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(iso_frame, text="ISO 磁碟機代號：",
                     font=ctk.CTkFont(size=14)).pack(side="left")
        self.iso_entry = ctk.CTkEntry(iso_frame, width=60, placeholder_text="E")
        self.iso_entry.pack(side="left", padx=10)

        # Scratch drive
        scratch_frame = ctk.CTkFrame(drive_frame, fg_color="transparent")
        scratch_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(scratch_frame, text="暫存磁碟：",
                     font=ctk.CTkFont(size=14)).pack(side="left")
        self.scratch_entry = ctk.CTkEntry(scratch_frame, width=60, placeholder_text="D")
        self.scratch_entry.pack(side="left", padx=10)

        # Info
        ctk.CTkLabel(
            self,
            text="💡 先掛載 Windows 11 ISO，然後輸入掛載的磁碟機代號（只需字母，不含冒號）",
            font=ctk.CTkFont(size=12),
            text_color="gray60",
            wraplength=500,
        ).pack(anchor="w", padx=25, pady=(5, 15))

        # Command preview
        ctk.CTkLabel(
            self, text="執行命令預覽：",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(10, 5))

        self.cmd_text = ctk.CTkTextbox(self, height=80, font=ctk.CTkFont(family="Consolas", size=12))
        self.cmd_text.pack(fill="x", padx=20, pady=5)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=15)

        ctk.CTkButton(
            btn_frame, text="📋 複製命令",
            command=self._copy_command,
            width=140,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame, text="💾 下載腳本",
            command=self._download_script,
            width=140,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame, text="🚀 以管理員執行",
            command=self._run_elevated,
            width=160,
            fg_color="#10B981",
            hover_color="#059669",
        ).pack(side="left", padx=5)

        # Update preview on changes
        self.iso_entry.bind("<KeyRelease>", lambda e: self._update_preview())
        self.scratch_entry.bind("<KeyRelease>", lambda e: self._update_preview())
        self.mode_var.trace_add("write", lambda *a: self._update_preview())
        self._update_preview()

    def _update_preview(self):
        iso = self.iso_entry.get().strip().upper()
        scratch = self.scratch_entry.get().strip().upper()
        mode = self.mode_var.get()
        cmd = generate_command(
            BuildConfig(mode=mode, iso_drive=iso, scratch_drive=scratch),
            SCRIPT_DIR,
        )
        self.cmd_text.delete("1.0", "end")
        self.cmd_text.insert("1.0", cmd)

    def _copy_command(self):
        cmd = self.cmd_text.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(cmd)
        messagebox.showinfo("已複製", "命令已複製到剪貼簿")

    def _download_script(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".ps1",
            filetypes=[("PowerShell Script", "*.ps1")],
            initialfile="tiny11-build.ps1",
        )
        if path:
            cmd = self.cmd_text.get("1.0", "end-1c")
            Path(path).write_text(cmd, encoding="utf-8")
            messagebox.showinfo("已儲存", f"腳本已儲存至：{path}")

    def _run_elevated(self):
        iso = self.iso_entry.get().strip().upper()
        scratch = self.scratch_entry.get().strip().upper()
        mode = self.mode_var.get()
        if not iso:
            messagebox.showwarning("缺少參數", "請輸入 ISO 磁碟機代號")
            return

        script_name = "tiny11maker.ps1" if mode == "regular" else "tiny11Coremaker.ps1"
        script_path = SCRIPT_DIR / script_name
        args = f"-ISO {iso}"
        if scratch:
            args += f" -SCRATCH {scratch}"

        ps_cmd = f'Set-ExecutionPolicy Bypass -Scope Process; & "{script_path}" {args}'

        try:
            # ShellExecuteW to elevate
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas",
                "powershell.exe",
                f'-NoExit -Command "{ps_cmd}"',
                str(SCRIPT_DIR),
                1,  # SW_SHOWNORMAL
            )
        except Exception as e:
            messagebox.showerror("錯誤", f"無法啟動管理員 PowerShell：{e}")


class PackagePage(ctk.CTkFrame):
    """Package management page — toggle which apps to remove."""

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.packages = get_all_packages(SCRIPT_DIR)
        self.checkboxes: dict[str, ctk.CTkCheckBox] = {}
        self._build()

    def _build(self):
        ctk.CTkLabel(
            self, text="包管理 — 選擇要移除的應用",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(20, 5))

        ctk.CTkLabel(
            self,
            text="取消勾選 = 保留該應用（不會被移除）",
            font=ctk.CTkFont(size=12),
            text_color="gray60",
        ).pack(anchor="w", padx=20, pady=(0, 10))

        # Select all / none
        sel_frame = ctk.CTkFrame(self, fg_color="transparent")
        sel_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkButton(
            sel_frame, text="全選", width=80,
            command=lambda: self._select_all(True),
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            sel_frame, text="全不選", width=80,
            command=lambda: self._select_all(False),
        ).pack(side="left", padx=5)

        # Tabview for categories
        tabview = ctk.CTkTabview(self)
        tabview.pack(fill="both", expand=True, padx=20, pady=10)

        # Regular packages tab
        tab_regular = tabview.add("Regular 應用")
        self._build_package_list(
            tab_regular,
            self.packages["regular"],
            "regular",
        )

        # Core-only packages tab
        tab_core = tabview.add("Core 額外移除")
        self._build_package_list(
            tab_core,
            self.packages.get("core_only", []),
            "core_only",
        )

        # System packages tab (Core only)
        tab_sys = tabview.add("系統組件 (Core)")
        self._build_system_list(tab_sys)

    def _build_package_list(self, parent, packages, group: str):
        scroll = ctk.CTkScrollableFrame(parent)
        scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # Group by category
        categories: dict[str, list] = {}
        for pkg in packages:
            categories.setdefault(pkg.category, []).append(pkg)

        cat_labels = {
            "bloatware": "🗑️ 雜項臃腫軟體",
            "gaming": "🎮 遊戲相關",
            "web_news": "🌐 新聞與天氣",
            "ai": "🤖 AI 助手",
            "productivity": "💼 生產力",
            "browser": "🌍 瀏覽器",
        }

        for cat, pkgs in categories.items():
            label = cat_labels.get(cat, cat)
            ctk.CTkLabel(
                scroll, text=label,
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color="#3B82F6",
            ).pack(anchor="w", padx=10, pady=(10, 3))

            for pkg in pkgs:
                var = ctk.BooleanVar(value=True)
                cb = ctk.CTkCheckBox(
                    scroll,
                    text=f"{pkg.display_name}  ({pkg.prefix})",
                    variable=var,
                    font=ctk.CTkFont(size=12),
                    checkbox_width=18,
                    checkbox_height=18,
                )
                cb.pack(anchor="w", padx=20, pady=2)
                self.checkboxes[f"{group}:{pkg.prefix}"] = cb

    def _build_system_list(self, parent):
        scroll = ctk.CTkScrollableFrame(parent)
        scroll.pack(fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(
            scroll,
            text="⚠️ Core 模式專用 — 移除這些組件後無法恢復",
            font=ctk.CTkFont(size=12),
            text_color="#F59E0B",
        ).pack(anchor="w", padx=10, pady=5)

        for pkg in self.packages.get("system", []):
            var = ctk.BooleanVar(value=True)
            cb = ctk.CTkCheckBox(
                scroll,
                text=pkg.display_name,
                variable=var,
                font=ctk.CTkFont(size=12),
                checkbox_width=18,
                checkbox_height=18,
            )
            cb.pack(anchor="w", padx=20, pady=2)
            self.checkboxes[f"system:{pkg.display_name}"] = cb

    def _select_all(self, state: bool):
        for cb in self.checkboxes.values():
            if state:
                cb.select()
            else:
                cb.deselect()

    def get_selected_packages(self) -> list[str]:
        """Return list of selected package prefixes."""
        selected = []
        for key, cb in self.checkboxes.items():
            if cb.get():
                group, name = key.split(":", 1)
                if group in ("regular", "core_only"):
                    selected.append(name)
        return selected

    def get_selected_system_packages(self) -> list[str]:
        """Return list of selected system package names."""
        selected = []
        for key, cb in self.checkboxes.items():
            if cb.get() and key.startswith("system:"):
                selected.append(key.split(":", 1)[1])
        return selected


class TweaksPage(ctk.CTkFrame):
    """Registry tweaks page — toggle switches."""

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.tweaks = get_all_tweaks(SCRIPT_DIR)
        self.switches: dict[str, ctk.CTkSwitch] = {}
        self._build()

    def _build(self):
        ctk.CTkLabel(
            self, text="註冊表調整",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(20, 5))

        ctk.CTkLabel(
            self,
            text="開關調整系統設定（綠色 = 啟用此調整）",
            font=ctk.CTkFont(size=12),
            text_color="gray60",
        ).pack(anchor="w", padx=20, pady=(0, 10))

        scroll = ctk.CTkScrollableFrame(self)
        scroll.pack(fill="both", expand=True, padx=20, pady=5)

        for category, tweaks_list in self.tweaks.items():
            # Category header
            ctk.CTkLabel(
                scroll, text=f"▸ {category}",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#3B82F6",
            ).pack(anchor="w", padx=10, pady=(15, 5))

            for tweak in tweaks_list:
                switch = ctk.CTkSwitch(
                    scroll,
                    text=tweak.description,
                    font=ctk.CTkFont(size=12),
                    switch_width=40,
                    switch_height=22,
                )
                switch.pack(anchor="w", padx=30, pady=2)
                switch.select()  # Default on
                self.switches[tweak.description] = switch

        # Additional file-level removals
        ctk.CTkLabel(
            scroll, text="▸ 檔案級移除",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#3B82F6",
        ).pack(anchor="w", padx=10, pady=(15, 5))

        extra_toggles = [
            ("移除 Microsoft Edge", True),
            ("移除 OneDrive", True),
            ("移除 Edge Webview", True),
            ("移除排程任務（遙測相關）", True),
        ]
        for label, default in extra_toggles:
            switch = ctk.CTkSwitch(
                scroll, text=label,
                font=ctk.CTkFont(size=12),
                switch_width=40, switch_height=22,
            )
            switch.pack(anchor="w", padx=30, pady=2)
            if default:
                switch.select()
            self.switches[label] = switch

    def get_enabled_tweaks(self) -> list[str]:
        """Return list of enabled tweak descriptions."""
        return [desc for desc, sw in self.switches.items() if sw.get()]


class SyncPage(ctk.CTkFrame):
    """Upstream sync page."""

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._build()

    def _build(self):
        ctk.CTkLabel(
            self, text="上游同步",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(20, 10))

        # Status
        self.status_frame = ctk.CTkFrame(self, corner_radius=10)
        self.status_frame.pack(fill="x", padx=20, pady=10)

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="載入中...",
            font=ctk.CTkFont(size=14),
            wraplength=500,
        )
        self.status_label.pack(padx=15, pady=15)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkButton(
            btn_frame, text="🔄 刷新狀態",
            command=self._refresh,
            width=140,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame, text="⬇️ 拉取上游更新",
            command=self._pull,
            width=160,
            fg_color="#10B981",
            hover_color="#059669",
        ).pack(side="left", padx=5)

        # Log
        ctk.CTkLabel(
            self, text="提交記錄：",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(15, 5))

        self.log_text = ctk.CTkTextbox(
            self, font=ctk.CTkFont(family="Consolas", size=11),
        )
        self.log_text.pack(fill="both", expand=True, padx=20, pady=5)

        # Auto-refresh
        self.after(500, self._refresh)

    def _refresh(self):
        def _do():
            try:
                status = get_status(SCRIPT_DIR)
                log = get_log(SCRIPT_DIR, 15)
                self.after(0, lambda: self._update_ui(status, log))
            except Exception as e:
                self.after(0, lambda: self.status_label.configure(
                    text=f"錯誤：{e}"
                ))
        threading.Thread(target=_do, daemon=True).start()

    def _update_ui(self, status, log):
        parts = [f"分支：{status.branch}"]
        if status.has_upstream:
            if status.behind > 0:
                parts.append(f"落後上游 {status.behind} 個提交")
            if status.ahead > 0:
                parts.append(f"領先 {status.ahead} 個提交")
            if status.ahead == 0 and status.behind == 0:
                parts.append("✅ 與上游同步")
        else:
            parts.append("⚠️ 未設置 upstream remote")
        if status.dirty:
            parts.append("（有未提交的修改）")

        self.status_label.configure(text="  |  ".join(parts))

        self.log_text.delete("1.0", "end")
        for entry in log:
            self.log_text.insert("end", f"{entry['short']}  {entry['subject']}\n")
            self.log_text.insert("end", f"  {entry['author']}  {entry['date']}\n\n")

    def _pull(self):
        if not messagebox.askyesno("確認", "確定要從上游拉取並合併更新嗎？"):
            return

        def _do():
            self.after(0, lambda: self.status_label.configure(text="正在拉取..."))
            ok, msg = pull_upstream(SCRIPT_DIR)
            self.after(0, lambda: self._pull_done(ok, msg))

        threading.Thread(target=_do, daemon=True).start()

    def _pull_done(self, ok, msg):
        if ok:
            messagebox.showinfo("成功", msg)
            self._refresh()
        else:
            messagebox.showerror("失敗", msg)


class App(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.title("tiny11 Builder")
        self.geometry("1000x700")
        self.minsize(800, 500)

        # Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = Sidebar(self, on_navigate=self._show_page)
        self.sidebar.grid(row=0, column=0, sticky="nsw")

        # Pages
        self.pages: dict[str, ctk.CTkFrame] = {}
        self._build_pages()
        self.sidebar._select("home")

    def _build_pages(self):
        self.pages["home"] = HomePage(self)
        self.pages["build"] = BuildPage(self)
        self.pages["packages"] = PackagePage(self)
        self.pages["tweaks"] = TweaksPage(self)
        self.pages["sync"] = SyncPage(self)

    def _show_page(self, name: str):
        for page in self.pages.values():
            page.grid_forget()
        self.pages[name].grid(row=0, column=1, sticky="nsew", padx=5, pady=5)


def main():
    print("[1/4] 啟動中...")
    try:
        print("[2/4] 初始化 CustomTkinter...")
        app = App()
        print("[3/4] 窗口創建成功，進入事件循環...")
        app.mainloop()
        print("[4/4] 事件循環結束")
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"\n[ERROR] {error_msg}", file=sys.stderr)
        # Write error.log
        error_file = Path(__file__).parent / "error.log"
        error_file.write_text(error_msg, encoding="utf-8")
        print(f"錯誤已記錄至：{error_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
