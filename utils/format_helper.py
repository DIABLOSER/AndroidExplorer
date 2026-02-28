#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re


class FormatHelper:
    """格式化辅助工具"""
    
    @staticmethod
    def build_format_string(fmt_type, prefix, keyword, suffix):
        """构建格式预览字符串（不自动添加分隔符，由用户控制）"""
        import re
        number_example = "1"
        
        if "{number" in suffix:
            match = re.search(r'\{number:(\d+)d\}', suffix)
            if match:
                width = int(match.group(1))
                number_example = str(1).zfill(width)
            else:
                number_example = "1"
            suffix_formatted = re.sub(r'\{number(?::\d+d)?\}', number_example, suffix)
        else:
            suffix_formatted = suffix
        
        keyword_formatted = keyword.replace("{name}", "example")
        
        # 直接拼接，不添加下划线，由用户在输入框中自行控制
        if fmt_type == "prefix_keyword_number":
            return f"{prefix}{keyword_formatted}{suffix_formatted}"
        elif fmt_type == "keyword_prefix_number":
            return f"{keyword_formatted}{prefix}{suffix_formatted}"
        elif fmt_type == "prefix_number_keyword":
            return f"{prefix}{suffix_formatted}{keyword_formatted}"
        else:
            return f"{prefix}{keyword_formatted}{suffix_formatted}"
    
    @staticmethod
    def snake_to_pascal(name):
        """蛇形命名转帕斯卡命名"""
        parts = [p for p in name.split('_') if p]
        return ''.join(p[:1].upper() + p[1:] for p in parts)
    
    @staticmethod
    def snake_to_camel(name):
        """蛇形命名转驼峰命名"""
        pascal = FormatHelper.snake_to_pascal(name)
        return pascal[:1].lower() + pascal[1:] if pascal else pascal
