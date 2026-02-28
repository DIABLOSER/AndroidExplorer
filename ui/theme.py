#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from tkinter import ttk


class ThemeManager:
    """主题管理器"""
    
    def __init__(self, theme_mode):
        self.theme_mode = theme_mode
        self._setup_theme_colors()
    
    def _setup_theme_colors(self):
        """主题色表（参考 VS Code）"""
        self._theme_light = {
            "main": "#ffffff", "menubar": "#f3f3f3", "menubar_fg": "#333333",
            "sidebar": "#f3f3f3", "sidebar_btn": "#e8e8e8", "sidebar_btn_active": "#094771",
            "sidebar_border": "#e0e0e0", "listbox": "#ffffff", "listbox_fg": "#333333",
            "listbox_sel": "#094771", "listbox_sel_fg": "#ffffff",
            "editor": "#ffffff", "editor_fg": "#333333", "editor_border": "#e0e0e0",
            "statusbar": "#007acc", "statusbar_fg": "#ffffff", "tab_bg": "#f3f3f3", "tab_fg": "#333333",
        }
        self._theme_dark = {
            "main": "#1e1e1e", "menubar": "#323233", "menubar_fg": "#cccccc",
            "sidebar": "#252526", "sidebar_btn": "#2d2d30", "sidebar_btn_active": "#0e639c",
            "sidebar_border": "#3c3c3c", "listbox": "#252526", "listbox_fg": "#cccccc",
            "listbox_sel": "#094771", "listbox_sel_fg": "#ffffff",
            "editor": "#1e1e1e", "editor_fg": "#d4d4d4", "editor_border": "#3c3c3c",
            "statusbar": "#007acc", "statusbar_fg": "#ffffff", "tab_bg": "#252526", "tab_fg": "#cccccc",
        }
        self._theme_light_fg = {
            "menubar": "#333333", "sidebar_btn": "#333333", "sidebar_btn_active": "#ffffff",
            "editor": "#333333", "listbox": "#333333", "listbox_sel": "#ffffff"
        }
    
    def get_bg(self, key):
        """获取背景色"""
        if self.theme_mode.get() == "Light":
            return self._theme_light.get(key, "#ffffff")
        return self._theme_dark.get(key, "#252526")
    
    def get_fg(self, key):
        """获取前景色"""
        if self.theme_mode.get() == "Light":
            return self._theme_light_fg.get(key, "#000000")
        return self._theme_dark.get(key + "_fg", "#cccccc")
    
    def setup_ttk_styles(self):
        """配置 ttk 样式（VS Code 风格）"""
        s = ttk.Style()
        bg_main = self.get_bg("main")
        border = self.get_bg("sidebar_border")
        
        s.configure("TFrame", background=bg_main)
        s.configure("TNotebook", background=bg_main, borderwidth=0)
        
        # Notebook tab styling
        s.configure("TNotebook.Tab", padding=[12, 6], font=("Segoe UI", 9, "bold"),
                   background=self.get_bg("sidebar_btn"), foreground=self.get_fg("sidebar_btn"))
        s.map("TNotebook.Tab", 
              background=[("selected", "#007acc"), ("active", "#007acc")],
              foreground=[("selected", "#ffffff"), ("active", "#ffffff")])
        
        # Button styling
        s.configure("TButton", padding=[10, 4], font=("Segoe UI", 9), 
                   background="#007acc", foreground="#ffffff", 
                   relief="flat", borderwidth=0)
        s.map("TButton", 
              background=[("active", "#005a9e"), ("pressed", "#004a8c")],
              foreground=[("active", "#ffffff")])
        
        s.configure("Primary.TButton", padding=[12, 6], font=("Segoe UI", 9, "bold"),
                   background="#007acc", foreground="#ffffff")
        s.map("Primary.TButton",
              background=[("active", "#005a9e"), ("pressed", "#004a8c")])
        
        s.configure("TLabelFrame", padding=2, font=("Segoe UI", 9))
        s.configure("TLabelFrame.Label", font=("Segoe UI", 9, "bold"))
        s.configure("TLabelframe", padding=2)
        
        # Combobox styling
        combo_bg = "#ffffff" if self.theme_mode.get() == "Light" else "#2d2d2d"
        combo_fg = "#000000" if self.theme_mode.get() == "Light" else "#ffffff"
        combo_field_bg = "#f5f5f5" if self.theme_mode.get() == "Light" else "#3a3a3a"
        combo_select_bg = "#007acc"
        combo_select_fg = "#ffffff"
        
        s.configure("TCombobox",
                   fieldbackground=combo_field_bg,
                   background=combo_bg,
                   foreground=combo_fg,
                   arrowcolor=combo_fg,
                   borderwidth=1,
                   relief="flat",
                   padding=5)
        
        s.map("TCombobox",
              fieldbackground=[("readonly", combo_field_bg), ("disabled", combo_field_bg)],
              selectbackground=[("readonly", combo_select_bg)],
              selectforeground=[("readonly", combo_select_fg)],
              foreground=[("readonly", combo_fg), ("disabled", "#999999")])
        
        # PanedWindow styling
        sash_color = "#e0e0e0" if self.theme_mode.get() == "Light" else "#404040"
        s.configure("TPanedwindow", background=sash_color, sashwidth=1, sashpad=0, sashrelief="flat")
        
        # Scrollbar styling
        scrollbar_bg = self.get_bg("main")
        scrollbar_trough = "#f0f0f0" if self.theme_mode.get() == "Light" else "#3a3a3a"
        scrollbar_thumb = "#c0c0c0" if self.theme_mode.get() == "Light" else "#666666"
        
        s.configure("Vertical.TScrollbar", 
                   troughcolor=scrollbar_trough,
                   background=scrollbar_bg,
                   bordercolor=scrollbar_bg,
                   darkcolor=scrollbar_bg,
                   lightcolor=scrollbar_bg,
                   arrowcolor=scrollbar_thumb,
                   width=9)
        
        s.map("Vertical.TScrollbar",
              background=[("active", scrollbar_bg), ("!active", scrollbar_bg)],
              troughcolor=[("active", scrollbar_trough), ("!active", scrollbar_trough)])
        
        s.configure("Horizontal.TScrollbar",
                   troughcolor=scrollbar_trough,
                   background=scrollbar_bg,
                   bordercolor=scrollbar_bg,
                   darkcolor=scrollbar_bg,
                   lightcolor=scrollbar_bg,
                   arrowcolor=scrollbar_thumb,
                   height=9)
        
        s.map("Horizontal.TScrollbar",
              background=[("active", scrollbar_bg), ("!active", scrollbar_bg)],
              troughcolor=[("active", scrollbar_trough), ("!active", scrollbar_trough)])
        
        # Entry and Combobox
        s.configure("TEntry", fieldbackground="#ffffff", bordercolor="#cccccc", 
                   lightcolor="#eeeeee", darkcolor="#aaaaaa", padding=5)
