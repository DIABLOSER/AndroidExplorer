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

    def generate_random_string(self, length=4, app=None):
        """生成随机字符串"""
        # 如果提供了app实例，使用其配置
        if app and hasattr(app, 'random_length'):
            length = app.random_length.get()
            
            # 构建字符集
            char_set = ""
            if app.random_include_lowercase.get():
                char_set += string.ascii_lowercase
            if app.random_include_uppercase.get():
                char_set += string.ascii_uppercase
            if app.random_include_digits.get():
                char_set += string.digits
            
            # 如果没有任何字符类型被选中，默认使用小写字母
            if not char_set:
                char_set = string.ascii_lowercase
        else:
            # 默认使用小写字母
            char_set = string.ascii_lowercase
        
        return ''.join(random.choices(char_set, k=length))

    def _uses_name_placeholder(self, format_input):
        if isinstance(format_input, dict):
            return '{name}' in format_input.get('keyword', '')
        return '{name}' in format_input

    def generate_new_name(self, old_name, format_input, existing_names, app=None):
        """生成新名称（format_input 为配置 dict 或旧版格式字符串）"""
        from utils.format_helper import FormatHelper

        if self._uses_name_placeholder(format_input):
            base_name = self.extract_base_name(old_name)
        else:
            base_name = ''

        used_names = set(existing_names)
        need_random = FormatHelper.config_uses_random_placeholder(format_input)

        for counter in range(1, 200000):
            random_str = self.generate_random_string(app=app) if need_random else ''
            new_name = FormatHelper.build_name(
                format_input, base_name, counter, random_str, rng=random
            )
            if new_name and new_name not in used_names:
                return new_name

        for _ in range(1000):
            random_str = self.generate_random_string(app=app)
            new_name = FormatHelper.build_name(
                format_input, base_name, 1, random_str, rng=random
            )
            if new_name and new_name not in used_names:
                return new_name

        return None

    def generate_mapping(self, files, format_input, app=None):
        """生成文件映射"""
        mapping = OrderedDict()
        existing_names = set()

        for file_path in files:
            old_name = file_path.stem
            new_name = self.generate_new_name(old_name, format_input, existing_names, app)
            if new_name:
                mapping[old_name] = new_name
                existing_names.add(new_name)

        return mapping

    def generate_string_mapping(self, string_files, format_input, app=None):
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
                    new_name = self.generate_new_name(old_name, format_input, existing_names, app)
                    if new_name:
                        mapping[old_name] = new_name
                        existing_names.add(new_name)
            except Exception as e:
                self.log(f"解析{file_path}失败: {e}", "ERROR")

        return mapping
