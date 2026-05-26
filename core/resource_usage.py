#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""检测 Drawable / Layout / String 资源是否在项目中被引用"""

import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from utils.file_helper import FileHelper


class ResourceUsageChecker:
    """扫描项目源码与 XML，判断资源是否被使用"""

    DRAWABLE_DIR_PREFIXES = ('drawable', 'mipmap')
    LAYOUT_DIR_PREFIXES = ('layout',)

    def __init__(self, log_func=None):
        self.log = log_func or (lambda msg, level='INFO': None)

    def check_drawables(self, project_root, drawable_files):
        by_stem = defaultdict(list)
        for path in drawable_files:
            by_stem[path.stem].append(path)
        return self._check_grouped(project_root, 'drawable', by_stem)

    def check_layouts(self, project_root, layout_files):
        by_stem = defaultdict(list)
        for path in layout_files:
            by_stem[path.stem].append(path)
        return self._check_grouped(project_root, 'layout', by_stem)

    def check_strings(self, project_root, string_names, string_sources):
        """string_sources: name -> [strings.xml 路径列表]"""
        by_name = {name: string_sources.get(name, []) for name in string_names}
        return self._check_grouped(project_root, 'string', by_name)

    def _check_grouped(self, project_root, res_type, name_to_paths):
        if not project_root or not name_to_paths:
            return {}, {}

        root = Path(project_root)
        if not root.exists():
            return {}, {}

        self.log(f'正在检测 {res_type} 使用情况…')
        search_files = FileHelper.collect_project_files(root)
        content_cache = self._load_contents(search_files)

        used = {}
        unused = {}

        for name, own_paths in sorted(name_to_paths.items()):
            exclude = {Path(p).resolve() for p in own_paths}
            patterns = self._reference_patterns(res_type, name)
            if self._has_reference(patterns, content_cache, exclude):
                used[name] = own_paths
            else:
                unused[name] = own_paths

        self.log(
            f'{res_type}: 已使用 {len(used)}，未使用 {len(unused)}',
        )
        return used, unused

    @staticmethod
    def _load_contents(paths):
        cache = {}
        for path in paths:
            path = Path(path)
            try:
                text = path.read_text(encoding='utf-8', errors='ignore')
            except (OSError, UnicodeError):
                try:
                    text = path.read_bytes().decode('utf-8', errors='ignore')
                except OSError:
                    text = ''
            cache[path.resolve()] = text
        return cache

    @staticmethod
    def _has_reference(patterns, content_cache, exclude_paths):
        for path, content in content_cache.items():
            if path in exclude_paths:
                continue
            for pattern in patterns:
                if pattern.search(content):
                    return True
        return False

    @staticmethod
    def _reference_patterns(res_type, name):
        esc = re.escape(name)
        if res_type == 'drawable':
            return [
                re.compile(rf'R\.drawable\.{esc}\b'),
                re.compile(rf'R\.mipmap\.{esc}\b'),
                re.compile(rf'@drawable/{esc}\b'),
                re.compile(rf'@mipmap/{esc}\b'),
                re.compile(rf'@drawable/{esc}"'),
                re.compile(rf"@drawable/{esc}'"),
                re.compile(rf'@mipmap/{esc}"'),
            ]
        if res_type == 'layout':
            return [
                re.compile(rf'R\.layout\.{esc}\b'),
                re.compile(rf'@layout/{esc}\b'),
                re.compile(rf'@layout/{esc}"'),
                re.compile(rf"@layout/{esc}'"),
                re.compile(
                    rf'<include\b[^>]*\blayout\s*=\s*"@layout/{esc}"',
                    re.IGNORECASE,
                ),
                re.compile(
                    rf"<include\b[^>]*\blayout\s*=\s*'@layout/{esc}'",
                    re.IGNORECASE,
                ),
            ]
        if res_type == 'string':
            return [
                re.compile(rf'R\.string\.{esc}\b'),
                re.compile(rf'@string/{esc}\b'),
                re.compile(rf'@string/{esc}"'),
                re.compile(rf"@string/{esc}'"),
                re.compile(rf'@string/{esc}/'),
                re.compile(rf'getString\s*\(\s*R\.string\.{esc}\b'),
                re.compile(rf'getText\s*\(\s*R\.string\.{esc}\b'),
                re.compile(rf'stringResource\s*\(\s*R\.string\.{esc}\b'),
                re.compile(rf'context\.getString\s*\(\s*R\.string\.{esc}\b'),
            ]
        return []

    @staticmethod
    def delete_drawable_files(paths):
        deleted = []
        for path in paths:
            p = Path(path)
            if p.is_file():
                p.unlink()
                deleted.append(p)
        return deleted

    @staticmethod
    def delete_layout_files(paths):
        return ResourceUsageChecker.delete_drawable_files(paths)

    @staticmethod
    def remove_strings_from_xml(string_sources, names):
        """从各 strings.xml 删除指定 name 的 <string> 节点"""
        removed = []
        for name in names:
            for xml_path in string_sources.get(name, []):
                path = Path(xml_path)
                if not path.is_file():
                    continue
                try:
                    count = ResourceUsageChecker._remove_string_name(path, name)
                    if count:
                        removed.append((path, name))
                except Exception as exc:
                    raise OSError(f'无法编辑 {path}: {exc}') from exc
        return removed

    @staticmethod
    def _remove_string_name(xml_path, name):
        tree = ET.parse(xml_path)
        root = tree.getroot()
        removed = 0
        for elem in list(root.findall('string')):
            if elem.attrib.get('name') == name:
                root.remove(elem)
                removed += 1
        if removed:
            tree.write(xml_path, encoding='utf-8', xml_declaration=True)
        return removed
