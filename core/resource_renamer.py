#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
import string
from collections import OrderedDict
import xml.etree.ElementTree as ET


class ResourceRenamer:
    """资源文件重命名器"""
    
    def __init__(self, log_func=None):
        self.log = log_func or (lambda msg, level='INFO': None)

    def extract_base_name(self, filename):
        """从文件名中提取基础名称"""
        return filename

    def generate_random_string(self, length=4):
        """生成随机字符串"""
        return ''.join(random.choices(string.ascii_lowercase, k=length))

    def generate_new_name(self, old_name, format_string, existing_names):
        """生成新名称"""
        if '{name}' in format_string:
            base_name = self.extract_base_name(old_name)
        else:
            base_name = ""
        
        used_names = set(existing_names)
        
        # 先用递增序号生成
        for counter in range(1, 200000):
            format_vars = {
                'name': base_name,
                'number': counter,
                'random': ''
            }
            try:
                new_name = format_string.format(**format_vars)
            except (KeyError, ValueError):
                try:
                    new_name = format_string.replace('{number}', str(counter))
                    new_name = new_name.replace('{random}', '')
                    if '{name}' in new_name:
                        new_name = new_name.replace('{name}', base_name)
                except Exception:
                    return None
            
            if new_name not in used_names:
                return new_name
        
        # 序号用尽则加随机后缀
        for _ in range(1000):
            random_str = self.generate_random_string()
            try:
                new_name = format_string.format(name=base_name, number=1, random=random_str)
            except (KeyError, ValueError):
                new_name = format_string.replace('{random}', random_str).replace('{number}', '1')
                if '{name}' in new_name:
                    new_name = new_name.replace('{name}', base_name)
            
            if new_name not in used_names:
                return new_name
        
        return None

    def generate_mapping(self, files, format_string):
        """生成文件映射"""
        mapping = OrderedDict()
        existing_names = set()
        
        for file_path in files:
            old_name = file_path.stem
            new_name = self.generate_new_name(old_name, format_string, existing_names)
            if new_name:
                mapping[old_name] = new_name
                existing_names.add(new_name)
        
        return mapping

    def generate_string_mapping(self, string_files, format_string):
        """生成字符串资源映射"""
        mapping = OrderedDict()
        existing_names = set()
        
        for file_path in string_files:
            try:
                tree = ET.parse(file_path)
                root = tree.getroot()
                for elem in root.findall('string'):
                    old_name = elem.attrib.get('name')
                    if not old_name:
                        continue
                    new_name = self.generate_new_name(old_name, format_string, existing_names)
                    if new_name:
                        mapping[old_name] = new_name
                        existing_names.add(new_name)
            except Exception as e:
                self.log(f"解析{file_path}失败: {e}", "ERROR")
        
        return mapping
