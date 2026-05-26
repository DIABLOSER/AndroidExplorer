#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from tkinter import ttk


class ThemeManager:
    """VS Code 风格主题（默认暗色）"""

    def __init__(self, theme_mode):
        self.theme_mode = theme_mode
        self._setup_theme_colors()

    def _setup_theme_colors(self):
        self._theme_light = {
            "main": "#ffffff",
            "menubar": "#f3f3f3", "menubar_fg": "#333333",
            "sidebar": "#f3f3f3", "sidebar_btn": "#e8e8e8", "sidebar_btn_fg": "#333333",
            "sidebar_btn_active": "#094771", "sidebar_active_fg": "#ffffff",
            "divider": "#e5e5e5",
            "sidebar_border": "#e5e5e5",
            "panel_header": "#f3f3f3",
            "listbox": "#ffffff", "listbox_fg": "#333333",
            "listbox_sel": "#094771", "listbox_sel_fg": "#ffffff",
            "editor": "#ffffff", "editor_fg": "#333333",
            "gutter": "#f5f5f5",
            "input_bg": "#ffffff", "input_fg": "#333333",
            "hint_fg": "#6e6e6e",
            "statusbar": "#007acc", "statusbar_fg": "#ffffff",
            "tab_bg": "#f3f3f3", "tab_fg": "#333333",
            "accent": "#007acc", "preview_fg": "#0066b8",
        }
        self._theme_dark = {
            "main": "#1e1e1e",
            "menubar": "#323233", "menubar_fg": "#cccccc",
            "sidebar": "#252526", "sidebar_btn": "#2d2d30", "sidebar_btn_fg": "#cccccc",
            "sidebar_btn_active": "#37373d", "sidebar_active_fg": "#ffffff",
            "divider": "#2a2a2a",
            "sidebar_border": "#2a2a2a",
            "panel_header": "#252526",
            "listbox": "#1e1e1e", "listbox_fg": "#cccccc",
            "listbox_sel": "#094771", "listbox_sel_fg": "#ffffff",
            "editor": "#1e1e1e", "editor_fg": "#d4d4d4",
            "gutter": "#1e1e1e",
            "input_bg": "#3c3c3c", "input_fg": "#cccccc",
            "hint_fg": "#858585",
            "statusbar": "#007acc", "statusbar_fg": "#ffffff",
            "tab_bg": "#252526", "tab_fg": "#cccccc",
            "accent": "#007acc", "preview_fg": "#3794ff",
        }
        self._theme_light_fg = {
            "menubar": "#333333", "sidebar_btn": "#333333",
            "sidebar_btn_active": "#ffffff", "editor": "#333333",
            "listbox": "#333333", "listbox_sel": "#ffffff",
        }

    def is_dark(self):
        return self.theme_mode.get() == "Dark"

    def get_bg(self, key):
        theme = self._theme_dark if self.is_dark() else self._theme_light
        return theme.get(key, "#1e1e1e" if self.is_dark() else "#ffffff")

    def get_fg(self, key):
        if self.is_dark():
            theme = self._theme_dark
            if key == "sidebar_btn":
                return theme.get("sidebar_btn_fg", "#cccccc")
            if key == "sidebar_btn_active":
                return theme.get("sidebar_active_fg", "#ffffff")
            return theme.get(f"{key}_fg", theme.get("editor_fg", "#cccccc"))
        return self._theme_light_fg.get(key, "#333333")

    def get_border(self):
        return self.get_bg("divider")

    def setup_ttk_styles(self):
        s = ttk.Style()
        dark = self.is_dark()
        bg_main = self.get_bg("main")
        bg_sidebar = self.get_bg("sidebar")
        bg_input = self.get_bg("input_bg")
        fg = self.get_fg("editor")
        fg_dim = self.get_bg("hint_fg") if dark else "#6e6e6e"
        border = self.get_border()
        accent = self.get_bg("accent")

        s.configure("TFrame", background=bg_main)
        s.configure("Sidebar.TFrame", background=bg_sidebar)
        s.configure("TLabel", background=bg_main, foreground=fg)
        s.configure("Sidebar.TLabel", background=bg_sidebar, foreground=fg)
        s.configure("Dim.TLabel", background=bg_sidebar, foreground=fg_dim)

        s.configure("TNotebook", background=bg_main, borderwidth=0)
        s.configure("TNotebook.Tab", padding=[12, 6], font=("Segoe UI", 9, "bold"),
                    background=self.get_bg("sidebar_btn"), foreground=self.get_fg("sidebar_btn"))
        s.map("TNotebook.Tab",
              background=[("selected", accent), ("active", accent)],
              foreground=[("selected", "#ffffff"), ("active", "#ffffff")])

        s.configure("TButton", padding=[8, 4], font=("Segoe UI", 9),
                    background=accent, foreground="#ffffff", relief="flat", borderwidth=0)
        s.map("TButton",
              background=[("active", "#005a9e"), ("pressed", "#004a8c")])

        sash = self.get_bg("divider")
        s.configure("TPanedwindow", background=sash, sashwidth=1, sashpad=0, sashrelief="flat")

        trough = "#3a3a3a" if dark else "#f0f0f0"
        thumb = "#5a5a5a" if dark else "#c0c0c0"
        editor_bg = self.get_bg("editor")
        for orient in ("Vertical", "Horizontal"):
            s.configure(f"{orient}.TScrollbar",
                        troughcolor=trough, background=bg_main,
                        bordercolor=bg_main, arrowcolor=thumb, width=10)
        s.configure(
            "Editor.Vertical.TScrollbar",
            troughcolor=editor_bg, background=editor_bg,
            bordercolor=editor_bg, darkcolor=editor_bg, lightcolor=editor_bg,
            arrowcolor=thumb, width=8,
        )
        s.map(
            "Editor.Vertical.TScrollbar",
            background=[("active", thumb), ("!active", editor_bg)],
            arrowcolor=[("active", "#888888" if dark else "#666666")],
        )

        s.configure("TEntry",
                    fieldbackground=bg_input, foreground=self.get_fg("input_fg"),
                    bordercolor=border, lightcolor=border, darkcolor=border,
                    insertcolor=self.get_fg("input_fg"), padding=4)
        s.map("TEntry", fieldbackground=[("readonly", bg_input), ("disabled", bg_input)])

        combo_bg = bg_input
        combo_fg = self.get_fg("input_fg")
        s.configure("TCombobox",
                    fieldbackground=combo_bg, background=combo_bg,
                    foreground=combo_fg, arrowcolor=combo_fg,
                    bordercolor=border, lightcolor=border, darkcolor=border, padding=4)
        s.map("TCombobox",
              fieldbackground=[("readonly", combo_bg)],
              selectbackground=[("readonly", accent)],
              selectforeground=[("readonly", "#ffffff")])

        menubar_bg = self.get_bg("menubar")
        menubar_fg = self.get_fg("menubar")
        s.configure("TCheckbutton", background=bg_sidebar, foreground=fg)
        s.configure("Menubar.TCheckbutton", background=menubar_bg, foreground=menubar_fg)
        s.configure("TRadiobutton", background=bg_sidebar, foreground=fg)
        s.map("TCheckbutton", background=[("active", bg_sidebar)])
        s.map("Menubar.TCheckbutton", background=[("active", menubar_bg)])
        s.map("TRadiobutton", background=[("active", bg_sidebar)])

        s.configure("TLabelFrame", background=bg_sidebar, foreground=fg, bordercolor=border)
        s.configure("TLabelFrame.Label", background=bg_sidebar, foreground=fg)

        s.configure("TSeparator", background=border)
        s.configure("Horizontal.TSeparator", background=border)
        s.configure("Vertical.TSeparator", background=border)

        s.configure("TSpinbox",
                    fieldbackground=bg_input, foreground=combo_fg,
                    bordercolor=border, arrowcolor=combo_fg)
