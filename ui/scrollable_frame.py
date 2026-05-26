#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk


class ScrollableFrame(ttk.Frame):
    """可垂直滚动的容器，用于右侧格式面板等长内容"""

    def __init__(self, parent, bg=None, **kwargs):
        super().__init__(parent, **kwargs)
        canvas_bg = bg or '#252526'
        self._canvas = tk.Canvas(
            self, highlightthickness=0, borderwidth=0, bg=canvas_bg,
        )
        self._scrollbar = ttk.Scrollbar(
            self, orient=tk.VERTICAL, command=self._canvas.yview,
            style='Vertical.TScrollbar',
        )
        self.body = ttk.Frame(self._canvas, style='Sidebar.TFrame')

        self._canvas_window = self._canvas.create_window((0, 0), window=self.body, anchor=tk.NW)
        self._canvas.configure(yscrollcommand=self._on_yscroll)

        self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.body.bind('<Configure>', self._on_body_configure)
        self._canvas.bind('<Configure>', self._on_canvas_configure)
        self._mousewheel_bound = False

        for widget in (self, self._canvas, self.body):
            widget.bind('<Enter>', self._bind_mousewheel)
            widget.bind('<Leave>', self._maybe_unbind_mousewheel)

    def set_background(self, bg):
        self._canvas.configure(bg=bg)

    def update_scroll_region(self):
        self._canvas.configure(scrollregion=self._canvas.bbox('all'))
        self.after_idle(self._sync_scrollbar_visibility)

    def bind_wheel_to_body(self):
        """为格式面板内所有控件绑定滚轮，避免鼠标在输入框上时无法滚动"""
        def _walk(widget):
            widget.bind('<MouseWheel>', self._on_mousewheel, add='+')
            for child in widget.winfo_children():
                _walk(child)
        _walk(self.body)

    def _on_body_configure(self, _event=None):
        self.update_scroll_region()

    def _on_canvas_configure(self, event):
        self._canvas.itemconfigure(self._canvas_window, width=event.width)
        self.after_idle(self._sync_scrollbar_visibility)

    def _on_yscroll(self, first, last):
        self._scrollbar.set(first, last)

    def _content_taller_than_view(self):
        bbox = self._canvas.bbox('all')
        if not bbox:
            return False
        content_h = bbox[3] - bbox[1]
        return content_h > self._canvas.winfo_height()

    def _sync_scrollbar_visibility(self):
        if self._content_taller_than_view():
            if not self._scrollbar.winfo_ismapped():
                self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        else:
            self._scrollbar.pack_forget()
            self._canvas.yview_moveto(0)

    def _on_mousewheel(self, event):
        if not self._content_taller_than_view():
            return
        delta = -1 * (event.delta // 120) if event.delta else 0
        if delta:
            self._canvas.yview_scroll(delta, 'units')

    def _bind_mousewheel(self, _event=None):
        if not self._mousewheel_bound:
            self.bind_all('<MouseWheel>', self._on_mousewheel)
            self._mousewheel_bound = True

    def _maybe_unbind_mousewheel(self, event=None):
        if event:
            x, y = self.winfo_pointerxy()
            target = self.winfo_containing(x, y)
            w = target
            while w is not None:
                if w == self:
                    return
                w = w.master if hasattr(w, 'master') else None
        if self._mousewheel_bound:
            self.unbind_all('<MouseWheel>')
            self._mousewheel_bound = False

    def _unbind_mousewheel(self):
        if self._mousewheel_bound:
            self.unbind_all('<MouseWheel>')
            self._mousewheel_bound = False
