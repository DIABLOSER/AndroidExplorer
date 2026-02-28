#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
from pathlib import Path


class FileHelper:
    """文件操作辅助工具"""
    
    @staticmethod
    def export_mapping_to_file(file_path, mapping, format_info):
        """导出映射到文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("# Android资源文件重命名映射\n")
            f.write(f"# 导出时间: {datetime.datetime.now()}\n")
            
            for key, value in format_info.items():
                f.write(f"# {key}格式: {value}\n")
            f.write("\n")
            
            for section, data in mapping.items():
                if data:
                    f.write(f"# {section}映射\n")
                    for old_name, new_name in data.items():
                        f.write(f"{old_name} = {new_name}\n")
                    f.write("\n")
    
    @staticmethod
    def import_mapping_from_file(file_path):
        """从文件导入映射"""
        from collections import OrderedDict
        
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
                
                if line.startswith('#'):
                    if 'drawable' in line.lower():
                        current_section = 'drawable'
                    elif 'layout' in line.lower():
                        current_section = 'layout'
                    elif 'string' in line.lower():
                        current_section = 'string'
                    elif 'id' in line.lower():
                        current_section = 'id'
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
        
        return {
            'drawable': drawable_mapping,
            'layout': layout_mapping,
            'string': string_mapping,
            'id': id_mapping
        }
    
    @staticmethod
    def discover_modules(project_path):
        """发现项目下的模块"""
        modules = ["全部模块"]
        module_paths = {"全部模块": project_path if project_path else Path('.')}
        
        if project_path and project_path.exists():
            app_path = project_path / 'app'
            if (app_path / 'src' / 'main' / 'res').exists():
                modules.append('app')
                module_paths['app'] = app_path
            
            for child in project_path.iterdir():
                if not child.is_dir() or child.name == 'app':
                    continue
                if (child / 'src' / 'main' / 'res').exists() or (child / 'res').exists():
                    modules.append(child.name)
                    module_paths[child.name] = child
            
            if (project_path / 'res').exists():
                modules.append('root')
                module_paths['root'] = project_path
        
        return modules, module_paths
