#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk

from utils.format_helper import FormatHelper


class PartOrderEditor(ttk.Frame):
    """部件顺序编辑器（前缀 / 关键词 / 后缀 / 序号）"""

    def __init__(self, parent, part_order_var, on_change=None, listbox_kwargs=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.part_order_var = part_order_var
        self._on_change = on_change
        self._syncing = False

        ttk.Label(self, text='部件顺序（上→下）:').pack(anchor=tk.W, pady=(0, 2))
        row = ttk.Frame(self)
        row.pack(fill=tk.X)

        lb_kw = dict(height=4, exportselection=False, font=('Segoe UI', 9))
        if listbox_kwargs:
            lb_kw.update(listbox_kwargs)
        self._listbox = tk.Listbox(row, **lb_kw)
        self._listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)

        btn_col = ttk.Frame(row)
        btn_col.pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(btn_col, text='↑', width=3, command=self._move_up).pack(pady=1)
        ttk.Button(btn_col, text='↓', width=3, command=self._move_down).pack(pady=1)

        self.part_order_var.trace_add('write', self._on_var_changed)
        self._load_from_var()

    def _notify(self):
        if self._on_change:
            self._on_change()

    def _load_from_var(self):
        labels = FormatHelper.labels_from_part_order(self.part_order_var.get())
        self._listbox.delete(0, tk.END)
        for label in labels:
            self._listbox.insert(tk.END, label)
        self._listbox.configure(height=max(4, min(6, len(labels))))

    def _save_to_var(self):
        labels = [self._listbox.get(i) for i in range(self._listbox.size())]
        self._syncing = True
        self.part_order_var.set(FormatHelper.part_order_from_labels(labels))
        self._syncing = False
        self._notify()

    def _on_var_changed(self, *_args):
        if self._syncing:
            return
        self._load_from_var()

    def _move_up(self):
        sel = self._listbox.curselection()
        if not sel or sel[0] == 0:
            return
        idx = sel[0]
        text = self._listbox.get(idx)
        self._listbox.delete(idx)
        self._listbox.insert(idx - 1, text)
        self._listbox.selection_set(idx - 1)
        self._save_to_var()

    def _move_down(self):
        sel = self._listbox.curselection()
        if not sel or sel[0] >= self._listbox.size() - 1:
            return
        idx = sel[0]
        text = self._listbox.get(idx)
        self._listbox.delete(idx)
        self._listbox.insert(idx + 1, text)
        self._listbox.selection_set(idx + 1)
        self._save_to_var()


class FormatPanelBuilder:
    """格式面板构建器"""

    @staticmethod
    def build_drawable_panel(parent, app):
        content = ttk.Frame(parent, style='Sidebar.TFrame')
        content.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 8))
        FormatPanelBuilder._build_format_controls(
            content, app, 'drawable',
            app.drawable_order_mode, app.drawable_part_order,
            app.drawable_prefix, app.drawable_keyword,
            app.drawable_suffix, app.drawable_number,
            on_change=app.update_drawable_format,
        )
        app.drawable_format_preview = FormatPanelBuilder._build_preview(content, app)
        FormatPanelBuilder._build_hint(
            content, app,
            '后缀默认 {random}，序号默认 {number:04d}；随机字符配置见下方',
        )

    @staticmethod
    def build_layout_panel(parent, app):
        content = ttk.Frame(parent, style='Sidebar.TFrame')
        content.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 8))
        FormatPanelBuilder._build_format_controls(
            content, app, 'layout',
            app.layout_order_mode, app.layout_part_order,
            app.layout_prefix, app.layout_keyword,
            app.layout_suffix, app.layout_number,
            on_change=app.update_layout_format,
        )
        app.layout_format_preview = FormatPanelBuilder._build_preview(content, app)

    @staticmethod
    def build_string_panel(parent, app):
        content = ttk.Frame(parent, style='Sidebar.TFrame')
        content.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 8))
        FormatPanelBuilder._build_format_controls(
            content, app, 'string',
            app.string_order_mode, app.string_part_order,
            app.string_prefix, app.string_keyword,
            app.string_suffix, app.string_number,
            on_change=app.update_string_format,
        )
        app.string_format_preview = FormatPanelBuilder._build_preview(content, app)

    @staticmethod
    def build_id_panel(parent, app):
        content = ttk.Frame(parent, style='Sidebar.TFrame')
        content.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 8))
        FormatPanelBuilder._build_format_controls(
            content, app, 'id',
            app.id_order_mode, app.id_part_order,
            app.id_prefix, app.id_keyword,
            app.id_suffix, app.id_number,
            on_change=app.update_id_format,
        )
        app.id_format_preview = FormatPanelBuilder._build_preview(content, app)
        FormatPanelBuilder._build_hint(content, app, '用于重命名 @+id/xxx，引用将同步更新')

    @staticmethod
    def build_class_panel(parent, app):
        content = ttk.Frame(parent, style='Sidebar.TFrame')
        content.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 8))
        FormatPanelBuilder._build_format_controls(
            content, app, 'class',
            app.class_order_mode, app.class_part_order,
            app.class_prefix, app.class_keyword,
            app.class_suffix, app.class_number,
            on_change=app.update_class_format,
        )

        ttk.Label(content, text='类名处理', style='Dim.TLabel').pack(anchor=tk.W, pady=(10, 4))
        ttk.Label(content, text='过滤字符:').pack(anchor=tk.W, pady=(4, 0))
        app.class_filter_entry = ttk.Entry(content, textvariable=app.class_filter_chars)
        app.class_filter_entry.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(content, text='替换字符:').pack(anchor=tk.W, pady=(0, 0))
        app.class_replace_entry = ttk.Entry(content, textvariable=app.class_replace_chars)
        app.class_replace_entry.pack(fill=tk.X, pady=(0, 4))

        app.class_format_preview = FormatPanelBuilder._build_preview(content, app)
        FormatPanelBuilder._build_hint(content, app, '重命名.java文件，更新 AndroidManifest 与 import 引用')
        FormatPanelBuilder._build_hint(
            content, app,
            '过滤：待处理的子串（逗号分隔，如 Activity,Fragment）',
        )
        FormatPanelBuilder._build_hint(
            content, app,
            '替换：与过滤项对应替换为的内容（如 View,Item）；仅一项则共用；留空则删除',
        )

    @staticmethod
    def _build_format_controls(
        parent, app, type_name,
        order_mode_var, part_order_var,
        prefix_var, keyword_var, suffix_var, number_var,
        on_change=None,
    ):
        ttk.Label(parent, text='顺序模式:').pack(anchor=tk.W, pady=(0, 2))
        mode_f = ttk.Frame(parent)
        mode_f.pack(fill=tk.X, pady=(0, 4))
        ttk.Radiobutton(
            mode_f, text='固定顺序', variable=order_mode_var, value='fixed',
            command=on_change,
        ).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Radiobutton(
            mode_f, text='随机顺序', variable=order_mode_var, value='random',
            command=on_change,
        ).pack(side=tk.LEFT)

        editor = PartOrderEditor(
            parent, part_order_var, on_change=on_change,
            listbox_kwargs=app._listbox_kwargs(),
        )
        editor.pack(fill=tk.X, pady=(0, 6))
        setattr(app, f'{type_name}_part_order_editor', editor)

        def _bind_entry(var):
            var.trace_add('write', lambda *_a: on_change() if on_change else None)

        for label, var, attr in [
            ('前缀:', prefix_var, 'prefix'),
            ('关键词:', keyword_var, 'keyword'),
            ('后缀:', suffix_var, 'suffix'),
            ('序号:', number_var, 'number'),
        ]:
            row = ttk.Frame(parent)
            row.pack(fill=tk.X, pady=(4, 4))
            ttk.Label(row, text=label).pack(anchor=tk.W)
            entry = ttk.Entry(row, textvariable=var)
            entry.pack(fill=tk.X)
            setattr(app, f'{type_name}_{attr}_entry', entry)
            _bind_entry(var)

        random_cfg_frame = ttk.Frame(parent)
        random_cfg_frame.pack(fill=tk.X, pady=(0, 6))
        FormatPanelBuilder._build_random_config(random_cfg_frame, app)

        order_mode_var.trace_add('write', lambda *_a: on_change() if on_change else None)
        part_order_var.trace_add('write', lambda *_a: on_change() if on_change else None)

    @staticmethod
    def _build_random_config(parent, app):
        ttk.Label(parent, text='随机字符配置:').pack(anchor=tk.W, pady=(4, 2))
        length_frame = ttk.Frame(parent)
        length_frame.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(length_frame, text='长度:').pack(side=tk.LEFT, padx=(0, 4))
        ttk.Spinbox(
            length_frame, from_=1, to=20, width=5, textvariable=app.random_length,
        ).pack(side=tk.LEFT)

        type_frame = ttk.Frame(parent)
        type_frame.pack(fill=tk.X, pady=(0, 2))
        ttk.Checkbutton(type_frame, text='小写字母', variable=app.random_include_lowercase).pack(
            side=tk.LEFT, padx=(0, 8))
        ttk.Checkbutton(type_frame, text='大写字母', variable=app.random_include_uppercase).pack(
            side=tk.LEFT, padx=(0, 8))
        ttk.Checkbutton(type_frame, text='数字', variable=app.random_include_digits).pack(side=tk.LEFT)

    @staticmethod
    def _build_preview(parent, app):
        prev_f = ttk.Frame(parent)
        prev_f.pack(fill=tk.X, pady=(0, 2))
        ttk.Label(prev_f, text='预览:').pack(side=tk.LEFT, padx=(0, 4))
        preview_label = ttk.Label(
            prev_f, text='', foreground=app.theme_manager.get_bg('preview_fg'), wraplength=220,
        )
        preview_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        return preview_label

    @staticmethod
    def _build_hint(parent, app, text):
        ttk.Label(parent, text=text, font=('Segoe UI', 8), style='Dim.TLabel').pack(
            anchor=tk.W, pady=(0, 4),
        )
