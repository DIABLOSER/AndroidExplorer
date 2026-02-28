#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path


class ResourceScanner:
    """资源文件扫描器"""
    
    def __init__(self, module_selection, module_paths, log_func=None):
        self.module_selection = module_selection
        self.module_paths = module_paths
        self.log = log_func or (lambda msg: None)

    def scan_drawable_files(self, project_path):
        """扫描drawable文件"""
        drawable_dirs = [
            'drawable', 'drawable-hdpi', 'drawable-mdpi', 'drawable-xhdpi',
            'drawable-xxhdpi', 'drawable-xxxhdpi', 'drawable-nodpi', 'drawable-anydpi'
        ]
        extensions = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.xml', '.svg'}
        selected = self.module_selection.get() if hasattr(self.module_selection, 'get') else '全部模块'
        res_paths = []
        
        if selected == '全部模块':
            for mp in self.module_paths.values():
                res_paths.extend([mp / 'src' / 'main' / 'res', mp / 'res'])
        else:
            mp = self.module_paths.get(selected, Path(project_path))
            res_paths.extend([mp / 'src' / 'main' / 'res', mp / 'res'])
        
        found_files = []
        for res_path in res_paths:
            if res_path.exists():
                for drawable_dir in drawable_dirs:
                    dir_path = res_path / drawable_dir
                    if dir_path.exists():
                        for file_path in dir_path.iterdir():
                            if file_path.is_file() and file_path.suffix.lower() in extensions:
                                found_files.append(file_path)
        
        self.log(f"Drawable扫描完成，找到 {len(found_files)} 个文件")
        return found_files

    def scan_layout_files(self, project_path):
        """扫描layout文件"""
        layout_dirs = ['layout', 'layout-land', 'layout-port', 'layout-sw600dp', 'layout-w600dp']
        extensions = {'.xml'}
        selected = self.module_selection.get() if hasattr(self.module_selection, 'get') else '全部模块'
        res_paths = []
        
        if selected == '全部模块':
            for mp in self.module_paths.values():
                res_paths.extend([mp / 'src' / 'main' / 'res', mp / 'res'])
        else:
            mp = self.module_paths.get(selected, Path(project_path))
            res_paths.extend([mp / 'src' / 'main' / 'res', mp / 'res'])
        
        found_files = []
        for res_path in res_paths:
            if res_path.exists():
                for layout_dir in layout_dirs:
                    dir_path = res_path / layout_dir
                    if dir_path.exists():
                        for file_path in dir_path.iterdir():
                            if file_path.is_file() and file_path.suffix.lower() in extensions:
                                found_files.append(file_path)
        
        self.log(f"Layout扫描完成，找到 {len(found_files)} 个文件")
        return found_files
