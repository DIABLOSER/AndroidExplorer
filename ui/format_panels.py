#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk


class FormatPanelBuilder:
    """格式面板构建器"""
    
    @staticmethod
    def build_drawable_panel(parent, app):
        """构建Drawable格式面板"""
        header = tk.Frame(parent, bg=app.theme_manager.get_bg("sidebar"), height=32)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        title_label = tk.Label(header, text="资源命名格式", 
                              font=("Segoe UI", 9, "bold"),
                              bg=app.theme_manager.get_bg("sidebar"), 
                              fg=app.theme_manager.get_fg("sidebar_btn"),
                              pady=4)
        title_label.pack(side=tk.LEFT, padx=8)
        
        content = ttk.Frame(parent)
        content.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        FormatPanelBuilder._build_format_controls(
            content, app, "drawable",
            app.drawable_format_type, app.drawable_prefix, 
            app.drawable_keyword, app.drawable_suffix
        )
        
        app.drawable_format_preview = FormatPanelBuilder._build_preview(content)
        FormatPanelBuilder._build_hint(content, "关键词可用 {name}；后缀可用 {number:04d}、{random}")
    
    @staticmethod
    def build_layout_panel(parent, app):
        """构建Layout格式面板"""
        header = tk.Frame(parent, bg=app.theme_manager.get_bg("sidebar"), height=32)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        title_label = tk.Label(header, text="布局命名格式", 
                              font=("Segoe UI", 9, "bold"),
                              bg=app.theme_manager.get_bg("sidebar"), 
                              fg=app.theme_manager.get_fg("sidebar_btn"),
                              pady=4)
        title_label.pack(side=tk.LEFT, padx=8)
        
        content = ttk.Frame(parent)
        content.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        FormatPanelBuilder._build_format_controls(
            content, app, "layout",
            app.layout_format_type, app.layout_prefix, 
            app.layout_keyword, app.layout_suffix
        )
        
        app.layout_format_preview = FormatPanelBuilder._build_preview(content)
        
        # 预设按钮
        ttk.Label(content, text="预设:").pack(anchor=tk.W, pady=(6, 2))
        preset_f = ttk.Frame(content)
        preset_f.pack(fill=tk.X)
        for text, prefix, keyword, suffix in [
            ("Activity", "activity", "{name}", "{number:04d}"),
            ("Fragment", "fragment", "{name}", "{number:04d}"),
            ("Dialog", "dialog", "{name}", "{number:04d}"),
            ("Item", "item", "{name}", "{number:04d}"),
            ("Layout", "layout", "{name}", "{number:04d}"),
        ]:
            btn = ttk.Button(preset_f, text=text, 
                           command=lambda p=prefix, k=keyword, s=suffix: app.set_layout_preset(p, k, s))
            btn.pack(anchor=tk.W, pady=1, padx=2, fill=tk.X)
    
    @staticmethod
    def build_string_panel(parent, app):
        """构建String格式面板"""
        header = tk.Frame(parent, bg=app.theme_manager.get_bg("sidebar"), height=32)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        title_label = tk.Label(header, text="字符命名格式", 
                              font=("Segoe UI", 9, "bold"),
                              bg=app.theme_manager.get_bg("sidebar"), 
                              fg=app.theme_manager.get_fg("sidebar_btn"),
                              pady=4)
        title_label.pack(side=tk.LEFT, padx=8)
        
        content = ttk.Frame(parent)
        content.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        FormatPanelBuilder._build_format_controls(
            content, app, "string",
            app.string_format_type, app.string_prefix, 
            app.string_keyword, app.string_suffix
        )
        
        app.string_format_preview = FormatPanelBuilder._build_preview(content)
        FormatPanelBuilder._build_hint(content, "关键词可用 {name}；后缀可用 {number:04d}、{random}")
    
    @staticmethod
    def build_id_panel(parent, app):
        """构建ID格式面板"""
        header = tk.Frame(parent, bg=app.theme_manager.get_bg("sidebar"), height=32)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        title_label = tk.Label(header, text="ID命名格式", 
                              font=("Segoe UI", 9, "bold"),
                              bg=app.theme_manager.get_bg("sidebar"), 
                              fg=app.theme_manager.get_fg("sidebar_btn"),
                              pady=4)
        title_label.pack(side=tk.LEFT, padx=8)
        
        content = ttk.Frame(parent)
        content.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        FormatPanelBuilder._build_format_controls(
            content, app, "id",
            app.id_format_type, app.id_prefix, 
            app.id_keyword, app.id_suffix
        )
        
        app.id_format_preview = FormatPanelBuilder._build_preview(content)
        FormatPanelBuilder._build_hint(content, "用于重命名 @+id/xxx，引用将同步更新")
    
    @staticmethod
    def build_class_panel(parent, app):
        """构建Class格式面板"""
        header = tk.Frame(parent, bg=app.theme_manager.get_bg("sidebar"), height=32)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        title_label = tk.Label(header, text="类名命名格式", 
                              font=("Segoe UI", 9, "bold"),
                              bg=app.theme_manager.get_bg("sidebar"), 
                              fg=app.theme_manager.get_fg("sidebar_btn"),
                              pady=4)
        title_label.pack(side=tk.LEFT, padx=8)
        
        content = ttk.Frame(parent)
        content.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        FormatPanelBuilder._build_format_controls(
            content, app, "class",
            app.class_format_type, app.class_prefix, 
            app.class_keyword, app.class_suffix
        )
        
        # 过滤字符
        ttk.Label(content, text="过滤字符:").pack(anchor=tk.W, pady=(0, 0))
        app.class_filter_entry = ttk.Entry(content, textvariable=app.class_filter_chars)
        app.class_filter_entry.pack(fill=tk.X, pady=(0, 6))
        
        app.class_format_preview = FormatPanelBuilder._build_preview(content)
        FormatPanelBuilder._build_hint(content, "重命名.java文件，更新AndroidManifest.xml和import引用")
        FormatPanelBuilder._build_hint(content, "过滤字符：从原类名中移除指定字符（如Activity）")
    
    @staticmethod
    def _build_format_controls(parent, app, type_name, format_type_var, prefix_var, keyword_var, suffix_var):
        """构建格式控制组件"""
        ttk.Label(parent, text="格式:").pack(anchor=tk.W, pady=(0, 2))
        ftype = ttk.Frame(parent)
        ftype.pack(fill=tk.X, pady=(0, 6))
        ttk.Radiobutton(ftype, text="前缀_关键词_后缀", variable=format_type_var, 
                       value="prefix_keyword_number").pack(anchor=tk.W)
        ttk.Radiobutton(ftype, text="关键词_前缀_后缀", variable=format_type_var, 
                       value="keyword_prefix_number").pack(anchor=tk.W)
        ttk.Radiobutton(ftype, text="前缀_后缀_关键词", variable=format_type_var, 
                       value="prefix_number_keyword").pack(anchor=tk.W)
        
        ttk.Label(parent, text="前缀:").pack(anchor=tk.W, pady=(4, 0))
        entry = ttk.Entry(parent, textvariable=prefix_var)
        entry.pack(fill=tk.X, pady=(0, 4))
        setattr(app, f"{type_name}_prefix_entry", entry)
        
        ttk.Label(parent, text="关键词:").pack(anchor=tk.W, pady=(0, 0))
        entry = ttk.Entry(parent, textvariable=keyword_var)
        entry.pack(fill=tk.X, pady=(0, 4))
        setattr(app, f"{type_name}_keyword_entry", entry)
        
        ttk.Label(parent, text="后缀:").pack(anchor=tk.W, pady=(0, 0))
        entry = ttk.Entry(parent, textvariable=suffix_var)
        entry.pack(fill=tk.X, pady=(0, 6))
        setattr(app, f"{type_name}_suffix_entry", entry)
    
    @staticmethod
    def _build_preview(parent):
        """构建预览标签"""
        prev_f = ttk.Frame(parent)
        prev_f.pack(fill=tk.X, pady=(0, 2))
        ttk.Label(prev_f, text="预览:").pack(side=tk.LEFT, padx=(0, 4))
        preview_label = ttk.Label(prev_f, text="", foreground="blue")
        preview_label.pack(side=tk.LEFT)
        return preview_label
    
    @staticmethod
    def _build_hint(parent, text):
        """构建提示文本"""
        ttk.Label(parent, text=text, font=("", 8), foreground="gray").pack(anchor=tk.W, pady=(0, 4))
