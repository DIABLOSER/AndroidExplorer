#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk


class ToolTip:
    """简单的Tooltip工具提示类"""
    def __init__(self, widget):
        self.widget = widget
        self.tip_window = None
        self.text = ""
        
    def show_tip(self, text, x, y):
        """显示提示"""
        if self.tip_window or not text:
            return
        self.text = text
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                        background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                        font=("Consolas", 9))
        label.pack(ipadx=1)
        
    def hide_tip(self):
        """隐藏提示"""
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()
