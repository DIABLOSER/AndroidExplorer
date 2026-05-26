#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""批量引用替换（性能优化）"""


class ReferenceUpdater:
    @staticmethod
    def may_need_update(content, needles):
        """快速判断文件是否可能包含待替换内容"""
        if not needles:
            return True
        return any(needle in content for needle in needles)

    @staticmethod
    def apply_compiled_rules(content, compiled_rules):
        """对文本应用已编译的正则规则，有变化才返回新内容"""
        new_content = content
        changed = False
        for pattern, replacement in compiled_rules:
            try:
                replaced = pattern.sub(replacement, new_content)
                if replaced != new_content:
                    new_content = replaced
                    changed = True
            except Exception:
                continue
        return new_content if changed else content

    @staticmethod
    def build_needles_from_mapping(mapping, extra_tokens=None):
        """从映射表构建快速检索用的子串集合"""
        needles = set(extra_tokens or [])
        for old_name in mapping:
            if old_name:
                needles.add(old_name)
                if '_' in old_name:
                    parts = old_name.split('_')
                    needles.add(f'@{parts[0]}/')
                    needles.add(f'R.{parts[0]}')
        return needles
