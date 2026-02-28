#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import xml.etree.ElementTree as ET
from pathlib import Path


class ScannerManager:
    """扫描管理器 - 负责所有资源扫描逻辑"""
    
    def __init__(self, app):
        self.app = app
    
    def scan_all_files(self, project_path):
        """扫描所有资源文件"""
        if not project_path:
            return
        
        self.app.drawable_files.clear()
        self.app.layout_files.clear()
        self.app.string_files.clear()
        self.app.id_layout_files.clear()
        self.app.id_entries.clear()
        
        # 清空列表框
        for listbox_name in ['drawable_listbox', 'layout_listbox', 'string_listbox', 'id_listbox', 'class_listbox']:
            if hasattr(self.app, listbox_name):
                getattr(self.app, listbox_name).delete(0, 'end')
        
        self.app.log("开始扫描资源文件...")
        
        # 扫描各类资源
        self.scan_string_files(project_path)
        self.scan_id_entries(project_path)
        self.scan_class_files(project_path)
        
        if self.app.resource_type.get() in ["drawable", "both"]:
            self.scan_drawable_files(project_path)
        
        if self.app.resource_type.get() in ["layout", "both"]:
            self.scan_layout_files(project_path)
        
        # 更新计数
        self._update_counts()
        
        # 更新状态栏
        self.app.status_var.set(
            f"已找到 {len(self.app.drawable_files)} 个drawable, {len(self.app.layout_files)} 个layout, "
            f"{len(self.app.string_entries)} 条string, {len(self.app.id_entries)} 条id, {len(self.app.class_files)} 个类"
        )
    
    def scan_drawable_files(self, project_path):
        """扫描drawable文件"""
        self.app.drawable_files = self.app.scanner.scan_drawable_files(project_path)
        if hasattr(self.app, 'drawable_listbox'):
            self.app.drawable_listbox.delete(0, 'end')
            for file_path in self.app.drawable_files:
                self.app.drawable_listbox.insert('end', file_path.name)
    
    def scan_layout_files(self, project_path):
        """扫描layout文件"""
        self.app.layout_files = self.app.scanner.scan_layout_files(project_path)
        if hasattr(self.app, 'layout_listbox'):
            self.app.layout_listbox.delete(0, 'end')
            for file_path in self.app.layout_files:
                self.app.layout_listbox.insert('end', file_path.name)
    
    def scan_string_files(self, project_path):
        """扫描strings.xml文件"""
        self.app.string_files.clear()
        self.app.string_entries.clear()
        
        selected = self.app.module_selection.get() if hasattr(self.app, 'module_selection') else '全部模块'
        res_paths = self._get_res_paths(project_path, selected)
        
        for res_path in res_paths:
            if res_path.exists():
                values_dir = res_path / 'values'
                if values_dir.exists():
                    for file_path in values_dir.iterdir():
                        if file_path.is_file() and file_path.name == 'strings.xml':
                            self.app.string_files.append(file_path)
                            self._parse_strings_xml(file_path)
        
        if hasattr(self.app, 'string_listbox'):
            self.app.string_listbox.delete(0, 'end')
            for name, preview in self.app.string_entries:
                self.app.string_listbox.insert('end', f"{name}  |  {preview}" if preview else name)
        
        self.app.log(f"String资源扫描完成，找到 {len(self.app.string_files)} 个strings.xml，共 {len(self.app.string_entries)} 条string")
    
    def scan_id_entries(self, project_path):
        """扫描layout中的ID"""
        self.app.id_layout_files = self.app.scanner.scan_layout_files(project_path)
        id_set = set()
        
        id_attr_patterns = [
            re.compile(r'android:id\s*=\s*"@\+id/([A-Za-z0-9_]+)"'),
            re.compile(r"android:id\s*=\s*'@\+id/([A-Za-z0-9_]+)'"),
        ]
        fallback_pattern = re.compile(r'@\+id/([A-Za-z0-9_]+)')
        
        for file_path in self.app.id_layout_files:
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
                    id_set.update(fallback_pattern.findall(content))
            except Exception as e:
                self.app.log(f"解析ID失败 {file_path}: {e}", "ERROR")
        
        self.app.id_entries = sorted(id_set)
        if hasattr(self.app, "id_listbox"):
            self.app.id_listbox.delete(0, 'end')
            for name in self.app.id_entries:
                self.app.id_listbox.insert('end', name)
        
        self.app.log(f"ID扫描完成，找到 {len(self.app.id_entries)} 条id")
    
    def scan_class_files(self, project_path):
        """扫描Java类文件"""
        try:
            if isinstance(project_path, str):
                project_path = Path(project_path)
            
            self.app.log(f"开始扫描Java类文件，项目路径: {project_path}")
            
            self.app.class_files = self.app.class_renamer.scan_java_files(
                project_path, 
                self.app.module_paths, 
                self.app.module_selection.get()
            )
            
            if hasattr(self.app, 'class_listbox'):
                self.app.class_listbox.delete(0, 'end')
                for file_path in self.app.class_files:
                    self.app.class_listbox.insert('end', file_path.name)
            
            self.app.log(f"Java类扫描完成，找到 {len(self.app.class_files)} 个文件")
        except Exception as e:
            self.app.log(f"扫描Java类文件失败: {e}", "ERROR")
    
    def _get_res_paths(self, project_path, selected):
        """获取资源路径列表"""
        res_paths = []
        if selected == '全部模块':
            for mp in self.app.module_paths.values():
                res_paths.extend([mp / 'src' / 'main' / 'res', mp / 'res'])
        else:
            mp = self.app.module_paths.get(selected, Path(project_path))
            res_paths.extend([mp / 'src' / 'main' / 'res', mp / 'res'])
        return res_paths
    
    def _parse_strings_xml(self, file_path):
        """解析strings.xml文件"""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            for elem in root.findall('string'):
                name = elem.attrib.get('name')
                if not name:
                    continue
                text = (elem.text or '').strip()
                preview = (text[:50] + '…') if len(text) > 50 else text
                self.app.string_entries.append((name, preview))
        except Exception as e:
            self.app.log(f"解析 {file_path} 失败: {e}", "ERROR")
    
    def _update_counts(self):
        """更新计数标签"""
        if hasattr(self.app, 'drawable_count_label'):
            self.app.drawable_count_label.config(text=f"({len(self.app.drawable_files)})")
        if hasattr(self.app, 'layout_count_label'):
            self.app.layout_count_label.config(text=f"({len(self.app.layout_files)})")
        if hasattr(self.app, 'string_count_label'):
            self.app.string_count_label.config(text=f"({len(self.app.string_entries)})")
        if hasattr(self.app, 'class_count_label'):
            self.app.class_count_label.config(text=f"共 {len(self.app.class_files)} 个类")
