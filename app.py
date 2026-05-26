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
from collections import OrderedDict, defaultdict
import datetime
import xml.etree.ElementTree as ET

# 导入核心模块
from core import ResourceScanner, ResourceRenamer, ClassRenamer, ResourceUsageChecker
# 导入UI组件
from ui import ToolTip, ThemeManager, FormatPanelBuilder, ScrollableFrame
# 导入工具函数
from utils import FormatHelper, FileHelper, ReferenceUpdater


class AndroidResourceRenamerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Android Explorer v3.3")
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
        self._format_preview_timer = None
        
        # Drawable相关变量
        self.drawable_prefix = tk.StringVar(value="icon")
        self.drawable_keyword = tk.StringVar(value="{name}")
        self.drawable_suffix = tk.StringVar(value="{random}")
        self.drawable_number = tk.StringVar(value="{number:04d}")
        self.drawable_order_mode = tk.StringVar(value="fixed")
        self.drawable_part_order = tk.StringVar(value=FormatHelper.DEFAULT_PART_ORDER)
        
        # Layout相关变量
        self.layout_prefix = tk.StringVar(value="activity")
        self.layout_keyword = tk.StringVar(value="{name}")
        self.layout_suffix = tk.StringVar(value="{random}")
        self.layout_number = tk.StringVar(value="{number:04d}")
        self.layout_order_mode = tk.StringVar(value="fixed")
        self.layout_part_order = tk.StringVar(value=FormatHelper.DEFAULT_PART_ORDER)

        # String资源相关变量
        self.string_prefix = tk.StringVar(value="str")
        self.string_keyword = tk.StringVar(value="{name}")
        self.string_suffix = tk.StringVar(value="{random}")
        self.string_number = tk.StringVar(value="{number:04d}")
        self.string_order_mode = tk.StringVar(value="fixed")
        self.string_part_order = tk.StringVar(value=FormatHelper.DEFAULT_PART_ORDER)
        self.string_mapping = OrderedDict()
        self.string_files = []
        self.string_entries = []  # 从 values/strings.xml 解析出的 (name, value_preview) 列表
        self.string_sources = defaultdict(list)  # string name -> [strings.xml 路径]

        # 资源使用情况（资源/布局/字符）
        self._usage_status = {'drawable': {}, 'layout': {}, 'string': {}}
        self._usage_unused = {'drawable': {}, 'layout': {}, 'string': {}}

        # ID资源相关变量（来自 layout/*.xml 的 @+id/...）
        self.id_prefix = tk.StringVar(value="id")
        self.id_keyword = tk.StringVar(value="{name}")
        self.id_suffix = tk.StringVar(value="{random}")
        self.id_number = tk.StringVar(value="{number:04d}")
        self.id_order_mode = tk.StringVar(value="fixed")
        self.id_part_order = tk.StringVar(value=FormatHelper.DEFAULT_PART_ORDER)
        self.id_mapping = OrderedDict()
        self.id_entries = []
        self.id_layout_files = []
        
        # Java类相关变量
        self.class_prefix = tk.StringVar(value="")
        self.class_keyword = tk.StringVar(value="{name}")
        self.class_suffix = tk.StringVar(value="{random}")
        self.class_number = tk.StringVar(value="{number:04d}")
        self.class_order_mode = tk.StringVar(value="fixed")
        self.class_part_order = tk.StringVar(value=FormatHelper.DEFAULT_PART_ORDER)
        self.class_filter_chars = tk.StringVar(value="")  # 类名过滤字符
        self.class_replace_chars = tk.StringVar(value="")  # 类名替换规则
        self.class_mapping = OrderedDict()
        self.class_files = []  # Java文件列表
        
        # 随机字符配置变量
        self.random_length = tk.IntVar(value=4)  # 随机字符长度
        self.random_include_lowercase = tk.BooleanVar(value=True)  # 包含小写字母
        self.random_include_uppercase = tk.BooleanVar(value=False)  # 包含大写字母
        self.random_include_digits = tk.BooleanVar(value=False)  # 包含数字
        
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

        # 主题: Light / Dark（默认 VS Code 暗色）
        self.theme_mode = tk.StringVar(value="Dark")

        self.theme_manager = ThemeManager(self.theme_mode)

        # 拆分后的工具类
        self.scanner = ResourceScanner(self.module_selection, self.module_paths, log_func=self.log)
        self.renamer = ResourceRenamer(log_func=self.log)
        self.class_renamer = ClassRenamer(log_func=self.log)
        self.usage_checker = ResourceUsageChecker(log_func=self.log)

        # 创建界面
        self.create_widgets()
        
        # 绑定事件
        for _trace_vars, _updater in [
            ((self.drawable_prefix, self.drawable_keyword, self.drawable_suffix,
              self.drawable_number, self.drawable_order_mode, self.drawable_part_order),
             'drawable'),
            ((self.layout_prefix, self.layout_keyword, self.layout_suffix,
              self.layout_number, self.layout_order_mode, self.layout_part_order),
             'layout'),
            ((self.string_prefix, self.string_keyword, self.string_suffix,
              self.string_number, self.string_order_mode, self.string_part_order),
             'string'),
            ((self.id_prefix, self.id_keyword, self.id_suffix,
              self.id_number, self.id_order_mode, self.id_part_order),
             'id'),
            ((self.class_prefix, self.class_keyword, self.class_suffix,
              self.class_number, self.class_order_mode, self.class_part_order),
             'class'),
        ]:
            for var in _trace_vars:
                var.trace('w', lambda *args, t=_updater: self._schedule_format_preview(t))
        self.class_filter_chars.trace('w', lambda *args: self._schedule_format_preview('class'))
        self.class_replace_chars.trace('w', lambda *args: self._schedule_format_preview('class'))
        
        # 随机字符配置变更时更新所有格式预览（防抖）
        for _rv in (
            self.random_length, self.random_include_lowercase,
            self.random_include_uppercase, self.random_include_digits,
        ):
            _rv.trace('w', lambda *args: self._schedule_format_preview_all())
        
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

    def _bg(self, key):
        return self.theme_manager.get_bg(key)

    def _fg(self, key):
        return self.theme_manager.get_fg(key)

    def _border(self):
        return self.theme_manager.get_border()

    def _hline(self, parent):
        tk.Frame(parent, height=1, bg=self._border()).pack(fill=tk.X)

    def _vline(self, parent, side=tk.RIGHT):
        tk.Frame(parent, width=1, bg=self._border()).pack(side=side, fill=tk.Y)

    def _vsep(self, parent, padx=4, pady=6):
        """菜单栏等处的竖向细分隔"""
        tk.Frame(parent, width=1, bg=self._border()).pack(
            side=tk.LEFT, fill=tk.Y, padx=padx, pady=pady,
        )

    def _section_title(self, parent, text, bg_key="main", textvariable=None):
        """VS Code 式小节标题：无底色条、无下划线"""
        hint = self.theme_manager.get_bg("hint_fg")
        kw = dict(
            font=("Segoe UI", 9), bg=self._bg(bg_key), fg=hint, anchor="w",
        )
        if textvariable is not None:
            lbl = tk.Label(parent, textvariable=textvariable, **kw)
        else:
            lbl = tk.Label(parent, text=text, **kw)
        lbl.pack(fill=tk.X, padx=8, pady=(6, 2))
        return lbl

    def _listbox_kwargs(self):
        return dict(
            bg=self._bg("listbox"), fg=self._fg("listbox"),
            selectbackground=self._bg("listbox_sel"),
            selectforeground=self._fg("listbox_sel"),
            bd=0, highlightthickness=0,
            activestyle='none',
        )

    def _text_kwargs(self):
        return dict(
            bg=self._bg("editor"), fg=self._fg("editor"),
            insertbackground=self._fg("editor"),
            selectbackground=self._bg("listbox_sel"),
            selectforeground=self._fg("listbox_sel"),
            bd=0, relief=tk.FLAT, highlightthickness=0,
        )

    def _create_editor(self, parent, show_scrollbar=True, line_numbers=False, **text_options):
        """Text + ttk 垂直滚动条；line_numbers 为映射区显示行号栏"""
        container = tk.Frame(parent, bg=self._bg("editor"))
        container.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        kw = self._text_kwargs()
        kw.update(text_options)
        editor_font = kw.get("font", ("Consolas", 10))
        text = tk.Text(container, **kw)

        gutter = None
        if line_numbers:
            gutter = tk.Text(
                container, width=4,
                font=editor_font, bg=self._bg("gutter"),
                fg=self.theme_manager.get_bg("hint_fg"),
                state=tk.DISABLED, relief=tk.FLAT, bd=0,
                highlightthickness=0, cursor="arrow", takefocus=0,
                padx=6, pady=0, spacing1=0, spacing2=0, spacing3=0,
            )
            gutter.pack(side=tk.LEFT, fill=tk.Y)
            tk.Frame(container, width=1, bg=self._border()).pack(side=tk.LEFT, fill=tk.Y)
            gutter.bind("<MouseWheel>", lambda e: text.yview_scroll(
                -1 * (e.delta // 120) if e.delta else 0, "units",
            ))
            text._line_gutter = gutter

        vbar = ttk.Scrollbar(
            container, orient=tk.VERTICAL, style="Editor.Vertical.TScrollbar",
        )

        def _yscroll(first, last):
            vbar.set(first, last)
            if gutter is not None:
                gutter.yview_moveto(first)

        text.configure(yscrollcommand=_yscroll)
        vbar.configure(command=text.yview)
        vbar.pack(side=tk.RIGHT, fill=tk.Y)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def _sync_scrollbar(*_args):
            if not show_scrollbar:
                vbar.pack_forget()
                return
            text.update_idletasks()
            first, last = text.yview()
            needs = float(first) > 0.0 or float(last) < 1.0
            if needs:
                if not vbar.winfo_ismapped():
                    vbar.pack(side=tk.RIGHT, fill=tk.Y)
            else:
                vbar.pack_forget()

        def _schedule_sync(_event=None):
            text.after_idle(_sync_scrollbar)
            if line_numbers:
                text.after_idle(lambda: self._sync_line_numbers(text))

        text.bind("<<Modified>>", _schedule_sync)
        text.bind("<Configure>", _schedule_sync)
        text.bind("<KeyRelease>", _schedule_sync)
        text.bind("<MouseWheel>", lambda _e: text.after_idle(_sync_scrollbar))
        container._editor_vbar = vbar
        container._sync_scrollbar = _sync_scrollbar
        text._editor_container = container
        text.after_idle(_sync_scrollbar)
        if line_numbers:
            text.after_idle(lambda: self._sync_line_numbers(text))
        return text

    def _sync_line_numbers(self, text_widget):
        """刷新行号栏（与映射编辑区行数对齐）"""
        gutter = getattr(text_widget, "_line_gutter", None)
        if gutter is None:
            return
        try:
            end_line = int(text_widget.index("end-1c").split(".")[0])
        except (tk.TclError, ValueError):
            end_line = 1
        end_line = max(1, end_line)
        width = max(3, len(str(end_line)) + 1)
        gutter.configure(width=width, state=tk.NORMAL)
        gutter.delete("1.0", tk.END)
        nums = "\n".join(f"{i:>{len(str(end_line))}}" for i in range(1, end_line + 1))
        gutter.insert("1.0", nums)
        gutter.configure(state=tk.DISABLED)
        try:
            gutter.yview_moveto(text_widget.yview()[0])
        except tk.TclError:
            pass

    def _sync_editor_scrollbar(self, text_widget):
        container = getattr(text_widget, '_editor_container', None)
        sync = getattr(container, '_sync_scrollbar', None)
        if sync:
            sync()

    def _menu_file(self):
        """顶部菜单：文件（浏览项目）"""
        self.browse_project()

    def _schedule_format_preview(self, type_name):
        """格式预览防抖，减少输入时 UI 卡顿"""
        if self._format_preview_timer is not None:
            self.root.after_cancel(self._format_preview_timer)
        self._format_preview_timer = self.root.after(
            200, lambda t=type_name: self._run_format_preview(t)
        )

    def _schedule_format_preview_all(self):
        if self._format_preview_timer is not None:
            self.root.after_cancel(self._format_preview_timer)
        self._format_preview_timer = self.root.after(200, self._run_all_format_previews)

    def _run_format_preview(self, type_name):
        self._format_preview_timer = None
        updaters = {
            'drawable': self.update_drawable_format,
            'layout': self.update_layout_format,
            'string': self.update_string_format,
            'id': self.update_id_format,
            'class': self.update_class_format,
        }
        fn = updaters.get(type_name)
        if fn:
            fn()

    def _run_all_format_previews(self):
        self._format_preview_timer = None
        self.update_all_format_previews()

    def create_widgets(self):
        """创建界面组件 - 系统标题栏 + 其下菜单栏"""
        self.root.configure(bg=self.theme_manager.get_bg("main"))
        self.theme_manager.setup_ttk_styles()

        menubar_frame = tk.Frame(self.root, height=36, bg=self._bg("menubar"))
        menubar_frame.pack(fill=tk.X)
        menubar_frame.pack_propagate(False)
        menubar_bg = self._bg("menubar")
        menubar_fg = self._fg("menubar")

        def _menu_label(parent, text, cmd, fg=None):
            lbl = tk.Label(
                parent, text=text, font=("Segoe UI", 9, "bold"),
                bg=menubar_bg, fg=fg or menubar_fg, cursor="hand2",
                padx=8, pady=6, relief="flat",
            )
            lbl.pack(side=tk.LEFT)
            lbl.bind("<Button-1>", lambda e, c=cmd: c())
            lbl.bind("<Enter>", lambda e, w=lbl: w.configure(bg=self._bg("accent"), fg="#ffffff"))
            lbl.bind("<Leave>", lambda e, w=lbl: w.configure(bg=menubar_bg, fg=fg or menubar_fg))
            return lbl

        _menu_label(menubar_frame, "文件", self._menu_file)
        _menu_label(menubar_frame, "关于", self._menu_about)
        _menu_label(menubar_frame, "生成映射", self.generate_mapping)
        _menu_label(menubar_frame, "应用修改", self._mapping_apply_current)
        _menu_label(menubar_frame, "重置", self._mapping_reset_current)
        _menu_label(menubar_frame, "清空", self._mapping_clear_current)
        _menu_label(menubar_frame, "导入映射", self.import_mapping)
        _menu_label(menubar_frame, "反向映射", self._mapping_reverse_current)
        _menu_label(menubar_frame, "导出映射", self.export_mapping)
        _menu_label(menubar_frame, "执行", self._menu_execute, fg=self._bg("accent"))

        self._vsep(menubar_frame)
        self.module_combobox = ttk.Combobox(
            menubar_frame, textvariable=self.module_selection,
            values=self.modules, state="readonly", width=16,
        )
        self.module_combobox.pack(side=tk.LEFT, padx=(0, 8), pady=4)

        self._vsep(menubar_frame)
        tk.Label(menubar_frame, text="选项", font=("Segoe UI", 9, "bold"),
                 bg=menubar_bg, fg=menubar_fg, padx=4).pack(side=tk.LEFT, pady=4)
        opt_frame = tk.Frame(menubar_frame, bg=menubar_bg)
        opt_frame.pack(side=tk.LEFT, pady=4)
        self.cb_preview = ttk.Checkbutton(
            opt_frame, text="预览", variable=self.preview_mode, style="Menubar.TCheckbutton",
        )
        self.cb_preview.pack(side=tk.LEFT, padx=3)
        self.cb_update_ref = ttk.Checkbutton(
            opt_frame, text="更新引用", variable=self.update_references, style="Menubar.TCheckbutton",
        )
        self.cb_update_ref.pack(side=tk.LEFT, padx=3)
        self.cb_subdirs = ttk.Checkbutton(
            opt_frame, text="子目录", variable=self.include_subdirs, style="Menubar.TCheckbutton",
        )
        self.cb_subdirs.pack(side=tk.LEFT, padx=3)

        main_container = tk.Frame(self.root, bg=self._bg("main"))
        main_container.pack(fill=tk.BOTH, expand=True)

        # ========== 主内容区：左 | 中 | 右（VS Code 三栏） ==========
        content_paned = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
        content_paned.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        # ----- 左侧边栏 -----
        left_outer = tk.Frame(content_paned, bg=self._bg("main"))
        content_paned.add(left_outer, weight=0)
        left_inner = tk.Frame(left_outer, bg=self._bg("sidebar"), width=220)
        left_inner.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_inner.pack_propagate(False)
        self._vline(left_outer)

        btn_frame = tk.Frame(left_inner, bg=self._bg("sidebar"))
        btn_frame.pack(fill=tk.X, padx=2, pady=(4, 0))
        self._left_active = tk.StringVar(value="资源")
        
        # Store button references for selection state management
        self._nav_buttons = {}
        
        nav_items = [("资源", "资源"), ("布局", "布局"), ("字符", "字符"), ("ID", "ID"), ("类名", "类名")]
        for col, (name, key) in enumerate(nav_items):
            btn_frame.columnconfigure(col, weight=1)
            b = tk.Button(
                btn_frame, text=name, relief=tk.FLAT, font=("Segoe UI", 9, "bold"),
                bd=0, bg=self._bg("sidebar_btn"), fg=self._fg("sidebar_btn"),
                activebackground=self._bg("accent"), activeforeground="#ffffff",
                highlightthickness=0, padx=4, pady=5,
                command=lambda k=key: self._switch_left_view(k),
            )
            b.grid(row=0, column=col, sticky="ew", padx=1)
            b.bind("<Enter>", lambda e, w=b: w.configure(bg=self._bg("accent"), fg="#ffffff"))
            b.bind("<Leave>", lambda e, w=b: self._update_button_state(w))
            self._nav_buttons[key] = b
        
        self._update_button_state(self._nav_buttons["资源"])

        self._left_stack = tk.Frame(left_inner, bg=self._bg("sidebar"))
        self._left_stack.pack(fill=tk.BOTH, expand=True, pady=2)  # Reduced padding

        # Create left sidebar frames
        self._left_drawable_frame = tk.Frame(self._left_stack, bg=self._bg("sidebar"))
        self._build_usage_toolbar(self._left_drawable_frame, 'drawable')
        list_frame = ttk.Frame(self._left_drawable_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.drawable_listbox = tk.Listbox(
            list_frame, selectmode=tk.EXTENDED, height=15, **self._listbox_kwargs()
        )
        self.drawable_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.drawable_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar.pack_forget()
        self.drawable_listbox.configure(yscrollcommand=scrollbar.set)
        self.drawable_count_label = ttk.Label(
            self._left_drawable_frame, text="共 0 个文件", font=("Segoe UI", 8),
            style="Dim.TLabel",
        )
        self.drawable_count_label.pack(anchor=tk.W, padx=4, pady=(2, 4))

        self._left_layout_frame = tk.Frame(self._left_stack, bg=self._bg("sidebar"))
        self._build_usage_toolbar(self._left_layout_frame, 'layout')
        list_frame = ttk.Frame(self._left_layout_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.layout_listbox = tk.Listbox(
            list_frame, selectmode=tk.EXTENDED, height=15, **self._listbox_kwargs()
        )
        self.layout_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.layout_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar.pack_forget()
        self.layout_listbox.configure(yscrollcommand=scrollbar.set)
        self.layout_count_label = ttk.Label(
            self._left_layout_frame, text="共 0 个文件", font=("Segoe UI", 8), style="Dim.TLabel",
        )
        self.layout_count_label.pack(anchor=tk.W, padx=4, pady=(2, 4))

        self._left_string_frame = tk.Frame(self._left_stack, bg=self._bg("sidebar"))
        self._build_usage_toolbar(self._left_string_frame, 'string')
        list_frame = ttk.Frame(self._left_string_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.string_listbox = tk.Listbox(
            list_frame, selectmode=tk.EXTENDED, height=15, **self._listbox_kwargs()
        )
        self.string_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.string_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar.pack_forget()
        self.string_listbox.configure(yscrollcommand=scrollbar.set)
        self.string_count_label = ttk.Label(
            self._left_string_frame, text="共 0 条", font=("Segoe UI", 8), style="Dim.TLabel",
        )
        self.string_count_label.pack(anchor=tk.W, padx=4, pady=(2, 4))

        self._left_id_frame = tk.Frame(self._left_stack, bg=self._bg("sidebar"))
        list_frame = ttk.Frame(self._left_id_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.id_listbox = tk.Listbox(
            list_frame, selectmode=tk.EXTENDED, height=15, **self._listbox_kwargs()
        )
        self.id_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.id_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar.pack_forget()
        self.id_listbox.configure(yscrollcommand=scrollbar.set)
        count_label = ttk.Label(
            self._left_id_frame, text="共 0 个ID", font=("Segoe UI", 8), style="Dim.TLabel",
        )
        count_label.pack(anchor=tk.W, padx=4, pady=(2, 4))

        # 类名列表 frame
        self._left_class_frame = tk.Frame(self._left_stack, bg=self._bg("sidebar"))
        list_frame = ttk.Frame(self._left_class_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.class_listbox = tk.Listbox(
            list_frame, selectmode=tk.EXTENDED, height=15, **self._listbox_kwargs()
        )
        self.class_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.class_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar.pack_forget()
        self.class_listbox.configure(yscrollcommand=scrollbar.set)
        self.class_count_label = ttk.Label(
            self._left_class_frame, text="共 0 个类", font=("Segoe UI", 8), style="Dim.TLabel",
        )
        self.class_count_label.pack(anchor=tk.W, padx=4, pady=(2, 4))

        # 默认显示资源列表
        self._left_drawable_frame.pack(fill=tk.BOTH, expand=True)
        # Hide other frames initially
        self._left_layout_frame.pack_forget()
        self._left_string_frame.pack_forget()
        self._left_id_frame.pack_forget()
        self._left_class_frame.pack_forget()

        # ----- 中间栏：映射 + 日志 -----
        center_frame = tk.Frame(content_paned, bg=self._bg("main"))
        content_paned.add(center_frame, weight=1)
        center_paned = ttk.PanedWindow(center_frame, orient=tk.VERTICAL)
        center_paned.pack(fill=tk.BOTH, expand=True)

        work_frame = tk.Frame(center_paned, bg=self._bg("main"))
        center_paned.add(work_frame, weight=2)
        mapping_frame = tk.Frame(work_frame, bg=self._bg("main"))
        mapping_frame.pack(fill=tk.BOTH, expand=True)

        self._mapping_display_type = "drawable"
        self._mapping_title_var = tk.StringVar(value="Drawable 映射")
        self._section_title(mapping_frame, "", bg_key="main", textvariable=self._mapping_title_var)

        self.mapping_text = self._create_editor(
            mapping_frame, height=20, wrap=tk.WORD, font=("Consolas", 10),
            line_numbers=True,
        )

        log_frame = tk.Frame(center_paned, bg=self._bg("main"))
        center_paned.add(log_frame, weight=1)
        try:
            center_paned.pane(work_frame, minsize=200)
            center_paned.pane(log_frame, minsize=80)
        except tk.TclError:
            pass

        self._section_title(log_frame, "输出", bg_key="main")

        self.log_text = self._create_editor(
            log_frame, height=5, wrap=tk.WORD, font=("Consolas", 9),
        )
        self.status_var = tk.StringVar(value="就绪")

        # ----- 右侧边栏 -----
        right_outer = tk.Frame(content_paned, bg=self._bg("main"))
        content_paned.add(right_outer, weight=0)
        self._vline(right_outer, side=tk.LEFT)
        right_inner = tk.Frame(right_outer, bg=self._bg("sidebar"), width=300)
        right_inner.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right_inner.pack_propagate(False)

        self._section_title(right_inner, "命名格式", bg_key="sidebar")

        self._right_scroll = ScrollableFrame(right_inner, bg=self._bg("sidebar"))
        self._right_scroll.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        self._right_content_frame = self._right_scroll.body

        self._drawable_format_panel = ttk.Frame(self._right_content_frame)
        FormatPanelBuilder.build_drawable_panel(self._drawable_format_panel, self)

        self._layout_format_panel = ttk.Frame(self._right_content_frame)
        FormatPanelBuilder.build_layout_panel(self._layout_format_panel, self)

        self._string_format_panel = ttk.Frame(self._right_content_frame)
        FormatPanelBuilder.build_string_panel(self._string_format_panel, self)

        self._id_format_panel = ttk.Frame(self._right_content_frame)
        FormatPanelBuilder.build_id_panel(self._id_format_panel, self)

        self._class_format_panel = ttk.Frame(self._right_content_frame)
        FormatPanelBuilder.build_class_panel(self._class_format_panel, self)

        self._drawable_format_panel.pack(fill=tk.BOTH, expand=True)
        self._right_scroll.bind_wheel_to_body()

        self._content_paned = content_paned
        self.root.after_idle(self._init_paned_layout)

        # 底部状态栏
        status_bg = self._bg("statusbar") or "#007acc"
        status_fg = self.theme_manager.get_bg("statusbar_fg")
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
        
        ttk.Label(content_frame, text="Android Explorer", 
                 font=("Segoe UI", 12, "bold")).pack(pady=(0, 15))
        
        ttk.Label(content_frame, text="作者：大菠萝", 
                 font=("Segoe UI", 10)).pack(pady=3)
        
        ttk.Label(content_frame, text="邮箱：daboluo719@gmail.com", 
                 font=("Segoe UI", 10)).pack(pady=3)
        
        ttk.Button(content_frame, text="关闭", command=win.destroy).pack(pady=(15, 0))

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

    def build_format_string(self, order_mode, part_order, prefix, keyword, suffix, number):
        """构建格式预览字符串"""
        return FormatHelper.build_format_string(
            order_mode, part_order, prefix, keyword, suffix, number,
        )

    def _make_format_config(
        self, order_mode_var, part_order_var,
        prefix_var, keyword_var, suffix_var, number_var,
    ):
        return FormatHelper.make_config(
            order_mode_var.get(),
            part_order_var.get(),
            prefix_var.get(),
            keyword_var.get(),
            suffix_var.get(),
            number_var.get(),
        )

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

        if hasattr(self, '_right_scroll'):
            self.root.after_idle(self._right_scroll.update_scroll_region)

        # 同步中间映射编辑区显示类型（仅切到资源相关视图时）
        key_to_type = {"资源": "drawable", "布局": "layout", "字符": "string", "ID": "id", "类名": "class"}
        if key in key_to_type:
            self.refresh_mapping_display(key_to_type[key])
        
        # Update button selection states
        for view_key, button in self._nav_buttons.items():
            if view_key == key:
                button.configure(
                    bg=self._bg("sidebar_btn_active"),
                    fg=self._fg("sidebar_btn_active"),
                )
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
            button.configure(
                bg=self._bg("sidebar_btn_active"),
                fg=self._fg("sidebar_btn_active"),
            )
        else:
            button.configure(bg=self._bg("sidebar_btn"), fg=self._fg("sidebar_btn"))

    def _menu_execute(self):
        """顶部菜单：执行"""
        self.execute_rename()




    






    def _init_paned_layout(self):
        """设置三栏默认宽度比例"""
        try:
            w = self._content_paned.winfo_width()
            if w > 400:
                self._content_paned.sashpos(0, 220)
                self._content_paned.sashpos(1, max(w - 300, int(w * 0.62)))
        except tk.TclError:
            pass

    def _format_preview_args(self, type_name):
        """获取某资源类型的格式预览参数"""
        return (
            getattr(self, f'{type_name}_order_mode').get(),
            getattr(self, f'{type_name}_part_order').get(),
            getattr(self, f'{type_name}_prefix').get(),
            getattr(self, f'{type_name}_keyword').get(),
            getattr(self, f'{type_name}_suffix').get(),
            getattr(self, f'{type_name}_number').get(),
        )

    def _preview_fg(self):
        return self.theme_manager.get_bg("preview_fg")

    def update_drawable_format(self):
        if self.drawable_format_preview:
            self.drawable_format_preview.config(
                text=self.build_format_string(*self._format_preview_args('drawable')),
                foreground=self._preview_fg(),
            )

    def update_layout_format(self):
        if self.layout_format_preview:
            self.layout_format_preview.config(
                text=self.build_format_string(*self._format_preview_args('layout')),
                foreground=self._preview_fg(),
            )

    def update_string_format(self):
        if self.string_format_preview:
            self.string_format_preview.config(
                text=self.build_format_string(*self._format_preview_args('string')),
                foreground=self._preview_fg(),
            )

    def update_id_format(self):
        if self.id_format_preview:
            self.id_format_preview.config(
                text=self.build_format_string(*self._format_preview_args('id')),
                foreground=self._preview_fg(),
            )

    def update_class_format(self):
        if self.class_format_preview:
            sample = 'MainActivity'
            base = self.class_renamer.transform_class_name(
                sample,
                self.class_filter_chars.get(),
                self.class_replace_chars.get(),
            )
            formatted = self.build_format_string(*self._format_preview_args('class'))
            preview = (
                f'{sample} → {base} → {formatted}'
                if base != sample or formatted != base
                else formatted
            )
            self.class_format_preview.config(
                text=preview,
                foreground=self._preview_fg(),
            )

    def update_all_format_previews(self):
        """更新所有格式预览（当随机字符配置变更时调用）"""
        self.update_drawable_format()
        self.update_layout_format()
        self.update_string_format()
        self.update_id_format()
        self.update_class_format()

    def get_drawable_format_config(self):
        return self._make_format_config(
            self.drawable_order_mode, self.drawable_part_order,
            self.drawable_prefix, self.drawable_keyword,
            self.drawable_suffix, self.drawable_number,
        )

    def get_layout_format_config(self):
        return self._make_format_config(
            self.layout_order_mode, self.layout_part_order,
            self.layout_prefix, self.layout_keyword,
            self.layout_suffix, self.layout_number,
        )

    def get_string_format_config(self):
        return self._make_format_config(
            self.string_order_mode, self.string_part_order,
            self.string_prefix, self.string_keyword,
            self.string_suffix, self.string_number,
        )

    def get_id_format_config(self):
        return self._make_format_config(
            self.id_order_mode, self.id_part_order,
            self.id_prefix, self.id_keyword,
            self.id_suffix, self.id_number,
        )

    def get_class_format_config(self):
        return self._make_format_config(
            self.class_order_mode, self.class_part_order,
            self.class_prefix, self.class_keyword,
            self.class_suffix, self.class_number,
        )

    def _format_config_summary(self, config):
        """导出/日志用的格式描述"""
        order_desc = (
            '随机顺序' if config.get('order_mode') == 'random'
            else '→'.join(FormatHelper.PART_LABELS[k] for k in config['part_order'])
        )
        return (
            f"[{order_desc}] "
            f"前缀={config['prefix']!r} 关键词={config['keyword']!r} "
            f"后缀={config['suffix']!r} 序号={config['number']!r}"
        )

    def get_drawable_format(self):
        return self._format_config_summary(self.get_drawable_format_config())

    def get_layout_format(self):
        return self._format_config_summary(self.get_layout_format_config())

    def get_string_format(self):
        return self._format_config_summary(self.get_string_format_config())

    def get_id_format(self):
        return self._format_config_summary(self.get_id_format_config())

    def get_class_format(self):
        return self._format_config_summary(self.get_class_format_config())
    
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
        self._sync_editor_scrollbar(self.log_text)
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
    
    def _build_usage_toolbar(self, parent, resource_type):
        """左侧列表上方：检测使用情况 / 删除未使用"""
        bar = tk.Frame(parent, bg=self._bg('sidebar'))
        bar.pack(fill=tk.X, padx=4, pady=(4, 2))
        ttk.Button(
            bar, text='检测使用情况',
            command=lambda t=resource_type: self.check_resource_usage(t),
        ).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(
            bar, text='删除未使用',
            command=lambda t=resource_type: self.delete_unused_resources(t),
        ).pack(side=tk.LEFT)
        label = ttk.Label(bar, text='', font=('Segoe UI', 8), style='Dim.TLabel')
        label.pack(side=tk.LEFT, padx=(8, 0))
        if not hasattr(self, '_usage_summary_labels'):
            self._usage_summary_labels = {}
        self._usage_summary_labels[resource_type] = label

    def _clear_usage_status(self, resource_type=None):
        types = [resource_type] if resource_type else ('drawable', 'layout', 'string')
        for t in types:
            self._usage_status[t].clear()
            self._usage_unused[t].clear()
            if hasattr(self, '_usage_summary_labels') and t in self._usage_summary_labels:
                self._usage_summary_labels[t].config(text='')

    def _usage_unused_fg(self):
        return '#f48771' if self.theme_mode.get() == 'Dark' else '#c72e2e'

    def check_resource_usage(self, resource_type):
        """检测当前类型资源的使用情况（后台线程）"""
        project_path = self.project_path.get()
        if not project_path:
            messagebox.showwarning('警告', '请先选择项目路径')
            return
        if resource_type == 'drawable' and not self.drawable_files:
            messagebox.showinfo('提示', '请先扫描项目（选择项目后会自动扫描）')
            return
        if resource_type == 'layout' and not self.layout_files:
            messagebox.showinfo('提示', '请先扫描项目')
            return
        if resource_type == 'string' and not self.string_entries:
            messagebox.showinfo('提示', '请先扫描项目')
            return

        self.status_var.set(f'正在检测 {resource_type} 使用情况…')
        self.log(f'开始检测 {self._usage_type_label(resource_type)} 使用情况…')

        def worker():
            try:
                used, unused = self._run_usage_check(resource_type, project_path)
                self.root.after(0, lambda: self._on_usage_check_done(resource_type, used, unused))
            except Exception as exc:
                self.root.after(0, lambda: self._on_usage_check_error(resource_type, exc))

        threading.Thread(target=worker, daemon=True).start()

    def _usage_type_label(self, resource_type):
        return {'drawable': '资源(Drawable)', 'layout': '布局', 'string': '字符'}.get(
            resource_type, resource_type,
        )

    def _run_usage_check(self, resource_type, project_path):
        if resource_type == 'drawable':
            return self.usage_checker.check_drawables(
                project_path, self.drawable_files,
            )
        if resource_type == 'layout':
            return self.usage_checker.check_layouts(
                project_path, self.layout_files,
            )
        names = list(dict.fromkeys(e[0] for e in self.string_entries))
        return self.usage_checker.check_strings(
            project_path, names, self.string_sources,
        )

    def _on_usage_check_done(self, resource_type, used, unused):
        self._usage_status[resource_type] = {}
        for name in used:
            self._usage_status[resource_type][name] = True
        for name in unused:
            self._usage_status[resource_type][name] = False
        self._usage_unused[resource_type] = dict(unused)

        self._refresh_resource_listbox(resource_type)
        summary = f'已使用 {len(used)}，未使用 {len(unused)}'
        if hasattr(self, '_usage_summary_labels'):
            self._usage_summary_labels[resource_type].config(text=summary)
        self.log(f'{self._usage_type_label(resource_type)} 检测完成：{summary}')
        self.status_var.set(summary)

    def _on_usage_check_error(self, resource_type, exc):
        self.log(f'检测失败: {exc}', 'ERROR')
        messagebox.showerror('错误', f'检测使用情况失败：{exc}')
        self.status_var.set('检测失败')

    def _refresh_resource_listbox(self, resource_type):
        unused_fg = self._usage_unused_fg()
        normal_fg = self._fg('listbox')

        if resource_type == 'drawable':
            lb = self.drawable_listbox
            lb.delete(0, tk.END)
            status = self._usage_status.get('drawable', {})
            for file_path in self.drawable_files:
                stem = file_path.stem
                label = file_path.name
                if stem in status:
                    label = ('[未使用] ' if not status[stem] else '') + label
                lb.insert(tk.END, label)
                if stem in status and not status[stem]:
                    lb.itemconfig(tk.END, fg=unused_fg)
                else:
                    lb.itemconfig(tk.END, fg=normal_fg)
            n_unused = sum(1 for v in status.values() if v is False)
            self.drawable_count_label.config(
                text=f'共 {len(self.drawable_files)} 个文件'
                + (f'，未使用 {n_unused}' if status else ''),
            )
        elif resource_type == 'layout':
            lb = self.layout_listbox
            lb.delete(0, tk.END)
            status = self._usage_status.get('layout', {})
            for file_path in self.layout_files:
                stem = file_path.stem
                label = file_path.name
                if stem in status:
                    label = ('[未使用] ' if not status[stem] else '') + label
                lb.insert(tk.END, label)
                if stem in status and not status[stem]:
                    lb.itemconfig(tk.END, fg=unused_fg)
                else:
                    lb.itemconfig(tk.END, fg=normal_fg)
            n_unused = sum(1 for v in status.values() if v is False)
            self.layout_count_label.config(
                text=f'共 {len(self.layout_files)} 个文件'
                + (f'，未使用 {n_unused}' if status else ''),
            )
        elif resource_type == 'string':
            lb = self.string_listbox
            lb.delete(0, tk.END)
            status = self._usage_status.get('string', {})
            for name, preview in self.string_entries:
                line = f'{name}  |  {preview}' if preview else name
                if name in status:
                    line = ('[未使用] ' if not status[name] else '') + line
                lb.insert(tk.END, line)
                if name in status and not status[name]:
                    lb.itemconfig(tk.END, fg=unused_fg)
                else:
                    lb.itemconfig(tk.END, fg=normal_fg)
            n_unused = sum(1 for v in status.values() if v is False)
            self.string_count_label.config(
                text=f'共 {len(self.string_entries)} 条'
                + (f'，未使用 {n_unused}' if status else ''),
            )

    def delete_unused_resources(self, resource_type):
        """一键删除未使用的资源（需先检测）"""
        unused = self._usage_unused.get(resource_type) or {}
        if not unused:
            if not self._usage_status.get(resource_type):
                messagebox.showinfo('提示', '请先点击「检测使用情况」')
            else:
                messagebox.showinfo('提示', '没有检测到未使用的资源')
            return

        label = self._usage_type_label(resource_type)
        names = sorted(unused.keys())
        preview = '\n'.join(names[:15])
        if len(names) > 15:
            preview += f'\n… 等共 {len(names)} 项'

        file_count = sum(len(paths) for paths in unused.values())
        if not messagebox.askyesno(
            '确认删除',
            f'将删除 {len(names)} 个未使用的{label}资源（{file_count} 个文件/条目）：\n\n'
            f'{preview}\n\n此操作不可撤销，请确保已备份项目。',
        ):
            return

        try:
            deleted_count = self._execute_delete_unused(resource_type, unused)
            self._clear_usage_status(resource_type)
            self.log(f'已删除 {deleted_count} 个未使用{label}相关文件/条目')
            messagebox.showinfo('完成', f'已删除 {deleted_count} 项，正在重新扫描…')
            self.scan_files()
            if resource_type == 'drawable':
                self._switch_left_view('资源')
            elif resource_type == 'layout':
                self._switch_left_view('布局')
            elif resource_type == 'string':
                self._switch_left_view('字符')
        except Exception as exc:
            self.log(f'删除失败: {exc}', 'ERROR')
            messagebox.showerror('错误', f'删除失败：\n{exc}')

    def _execute_delete_unused(self, resource_type, unused_map):
        if resource_type == 'drawable':
            paths = []
            for paths_list in unused_map.values():
                paths.extend(paths_list)
            deleted = self.usage_checker.delete_drawable_files(paths)
            for stem in list(unused_map.keys()):
                self.drawable_mapping.pop(stem, None)
            return len(deleted)
        if resource_type == 'layout':
            paths = []
            for paths_list in unused_map.values():
                paths.extend(paths_list)
            deleted = self.usage_checker.delete_layout_files(paths)
            for stem in list(unused_map.keys()):
                self.layout_mapping.pop(stem, None)
            return len(deleted)
        if resource_type == 'string':
            removed = self.usage_checker.remove_strings_from_xml(
                self.string_sources, list(unused_map.keys()),
            )
            for name in unused_map:
                self.string_mapping.pop(name, None)
            return len(removed)
        return 0

    def scan_files(self):
        """扫描项目中的资源文件"""
        project_path = self.project_path.get()
        if not project_path:
            messagebox.showwarning("警告", "请先选择项目路径")
            return

        self._clear_usage_status()

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
            self.drawable_count_label.config(text=f'共 {len(self.drawable_files)} 个文件')
        if hasattr(self, 'layout_count_label'):
            self.layout_count_label.config(text=f'共 {len(self.layout_files)} 个文件')
        if hasattr(self, 'string_count_label'):
            self.string_count_label.config(text=f'共 {len(self.string_entries)} 条')
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
        self.string_sources.clear()
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
                                    self.string_sources[name].append(file_path)
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
    
    def generate_random_string(self, length=None):
        """生成随机字符串"""
        if length is None:
            length = self.random_length.get()
        
        # 构建字符集
        char_set = ""
        if self.random_include_lowercase.get():
            char_set += string.ascii_lowercase
        if self.random_include_uppercase.get():
            char_set += string.ascii_uppercase
        if self.random_include_digits.get():
            char_set += string.digits
        
        # 如果没有任何字符类型被选中，默认使用小写字母
        if not char_set:
            char_set = string.ascii_lowercase
        
        return ''.join(random.choices(char_set, k=length))
    
    def generate_mapping(self):
        """在后台线程生成当前类型的映射，避免界面无响应"""
        target_type = self._infer_target_mapping_type()

        if target_type == "drawable":
            if not self.drawable_files:
                messagebox.showwarning("警告", "未扫描到 drawable 文件，请先扫描")
                return
            files_snapshot = list(self.drawable_files)
            format_config = self.get_drawable_format_config()
        elif target_type == "layout":
            if not self.layout_files:
                messagebox.showwarning("警告", "未扫描到 layout 文件，请先扫描")
                return
            files_snapshot = list(self.layout_files)
            format_config = self.get_layout_format_config()
        elif target_type == "string":
            if not self.string_files:
                messagebox.showwarning("警告", "未扫描到 strings.xml，请先扫描")
                return
            format_config = self.get_string_format_config()
            files_snapshot = None
        elif target_type == "id":
            if not self.id_entries:
                messagebox.showwarning("警告", "未扫描到 ID（@+id/...），请先扫描")
                return
            format_config = self.get_id_format_config()
            entries_snapshot = list(self.id_entries)
            files_snapshot = None
        else:  # class
            if not self.class_files:
                messagebox.showwarning("警告", "未扫描到 Java 类文件，请先扫描")
                return
            files_snapshot = list(self.class_files)
            format_config = self.get_class_format_config()
            filter_chars = self.class_filter_chars.get()
            replace_chars = self.class_replace_chars.get()

        self.status_var.set("正在生成映射...")
        self.root.update_idletasks()

        def run():
            try:
                if target_type == "drawable":
                    mapping = self.renamer.generate_mapping(files_snapshot, format_config, self)
                elif target_type == "layout":
                    mapping = self.renamer.generate_mapping(files_snapshot, format_config, self)
                elif target_type == "string":
                    mapping = self.renamer.generate_string_mapping(self.string_files, format_config, self)
                elif target_type == "id":
                    mapping = self._generate_id_mapping_fast(format_config, entries_snapshot)
                else:  # class
                    mapping = self.class_renamer.generate_class_mapping(
                        files_snapshot, format_config, filter_chars, replace_chars
                    )
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

    def _generate_id_mapping_fast(self, format_config, entries=None):
        """纯计算生成 ID 映射（不操作 UI，可在后台线程调用）"""
        if entries is None:
            entries = self.id_entries
        mapping = OrderedDict()
        used_names = set()
        for idx, old_name in enumerate(entries, 1):
            counter = idx
            while True:
                random_str = self.generate_random_string()
                new_name = FormatHelper.build_name(
                    format_config, old_name, counter, random_str, rng=random
                )
                if new_name and new_name not in used_names:
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
        self._sync_editor_scrollbar(self.mapping_text)
        self._sync_line_numbers(self.mapping_text)

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
        # 对于类文件，使用专门的重命名方法
        if resource_type == "class":
            renamed_count = self.class_renamer.rename_class_files(
                files, 
                mapping, 
                preview_mode=self.preview_mode.get()
            )
            rename_list = [(old, new) for old, new in self.class_renamer.renamed_files.items()]
            return renamed_count, rename_list
        
        # 其他资源类型使用原有逻辑
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
        return self.apply_replacements(
            self._get_drawable_replace_rules(),
            search_needles=list(self.drawable_mapping.keys()),
        )

    def update_layout_references(self):
        return self.apply_replacements(
            self._get_layout_replace_rules(),
            search_needles=list(self.layout_mapping.keys()),
        )

    def update_string_references(self):
        return self.apply_replacements(
            self._get_string_replace_rules(),
            search_needles=list(self.string_mapping.keys()),
        )

    def update_id_references(self):
        return self.apply_replacements(
            self._get_id_replace_rules(),
            search_needles=list(self.id_mapping.keys()),
        )

    def apply_replacements(self, replace_rules, search_needles=None):
        """应用替换规则到项目文件（后台线程调用，已做性能优化）"""
        if not replace_rules:
            return 0

        project_path = Path(self.project_path.get())
        if not project_path.exists():
            return 0

        compiled_rules = []
        for old_pattern, new_pattern in replace_rules:
            try:
                compiled_rules.append((re.compile(old_pattern), new_pattern))
            except re.error as e:
                self.root.after(
                    0,
                    lambda p=old_pattern, err=e: self.log(
                        f"正则表达式编译失败: {p} - {err}", "ERROR"
                    ),
                )
        if not compiled_rules:
            return 0

        needles = set(search_needles or [])
        if not needles:
            for pattern, _ in replace_rules:
                token = pattern.replace(r'\b', '').replace('\\', '')[:32]
                if token and not token.startswith('('):
                    needles.add(token.split('.')[-1].split('/')[0].strip('^$'))

        all_files = FileHelper.collect_project_files(project_path)
        total_files = len(all_files)
        self.root.after(0, lambda: self.log(f"开始更新引用，共 {total_files} 个文件..."))

        updated_count = 0
        preview = self.preview_mode.get()

        for idx, file_path in enumerate(all_files, 1):
            if idx == 1 or idx % 50 == 0 or idx == total_files:
                progress = f"正在更新引用... ({idx}/{total_files})"
                self.root.after(0, lambda p=progress: self.status_var.set(p))

            try:
                content = file_path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                continue
            except OSError as e:
                self.root.after(
                    0,
                    lambda fp=file_path, err=e: self.log(f"读取失败 {fp.name}: {err}", "ERROR"),
                )
                continue

            if needles and not ReferenceUpdater.may_need_update(content, needles):
                continue

            new_content = ReferenceUpdater.apply_compiled_rules(content, compiled_rules)
            if new_content == content:
                continue

            if not preview:
                try:
                    file_path.write_text(new_content, encoding='utf-8')
                except OSError as e:
                    self.root.after(
                        0,
                        lambda fp=file_path, err=e: self.log(f"写入失败 {fp.name}: {err}", "ERROR"),
                    )
                    continue

            updated_count += 1

        self.root.after(
            0,
            lambda n=updated_count: self.log(f"引用更新完成，共修改 {n} 个文件"),
        )
        return updated_count
    
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
                    if res_type == "class":
                        def on_progress(done, total):
                            msg = f"正在更新类引用... ({done}/{total})"
                            self.root.after(0, lambda m=msg: self.status_var.set(m))

                        updated_count = self.class_renamer.update_all_class_references(
                            Path(self.project_path.get()),
                            self.class_mapping,
                            preview_mode=self.preview_mode.get(),
                            progress_callback=on_progress,
                        )
                    else:
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
        verification_issues = []
        
        if self.preview_mode.get():
            self.log("预览完成 (未实际修改)")
        else:
            self.log("操作完成")
            # 自动导出映射表
            self._auto_export_mapping()
            
            # 对于类重命名，执行验证
            if type_name == "类名(Class)" and self.class_mapping:
                self.log("正在验证重命名完成情况...")
                try:
                    project_path = Path(self.project_path.get())
                    verification_issues = self.class_renamer.verify_rename_completion(project_path, self.class_mapping)
                    report = self.class_renamer.generate_verification_report(verification_issues)
                    self.log(report)
                    
                    if verification_issues:
                        self.log("⚠️ 发现未更新的引用，请查看日志", "WARNING")
                except Exception as e:
                    self.log(f"验证失败: {e}", "ERROR")
            
            self.log("正在重新扫描...")
            self.root.after(0, self._run_rescan)

        self.log("=" * 50)
        self.status_var.set("就绪")
        if self.preview_mode.get():
            messagebox.showinfo(
                "预览完成",
                f"【{type_name}】预览完成（未写入文件）\n"
                f"将重命名: {total_renamed}\n将更新引用: {updated_count}",
            )
        else:
            self._show_rename_done_message(
                type_name, total_renamed, updated_count, verification_issues
            )

    def _run_rescan(self):
        try:
            self.scan_files()
            self.log("重新扫描完成")
        except Exception as e:
            self.log(f"重新扫描失败: {e}", "ERROR")

    def _show_rename_done_message(self, type_name, total_renamed, updated_count, verification_issues):
        if type_name == "类名(Class)" and verification_issues:
            messagebox.showwarning(
                "完成（有警告）",
                f"【{type_name}】操作完成！\n"
                f"重命名: {total_renamed}\n"
                f"更新引用: {updated_count}\n\n"
                f"⚠️ 发现 {len(verification_issues)} 处未更新的引用\n"
                f"请查看日志获取详细信息",
            )
        elif type_name == "类名(Class)":
            messagebox.showinfo(
                "完成",
                f"【{type_name}】操作完成！\n"
                f"重命名: {total_renamed}\n"
                f"更新引用: {updated_count}\n\n"
                f"✅ 验证通过：所有引用已成功更新",
            )
        else:
            messagebox.showinfo(
                "完成",
                f"【{type_name}】操作完成！\n重命名: {total_renamed}\n更新引用: {updated_count}",
            )

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