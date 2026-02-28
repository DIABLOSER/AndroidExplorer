#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
import random
import string
import threading
from collections import OrderedDict
import datetime
import xml.etree.ElementTree as ET

# 导入核心模块
from core import ResourceScanner, ResourceRenamer, ClassRenamer
# 导入UI组件
from ui import ToolTip, ThemeManager
# 导入工具函数
from utils import FormatHelper, FileHelper


class AndroidResourceRenamerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Android Explorer v1.0")
        self.root.geometry("1100x780")
        self.root.minsize(900, 600)
        
        # Performance optimization: disable automatic updates during layout changes
        self.root.update_idletasks()
        
        # 设置样式
        style = ttk.Style()
        style.theme_use('clam')
        
        # 变量
        self.project_path = tk.StringVar()
        
        # 模块选择（新增）
        self.module_selection = tk.StringVar(value="全部模块")
        self.modules = ["全部模块"]
        self.module_paths = {"全部模块": Path('.')}
        
        # Performance flag for resize events
        self._is_resizing = False
        self._resize_timer = None
        
        # Drawable相关变量
        self.drawable_prefix = tk.StringVar(value="icon_")
        self.drawable_keyword = tk.StringVar(value="{name}_")
        self.drawable_suffix = tk.StringVar(value="{number:04d}")
        self.drawable_format_type = tk.StringVar(value="prefix_keyword_number")  # 格式类型
        
        # Layout相关变量
        self.layout_prefix = tk.StringVar(value="activity_")
        self.layout_keyword = tk.StringVar(value="{name}_")
        self.layout_suffix = tk.StringVar(value="{number:04d}")
        self.layout_format_type = tk.StringVar(value="prefix_keyword_number")

        # String资源相关变量
        self.string_prefix = tk.StringVar(value="str_")
        self.string_keyword = tk.StringVar(value="{name}_")
        self.string_suffix = tk.StringVar(value="{number:04d}")
        self.string_format_type = tk.StringVar(value="prefix_keyword_number")
        self.string_mapping = OrderedDict()
        self.string_files = []
        self.string_entries = []  # 从 values/strings.xml 解析出的 (name, value_preview) 列表

        # ID资源相关变量（来自 layout/*.xml 的 @+id/...）
        self.id_prefix = tk.StringVar(value="id_")
        self.id_keyword = tk.StringVar(value="{name}_")
        self.id_suffix = tk.StringVar(value="{number:04d}")
        self.id_format_type = tk.StringVar(value="prefix_keyword_number")
        self.id_mapping = OrderedDict()
        self.id_entries = []
        self.id_layout_files = []
        
        # Java类相关变量
        self.class_prefix = tk.StringVar(value="")
        self.class_keyword = tk.StringVar(value="{name}")
        self.class_suffix = tk.StringVar(value="{number:04d}")
        self.class_format_type = tk.StringVar(value="prefix_keyword_number")
        self.class_filter_chars = tk.StringVar(value="")  # 要过滤的字符
        self.class_mapping = OrderedDict()
        self.class_files = []  # Java文件列表
        
        # Preview label attributes (initialized as None to prevent AttributeError)
        self.drawable_format_preview = None
        self.layout_format_preview = None
        self.string_format_preview = None
        self.id_format_preview = None
        self.class_format_preview = None
        
        self.preview_mode = tk.BooleanVar(value=True)
        self.update_references = tk.BooleanVar(value=True)
        self.include_subdirs = tk.BooleanVar(value=True)
        self.resource_type = tk.StringVar(value="both")  # drawable, layout, both
        
        # 数据
        self.drawable_mapping = OrderedDict()
        self.layout_mapping = OrderedDict()
        self.drawable_files = []
        self.layout_files = []
        self.mapping_file_path = None

        # 主题: Light / Dark
        self.theme_mode = tk.StringVar(value="Light")
        
        # 初始化主题管理器
        self.theme_manager = ThemeManager(self.theme_mode)
        
        # 设置主题颜色（用于向后兼容）
        self._setup_theme_colors()

        # 拆分后的工具类
        self.scanner = ResourceScanner(self.module_selection, self.module_paths, log_func=self.log)
        self.renamer = ResourceRenamer(log_func=self.log)
        self.class_renamer = ClassRenamer(log_func=self.log)

        # 创建界面
        self.create_widgets()
        
        # 绑定事件
        self.drawable_prefix.trace('w', lambda *args: self.update_drawable_format())
        self.drawable_keyword.trace('w', lambda *args: self.update_drawable_format())
        self.drawable_suffix.trace('w', lambda *args: self.update_drawable_format())
        self.drawable_format_type.trace('w', lambda *args: self.update_drawable_format_preset())
        
        self.layout_prefix.trace('w', lambda *args: self.update_layout_format())
        self.layout_keyword.trace('w', lambda *args: self.update_layout_format())
        self.layout_suffix.trace('w', lambda *args: self.update_layout_format())
        self.layout_format_type.trace('w', lambda *args: self.update_layout_format_preset())
        
        self.string_prefix.trace('w', lambda *args: self.update_string_format())
        self.string_keyword.trace('w', lambda *args: self.update_string_format())
        self.string_suffix.trace('w', lambda *args: self.update_string_format())
        self.string_format_type.trace('w', lambda *args: self.update_string_format_preset())

        self.id_prefix.trace('w', lambda *args: self.update_id_format())
        self.id_keyword.trace('w', lambda *args: self.update_id_format())
        self.id_suffix.trace('w', lambda *args: self.update_id_format())
        self.id_format_type.trace('w', lambda *args: self.update_id_format_preset())
        
        self.class_prefix.trace('w', lambda *args: self.update_class_format())
        self.class_keyword.trace('w', lambda *args: self.update_class_format())
        self.class_suffix.trace('w', lambda *args: self.update_class_format())
        self.class_format_type.trace('w', lambda *args: self.update_class_format_preset())
        self.class_filter_chars.trace('w', lambda *args: self.update_class_format())
        
        self.resource_type.trace('w', lambda *args: self.on_resource_type_change())
        # 模块变更时重新扫描
        self.module_selection.trace('w', lambda *args: self.on_resource_type_change())

        # Set initial selection state (资源)
        self._update_button_state(self._nav_buttons["资源"])

        # Update format previews (safe with null checks)
        self.update_drawable_format()
        self.update_layout_format()
        self.update_string_format()
        self.update_id_format()
        self.update_class_format()

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

    def _menu_file(self):
        """顶部菜单：文件（浏览项目）"""
        self.browse_project()

    def create_widgets(self):
        """创建界面组件 - 系统标题栏 + 其下菜单栏"""
        self.root.configure(bg=self.theme_manager.get_bg("main"))
        # 配置TTK样式
        self.theme_manager.setup_ttk_styles()
        
        # 菜单栏（位于系统标题栏下方）
        menubar_frame = tk.Frame(self.root, height=32, bg=self.theme_manager.get_bg("menubar"), cursor="hand2")  # Reduced height
        menubar_frame.pack(fill=tk.X)
        menubar_frame.pack_propagate(False)
        menubar_bg = self._bg("menubar")
        menubar_fg = self._fg("menubar")
        for label, cmd in [
            ("文件", self._menu_file),
            ("关于", self._menu_about),
            ("生成映射", self.generate_mapping),
            ("应用修改", self._mapping_apply_current),
            ("重置", self._mapping_reset_current),
            ("清空", self._mapping_clear_current),
            ("导入映射", self.import_mapping),
            ("反向映射", self._mapping_reverse_current),
            ("导出映射", self.export_mapping),
            ("执行", self._menu_execute),
        ]:
            lbl = tk.Label(menubar_frame, text=label, font=("Segoe UI", 9, "bold"),
                           bg=menubar_bg, fg=menubar_fg, cursor="hand2",
                           padx=10, pady=6, relief="flat")  # Reduced padding
            lbl.pack(side=tk.LEFT)
            lbl.bind("<Button-1>", lambda e, c=cmd: c())
            lbl.bind("<Enter>", lambda e, w=lbl: w.configure(bg="#007acc", fg="#ffffff"))
            lbl.bind("<Leave>", lambda e, w=lbl: w.configure(bg=menubar_bg, fg=menubar_fg))
        
        # Add separator before module selection
        ttk.Separator(menubar_frame, orient='vertical').pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=4)  # Reduced padding
        
        self.module_combobox = ttk.Combobox(menubar_frame, textvariable=self.module_selection,
                                            values=self.modules, state="readonly", width=18, height=15)
        self.module_combobox.pack(side=tk.LEFT, padx=(4, 12), pady=4)  # Reduced padding
        
        # Add separator before options
        ttk.Separator(menubar_frame, orient='vertical').pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=4)  # Reduced padding
        
        tk.Label(menubar_frame, text="选项", font=("Segoe UI", 9, "bold"),
                 bg=menubar_bg, fg=menubar_fg, padx=4).pack(side=tk.LEFT, pady=4)
        opt_frame = tk.Frame(menubar_frame, bg=menubar_bg)
        opt_frame.pack(side=tk.LEFT, pady=4)
        self.cb_preview = ttk.Checkbutton(opt_frame, text="预览", variable=self.preview_mode)
        self.cb_preview.pack(side=tk.LEFT, padx=3)  # Reduced padding
        self.cb_update_ref = ttk.Checkbutton(opt_frame, text="更新引用", variable=self.update_references)
        self.cb_update_ref.pack(side=tk.LEFT, padx=3)  # Reduced padding
        self.cb_subdirs = ttk.Checkbutton(opt_frame, text="子目录", variable=self.include_subdirs)
        self.cb_subdirs.pack(side=tk.LEFT, padx=3)  # Reduced padding

        main_container = tk.Frame(self.root, bg=self._bg("main"))
        main_container.pack(fill=tk.BOTH, expand=True)

        # ========== 主内容区：左 | 中 | 右（VS Code 三栏） ==========
        content_paned = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
        content_paned.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        # ----- 左侧边栏（含竖线分隔） -----
        left_outer = ttk.Frame(content_paned, padding=0)
        content_paned.add(left_outer, weight=0)
        # left_wrapper = tk.Frame(left_outer, bg=self._bg("sidebar_border"), width=1)
        # left_wrapper.pack(side=tk.RIGHT, fill=tk.Y)
        left_inner = tk.Frame(left_outer, bg=self._bg("sidebar"), width=240)  # Reduced width
        left_inner.pack(fill=tk.BOTH, expand=True)
        left_inner.pack_propagate(False)

        # 五个视图切换按钮（VS Code 活动栏风格）
        btn_frame = tk.Frame(left_inner, bg=self._bg("sidebar"), height=36)  # Reduced height
        btn_frame.pack(fill=tk.X)
        btn_frame.pack_propagate(False)
        self._left_active = tk.StringVar(value="资源")
        
        # Store button references for selection state management
        self._nav_buttons = {}
        
        for name, key in [("资源", "资源"), ("布局", "布局"), ("字符", "字符"), ("ID", "ID"), ("类名", "类名")]:
            b = tk.Button(btn_frame, text=name, relief=tk.FLAT, font=("Segoe UI", 9, "bold"),
                          bd=0, bg=self._bg("sidebar_btn"), fg=self._fg("sidebar_btn"),
                          activebackground="#007acc", activeforeground="#ffffff",
                          highlightthickness=0, padx=8, pady=6,
                          command=lambda k=key: self._switch_left_view(k))
            b.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1, pady=2)
            b.bind("<Enter>", lambda e, w=b: w.configure(bg="#007acc", fg="#ffffff"))
            b.bind("<Leave>", lambda e, w=b: self._update_button_state(w))
            self._nav_buttons[key] = b
        
        # Set initial selection state (资源)
        self._update_button_state(self._nav_buttons["资源"])

        # 左侧堆叠内容（资源列表 / 布局列表 / 字符列表 / ID列表 / 类名列表）
        self._left_stack = tk.Frame(left_inner, bg=self._bg("sidebar"))
        self._left_stack.pack(fill=tk.BOTH, expand=True, pady=2)  # Reduced padding

        # Create left sidebar frames
        self._left_drawable_frame = tk.Frame(self._left_stack, bg=self._bg("sidebar"))
        list_frame = ttk.Frame(self._left_drawable_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.drawable_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, height=15,
                                           bg=self._bg("listbox"), fg=self._fg("listbox"),
                                           selectbackground=self._bg("listbox_sel"), selectforeground=self._fg("listbox_sel"),
                                           bd=0, highlightthickness=0)
        self.drawable_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.drawable_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar.pack_forget()
        self.drawable_listbox.configure(yscrollcommand=scrollbar.set)
        count_label = ttk.Label(self._left_drawable_frame, text="共 0 个文件", font=("Segoe UI", 8), foreground="gray")
        count_label.pack(anchor=tk.W, padx=4, pady=(2, 4))

        self._left_layout_frame = tk.Frame(self._left_stack, bg=self._bg("sidebar"))
        list_frame = ttk.Frame(self._left_layout_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.layout_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, height=15,
                                         bg=self._bg("listbox"), fg=self._fg("listbox"),
                                         selectbackground=self._bg("listbox_sel"), selectforeground=self._fg("listbox_sel"),
                                         bd=0, highlightthickness=0)
        self.layout_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.layout_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar.pack_forget()
        self.layout_listbox.configure(yscrollcommand=scrollbar.set)
        count_label = ttk.Label(self._left_layout_frame, text="共 0 个文件", font=("Segoe UI", 8), foreground="gray")
        count_label.pack(anchor=tk.W, padx=4, pady=(2, 4))

        self._left_string_frame = tk.Frame(self._left_stack, bg=self._bg("sidebar"))
        list_frame = ttk.Frame(self._left_string_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.string_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, height=15,
                                         bg=self._bg("listbox"), fg=self._fg("listbox"),
                                         selectbackground=self._bg("listbox_sel"), selectforeground=self._fg("listbox_sel"),
                                         bd=0, highlightthickness=0)
        self.string_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.string_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar.pack_forget()
        self.string_listbox.configure(yscrollcommand=scrollbar.set)
        count_label = ttk.Label(self._left_string_frame, text="共 0 个文件", font=("Segoe UI", 8), foreground="gray")
        count_label.pack(anchor=tk.W, padx=4, pady=(2, 4))

        self._left_id_frame = tk.Frame(self._left_stack, bg=self._bg("sidebar"))
        list_frame = ttk.Frame(self._left_id_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.id_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, height=15,
                                     bg=self._bg("listbox"), fg=self._fg("listbox"),
                                     selectbackground=self._bg("listbox_sel"), selectforeground=self._fg("listbox_sel"),
                                     bd=0, highlightthickness=0)
        self.id_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.id_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar.pack_forget()
        self.id_listbox.configure(yscrollcommand=scrollbar.set)
        count_label = ttk.Label(self._left_id_frame, text="共 0 个ID", font=("Segoe UI", 8), foreground="gray")
        count_label.pack(anchor=tk.W, padx=4, pady=(2, 4))

        # 类名列表 frame
        self._left_class_frame = tk.Frame(self._left_stack, bg=self._bg("sidebar"))
        list_frame = ttk.Frame(self._left_class_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.class_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, height=15,
                                        bg=self._bg("listbox"), fg=self._fg("listbox"),
                                        selectbackground=self._bg("listbox_sel"), selectforeground=self._fg("listbox_sel"),
                                        bd=0, highlightthickness=0)
        self.class_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.class_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar.pack_forget()
        self.class_listbox.configure(yscrollcommand=scrollbar.set)
        self.class_count_label = ttk.Label(self._left_class_frame, text="共 0 个类", font=("Segoe UI", 8), foreground="gray")
        self.class_count_label.pack(anchor=tk.W, padx=4, pady=(2, 4))

        # 默认显示资源列表
        self._left_drawable_frame.pack(fill=tk.BOTH, expand=True)
        # Hide other frames initially
        self._left_layout_frame.pack_forget()
        self._left_string_frame.pack_forget()
        self._left_id_frame.pack_forget()
        self._left_class_frame.pack_forget()

        # ----- 中间栏：工作区 + 日志（左中右三栏之「中」） -----
        center_frame = ttk.Frame(content_paned, padding=2)
        content_paned.add(center_frame, weight=1)
        center_paned = ttk.PanedWindow(center_frame, orient=tk.VERTICAL)
        center_paned.pack(fill=tk.BOTH, expand=True)
        work_frame = ttk.Frame(center_paned)
        center_paned.add(work_frame, weight=2)
        # 中间工作区直接显示映射编辑内容（不再使用外层标签）
        mapping_frame = ttk.Frame(work_frame)
        mapping_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 2))
        
        # 标题栏（与左侧按钮样式一致）
        mapping_header = tk.Frame(mapping_frame, bg=self._bg("sidebar"), height=32)
        mapping_header.pack(fill=tk.X)
        mapping_header.pack_propagate(False)
        
        self._mapping_display_type = "drawable"
        self._mapping_title_var = tk.StringVar(value="Drawable 映射")
        title_label = tk.Label(mapping_header, textvariable=self._mapping_title_var, 
                              font=("Segoe UI", 9, "bold"),
                              bg=self._bg("sidebar"), fg=self._fg("sidebar_btn"),
                              pady=4)
        title_label.pack(side=tk.LEFT, padx=8)
        
        self.mapping_text = scrolledtext.ScrolledText(
            mapping_frame,
            height=20,
            wrap=tk.WORD,
            bg=self._bg("editor"),
            fg=self._fg("editor"),
            bd=0,
            relief=tk.FLAT,
            highlightthickness=0,
        )
        self.mapping_text.vbar.configure(width=9)
        self.mapping_text.vbar.pack_forget()
        self.mapping_text.pack(fill=tk.BOTH, expand=True, pady=2)
        # 中间栏下半：日志
        log_frame = ttk.Frame(center_paned, padding=2)
        center_paned.add(log_frame, weight=1)
        
        # 日志标题栏
        log_header = tk.Frame(log_frame, bg=self._bg("editor"), height=24)
        log_header.pack(fill=tk.X)
        log_header.pack_propagate(False)
        log_title = tk.Label(log_header, text="日志", 
                            font=("Segoe UI", 9, "bold"),
                            bg=self._bg("editor"), fg=self._fg("editor"))
        log_title.pack(side=tk.LEFT, padx=8)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=5,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg=self._bg("editor"),
            fg=self._fg("editor"),
            bd=0,
            relief=tk.FLAT,
            highlightthickness=0,
        )
        self.log_text.vbar.configure(width=9)
        self.log_text.vbar.pack_forget()
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.status_var = tk.StringVar(value="就绪")

        # ----- 右侧边栏（含竖线分隔） -----
        right_outer = ttk.Frame(content_paned, padding=0)
        content_paned.add(right_outer, weight=0)
        right_border = tk.Frame(right_outer, bg=self._bg("sidebar_border"), width=1)
        right_border.pack(side=tk.LEFT, fill=tk.Y)
        right_inner = tk.Frame(right_outer, bg=self._bg("sidebar"), width=260)  # Slightly reduced width
        right_inner.pack(fill=tk.BOTH, expand=True)
        right_inner.pack_propagate(False)
        # ttk.Label(right_inner, text="命名格式", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=(8, 6), padx=6)  # Reduced padding
        
        # 右侧内容面板容器（由左侧菜单控制）
        self._right_content_frame = tk.Frame(right_inner, bg=self._bg("sidebar"))
        self._right_content_frame.pack(fill=tk.BOTH, expand=True, pady=2)

        # 创建各个格式设置面板
        self._drawable_format_panel = ttk.Frame(self._right_content_frame)
        self._build_drawable_format_ui(self._drawable_format_panel)

        self._layout_format_panel = ttk.Frame(self._right_content_frame)
        self._build_layout_format_ui(self._layout_format_panel)

        self._string_format_panel = ttk.Frame(self._right_content_frame)
        self._build_string_format_ui(self._string_format_panel)

        self._id_format_panel = ttk.Frame(self._right_content_frame)
        self._build_id_format_ui(self._id_format_panel)

        self._class_format_panel = ttk.Frame(self._right_content_frame)
        self._build_class_format_ui(self._class_format_panel)

        # 默认显示资源面板
        self._drawable_format_panel.pack(fill=tk.BOTH, expand=True)

        # 底部状态栏（VS Code 风格：蓝条白字）
        status_bg = self._bg("statusbar") or "#007acc"
        status_fg = (self._theme_light if self.theme_mode.get() == "Light" else self._theme_dark).get("statusbar_fg", "#ffffff")
        self._status_frame = tk.Frame(main_container, height=24, bg=status_bg)
        self._status_frame.pack(fill=tk.X)
        self._status_frame.pack_propagate(False)
        self._status_label = tk.Label(self._status_frame, textvariable=self.status_var, font=("Segoe UI", 9),
                 bg=status_bg, fg=status_fg)
        self._status_label.pack(side=tk.LEFT, padx=(10, 0), pady=2)

        self.update_drawable_format()
        self.update_layout_format()
        self.update_string_format()
        self.update_id_format()
        
        # 绑定listbox的tooltip和点击事件
        self._bind_listbox_tooltips()

    def _bind_listbox_tooltips(self):
        """为所有listbox绑定tooltip显示完整路径"""
        # Drawable listbox
        if hasattr(self, 'drawable_listbox'):
            self._setup_listbox_tooltip(self.drawable_listbox, self.drawable_files)
        
        # Layout listbox
        if hasattr(self, 'layout_listbox'):
            self._setup_listbox_tooltip(self.layout_listbox, self.layout_files)
        
        # Class listbox
        if hasattr(self, 'class_listbox'):
            self._setup_listbox_tooltip(self.class_listbox, self.class_files)
    
    def _setup_listbox_tooltip(self, listbox, file_list):
        """为listbox设置tooltip"""
        tooltip = ToolTip(listbox)
        
        def on_motion(event):
            # 获取鼠标位置对应的项
            index = listbox.nearest(event.y)
            if 0 <= index < len(file_list):
                file_path = file_list[index]
                # 显示完整路径
                tooltip.hide_tip()
                x = listbox.winfo_rootx() + event.x + 10
                y = listbox.winfo_rooty() + event.y + 10
                tooltip.show_tip(str(file_path), x, y)
        
        def on_leave(event):
            tooltip.hide_tip()
        
        def on_click(event):
            # 点击时在日志中显示完整路径
            index = listbox.nearest(event.y)
            if 0 <= index < len(file_list):
                file_path = file_list[index]
                self.log(f"文件路径: {file_path}")
        
        listbox.bind('<Motion>', on_motion)
        listbox.bind('<Leave>', on_leave)
        listbox.bind('<Button-1>', on_click)

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
        self._theme_light_fg = {"menubar": "#333333", "sidebar_btn": "#333333", "sidebar_btn_active": "#ffffff",
                               "editor": "#333333", "listbox": "#333333", "listbox_sel": "#ffffff"}
    def _setup_ttk_styles(self):
        """配置 ttk 样式（VS Code 风格）"""
        s = ttk.Style()
        bg_main = self._bg("main")
        bg_sidebar = self._bg("sidebar")
        fg = self._fg("editor") if self.theme_mode.get() == "Dark" else self._fg("editor")
        tab_bg = self._bg("tab_bg") if hasattr(self, "_theme_light") else "#f3f3f3"
        border = self._bg("sidebar_border") if self.theme_mode.get() == "Light" else self._bg("sidebar_border")
        s.configure("TFrame", background=bg_main)
        s.configure("TNotebook", background=bg_main, borderwidth=0)
        # Custom notebook tab styling to match left navigation buttons
        s.configure("TNotebook.Tab", padding=[12, 6], font=("Segoe UI", 9, "bold"),
                   background=self._bg("sidebar_btn"), foreground=self._fg("sidebar_btn"))
        s.map("TNotebook.Tab", 
              background=[("selected", "#007acc"), ("active", "#007acc")],
              foreground=[("selected", "#ffffff"), ("active", "#ffffff")])
        
        # Enhanced button styling with rounded appearance and hover effects
        s.configure("TButton", padding=[10, 4], font=("Segoe UI", 9), 
                   background="#007acc", foreground="#ffffff", 
                   relief="flat", borderwidth=0)
        s.map("TButton", 
              background=[("active", "#005a9e"), ("pressed", "#004a8c")],
              foreground=[("active", "#ffffff")])
        
        # Custom button style for primary actions
        s.configure("Primary.TButton", padding=[12, 6], font=("Segoe UI", 9, "bold"),
                   background="#007acc", foreground="#ffffff")
        s.map("Primary.TButton",
              background=[("active", "#005a9e"), ("pressed", "#004a8c")])
        
        s.configure("TLabelFrame", padding=2, font=("Segoe UI", 9))
        s.configure("TLabelFrame.Label", font=("Segoe UI", 9, "bold"))
        s.configure("TLabelframe", padding=2)
        
        # 美化Combobox下拉组件
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
        
        # 美化拖动条 - 窄而精致的分隔效果
        sash_color = "#e0e0e0" if self.theme_mode.get() == "Light" else "#404040"
        s.configure("TPanedwindow", background=sash_color, sashwidth=1, sashpad=0, sashrelief="flat")
        
        # Custom scrollbar styling - modern transparent appearance
        scrollbar_bg = self._bg("main")  # Transparent background matching main area
        scrollbar_trough = "#f0f0f0" if self.theme_mode.get() == "Light" else "#3a3a3a"
        scrollbar_thumb = "#c0c0c0" if self.theme_mode.get() == "Light" else "#666666"
        scrollbar_thumb_active = "#a0a0a0" if self.theme_mode.get() == "Light" else "#888888"
        
        # Vertical scrollbar
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
        
        # Horizontal scrollbar  
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
        
        # Entry widget styling
        s.configure("TEntry", fieldbackground="#ffffff", bordercolor="#cccccc", 
                   lightcolor="#eeeeee", darkcolor="#aaaaaa", padding=5)
        
        # Combobox styling
        s.configure("TCombobox", fieldbackground="#ffffff", bordercolor="#cccccc", 
                   arrowcolor="#333333", padding=5)

    def _bg(self, key):
        if self.theme_mode.get() == "Light":
            return self._theme_light.get(key, "#ffffff")
        return self._theme_dark.get(key, "#252526")

    def _fg(self, key):
        if self.theme_mode.get() == "Light":
            return self._theme_light_fg.get(key, "#000000")
        return self._theme_dark.get(key + "_fg", "#cccccc")

    def _build_project_panel(self, parent):
        """左侧「项目」面板：显示项目信息"""
        ttk.Label(parent, text="项目信息", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, padx=4, pady=(4, 2))
        
        # 显示项目路径
        info_frame = ttk.Frame(parent)
        info_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        ttk.Label(info_frame, text="项目路径:", font=("Segoe UI", 9)).pack(anchor=tk.W, pady=(0, 4))
        self._project_path_label = ttk.Label(info_frame, text="未选择项目", 
                                             font=("Segoe UI", 9), foreground="gray",
                                             wraplength=200)
        self._project_path_label.pack(anchor=tk.W, pady=(0, 12))
        
        ttk.Label(info_frame, text="使用顶部菜单「文件」选择项目路径", 
                 font=("Segoe UI", 8), foreground="gray",
                 wraplength=200).pack(anchor=tk.W, pady=(0, 4))

    def _menu_file(self):
        """顶部菜单：文件（浏览项目）"""
        self.browse_project()

    def _menu_about(self):
        """顶部菜单：关于"""
        win = tk.Toplevel(self.root)
        win.title("关于")
        win.geometry("360x150")
        win.transient(self.root)
        win.resizable(False, False)
        
        # 居中显示
        win.update_idletasks()
        x = (win.winfo_screenwidth() // 2) - (360 // 2)
        y = (win.winfo_screenheight() // 2) - (150 // 2)
        win.geometry(f"360x150+{x}+{y}")
        
        # 内容区域
        content_frame = ttk.Frame(win, padding=20)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(content_frame, text="Android 资源重命名工具", 
                 font=("Segoe UI", 12, "bold")).pack(pady=(0, 15))
        
        ttk.Label(content_frame, text="作者：大菠萝", 
                 font=("Segoe UI", 10)).pack(pady=3)
        
        ttk.Label(content_frame, text="邮箱：daboluo719@gmail.com", 
                 font=("Segoe UI", 10)).pack(pady=3)
        
        ttk.Button(content_frame, text="关闭", command=win.destroy).pack(pady=(15, 0))

    def _menu_execute(self):
        """顶部菜单：执行"""
        self.execute_rename()

    def _build_drawable_format_ui(self, parent):
        """构建可绘制格式的UI"""
        win = Toplevel(self.root)
        win.title("可绘制格式")
        win.geometry("400x300")

        ttk.Label(win, text="格式名称").grid(row=0, column=0, padx=8, pady=12)
        ttk.Entry(win, textvariable=self.drawable_format_name).grid(row=0, column=1, padx=8, pady=12)

        ttk.Label(win, text="格式描述").grid(row=1, column=0, padx=8, pady=12)
        ttk.Entry(win, textvariable=self.drawable_format_description).grid(row=1, column=1, padx=8, pady=12)

        ttk.Button(win, text="关闭", command=win.destroy).grid(row=2, column=1, padx=8, pady=12)

    def _refresh_project_tree(self):
        """根据当前项目路径刷新左侧项目树"""
        if not hasattr(self, "_project_tree"):
            return
        self._project_tree.delete(*self._project_tree.get_children(""))

        path_str = self.project_path.get().strip()
        if not path_str:
            return
        root_path = Path(path_str)
        if not root_path.exists() or not root_path.is_dir():
            return
        root_name = root_path.name or path_str
        self._project_tree.insert("", "end", iid=path_str, text=root_name, open=False)
        self._insert_project_tree_children(path_str, root_path)

    def build_format_string(self, fmt_type, prefix, keyword, suffix):
        """构建格式预览字符串"""
        return FormatHelper.build_format_string(fmt_type, prefix, keyword, suffix)

    def _insert_project_tree_children(self, parent_iid, dir_path):
        """向项目树中插入目录下的子项（仅一层）；跳过占位符子节点"""
        try:
            children = self._project_tree.get_children(parent_iid)
            for cid in children:
                if cid.endswith("_placeholder"):
                    self._project_tree.delete(cid)
                    break
        except Exception:
            pass
        skip_names = {".git", ".idea", "build", ".gradle", "node_modules"}
        try:
            entries = sorted(dir_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            for p in entries:
                if p.name.startswith(".") and p.name not in (".gradle",):
                    if p.name in skip_names or p.is_dir():
                        continue
                iid = str(p.resolve())
                if p.is_dir():
                    self._project_tree.insert(parent_iid, "end", iid=iid, text=p.name, open=False)
                    self._project_tree.insert(parent_iid, "end", iid=iid + "_placeholder", text="...")
                else:
                    self._project_tree.insert(parent_iid, "end", iid=iid, text=p.name)
        except (PermissionError, OSError):
            pass

    def _on_project_tree_open(self, event):
        """展开项目树节点时懒加载子节点"""
        tree = self._project_tree
        sel = tree.focus()
        if not sel:
            return
        children = tree.get_children(sel)
        for cid in children:
            if cid.endswith("_placeholder"):
                try:
                    dir_path = Path(sel)
                    if dir_path.is_dir():
                        tree.delete(cid)
                        self._insert_project_tree_children(sel, dir_path)
                except Exception:
                    pass
                break

    def _on_project_tree_double_click(self, event):
        """双击项目树节点：仅展开/收起目录，不在中间区打开文件"""
        tree = self._project_tree
        sel = tree.focus()
        if not sel or sel.endswith("_placeholder"):
            return
        try:
            path = Path(sel)
        except Exception:
            return
        if not path.exists() or not path.is_dir():
            return
        tree.item(sel, open=not tree.item(sel, "open"))

    def _switch_left_view(self, key):
        """切换左侧视图：资源 / 布局 / 字符 / ID / 类名"""
        self._left_active.set(key)
        
        # 隐藏所有左侧面板
        self._left_drawable_frame.pack_forget()
        self._left_layout_frame.pack_forget()
        self._left_string_frame.pack_forget()
        self._left_id_frame.pack_forget()
        self._left_class_frame.pack_forget()
        
        # 隐藏所有右侧面板
        self._drawable_format_panel.pack_forget()
        self._layout_format_panel.pack_forget()
        self._string_format_panel.pack_forget()
        self._id_format_panel.pack_forget()
        self._class_format_panel.pack_forget()
        
        # 根据选择显示对应的左侧和右侧面板
        if key == "资源":
            self._left_drawable_frame.pack(fill=tk.BOTH, expand=True)
            self._drawable_format_panel.pack(fill=tk.BOTH, expand=True)
        elif key == "布局":
            self._left_layout_frame.pack(fill=tk.BOTH, expand=True)
            self._layout_format_panel.pack(fill=tk.BOTH, expand=True)
        elif key == "字符":
            self._left_string_frame.pack(fill=tk.BOTH, expand=True)
            self._string_format_panel.pack(fill=tk.BOTH, expand=True)
        elif key == "ID":
            self._left_id_frame.pack(fill=tk.BOTH, expand=True)
            self._id_format_panel.pack(fill=tk.BOTH, expand=True)
        else:  # 类名
            self._left_class_frame.pack(fill=tk.BOTH, expand=True)
            self._class_format_panel.pack(fill=tk.BOTH, expand=True)

        # 同步中间映射编辑区显示类型（仅切到资源相关视图时）
        key_to_type = {"资源": "drawable", "布局": "layout", "字符": "string", "ID": "id", "类名": "class"}
        if key in key_to_type:
            self.refresh_mapping_display(key_to_type[key])
        
        # Update button selection states
        for view_key, button in self._nav_buttons.items():
            if view_key == key:
                button.configure(bg="#007acc", fg="#ffffff")
            else:
                self._update_button_state(button)

    def _update_button_state(self, button):
        """Update button appearance based on whether it's the active view"""
        current_active = self._left_active.get()
        button_text = button.cget("text")
        # Map button text to view keys
        text_to_key = {"资源": "资源", "布局": "布局", "字符": "字符", "ID": "ID", "类名": "类名"}
        button_key = text_to_key.get(button_text)
        
        if button_key and button_key == current_active:
            button.configure(bg="#007acc", fg="#ffffff")
        else:
            button.configure(bg=self._bg("sidebar_btn"), fg=self._fg("sidebar_btn"))

    def _menu_execute(self):
        """顶部菜单：执行"""
        self.execute_rename()



    def _build_drawable_format_ui(self, parent):
        for project in self.projects:
            project_id = self.project_tree.insert("", "end", text=project.name)
            for file in project.files:
                self.project_tree.insert(project_id, "end", text=file.name)

    def _refresh_format_type(self, parent, current_active):
        ftype = ttk.Frame(parent)
        ftype.pack(fill=tk.X, pady=(0, 6))
        ttk.Radiobutton(ftype, text="前缀_关键词_后缀", variable=self.drawable_format_type, value="prefix_keyword_number").pack(anchor=tk.W)
        ttk.Radiobutton(ftype, text="关键词_前缀_后缀", variable=self.drawable_format_type, value="keyword_prefix_number").pack(anchor=tk.W)
        ttk.Radiobutton(ftype, text="前缀_后缀_关键词", variable=self.drawable_format_type, value="prefix_number_keyword").pack(anchor=tk.W)
        ttk.Label(parent, text="前缀:").pack(anchor=tk.W, pady=(4, 0))

        self.drawable_prefix_entry = ttk.Entry(parent, textvariable=self.drawable_prefix)
        self.drawable_prefix_entry.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(parent, text="关键词:").pack(anchor=tk.W, pady=(0, 0))
        self.drawable_keyword_entry = ttk.Entry(parent, textvariable=self.drawable_keyword)
        self.drawable_keyword_entry.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(parent, text="后缀:").pack(anchor=tk.W, pady=(0, 0))
        self.drawable_suffix_entry = ttk.Entry(parent, textvariable=self.drawable_suffix)
        self.drawable_suffix_entry.pack(fill=tk.X, pady=(0, 6))
        prev_f = ttk.Frame(parent)
        prev_f.pack(fill=tk.X, pady=(0, 2))
        ttk.Label(prev_f, text="预览:").pack(side=tk.LEFT, padx=(0, 4))
        self.drawable_format_preview = ttk.Label(prev_f, text="", foreground="blue")
        self.drawable_format_preview.pack(side=tk.LEFT)
        ttk.Label(parent, text="关键词可用 {name}；后缀可用 {number:04d}、{random}", font=("", 8), foreground="gray").pack(anchor=tk.W, pady=(0, 4))

    def _build_layout_format_ui(self, parent):
        """构建 Layout 格式设置区域（垂直排列）"""
        # 标题栏
        header = tk.Frame(parent, bg=self._bg("sidebar"), height=32)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        title_label = tk.Label(header, text="布局命名格式", 
                              font=("Segoe UI", 9, "bold"),
                              bg=self._bg("sidebar"), fg=self._fg("sidebar_btn"),
                              pady=4)
        title_label.pack(side=tk.LEFT, padx=8)
        
        # 内容区域
        content = ttk.Frame(parent)
        content.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        ttk.Label(content, text="格式:").pack(anchor=tk.W, pady=(0, 2))
        ftype = ttk.Frame(content)
        ftype.pack(fill=tk.X, pady=(0, 6))
        ttk.Radiobutton(ftype, text="前缀_关键词_后缀", variable=self.layout_format_type, value="prefix_keyword_number").pack(anchor=tk.W)
        ttk.Radiobutton(ftype, text="关键词_前缀_后缀", variable=self.layout_format_type, value="keyword_prefix_number").pack(anchor=tk.W)
        ttk.Radiobutton(ftype, text="前缀_后缀_关键词", variable=self.layout_format_type, value="prefix_number_keyword").pack(anchor=tk.W)
        ttk.Label(content, text="前缀:").pack(anchor=tk.W, pady=(4, 0))
        self.layout_prefix_entry = ttk.Entry(content, textvariable=self.layout_prefix)
        self.layout_prefix_entry.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(content, text="关键词:").pack(anchor=tk.W, pady=(0, 0))
        self.layout_keyword_entry = ttk.Entry(content, textvariable=self.layout_keyword)
        self.layout_keyword_entry.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(content, text="后缀:").pack(anchor=tk.W, pady=(0, 0))
        self.layout_suffix_entry = ttk.Entry(content, textvariable=self.layout_suffix)
        self.layout_suffix_entry.pack(fill=tk.X, pady=(0, 6))
        prev_f = ttk.Frame(content)
        prev_f.pack(fill=tk.X, pady=(0, 2))
        ttk.Label(prev_f, text="预览:").pack(side=tk.LEFT, padx=(0, 4))
        self.layout_format_preview = ttk.Label(prev_f, text="", foreground="blue")
        self.layout_format_preview.pack(side=tk.LEFT)
        ttk.Label(content, text="预设:").pack(anchor=tk.W, pady=(6, 2))
        preset_f = ttk.Frame(content)
        preset_f.pack(fill=tk.X)
        for text, prefix, keyword, suffix in [
            ("Activity", "activity_", "{name}_", "{number:04d}"),
            ("Fragment", "fragment_", "{name}_", "{number:04d}"),
            ("Dialog", "dialog_", "{name}_", "{number:04d}"),
            ("Item", "item_", "{name}_", "{number:04d}"),
            ("Layout", "layout_", "{name}_", "{number:04d}"),
        ]:
            btn = ttk.Button(preset_f, text=text, command=lambda p=prefix, k=keyword, s=suffix: self.set_layout_preset(p, k, s))
            btn.pack(anchor=tk.W, pady=1, padx=2, fill=tk.X)
    
    def _build_string_format_ui(self, parent):
        """构建 String 格式设置区域（垂直排列）"""
        # 标题栏
        header = tk.Frame(parent, bg=self._bg("sidebar"), height=32)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        title_label = tk.Label(header, text="字符命名格式", 
                              font=("Segoe UI", 9, "bold"),
                              bg=self._bg("sidebar"), fg=self._fg("sidebar_btn"),
                              pady=4)
        title_label.pack(side=tk.LEFT, padx=8)
        
        # 内容区域
        content = ttk.Frame(parent)
        content.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        ttk.Label(content, text="格式:").pack(anchor=tk.W, pady=(0, 2))
        ftype = ttk.Frame(content)
        ftype.pack(fill=tk.X, pady=(0, 6))
        ttk.Radiobutton(ftype, text="前缀_关键词_后缀", variable=self.string_format_type, value="prefix_keyword_number").pack(anchor=tk.W)
        ttk.Radiobutton(ftype, text="关键词_前缀_后缀", variable=self.string_format_type, value="keyword_prefix_number").pack(anchor=tk.W)
        ttk.Radiobutton(ftype, text="前缀_后缀_关键词", variable=self.string_format_type, value="prefix_number_keyword").pack(anchor=tk.W)
        ttk.Label(content, text="前缀:").pack(anchor=tk.W, pady=(4, 0))
        self.string_prefix_entry = ttk.Entry(content, textvariable=self.string_prefix)
        self.string_prefix_entry.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(content, text="关键词:").pack(anchor=tk.W, pady=(0, 0))
        self.string_keyword_entry = ttk.Entry(content, textvariable=self.string_keyword)
        self.string_keyword_entry.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(content, text="后缀:").pack(anchor=tk.W, pady=(0, 0))
        self.string_suffix_entry = ttk.Entry(content, textvariable=self.string_suffix)
        self.string_suffix_entry.pack(fill=tk.X, pady=(0, 6))
        prev_f = ttk.Frame(content)
        prev_f.pack(fill=tk.X, pady=(0, 2))
        ttk.Label(prev_f, text="预览:").pack(side=tk.LEFT, padx=(0, 4))
        self.string_format_preview = ttk.Label(prev_f, text="", foreground="blue")
        self.string_format_preview.pack(side=tk.LEFT)
        ttk.Label(content, text="关键词可用 {name}；后缀可用 {number:04d}、{random}", font=("", 8), foreground="gray").pack(anchor=tk.W, pady=(0, 4))

    def _build_id_format_ui(self, parent):
        """构建 ID 格式设置区域（垂直排列）"""
        # 标题栏（与工作区域标题一致）
        header = tk.Frame(parent, bg=self._bg("sidebar"), height=32)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        title_label = tk.Label(header, text="ID命名格式", 
                              font=("Segoe UI", 9, "bold"),
                              bg=self._bg("sidebar"), fg=self._fg("sidebar_btn"),
                              pady=4)
        title_label.pack(side=tk.LEFT, padx=8)
        
        # 内容区域
        content = ttk.Frame(parent)
        content.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        ttk.Label(content, text="格式:").pack(anchor=tk.W, pady=(0, 2))
        ftype = ttk.Frame(content)
        ftype.pack(fill=tk.X, pady=(0, 6))
        ttk.Radiobutton(ftype, text="前缀_关键词_后缀", variable=self.id_format_type, value="prefix_keyword_number").pack(anchor=tk.W)
        ttk.Radiobutton(ftype, text="关键词_前缀_后缀", variable=self.id_format_type, value="keyword_prefix_number").pack(anchor=tk.W)
        ttk.Radiobutton(ftype, text="前缀_后缀_关键词", variable=self.id_format_type, value="prefix_number_keyword").pack(anchor=tk.W)
        ttk.Label(content, text="前缀:").pack(anchor=tk.W, pady=(4, 0))
        self.id_prefix_entry = ttk.Entry(content, textvariable=self.id_prefix)
        self.id_prefix_entry.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(content, text="关键词:").pack(anchor=tk.W, pady=(0, 0))
        self.id_keyword_entry = ttk.Entry(content, textvariable=self.id_keyword)
        self.id_keyword_entry.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(content, text="后缀:").pack(anchor=tk.W, pady=(0, 0))
        self.id_suffix_entry = ttk.Entry(content, textvariable=self.id_suffix)
        self.id_suffix_entry.pack(fill=tk.X, pady=(0, 6))
        prev_f = ttk.Frame(content)
        prev_f.pack(fill=tk.X, pady=(0, 2))
        ttk.Label(prev_f, text="预览:").pack(side=tk.LEFT, padx=(0, 4))
        self.id_format_preview = ttk.Label(prev_f, text="", foreground="blue")
        self.id_format_preview.pack(side=tk.LEFT)
        ttk.Label(content, text="用于重命名 @+id/xxx，引用将同步更新", font=("", 8), foreground="gray").pack(anchor=tk.W, pady=(0, 4))

    def _build_class_format_ui(self, parent):
        """构建类名格式设置区域（垂直排列）"""
        # 标题栏（与工作区域标题一致）
        header = tk.Frame(parent, bg=self._bg("sidebar"), height=32)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        title_label = tk.Label(header, text="类名命名格式", 
                              font=("Segoe UI", 9, "bold"),
                              bg=self._bg("sidebar"), fg=self._fg("sidebar_btn"),
                              pady=4)
        title_label.pack(side=tk.LEFT, padx=8)
        
        # 内容区域
        content = ttk.Frame(parent)
        content.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        ttk.Label(content, text="格式:").pack(anchor=tk.W, pady=(0, 2))
        ftype = ttk.Frame(content)
        ftype.pack(fill=tk.X, pady=(0, 6))
        ttk.Radiobutton(ftype, text="前缀_关键词_后缀", variable=self.class_format_type, value="prefix_keyword_number").pack(anchor=tk.W)
        ttk.Radiobutton(ftype, text="关键词_前缀_后缀", variable=self.class_format_type, value="keyword_prefix_number").pack(anchor=tk.W)
        ttk.Radiobutton(ftype, text="前缀_后缀_关键词", variable=self.class_format_type, value="prefix_number_keyword").pack(anchor=tk.W)
        ttk.Label(content, text="前缀:").pack(anchor=tk.W, pady=(4, 0))
        self.class_prefix_entry = ttk.Entry(content, textvariable=self.class_prefix)
        self.class_prefix_entry.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(content, text="关键词:").pack(anchor=tk.W, pady=(0, 0))
        self.class_keyword_entry = ttk.Entry(content, textvariable=self.class_keyword)
        self.class_keyword_entry.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(content, text="后缀:").pack(anchor=tk.W, pady=(0, 0))
        self.class_suffix_entry = ttk.Entry(content, textvariable=self.class_suffix)
        self.class_suffix_entry.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(content, text="过滤字符:").pack(anchor=tk.W, pady=(0, 0))
        self.class_filter_entry = ttk.Entry(content, textvariable=self.class_filter_chars)
        self.class_filter_entry.pack(fill=tk.X, pady=(0, 6))
        prev_f = ttk.Frame(content)
        prev_f.pack(fill=tk.X, pady=(0, 2))
        ttk.Label(prev_f, text="预览:").pack(side=tk.LEFT, padx=(0, 4))
        self.class_format_preview = ttk.Label(prev_f, text="", foreground="blue")
        self.class_format_preview.pack(side=tk.LEFT)
        ttk.Label(content, text="重命名.java文件，更新AndroidManifest.xml和import引用", font=("", 8), foreground="gray").pack(anchor=tk.W, pady=(0, 4))
        ttk.Label(content, text="过滤字符：从原类名中移除指定字符（如Activity）", font=("", 8), foreground="gray").pack(anchor=tk.W, pady=(0, 4))

    def _build_drawable_format_ui(self, parent):
        """构建 Drawable 格式设置区域（垂直排列）"""
        # 标题栏（与工作区域标题一致）
        header = tk.Frame(parent, bg=self._bg("sidebar"), height=32)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        title_label = tk.Label(header, text="资源命名格式", 
                              font=("Segoe UI", 9, "bold"),
                              bg=self._bg("sidebar"), fg=self._fg("sidebar_btn"),
                              pady=4)
        title_label.pack(side=tk.LEFT, padx=8)
        
        # 内容区域
        content = ttk.Frame(parent)
        content.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        ttk.Label(content, text="格式:").pack(anchor=tk.W, pady=(0, 2))
        ftype = ttk.Frame(content)
        ftype.pack(fill=tk.X, pady=(0, 6))
        ttk.Radiobutton(ftype, text="前缀_关键词_后缀", variable=self.drawable_format_type, value="prefix_keyword_number").pack(anchor=tk.W)
        ttk.Radiobutton(ftype, text="关键词_前缀_后缀", variable=self.drawable_format_type, value="keyword_prefix_number").pack(anchor=tk.W)
        ttk.Radiobutton(ftype, text="前缀_后缀_关键词", variable=self.drawable_format_type, value="prefix_number_keyword").pack(anchor=tk.W)
        ttk.Label(content, text="前缀:").pack(anchor=tk.W, pady=(4, 0))
        self.drawable_prefix_entry = ttk.Entry(content, textvariable=self.drawable_prefix)
        self.drawable_prefix_entry.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(content, text="关键词:").pack(anchor=tk.W, pady=(0, 0))
        self.drawable_keyword_entry = ttk.Entry(content, textvariable=self.drawable_keyword)
        self.drawable_keyword_entry.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(content, text="后缀:").pack(anchor=tk.W, pady=(0, 0))
        self.drawable_suffix_entry = ttk.Entry(content, textvariable=self.drawable_suffix)
        self.drawable_suffix_entry.pack(fill=tk.X, pady=(0, 6))
        prev_f = ttk.Frame(content)
        prev_f.pack(fill=tk.X, pady=(0, 2))
        ttk.Label(prev_f, text="预览:").pack(side=tk.LEFT, padx=(0, 4))
        self.drawable_format_preview = ttk.Label(prev_f, text="", foreground="blue")
        self.drawable_format_preview.pack(side=tk.LEFT)
        ttk.Label(content, text="关键词可用 {name}；后缀可用 {number:04d}、{random}", font=("", 8), foreground="gray").pack(anchor=tk.W, pady=(0, 4))

    def _refresh_format_type(self, parent, current_active):
        """更新格式类型"""
        pass

    def update_drawable_format(self):
        format_str = self.build_format_string(
            self.drawable_format_type.get(),
            self.drawable_prefix.get(),
            self.drawable_keyword.get(),
            self.drawable_suffix.get()
        )
        if self.drawable_format_preview:
            self.drawable_format_preview.config(text=format_str)
    
    def update_layout_format(self):
        """更新Layout格式预览"""
        format_str = self.build_format_string(
            self.layout_format_type.get(),
            self.layout_prefix.get(),
            self.layout_keyword.get(),
            self.layout_suffix.get()
        )
        if self.layout_format_preview:
            self.layout_format_preview.config(text=format_str)
    
    def update_string_format(self):
        format_str = self.build_format_string(
            self.string_format_type.get(),
            self.string_prefix.get(),
            self.string_keyword.get(),
            self.string_suffix.get()
        )
        if self.string_format_preview:
            self.string_format_preview.config(text=format_str)

    def update_id_format(self):
        format_str = self.build_format_string(
            self.id_format_type.get(),
            self.id_prefix.get(),
            self.id_keyword.get(),
            self.id_suffix.get()
        )
        if self.id_format_preview:
            self.id_format_preview.config(text=format_str)

    def update_class_format(self):
        format_str = self.build_format_string(
            self.class_format_type.get(),
            self.class_prefix.get(),
            self.class_keyword.get(),
            self.class_suffix.get()
        )
        if self.class_format_preview:
            self.class_format_preview.config(text=format_str)

    def update_drawable_format_preset(self):
        self.update_drawable_format()

    def update_layout_format_preset(self):
        self.update_layout_format()

    def update_string_format_preset(self):
        self.update_string_format()

    def update_id_format_preset(self):
        self.update_id_format()

    def update_class_format_preset(self):
        self.update_class_format()

    def set_layout_preset(self, prefix, keyword, suffix):
        """设置Layout预设"""
        self.layout_prefix.set(prefix)
        self.layout_keyword.set(keyword)
        self.layout_suffix.set(suffix)
    
    def get_drawable_format(self):
        """获取Drawable完整格式字符串（用于实际重命名）"""
        prefix = self.drawable_prefix.get()
        keyword = self.drawable_keyword.get()
        suffix = self.drawable_suffix.get()
        fmt_type = self.drawable_format_type.get()
        
        # 直接拼接，不添加下划线，由用户在输入框中自行控制
        if fmt_type == "prefix_keyword_number":
            return f"{prefix}{keyword}{suffix}"
        elif fmt_type == "keyword_prefix_number":
            return f"{keyword}{prefix}{suffix}"
        elif fmt_type == "prefix_number_keyword":
            return f"{prefix}{suffix}{keyword}"
        else:
            return f"{prefix}{keyword}{suffix}"
    
    def get_layout_format(self):
        """获取Layout完整格式字符串（用于实际重命名）"""
        prefix = self.layout_prefix.get()
        keyword = self.layout_keyword.get()
        suffix = self.layout_suffix.get()
        fmt_type = self.layout_format_type.get()
        
        # 直接拼接，不添加下划线，由用户在输入框中自行控制
        if fmt_type == "prefix_keyword_number":
            return f"{prefix}{keyword}{suffix}"
        elif fmt_type == "keyword_prefix_number":
            return f"{keyword}{prefix}{suffix}"
        elif fmt_type == "prefix_number_keyword":
            return f"{prefix}{suffix}{keyword}"
        else:
            return f"{prefix}{keyword}{suffix}"

    def get_string_format(self):
        """获取String完整格式字符串（用于实际重命名）"""
        prefix = self.string_prefix.get()
        keyword = self.string_keyword.get()
        suffix = self.string_suffix.get()
        fmt_type = self.string_format_type.get()
        
        # 直接拼接，不添加下划线，由用户在输入框中自行控制
        if fmt_type == "prefix_keyword_number":
            return f"{prefix}{keyword}{suffix}"
        elif fmt_type == "keyword_prefix_number":
            return f"{keyword}{prefix}{suffix}"
        elif fmt_type == "prefix_number_keyword":
            return f"{prefix}{suffix}{keyword}"
        else:
            return f"{prefix}{keyword}{suffix}"

    def get_id_format(self):
        """获取ID完整格式字符串（用于实际重命名）"""
        prefix = self.id_prefix.get()
        keyword = self.id_keyword.get()
        suffix = self.id_suffix.get()
        fmt_type = self.id_format_type.get()
        
        # 直接拼接，不添加下划线，由用户在输入框中自行控制
        if fmt_type == "prefix_keyword_number":
            return f"{prefix}{keyword}{suffix}"
        elif fmt_type == "keyword_prefix_number":
            return f"{keyword}{prefix}{suffix}"
        elif fmt_type == "prefix_number_keyword":
            return f"{prefix}{suffix}{keyword}"
        else:
            return f"{prefix}{keyword}{suffix}"
    
    def get_class_format(self):
        """获取类名完整格式字符串（用于实际重命名）"""
        prefix = self.class_prefix.get()
        keyword = self.class_keyword.get()
        suffix = self.class_suffix.get()
        fmt_type = self.class_format_type.get()
        
        # 直接拼接，不添加下划线，由用户在输入框中自行控制
        if fmt_type == "prefix_keyword_number":
            return f"{prefix}{keyword}{suffix}"
        elif fmt_type == "keyword_prefix_number":
            return f"{keyword}{prefix}{suffix}"
        elif fmt_type == "prefix_number_keyword":
            return f"{prefix}{suffix}{keyword}"
        else:
            return f"{prefix}{keyword}{suffix}"
    
    def create_preview_widgets(self, parent, resource_type):
        """创建预览区域组件"""
        # 创建左右分栏
        paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # 左侧：文件列表
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        
        # 文件计数标签
        count_frame = ttk.Frame(left_frame)
        count_frame.pack(fill=tk.X, pady=2)
        ttk.Label(count_frame, text="文件列表:").pack(side=tk.LEFT)
        
        if resource_type == "drawable":
            self.drawable_count_label = ttk.Label(count_frame, text="(0)", foreground="gray")
            self.drawable_count_label.pack(side=tk.LEFT, padx=5)
        elif resource_type == "layout":
            self.layout_count_label = ttk.Label(count_frame, text="(0)", foreground="gray")
            self.layout_count_label.pack(side=tk.LEFT, padx=5)
        else:
            self.string_count_label = ttk.Label(count_frame, text="(0)", foreground="gray")
            self.string_count_label.pack(side=tk.LEFT, padx=5)
        
        # 文件列表带滚动条
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        if resource_type == "drawable":
            self.drawable_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED)
            scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.drawable_listbox.yview)
            self.drawable_listbox.configure(yscrollcommand=scrollbar.set)
            self.drawable_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            scrollbar.pack_forget()
            self.drawable_listbox.bind('<<ListboxSelect>>', lambda e: self.on_file_select(e, "drawable"))
        elif resource_type == "layout":
            self.layout_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED)
            scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.layout_listbox.yview)
            self.layout_listbox.configure(yscrollcommand=scrollbar.set)
            self.layout_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            scrollbar.pack_forget()
            self.layout_listbox.bind('<<ListboxSelect>>', lambda e: self.on_file_select(e, "layout"))
        else:
            self.string_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED)
            scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.string_listbox.yview)
            self.string_listbox.configure(yscrollcommand=scrollbar.set)
            self.string_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            scrollbar.pack_forget()
            self.string_listbox.bind('<<ListboxSelect>>', lambda e: self.on_file_select(e, "string"))
        
        # 右侧：映射编辑
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)
        
        # 映射编辑标签
        edit_label_frame = ttk.Frame(right_frame)
        edit_label_frame.pack(fill=tk.X, pady=2)
        ttk.Label(edit_label_frame, text="映射编辑:").pack(side=tk.LEFT)
        
        if resource_type == "drawable":
            self.drawable_mapping_text = scrolledtext.ScrolledText(right_frame, height=15)
            self.drawable_mapping_text.pack(fill=tk.BOTH, expand=True)
        elif resource_type == "layout":
            self.layout_mapping_text = scrolledtext.ScrolledText(right_frame, height=15)
            self.layout_mapping_text.pack(fill=tk.BOTH, expand=True)
        elif resource_type == "string":
            self.string_mapping_text = scrolledtext.ScrolledText(right_frame, height=15)
            self.string_mapping_text.pack(fill=tk.BOTH, expand=True)
        
        # 映射操作按钮
        map_button_frame = ttk.Frame(right_frame)
        map_button_frame.pack(fill=tk.X, pady=5)
        
        if resource_type == "drawable":
            ttk.Button(map_button_frame, text="应用修改", 
                      command=lambda: self.apply_mapping_edit("drawable")).pack(side=tk.LEFT, padx=2)
            ttk.Button(map_button_frame, text="重置", 
                      command=lambda: self.refresh_mapping_display("drawable")).pack(side=tk.LEFT, padx=2)
            ttk.Button(map_button_frame, text="清空", 
                      command=lambda: self.clear_mapping("drawable")).pack(side=tk.LEFT, padx=2)
        elif resource_type == "layout":
            ttk.Button(map_button_frame, text="应用修改", 
                      command=lambda: self.apply_mapping_edit("layout")).pack(side=tk.LEFT, padx=2)
            ttk.Button(map_button_frame, text="重置", 
                      command=lambda: self.refresh_mapping_display("layout")).pack(side=tk.LEFT, padx=2)
            ttk.Button(map_button_frame, text="清空", 
                      command=lambda: self.clear_mapping("layout")).pack(side=tk.LEFT, padx=2)
        elif resource_type == "string":
            ttk.Button(map_button_frame, text="应用修改", 
                      command=lambda: self.apply_mapping_edit("string")).pack(side=tk.LEFT, padx=2)
            ttk.Button(map_button_frame, text="重置", 
                      command=lambda: self.refresh_mapping_display("string")).pack(side=tk.LEFT, padx=2)
            ttk.Button(map_button_frame, text="清空", 
                      command=lambda: self.clear_mapping("string")).pack(side=tk.LEFT, padx=2)
    
    def log(self, message, level="INFO"):
        """输出日志"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def browse_project(self):
        """浏览项目文件夹"""
        path = filedialog.askdirectory(title="选择Android项目根目录")
        if path:
            self.project_path.set(path)
            self.log(f"已选择项目路径: {path}")
            
            # 更新底部状态栏显示项目路径和名称
            project_name = Path(path).name
            self.status_var.set(f"项目: {project_name} | 路径: {path}")
            
            # 更新项目路径显示
            if hasattr(self, '_project_path_label'):
                self._project_path_label.config(text=path, foreground="black")
            # 发现模块并更新模块下拉，然后扫描文件
            self.discover_modules()
            # 如果有 combobox，更新其值列表
            if hasattr(self, 'module_combobox'):
                self.module_combobox['values'] = self.modules
                # 选择默认全部模块
                self.module_selection.set(self.modules[0])
            self.scan_files()
    
    def scan_files(self):
        """扫描项目中的资源文件"""
        project_path = self.project_path.get()
        if not project_path:
            messagebox.showwarning("警告", "请先选择项目路径")
            return

        # 发现模块并更新模块列表（以便在不同调用场景下保持同步）
        self.discover_modules()
        if hasattr(self, 'module_combobox'):
            self.module_combobox['values'] = self.modules

        self.drawable_files.clear()
        self.layout_files.clear()
        self.string_files.clear()
        self.id_layout_files.clear()
        self.id_entries.clear()
        
        if hasattr(self, 'drawable_listbox'):
            self.drawable_listbox.delete(0, tk.END)
        if hasattr(self, 'layout_listbox'):
            self.layout_listbox.delete(0, tk.END)
        if hasattr(self, 'string_listbox'):
            self.string_listbox.delete(0, tk.END)
        if hasattr(self, 'id_listbox'):
            self.id_listbox.delete(0, tk.END)
        if hasattr(self, 'class_listbox'):
            self.class_listbox.delete(0, tk.END)
        
        # 新增：扫描strings.xml
        self.scan_string_files(project_path)
        # 新增：扫描 layout 内定义的 @+id/...
        self.scan_id_entries(project_path)
        # 新增：扫描Java类文件
        self.scan_class_files(project_path)

        self.log("开始扫描资源文件...")
        
        # 扫描drawable文件
        if self.resource_type.get() in ["drawable", "both"]:
            self.scan_drawable_files(project_path)
        
        # 扫描layout文件
        if self.resource_type.get() in ["layout", "both"]:
            self.scan_layout_files(project_path)
        
        # 更新计数
        if hasattr(self, 'drawable_count_label'):
            self.drawable_count_label.config(text=f"({len(self.drawable_files)})")
        if hasattr(self, 'layout_count_label'):
            self.layout_count_label.config(text=f"({len(self.layout_files)})")
        if hasattr(self, 'string_count_label'):
            self.string_count_label.config(text=f"({len(self.string_entries)})")
        if hasattr(self, 'class_count_label'):
            self.class_count_label.config(text=f"共 {len(self.class_files)} 个类")
        
        self.status_var.set(
            f"已找到 {len(self.drawable_files)} 个drawable, {len(self.layout_files)} 个layout, "
            f"{len(self.string_entries)} 条string, {len(self.id_entries)} 条id, {len(self.class_files)} 个类"
        )
    
    def scan_drawable_files(self, project_path):
        self.drawable_files = self.scanner.scan_drawable_files(project_path)
        # 更新列表显示（只显示文件名）
        if hasattr(self, 'drawable_listbox'):
            self.drawable_listbox.delete(0, tk.END)
            for file_path in self.drawable_files:
                self.drawable_listbox.insert(tk.END, file_path.name)

    def scan_layout_files(self, project_path):
        self.layout_files = self.scanner.scan_layout_files(project_path)
        # 更新列表显示（只显示文件名）
        if hasattr(self, 'layout_listbox'):
            self.layout_listbox.delete(0, tk.END)
            for file_path in self.layout_files:
                self.layout_listbox.insert(tk.END, file_path.name)

    def scan_string_files(self, project_path):
        """扫描 values/strings.xml 并解析其中的 <string name="..."> 数据"""
        self.string_files.clear()
        self.string_entries.clear()
        selected = self.module_selection.get() if hasattr(self, 'module_selection') else '全部模块'
        res_paths = []
        if selected == '全部模块':
            for mp in self.module_paths.values():
                res_paths.extend([mp / 'src' / 'main' / 'res', mp / 'res'])
        else:
            mp = self.module_paths.get(selected, Path(project_path))
            res_paths.extend([mp / 'src' / 'main' / 'res', mp / 'res'])
        for res_path in res_paths:
            if res_path.exists():
                values_dir = res_path / 'values'
                if values_dir.exists():
                    for file_path in values_dir.iterdir():
                        if file_path.is_file() and file_path.name == 'strings.xml':
                            self.string_files.append(file_path)
                            try:
                                tree = ET.parse(file_path)
                                root = tree.getroot()
                                for elem in root.findall('string'):
                                    name = elem.attrib.get('name')
                                    if not name:
                                        continue
                                    text = (elem.text or '').strip()
                                    preview = (text[:50] + '…') if len(text) > 50 else text
                                    self.string_entries.append((name, preview))
                            except Exception as e:
                                self.log(f"解析 {file_path} 失败: {e}", "ERROR")
        if hasattr(self, 'string_listbox'):
            self.string_listbox.delete(0, tk.END)
            for name, preview in self.string_entries:
                self.string_listbox.insert(tk.END, f"{name}  |  {preview}" if preview else name)
        self.log(f"String资源扫描完成，找到 {len(self.string_files)} 个strings.xml，共 {len(self.string_entries)} 条string")

    def scan_id_entries(self, project_path):
        """扫描 layout/*.xml 中定义的 @+id/xxx"""
        self.id_layout_files = self.scanner.scan_layout_files(project_path)
        id_set = set()
        # 优先匹配真正定义 ID 的写法：android:id="@+id/xxx"
        id_attr_patterns = [
            re.compile(r'android:id\s*=\s*"@\+id/([A-Za-z0-9_]+)"'),
            re.compile(r"android:id\s*=\s*'@\+id/([A-Za-z0-9_]+)'"),
        ]
        # 兜底：匹配任意 @+id/xxx
        fallback_plus_id_pattern = re.compile(r'@\+id/([A-Za-z0-9_]+)')
        for file_path in self.id_layout_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                matched = False
                for pattern in id_attr_patterns:
                    items = pattern.findall(content)
                    if items:
                        matched = True
                        id_set.update(items)
                if not matched:
                    id_set.update(fallback_plus_id_pattern.findall(content))
            except Exception as e:
                self.log(f"解析ID失败 {file_path}: {e}", "ERROR")
        self.id_entries = sorted(id_set)
        if hasattr(self, "id_listbox"):
            self.id_listbox.delete(0, tk.END)
            for name in self.id_entries:
                self.id_listbox.insert(tk.END, name)
        self.log(f"ID扫描完成，找到 {len(self.id_entries)} 条id")
    
    def scan_class_files(self, project_path):
        """扫描Java类文件"""
        try:
            # 确保project_path是Path对象
            if isinstance(project_path, str):
                project_path = Path(project_path)
            
            self.log(f"开始扫描Java类文件，项目路径: {project_path}")
            self.log(f"模块选择: {self.module_selection.get()}")
            
            self.class_files = self.class_renamer.scan_java_files(
                project_path, 
                self.module_paths, 
                self.module_selection.get()
            )
            
            self.log(f"扫描到 {len(self.class_files)} 个Java文件")
            
            if hasattr(self, 'class_listbox'):
                self.class_listbox.delete(0, tk.END)
                # 显示文件名（包含.java扩展名）
                for file_path in self.class_files:
                    self.class_listbox.insert(tk.END, file_path.name)
            else:
                self.log("警告: class_listbox 不存在", "WARNING")
                
            self.log(f"Java类扫描完成，找到 {len(self.class_files)} 个文件")
        except Exception as e:
            self.log(f"扫描Java类文件失败: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
    
    def extract_base_name(self, filename):
        """从文件名中提取基础名称"""
        # 如果用户输入的是固定文本，不需要提取
        return filename
    
    def generate_random_string(self, length=4):
        """生成随机字符串"""
        return ''.join(random.choices(string.ascii_lowercase, k=length))
    
    def generate_mapping(self):
        """在后台线程生成当前类型的映射，避免界面无响应"""
        target_type = self._infer_target_mapping_type()

        if target_type == "drawable":
            if not self.drawable_files:
                messagebox.showwarning("警告", "未扫描到 drawable 文件，请先扫描")
                return
            files_snapshot = list(self.drawable_files)
            format_string = self.get_drawable_format()
        elif target_type == "layout":
            if not self.layout_files:
                messagebox.showwarning("警告", "未扫描到 layout 文件，请先扫描")
                return
            files_snapshot = list(self.layout_files)
            format_string = self.get_layout_format()
        elif target_type == "string":
            if not self.string_files:
                messagebox.showwarning("警告", "未扫描到 strings.xml，请先扫描")
                return
            format_string = self.get_string_format()
            files_snapshot = None
        elif target_type == "id":
            if not self.id_entries:
                messagebox.showwarning("警告", "未扫描到 ID（@+id/...），请先扫描")
                return
            format_string = self.get_id_format()
            entries_snapshot = list(self.id_entries)
            files_snapshot = None
        else:  # class
            if not self.class_files:
                messagebox.showwarning("警告", "未扫描到 Java 类文件，请先扫描")
                return
            files_snapshot = list(self.class_files)
            format_string = self.get_class_format()
            filter_chars = self.class_filter_chars.get()

        self.status_var.set("正在生成映射...")
        self.root.update_idletasks()

        def run():
            try:
                if target_type == "drawable":
                    mapping = self.renamer.generate_mapping(files_snapshot, format_string)
                elif target_type == "layout":
                    mapping = self.renamer.generate_mapping(files_snapshot, format_string)
                elif target_type == "string":
                    mapping = self.renamer.generate_string_mapping(self.string_files, format_string)
                elif target_type == "id":
                    mapping = self._generate_id_mapping_fast(format_string, entries_snapshot)
                else:  # class
                    mapping = self.class_renamer.generate_class_mapping(files_snapshot, format_string, filter_chars)
                self.root.after(0, lambda: self._on_generate_mapping_done(target_type, mapping))
            except Exception as e:
                self.root.after(0, lambda: self._on_generate_mapping_error(target_type, str(e)))

        threading.Thread(target=run, daemon=True).start()

    def _on_generate_mapping_done(self, target_type, mapping):
        """主线程：应用生成结果并刷新显示"""
        if target_type == "drawable":
            self.drawable_mapping = mapping
        elif target_type == "layout":
            self.layout_mapping = mapping
        elif target_type == "string":
            self.string_mapping = mapping
        elif target_type == "id":
            self.id_mapping = mapping
        else:  # class
            self.class_mapping = mapping
        self.refresh_mapping_display(target_type)
        self.log(f"已生成 {len(mapping)} 条{target_type}映射")
        self.status_var.set("就绪")

    def _on_generate_mapping_error(self, target_type, err_msg):
        """主线程：生成失败时恢复状态"""
        self.log(f"生成{target_type}映射失败: {err_msg}", "ERROR")
        self.status_var.set("就绪")
        messagebox.showerror("错误", f"生成映射失败：{err_msg}")

    def _generate_id_mapping_fast(self, format_string, entries=None):
        """纯计算生成 ID 映射（不操作 UI，可在后台线程调用）"""
        if entries is None:
            entries = self.id_entries
        mapping = OrderedDict()
        used_names = set()
        for idx, old_name in enumerate(entries, 1):
            counter = idx
            while True:
                random_str = self.generate_random_string()
                try:
                    new_name = format_string.format(name=old_name, number=counter, random=random_str)
                except Exception:
                    new_name = format_string.replace("{name}", old_name).replace("{number}", str(counter)).replace("{random}", random_str)
                if new_name not in used_names:
                    break
                counter += 1
            mapping[old_name] = new_name
            used_names.add(new_name)
        return mapping

    def _infer_target_mapping_type(self):
        """根据当前上下文决定中间区展示哪一种映射"""
        active_right = getattr(self, "_right_active", None)
        if active_right:
            right_key = active_right.get()
            if right_key == "资源":
                return "drawable"
            if right_key == "布局":
                return "layout"
            if right_key == "字符":
                return "string"
            if right_key == "ID":
                return "id"
            if right_key == "类名":
                return "class"

        preferred = self.resource_type.get()
        if preferred in ("drawable", "layout", "string", "id", "class"):
            return preferred
        active_left = getattr(self, "_left_active", None)
        if active_left:
            key = active_left.get()
            if key == "资源":
                return "drawable"
            if key == "布局":
                return "layout"
            if key == "字符":
                return "string"
            if key == "ID":
                return "id"
            if key == "类名":
                return "class"
        return "drawable"

    def _set_mapping_display_type(self, resource_type):
        """切换中间映射编辑区显示类型"""
        title_map = {
            "drawable": "Drawable 映射",
            "layout": "Layout 映射",
            "string": "String 映射",
            "id": "ID 映射",
            "class": "Class 映射",
        }
        self._mapping_display_type = resource_type if resource_type in title_map else "drawable"
        if hasattr(self, "_mapping_title_var"):
            self._mapping_title_var.set(title_map.get(self._mapping_display_type, "Drawable 映射"))
    
    def refresh_mapping_display(self, resource_type):
        """刷新映射显示"""
        if not hasattr(self, "mapping_text"):
            return
        self._set_mapping_display_type(resource_type)
        if resource_type == "drawable":
            source = self.drawable_mapping
        elif resource_type == "layout":
            source = self.layout_mapping
        elif resource_type == "string":
            source = self.string_mapping
        elif resource_type == "id":
            source = self.id_mapping
        elif resource_type == "class":
            source = self.class_mapping
        else:
            source = OrderedDict()
        self.mapping_text.delete(1.0, tk.END)
        lines = [f"{k} = {source[k]}" for k in sorted(source.keys())]
        if lines:
            self.mapping_text.insert(tk.END, "\n".join(lines) + "\n")
    
    def clear_mapping(self, resource_type):
        """清空映射"""
        if resource_type == "drawable":
            self.drawable_mapping.clear()
            self.refresh_mapping_display("drawable")
            self.log("已清空Drawable映射")
        elif resource_type == "layout":
            self.layout_mapping.clear()
            self.refresh_mapping_display("layout")
            self.log("已清空Layout映射")
        elif resource_type == "string":
            self.string_mapping.clear()
            self.refresh_mapping_display("string")
            self.log("已清空String映射")
        elif resource_type == "id":
            self.id_mapping.clear()
            self.refresh_mapping_display("id")
            self.log("已清空ID映射")
        elif resource_type == "class":
            self.class_mapping.clear()
            self.refresh_mapping_display("class")
            self.log("已清空Class映射")
    
    def _mapping_current_type(self):
        """当前映射编辑类型"""
        return getattr(self, "_mapping_display_type", "drawable")

    def _mapping_apply_current(self):
        self.apply_mapping_edit(self._mapping_current_type())

    def _mapping_reset_current(self):
        self.refresh_mapping_display(self._mapping_current_type())

    def _mapping_clear_current(self):
        self.clear_mapping(self._mapping_current_type())

    def _reverse_mapping_safe(self, source):
        """将映射 old->new 反转为 new->old，重复键会被跳过"""
        reversed_map = OrderedDict()
        conflict_count = 0
        for old_name, new_name in source.items():
            if new_name in reversed_map and reversed_map[new_name] != old_name:
                conflict_count += 1
                continue
            reversed_map[new_name] = old_name
        return reversed_map, conflict_count

    def _mapping_reverse_current(self):
        """反向当前显示的映射"""
        resource_type = self._mapping_current_type()
        if resource_type == "drawable":
            mapping = self.drawable_mapping
        elif resource_type == "layout":
            mapping = self.layout_mapping
        elif resource_type == "string":
            mapping = self.string_mapping
        elif resource_type == "id":
            mapping = self.id_mapping
        else:  # class
            mapping = self.class_mapping

        if not mapping:
            self.log(f"{resource_type} 映射为空，无法反向", "WARNING")
            return

        reversed_map, conflict_count = self._reverse_mapping_safe(mapping)
        if resource_type == "drawable":
            self.drawable_mapping = reversed_map
        elif resource_type == "layout":
            self.layout_mapping = reversed_map
        elif resource_type == "string":
            self.string_mapping = reversed_map
        elif resource_type == "id":
            self.id_mapping = reversed_map
        else:  # class
            self.class_mapping = reversed_map
        self.refresh_mapping_display(resource_type)
        self.log(f"已反向 {resource_type} 映射，共 {len(reversed_map)} 条")
        if conflict_count:
            self.log(f"反向时跳过 {conflict_count} 条冲突映射（新名称重复）", "WARNING")
        
        # 反向映射后需要重新扫描文件，因为文件名已经改变
        if resource_type in ["drawable", "layout"]:
            self.log(f"反向映射后重新扫描 {resource_type} 文件...")
            self.scan_files()
            self.log(f"{resource_type} 文件扫描完成")

    def apply_mapping_edit(self, resource_type):
        """应用映射编辑"""
        if resource_type not in ("drawable", "layout", "string", "id"):
            return
        content = self.mapping_text.get(1.0, tk.END).strip()
        if not content:
            return
        new_mapping = OrderedDict()
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                old_name, new_name = line.split('=', 1)
                old_name = old_name.strip()
                new_name = new_name.strip()
                if old_name and new_name:
                    new_mapping[old_name] = new_name
        if new_mapping:
            if resource_type == "drawable":
                self.drawable_mapping = new_mapping
            elif resource_type == "layout":
                self.layout_mapping = new_mapping
            elif resource_type == "string":
                self.string_mapping = new_mapping
            elif resource_type == "id":
                self.id_mapping = new_mapping
            self.log(f"已应用 {len(new_mapping)} 条{resource_type}映射编辑")
            self.refresh_mapping_display(resource_type)
    
    def on_file_select(self, event, resource_type):
        """文件选择事件"""
        if resource_type == "drawable":
            listbox = self.drawable_listbox
            files = self.drawable_files
            mapping = self.drawable_mapping
        elif resource_type == "layout":
            listbox = self.layout_listbox
            files = self.layout_files
            mapping = self.layout_mapping
        elif resource_type == "id":
            listbox = self.id_listbox
            mapping = self.id_mapping
            selection = listbox.curselection()
            if selection and selection[0] < len(self.id_entries):
                old_name = self.id_entries[selection[0]]
                if old_name in mapping:
                    self.status_var.set(f"选中: {old_name} -> {mapping[old_name]}")
                else:
                    self.status_var.set(f"选中: {old_name} (未映射)")
            return
        else:
            listbox = self.string_listbox
            mapping = self.string_mapping
            selection = listbox.curselection()
            if selection and selection[0] < len(self.string_entries):
                index = selection[0]
                old_name = self.string_entries[index][0]
                if old_name in mapping:
                    self.status_var.set(f"选中: {old_name} -> {mapping[old_name]}")
                else:
                    self.status_var.set(f"选中: {old_name} (未映射)")
            return
        
        selection = listbox.curselection()
        if selection:
            index = selection[0]
            file_path = files[index]
            old_name = file_path.stem
            if old_name in mapping:
                new_name = mapping[old_name]
                self.status_var.set(f"选中: {file_path.name} -> {new_name}{file_path.suffix}")
            else:
                self.status_var.set(f"选中: {file_path.name} (未映射)")
    
    def on_resource_type_change(self):
        """资源类型变更事件"""
        self.scan_files()
    
    def import_mapping(self):
        """导入映射文件"""
        file_path = filedialog.askopenfilename(
            title="选择映射文件",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                drawable_mapping = OrderedDict()
                layout_mapping = OrderedDict()
                string_mapping = OrderedDict()
                id_mapping = OrderedDict()
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    current_section = None
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        
                        if line.startswith('#') and 'drawable' in line.lower():
                            current_section = 'drawable'
                            continue
                        elif line.startswith('#') and 'layout' in line.lower():
                            current_section = 'layout'
                            continue
                        elif line.startswith('#') and 'string' in line.lower():
                            current_section = 'string'
                            continue
                        elif line.startswith('#') and 'id' in line.lower():
                            current_section = 'id'
                            continue
                        elif line.startswith('#'):
                            continue
                        
                        if '=' in line:
                            old_name, new_name = line.split('=', 1)
                            old_name = old_name.strip()
                            new_name = new_name.strip()
                            
                            if current_section == 'drawable':
                                drawable_mapping[old_name] = new_name
                            elif current_section == 'layout':
                                layout_mapping[old_name] = new_name
                            elif current_section == 'string':
                                string_mapping[old_name] = new_name
                            elif current_section == 'id':
                                id_mapping[old_name] = new_name
                            else:
                                # 如果没有分类，根据文件名特征判断
                                if any(old_name.endswith(ext) for ext in ['.png', '.jpg', '.webp']):
                                    drawable_mapping[old_name] = new_name
                                else:
                                    layout_mapping[old_name] = new_name

                if drawable_mapping:
                    self.drawable_mapping = drawable_mapping
                if layout_mapping:
                    self.layout_mapping = layout_mapping
                if string_mapping:
                    self.string_mapping = string_mapping
                if id_mapping:
                    self.id_mapping = id_mapping
                
                if drawable_mapping:
                    show_type = "drawable"
                elif layout_mapping:
                    show_type = "layout"
                elif string_mapping:
                    show_type = "string"
                elif id_mapping:
                    show_type = "id"
                else:
                    show_type = self._infer_target_mapping_type()
                self.refresh_mapping_display(show_type)
                self.log(
                    f"已从 {file_path} 导入 {len(drawable_mapping)} 条Drawable映射, {len(layout_mapping)} 条Layout映射, "
                    f"{len(string_mapping)} 条String映射, {len(id_mapping)} 条ID映射"
                )
                self.mapping_file_path = file_path
                
            except Exception as e:
                messagebox.showerror("错误", f"导入失败: {e}")
    
    def export_mapping(self):
        """导出映射文件"""
        if not self.drawable_mapping and not self.layout_mapping and not self.string_mapping and not self.id_mapping:
            messagebox.showwarning("警告", "没有映射数据可导出")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="保存映射文件",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("# Android资源文件重命名映射\n")
                    f.write(f"# 导出时间: {datetime.datetime.now()}\n")
                    f.write(f"# Drawable格式: {self.get_drawable_format()}\n")
                    f.write(f"# Layout格式: {self.get_layout_format()}\n\n")
                    f.write(f"# String格式: {self.get_string_format()}\n")
                    f.write(f"# ID格式: {self.get_id_format()}\n\n")
                    
                    if self.drawable_mapping:
                        f.write("# Drawable映射\n")
                        for old_name, new_name in self.drawable_mapping.items():
                            f.write(f"{old_name} = {new_name}\n")
                        f.write("\n")
                    
                    if self.layout_mapping:
                        f.write("# Layout映射\n")
                        for old_name, new_name in self.layout_mapping.items():
                            f.write(f"{old_name} = {new_name}\n")
                        f.write("\n")

                    if self.string_mapping:
                        f.write("# String映射\n")
                        for old_name, new_name in self.string_mapping.items():
                            f.write(f"{old_name} = {new_name}\n")
                        f.write("\n")

                    if self.id_mapping:
                        f.write("# ID映射\n")
                        for old_name, new_name in self.id_mapping.items():
                            f.write(f"{old_name} = {new_name}\n")
                
                self.log(f"已导出映射到 {file_path}")
                
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {e}")
    
    def rename_files_by_type(self, files, mapping, resource_type):
        """执行特定类型的文件重命名。返回 (重命名数量, 实际执行的 [(old_path, new_path), ...])"""
        renamed_count = 0
        rename_list = []
        for file_path in files:
            old_name = file_path.stem
            if old_name not in mapping:
                continue
            new_name = mapping[old_name]
            new_file_path = file_path.with_name(f"{new_name}{file_path.suffix}")
            counter = 1
            while new_file_path.exists():
                new_file_path = file_path.with_name(f"{new_name}_{counter}{file_path.suffix}")
                counter += 1
            self.log(f"重命名{resource_type}: {file_path.name} -> {new_file_path.name}")
            if not self.preview_mode.get():
                old_abs = str(file_path.resolve())
                file_path.rename(new_file_path)
                rename_list.append((old_abs, str(new_file_path.resolve())))
            renamed_count += 1
        return renamed_count, rename_list
    
    def update_references_in_files(self):
        """更新文件引用"""
        total_updated = 0
        
        # 更新drawable引用
        if self.drawable_mapping:
            updated = self.update_drawable_references()
            total_updated += updated
        
        # 更新layout引用
        if self.layout_mapping:
            updated = self.update_layout_references()
            total_updated += updated

        # 更新string引用
        if self.string_mapping:
            updated = self.update_string_references()
            total_updated += updated

        # 更新id引用
        if self.id_mapping:
            updated = self.update_id_references()
            total_updated += updated
        
        return total_updated
    
    def _get_drawable_replace_rules(self):
        """获取 drawable 引用替换规则（不执行）"""
        rules = []
        for old_name, new_name in self.drawable_mapping.items():
            rules.append((rf'R\.drawable\.{re.escape(old_name)}\b', f'R.drawable.{new_name}'))
            rules.append((rf'@drawable/{re.escape(old_name)}\b', f'@drawable/{new_name}'))
            rules.append((rf'@{{drawable\.{re.escape(old_name)}}}', f'@{{drawable.{new_name}}}'))
        return rules

    def _get_layout_replace_rules(self):
        """获取 layout 引用替换规则（不执行）"""
        rules = []
        for old_name, new_name in self.layout_mapping.items():
            rules.append((rf'R\.layout\.{re.escape(old_name)}\b', f'R.layout.{new_name}'))
            rules.append((rf'@layout/{re.escape(old_name)}\b', f'@layout/{new_name}'))
            rules.append((rf'@{{layout\.{re.escape(old_name)}}}', f'@{{layout.{new_name}}}'))
            old_camel = ''.join(x.capitalize() for x in old_name.split('_'))
            new_camel = ''.join(x.capitalize() for x in new_name.split('_'))
            rules.append((rf'{re.escape(old_camel)}Binding\b', f'{new_camel}Binding'))
        return rules

    def _get_string_replace_rules(self):
        rules = []
        for old_name, new_name in self.string_mapping.items():
            # 代码中的引用
            rules.append((rf'R\.string\.{re.escape(old_name)}\b', f'R.string.{new_name}'))
            rules.append((rf'@string/{re.escape(old_name)}\b', f'@string/{new_name}'))
            # strings.xml 中的 name 属性
            rules.append((rf'<string\s+name="{re.escape(old_name)}"', f'<string name="{new_name}"'))
            rules.append((rf'<string-array\s+name="{re.escape(old_name)}"', f'<string-array name="{new_name}"'))
            rules.append((rf'<plurals\s+name="{re.escape(old_name)}"', f'<plurals name="{new_name}"'))
        return rules

    def _snake_to_pascal(self, name):
        return FormatHelper.snake_to_pascal(name)

    def _snake_to_camel(self, name):
        return FormatHelper.snake_to_camel(name)

    def _get_id_replace_rules(self):
        """获取 id 引用替换规则（layout @+id/@id、R.id、binding/mBinding）"""
        rules = []
        for old_name, new_name in self.id_mapping.items():
            # XML id
            rules.append((rf'@\+id/{re.escape(old_name)}\b', f'@+id/{new_name}'))
            rules.append((rf'@id/{re.escape(old_name)}\b', f'@id/{new_name}'))
            # Java/Kotlin R.id
            rules.append((rf'R\.id\.{re.escape(old_name)}\b', f'R.id.{new_name}'))
            # binding 字段：示例 tv_back_12 -> TvBack12
            old_pascal = self._snake_to_pascal(old_name)
            new_pascal = self._snake_to_pascal(new_name)
            old_camel = self._snake_to_camel(old_name)
            new_camel = self._snake_to_camel(new_name)
            rules.append((rf'\bbinding\.{re.escape(old_pascal)}\b', f'binding.{new_pascal}'))
            rules.append((rf'\bmBinding\.{re.escape(old_pascal)}\b', f'mBinding.{new_pascal}'))
            rules.append((rf'\bmbinding\.{re.escape(old_pascal)}\b', f'mbinding.{new_pascal}'))
            # 兼容常见 lowerCamel 场景
            rules.append((rf'\bbinding\.{re.escape(old_camel)}\b', f'binding.{new_camel}'))
            rules.append((rf'\bmBinding\.{re.escape(old_camel)}\b', f'mBinding.{new_camel}'))
            rules.append((rf'\bmbinding\.{re.escape(old_camel)}\b', f'mbinding.{new_camel}'))
        return rules

    def _get_class_replace_rules(self):
        """获取类名引用替换规则"""
        project_path = Path(self.project_path.get())
        return self.class_renamer.get_class_replace_rules(
            self.class_files, 
            self.class_mapping, 
            project_path
        )

    def _get_combined_replace_rules(self):
        """获取合并后的引用替换规则（用于备份前收集）"""
        rules = []
        if self.drawable_mapping:
            rules.extend(self._get_drawable_replace_rules())
        if self.layout_mapping:
            rules.extend(self._get_layout_replace_rules())
        if self.string_mapping:
            rules.extend(self._get_string_replace_rules())
        if self.id_mapping:
            rules.extend(self._get_id_replace_rules())
        if self.class_mapping:
            rules.extend(self._get_class_replace_rules())
        return rules

    def update_drawable_references(self):
        """更新drawable引用"""
        return self.apply_replacements(self._get_drawable_replace_rules())

    def update_layout_references(self):
        """更新layout引用"""
        return self.apply_replacements(self._get_layout_replace_rules())

    def update_string_references(self):
        return self.apply_replacements(self._get_string_replace_rules())

    def update_id_references(self):
        return self.apply_replacements(self._get_id_replace_rules())
    
    def apply_replacements(self, replace_rules):
        """应用替换规则到所有相关文件（在后台线程中调用）"""
        if not replace_rules:
            return 0
        
        updated_files = []
        project_path = Path(self.project_path.get())
        patterns = ['**/*.java', '**/*.kt', '**/*.xml', '**/*.gradle']
        
        # 预编译所有正则表达式以提高性能
        compiled_rules = [(re.compile(old_pattern), new_pattern) for old_pattern, new_pattern in replace_rules]
        
        # 收集所有需要处理的文件
        all_files = []
        for pattern in patterns:
            for file_path in project_path.rglob(pattern):
                if 'build' in file_path.parts or '.idea' in file_path.parts:
                    continue
                all_files.append(file_path)
        
        total_files = len(all_files)
        self.root.after(0, lambda: self.log(f"开始更新引用，共 {total_files} 个文件..."))
        
        # 处理文件
        for idx, file_path in enumerate(all_files, 1):
            # 每处理10个文件更新一次进度
            if idx % 10 == 0 or idx == total_files:
                progress = f"正在更新引用... ({idx}/{total_files})"
                self.root.after(0, lambda p=progress: self.status_var.set(p))
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                new_content = content
                for compiled_pattern, new_pattern in compiled_rules:
                    new_content = compiled_pattern.sub(new_pattern, new_content)
                if new_content != content:
                    if not self.preview_mode.get():
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                    updated_files.append(str(file_path))
                    self.root.after(0, lambda fp=file_path: self.log(f"更新引用: {fp}"))
            except (UnicodeDecodeError, IOError) as e:
                continue
        
        return len(updated_files)
    
    def execute_rename(self):
        """执行重命名操作（仅执行当前选中的映射类型）"""
        res_type = self._mapping_current_type()
        type_name = {"drawable": "资源(Drawable)", "layout": "布局(Layout)", "string": "字符(String)", "id": "控件ID(ID)", "class": "类名(Class)"}[res_type]
        mapping = getattr(self, f"{res_type}_mapping")
        if not mapping:
            messagebox.showwarning("警告", f"当前选中的是「{type_name}」映射，但该映射为空。请先生成或导入「{type_name}」映射。")
            return

        mode = "预览" if self.preview_mode.get() else "执行"
        count = len(mapping)
        if not messagebox.askyesno("确认", f"确定要{mode}【仅{type_name}】重命名吗？\n\n"
                                           f"共 {count} 条映射\n"
                                           f"模式: {mode}\n"
                                           f"更新引用: {'是' if self.update_references.get() else '否'}"):
            return

        self.log("=" * 50)
        self.log(f"开始{mode}【{type_name}】操作...")
        total_renamed = 0
        all_renames = []

        if res_type == "drawable":
            renamed, rename_list = self.rename_files_by_type(
                self.drawable_files, self.drawable_mapping, "drawable"
            )
            total_renamed += renamed
            all_renames.extend(rename_list)
            self.log(f"重命名 drawable: {renamed}")
            replace_rules = self._get_drawable_replace_rules()
        elif res_type == "layout":
            renamed, rename_list = self.rename_files_by_type(
                self.layout_files, self.layout_mapping, "layout"
            )
            total_renamed += renamed
            all_renames.extend(rename_list)
            self.log(f"重命名 layout: {renamed}")
            replace_rules = self._get_layout_replace_rules()
        elif res_type == "string":
            # string：无文件重命名，仅更新引用
            replace_rules = self._get_string_replace_rules()
            self.log("String 仅更新引用（无文件重命名）")
        elif res_type == "id":
            # id：无文件重命名，仅更新引用（layout/xml/java/kt 中的 id 使用）
            replace_rules = self._get_id_replace_rules()
            self.log("ID 仅更新引用（无文件重命名）")
        else:  # class
            # class：重命名Java文件，更新引用
            renamed, rename_list = self.rename_files_by_type(
                self.class_files, self.class_mapping, "class"
            )
            total_renamed += renamed
            all_renames.extend(rename_list)
            self.log(f"重命名 class: {renamed}")
            replace_rules = self._get_class_replace_rules()

        # 如果需要更新引用，使用后台线程执行
        if self.update_references.get() and replace_rules:
            self.status_var.set("正在更新引用...")
            self.root.update_idletasks()
            
            def run_replacements():
                try:
                    updated_count = self.apply_replacements(replace_rules)
                    self.root.after(0, lambda: self._on_replacements_done(type_name, total_renamed, updated_count))
                except Exception as e:
                    self.root.after(0, lambda: self._on_replacements_error(str(e)))
            
            threading.Thread(target=run_replacements, daemon=True).start()
        else:
            # 没有引用更新，直接完成
            self._finish_rename_operation(type_name, total_renamed, 0)
    
    def _on_replacements_done(self, type_name, total_renamed, updated_count):
        """引用更新完成的回调"""
        self.log(f"更新引用: {updated_count}")
        self._finish_rename_operation(type_name, total_renamed, updated_count)
    
    def _on_replacements_error(self, error_msg):
        """引用更新失败的回调"""
        self.log(f"更新引用失败: {error_msg}", "ERROR")
        self.status_var.set("就绪")
        messagebox.showerror("错误", f"更新引用失败：{error_msg}")
    
    def _finish_rename_operation(self, type_name, total_renamed, updated_count):
        """完成重命名操作"""
        if self.preview_mode.get():
            self.log("预览完成 (未实际修改)")
        else:
            self.log("操作完成")
            # 自动导出映射表
            self._auto_export_mapping()
        self.log("=" * 50)
        self.status_var.set("就绪")
        messagebox.showinfo("完成", f"【{type_name}】操作完成！\n重命名: {total_renamed}\n更新引用: {updated_count}")
    
    def _auto_export_mapping(self):
        """自动导出当前类型的映射表到项目目录"""
        try:
            res_type = self._mapping_current_type()
            mapping = getattr(self, f"{res_type}_mapping")
            
            if not mapping:
                return
            
            # 生成文件名：类型_map_table_日期（纯数字）
            date_str = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"{res_type}_map_table_{date_str}.txt"
            
            # 保存到项目目录
            project_path = Path(self.project_path.get())
            file_path = project_path / filename
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"# {res_type.capitalize()} 映射表\n")
                f.write(f"# 导出时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                
                # 写入格式信息
                if res_type == "drawable":
                    f.write(f"# 格式: {self.get_drawable_format()}\n\n")
                elif res_type == "layout":
                    f.write(f"# 格式: {self.get_layout_format()}\n\n")
                elif res_type == "string":
                    f.write(f"# 格式: {self.get_string_format()}\n\n")
                else:  # id
                    f.write(f"# 格式: {self.get_id_format()}\n\n")
                
                # 写入映射数据
                for old_name, new_name in mapping.items():
                    f.write(f"{old_name} = {new_name}\n")
            
            self.log(f"已自动导出映射表到: {file_path}")
            
        except Exception as e:
            self.log(f"自动导出映射表失败: {e}", "ERROR")

    def discover_modules(self):
        """发现项目下的模块（包含 app 或其他含 src/main/res 的子目录），更新 self.modules 与 self.module_paths"""
        project_path = Path(self.project_path.get()) if self.project_path.get() else None
        self.modules, self.module_paths = FileHelper.discover_modules(project_path)
        # 修复：每次模块变更后，重新创建 ResourceScanner，保证 module_paths 最新
        self.scanner = ResourceScanner(self.module_selection, self.module_paths, log_func=self.log)

def main():
    root = tk.Tk()
    app = AndroidResourceRenamerGUI(root)
    
    # 设置窗口图标（支持打包后的路径）
    try:
        import sys
        import os
        
        # 获取程序所在目录
        if getattr(sys, 'frozen', False):
            # 打包后的路径（PyInstaller会解压到临时目录）
            application_path = sys._MEIPASS
        else:
            # 开发环境路径
            application_path = os.path.dirname(os.path.abspath(__file__))
        
        icon_path = os.path.join(application_path, 'applogo.ico')
        
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
        else:
            # 如果找不到，尝试当前目录
            if os.path.exists('applogo.ico'):
                root.iconbitmap('applogo.ico')
    except Exception as e:
        # 图标加载失败不影响程序运行
        print(f"加载图标失败: {e}")
    
    root.mainloop()

if __name__ == "__main__":
    main()