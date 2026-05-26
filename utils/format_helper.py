#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
import re
import string


class FormatHelper:
    """命名格式：前缀、关键词、后缀({random})、序号({number})，支持固定/随机顺序"""

    PART_KEYS = ('prefix', 'keyword', 'suffix', 'number')
    NO_LEADING_PART_KEYS = frozenset({'number'})
    PART_LABELS = {
        'prefix': '前缀',
        'keyword': '关键词',
        'suffix': '后缀',
        'number': '序号',
    }
    LABEL_TO_KEY = {v: k for k, v in PART_LABELS.items()}
    DEFAULT_PART_ORDER = 'prefix,keyword,suffix,number'
    DEFAULT_SUFFIX = '{random}'
    DEFAULT_NUMBER = '{number:04d}'

    LEGACY_FORMAT_ORDER = {
        'prefix_keyword_number': 'prefix,keyword,suffix,number',
        'keyword_prefix_number': 'keyword,prefix,suffix,number',
        'prefix_number_keyword': 'prefix,number,suffix,keyword',
    }

    @staticmethod
    def normalize_part_order(part_order_str):
        """解析顺序，固定包含四段；忽略旧版 random 段"""
        if part_order_str:
            order = [p.strip() for p in part_order_str.split(',') if p.strip()]
        else:
            order = []

        allowed = set(FormatHelper.PART_KEYS)
        seen = set()
        deduped = []
        for part in order:
            if part == 'random':
                continue
            if part in allowed and part not in seen:
                deduped.append(part)
                seen.add(part)
        order = deduped

        for key in FormatHelper.PART_KEYS:
            if key not in order:
                order.append(key)
        return order

    @staticmethod
    def part_order_from_labels(label_list):
        keys = []
        for label in label_list:
            key = FormatHelper.LABEL_TO_KEY.get(label)
            if key:
                keys.append(key)
        order_str = ','.join(keys) if keys else FormatHelper.DEFAULT_PART_ORDER
        return ','.join(FormatHelper.normalize_part_order(order_str))

    @staticmethod
    def labels_from_part_order(part_order_str):
        order = FormatHelper.normalize_part_order(part_order_str)
        return [FormatHelper.PART_LABELS[k] for k in order]

    @staticmethod
    def make_config(order_mode, part_order_str, prefix, keyword, suffix, number):
        """按界面当前值构建配置；空字符串表示该段不参与拼接（不偷偷回填默认模板）"""
        return {
            'order_mode': order_mode if order_mode in ('fixed', 'random') else 'fixed',
            'part_order': FormatHelper.normalize_part_order(part_order_str),
            'prefix': (prefix or '').strip() if prefix is not None else '',
            'keyword': (keyword or '').strip() if keyword is not None else '',
            'suffix': (suffix or '').strip() if suffix is not None else '',
            'number': (number or '').strip() if number is not None else '',
        }

    @staticmethod
    def config_uses_random_placeholder(config):
        if isinstance(config, str):
            return '{random}' in config
        if not isinstance(config, dict):
            return False
        for key in FormatHelper.PART_KEYS:
            if '{random}' in (config.get(key) or ''):
                return True
        return False

    @staticmethod
    def expand_part_template(template, name='', number=1, random_str=''):
        if not template:
            return ''
        result = template.replace('{name}', name)

        def _fmt_number(match):
            spec = match.group(1) or ''
            if spec.isdigit():
                return str(number).zfill(int(spec))
            return str(number)

        result = re.sub(r'\{number:(\d*)d\}', _fmt_number, result)
        result = result.replace('{number}', str(number))
        result = result.replace('{random}', random_str)
        return result

    @staticmethod
    def build_name(config, name='', number=1, random_str='', rng=None):
        if isinstance(config, str):
            return FormatHelper._build_name_from_legacy_string(
                config, name, number, random_str,
            )

        templates = {
            'prefix': config.get('prefix', ''),
            'keyword': config.get('keyword', ''),
            'suffix': config.get('suffix', ''),
            'number': config.get('number', ''),
        }
        order = list(config.get('part_order', list(FormatHelper.PART_KEYS)))
        if config.get('order_mode') == 'random':
            order = FormatHelper._randomize_part_order(
                order, rng or random, templates, name, number, random_str,
            )
        return ''.join(
            FormatHelper.expand_part_template(templates[k], name, number, random_str)
            for k in order
        )

    @staticmethod
    def _join_parts(order, templates, name, number, random_str):
        return ''.join(
            FormatHelper.expand_part_template(templates[k], name, number, random_str)
            for k in order
        )

    @staticmethod
    def _name_starts_with_digit(order, templates, name, number, random_str):
        text = FormatHelper._join_parts(order, templates, name, number, random_str)
        return bool(text) and text[0].isdigit()

    @staticmethod
    def _randomize_part_order(order, rng, templates, name='', number=1, random_str=''):
        order = list(order)
        if len(order) <= 1:
            return order

        unsafe = FormatHelper.NO_LEADING_PART_KEYS
        safe = [k for k in order if k not in unsafe]

        rng.shuffle(order)
        if not FormatHelper._name_starts_with_digit(order, templates, name, number, random_str):
            return order

        for key in safe:
            rest = [k for k in order if k != key]
            rng.shuffle(rest)
            candidate = [key] + rest
            if not FormatHelper._name_starts_with_digit(
                candidate, templates, name, number, random_str,
            ):
                return candidate

        leading = [k for k in ('prefix', 'keyword', 'suffix') if k in order]
        tail = [k for k in order if k in unsafe]
        rng.shuffle(tail)
        return leading + tail

    @staticmethod
    def _build_name_from_legacy_string(format_string, name, number, random_str):
        try:
            return format_string.format(name=name, number=number, random=random_str)
        except (KeyError, ValueError):
            result = format_string.replace('{number}', str(number))
            result = result.replace('{random}', random_str)
            if '{name}' in result:
                result = result.replace('{name}', name)
            return result

    @staticmethod
    def build_preview(config, name_example='example', number_example=1, random_example='abcd'):
        if isinstance(config, str):
            return FormatHelper.build_name(
                config, name_example, number_example, random_example,
            )
        if config.get('order_mode') == 'random':
            sample = FormatHelper.build_name(
                config, name_example, number_example, random_example,
            )
            return f'[随机顺序示例] {sample}'
        return FormatHelper.build_name(
            config, name_example, number_example, random_example,
        )

    @staticmethod
    def build_format_string(order_mode, part_order_str, prefix, keyword, suffix, number):
        config = FormatHelper.make_config(
            order_mode, part_order_str, prefix, keyword, suffix, number,
        )
        random_example = ''.join(random.choices(string.ascii_lowercase, k=4))
        return FormatHelper.build_preview(config, 'example', 1, random_example)

    @staticmethod
    def legacy_format_type_to_order(fmt_type):
        return FormatHelper.LEGACY_FORMAT_ORDER.get(
            fmt_type, FormatHelper.DEFAULT_PART_ORDER,
        )

    @staticmethod
    def snake_to_pascal(name):
        parts = [p for p in name.split('_') if p]
        return ''.join(p[:1].upper() + p[1:] for p in parts)

    @staticmethod
    def snake_to_camel(name):
        pascal = FormatHelper.snake_to_pascal(name)
        return pascal[:1].lower() + pascal[1:] if pascal else pascal
