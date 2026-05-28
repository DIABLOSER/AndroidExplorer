#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from pathlib import Path
from collections import OrderedDict


class ClassRenamer:
    """Java类文件重命名工具"""
    
    def __init__(self, log_func=None):
        self.log = log_func or (lambda msg, level='INFO': None)
        self.renamed_files = {}  # 记录已重命名的文件路径映射
    
    def scan_java_files(self, project_path, module_paths, module_selection):
        """扫描Java文件（仅扫描 app/src/main/java 目录）"""
        java_files = []
        
        if module_selection == "全部模块":
            search_paths = [project_path]
        else:
            module_path = module_paths.get(module_selection)
            if module_path:
                search_paths = [project_path / module_path]
            else:
                search_paths = [project_path]
        
        for search_path in search_paths:
            java_dir = search_path / "app" / "src" / "main" / "java"
            if not java_dir.exists():
                java_dir = search_path / "src" / "main" / "java"
            
            if java_dir.exists():
                for java_file in java_dir.rglob("*.java"):
                    java_files.append(java_file)
        
        return java_files
    
    def transform_class_name(self, class_name, filter_chars, replace_chars):
        """按「过滤字符 + 替换字符」处理类名。

        - 过滤字符：逗号分隔，要从类名中处理的子串（如 Activity,Fragment）
        - 替换字符：与过滤项一一对应的替换结果；仅写一项则全部过滤项共用；
          留空则删除对应过滤子串。
        - 若未填过滤字符、仅填替换规则，则仍支持 源->目标 写法（兼容旧用法）。
        """
        filter_chars = (filter_chars or '').strip()
        replace_chars = (replace_chars or '').strip()

        if not filter_chars and not replace_chars:
            return class_name

        if not filter_chars:
            return ClassRenamer.apply_class_name_replacements(
                self, class_name, replace_chars,
            )

        filters = [t.strip() for t in filter_chars.split(',') if t.strip()]
        if not filters:
            return class_name

        if not replace_chars:
            result = class_name
            for token in filters:
                result = result.replace(token, '')
            return result if result else class_name

        # 显式 源->目标 多条规则（未与过滤列表配对时）
        if '->' in replace_chars:
            parts = [p.strip() for p in replace_chars.split(',') if p.strip()]
            if parts and all('->' in p for p in parts):
                return self.apply_class_name_replacements(class_name, replace_chars)

        replaces = [t.strip() for t in replace_chars.split(',') if t.strip()]
        if len(replaces) == 1:
            replaces = replaces * len(filters)

        result = class_name
        for i, token in enumerate(filters):
            repl = replaces[i] if i < len(replaces) else ''
            result = result.replace(token, repl)
        return result if result else class_name

    def filter_class_name(self, class_name, filter_chars):
        """从类名中移除过滤列表中的子串（无替换内容时）"""
        return self.transform_class_name(class_name, filter_chars, '')

    def apply_class_name_replacements(self, class_name, replace_rules):
        """仅按 源->目标 规则替换（未指定过滤字符时）"""
        if not replace_rules:
            return class_name
        result = class_name
        for rule in replace_rules.split(','):
            rule = rule.strip()
            if not rule:
                continue
            if '->' in rule:
                old, new = rule.split('->', 1)
                old, new = old.strip(), new.strip()
            else:
                old, new = rule, ''
            if old:
                result = result.replace(old, new)
        return result if result else class_name

    def generate_class_mapping(self, java_files, format_input, filter_chars='', replace_chars=''):
        """生成类名映射（先按过滤/替换处理类名，再套用命名格式）"""
        from utils.format_helper import FormatHelper
        import random as rnd
        import string

        mapping = OrderedDict()
        existing_names = set()
        need_random = FormatHelper.config_uses_random_placeholder(format_input)
        serial_counter = 1

        for java_file in java_files:
            old_class_name = java_file.stem
            base_name = self.transform_class_name(
                old_class_name, filter_chars, replace_chars,
            )

            counter = serial_counter
            while True:
                random_str = (
                    ''.join(rnd.choices(string.ascii_lowercase, k=4))
                    if need_random else ''
                )
                new_class_name = FormatHelper.build_name(
                    format_input, base_name, counter, random_str, rng=rnd
                )
                if new_class_name and new_class_name not in existing_names:
                    break
                counter += 1
                if counter > 200000:
                    new_class_name = None
                    break

            if new_class_name:
                mapping[old_class_name] = new_class_name
                existing_names.add(new_class_name)
                serial_counter = max(serial_counter + 1, counter + 1)

        return mapping
    
    def get_class_package(self, java_file):
        """从Java文件中提取包名"""
        try:
            with open(java_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            match = re.search(r'^\s*package\s+([\w.]+)\s*;', content, re.MULTILINE)
            if match:
                return match.group(1)
        except Exception as e:
            self.log(f"读取包名失败 {java_file}: {e}", "ERROR")
        
        return None
    
    def replace_class_refs_in_content(self, content, mapping):
        """在单个文件内容中更新类名引用（按旧名长度降序，避免短名误伤长名）"""
        if not mapping or not content:
            return content
        sorted_items = sorted(mapping.items(), key=lambda x: len(x[0]), reverse=True)
        for old_name, new_name in sorted_items:
            if old_name == new_name or old_name not in content:
                continue
            content = self._replace_single_class_refs(content, old_name, new_name)
        return content

    def _replace_single_class_refs(self, content, old_name, new_name):
        """将单个旧类名的各类引用替换为新类名"""
        esc = re.escape(old_name)

        # import / import static
        content = re.sub(
            rf'import\s+static\s+((?:[a-zA-Z_]\w*\.)+){esc}\.\*\s*;',
            rf'import static \1{new_name}.*;',
            content,
        )
        content = re.sub(
            rf'import\s+static\s+((?:[a-zA-Z_]\w*\.)+){esc}(?=[.;])',
            rf'import static \1{new_name}',
            content,
        )
        content = re.sub(
            rf'import\s+((?:[a-zA-Z_]\w*\.)+){esc}\s*;',
            rf'import \1{new_name};',
            content,
        )

        # 完全限定名：com.example.OldName
        content = re.sub(
            rf'(\b(?:[a-zA-Z_]\w*\.)+){esc}(?=[.;,\s\)\]>;\[]|$)',
            rf'\1{new_name}',
            content,
        )

        # 限定引用：OldName.member（静态成员、内部类、嵌套类）
        content = re.sub(rf'(?<![.\w]){esc}(?=\.)', new_name, content)

        # OldName.class
        content = re.sub(rf'(?<![.\w]){esc}\.class\b', f'{new_name}.class', content)

        # 独立类名（类型、extends、new Foo()、泛型参数等）
        content = re.sub(rf'(?<![.\w]){esc}(?![.\w])', new_name, content)

        # 注解
        content = re.sub(rf'@{esc}\b', f'@{new_name}', content)

        return content

    def _replace_class_refs_in_xml(self, content, old_name, new_name):
        """更新 XML / Manifest 中的类名引用"""
        esc = re.escape(old_name)

        content = re.sub(
            rf'android:name="([a-zA-Z0-9_.]*\.)?{esc}"',
            lambda m: f'android:name="{(m.group(1) or "")}{new_name}"',
            content,
        )
        content = re.sub(rf'android:name="\.{esc}"', f'android:name=".{new_name}"', content)

        content = re.sub(
            rf'tools:context="([a-zA-Z0-9_.]*\.)?{esc}"',
            lambda m: f'tools:context="{(m.group(1) or "")}{new_name}"',
            content,
        )
        content = re.sub(rf'tools:context="\.{esc}"', f'tools:context=".{new_name}"', content)

        content = re.sub(
            rf'(<|</)([a-zA-Z0-9_.]+\.){esc}(?=[\s/>])',
            rf'\1\2{new_name}',
            content,
        )
        content = re.sub(rf'(<|</){esc}(?=[\s/>])', rf'\1{new_name}', content)

        return content

    def update_all_class_references(
        self, project_path, mapping, preview_mode=False, progress_callback=None,
    ):
        """遍历项目并更新 Java/Kotlin/XML 中的类名引用"""
        if not mapping:
            return 0

        from utils.file_helper import FileHelper

        project_path = Path(project_path)
        sorted_mapping = OrderedDict(
            sorted(mapping.items(), key=lambda x: len(x[0]), reverse=True)
        )
        needles = {old for old, new in sorted_mapping.items() if old != new}
        suffixes = {'.java', '.kt', '.xml'}
        all_files = [
            p for p in FileHelper.collect_project_files(project_path, suffixes)
            if p.suffix.lower() in suffixes
        ]
        total = len(all_files)
        updated_count = 0

        for idx, file_path in enumerate(all_files, 1):
            if progress_callback and (idx == 1 or idx % 50 == 0 or idx == total):
                progress_callback(idx, total)

            try:
                content = file_path.read_text(encoding='utf-8')
            except (UnicodeDecodeError, OSError):
                continue

            if needles and not any(n in content for n in needles):
                continue

            if file_path.suffix.lower() == '.xml':
                new_content = content
                for old_name, new_name in sorted_mapping.items():
                    if old_name != new_name and old_name in new_content:
                        new_content = self._replace_class_refs_in_xml(
                            new_content, old_name, new_name
                        )
            else:
                new_content = self.replace_class_refs_in_content(content, sorted_mapping)

            if new_content == content:
                continue

            if not preview_mode:
                file_path.write_text(new_content, encoding='utf-8')

            updated_count += 1

        if updated_count:
            self.log(f"类名引用已更新 {updated_count} 个文件")
        return updated_count

    def get_class_replace_rules(self, java_files, mapping, project_path):
        """生成类名替换规则（保留供备份收集；实际替换请用 update_all_class_references）"""
        rules = []
        
        for old_name, new_name in mapping.items():
            escaped_old = re.escape(old_name)
            
            # 首先，我们需要排除一些常见的情况，避免误替换
            # 1. 排除变量名（以小写字母开头的标识符）
            # 2. 排除方法名（后面跟着括号）
            # 3. 排除字段名（前面有点号但不是类名的情况）
            
            # ===== 0. 排除规则（防止误替换） =====
            # 排除以小写字母开头的标识符（很可能是变量名）
            # 注意：这个规则不添加到rules中，而是在应用时作为检查
            
            # 重要：避免替换变量名
            # 如果类名以小写字母开头，我们需要特别小心
            # 但大多数类名以大写字母开头，所以这个问题可能不严重
            
            # ===== 1. Import 语句（最高优先级，精确匹配） =====
            # 标准 import: import com.example.ClassName;
            rules.append((rf'import\s+([a-zA-Z0-9_.]+\.){escaped_old}\s*;', rf'import \1{new_name};'))
            # static import: import static com.example.ClassName.*;
            rules.append((rf'import\s+static\s+([a-zA-Z0-9_.]+\.){escaped_old}\.\*\s*;', rf'import static \1{new_name}.*;'))
            # static import 方法: import static com.example.ClassName.method;
            rules.append((rf'import\s+static\s+([a-zA-Z0-9_.]+\.){escaped_old}\.', rf'import static \1{new_name}.'))
            # 通配符 import: import com.example.*;
            # 注意：这种导入不需要替换类名，因为类名在通配符中
            
            # ===== 2. Package 和 AndroidManifest.xml =====
            # android:name 属性（Activity/Service/Receiver/Provider）
            rules.append((rf'(?<=android:name=")([a-zA-Z0-9_.]*\.)?{escaped_old}(?=")', rf'\1{new_name}'))
            rules.append((rf'(?<=android:name="\.)({escaped_old})(?=")', rf'{new_name}'))
            
            # ===== 2.1 完全限定类名引用（改进版） =====
            # 处理 com.example.ClassName 这种完整包名的引用
            # 但避免匹配 com.example.ClassName.method() 这种情况
            # 只匹配在特定上下文中的完全限定类名
            rules.append((rf'\b([a-zA-Z0-9_.]+\.){escaped_old}(?=\s*[;,)\]\s]|$)', rf'\1{new_name}'))
            # 匹配作为类型的完全限定类名：com.example.ClassName variable
            rules.append((rf'\b([a-zA-Z0-9_.]+\.){escaped_old}(?=\s+[a-zA-Z_][a-zA-Z0-9_]*)', rf'\1{new_name}'))
            # 匹配在泛型中的完全限定类名：List<com.example.ClassName>
            rules.append((rf'(?<=<[^<>]*)([a-zA-Z0-9_.]+\.){escaped_old}(?=[^<>]*>)', rf'\1{new_name}'))
            
            # ===== 3. 布局文件中的自定义 View（精确匹配） =====
            # 完整包名的自定义 View 开始标签: <com.example.app.CustomView
            rules.append((rf'(?<=<)([a-zA-Z0-9_.]+\.)({escaped_old})(?=[\s>])', rf'\1{new_name}'))
            # 完整包名的自定义 View 结束标签: </com.example.app.CustomView>
            rules.append((rf'(?<=</)([a-zA-Z0-9_.]+\.)({escaped_old})(?=>)', rf'\1{new_name}'))
            
            # 简短类名的自定义 View（需要确保不是系统控件）
            # 开始标签: <CustomView
            rules.append((rf'(?<=<){escaped_old}(?=[\s>])', f'{new_name}'))
            # 结束标签: </CustomView>
            rules.append((rf'(?<=</){escaped_old}(?=>)', f'{new_name}'))
            
            # Fragment 标签中的 android:name
            rules.append((rf'(?<=<fragment[^>]{{0,200}}android:name=")([a-zA-Z0-9_.]*\.)?{escaped_old}(?=")', rf'\1{new_name}'))
            rules.append((rf'(?<=<fragment[^>]{{0,200}}android:name="\.)({escaped_old})(?=")', rf'{new_name}'))
            
            # tools:context 属性
            rules.append((rf'(?<=tools:context=")([a-zA-Z0-9_.]*\.)?{escaped_old}(?=")', rf'\1{new_name}'))
            rules.append((rf'(?<=tools:context="\.)({escaped_old})(?=")', rf'{new_name}'))
            
            # ===== 4. 类/接口/枚举声明（使用词边界） =====
            rules.append((rf'(?<=\bclass\s){escaped_old}(?=\s)', f'{new_name}'))
            rules.append((rf'(?<=\binterface\s){escaped_old}(?=\s)', f'{new_name}'))
            rules.append((rf'(?<=\benum\s){escaped_old}(?=\s)', f'{new_name}'))
            rules.append((rf'(?<=\b@interface\s){escaped_old}(?=\s)', f'{new_name}'))
            rules.append((rf'(?<=\brecord\s){escaped_old}(?=\s)', f'{new_name}'))
            
            # ===== 5. 继承和实现 =====
            rules.append((rf'(?<=\bextends\s){escaped_old}(?=\s)', f'{new_name}'))
            rules.append((rf'(?<=\bimplements\s)([^{{]*?\b){escaped_old}(?=\b)', rf'\1{new_name}'))
            rules.append((rf'(?<=,\s*){escaped_old}(?=\s*[,{{])', f'{new_name}'))
            
            # ===== 6. 构造函数（所有修饰符组合） =====
            rules.append((rf'(?<=\bpublic\s){escaped_old}(?=\s*\()', f'{new_name}'))
            rules.append((rf'(?<=\bprivate\s){escaped_old}(?=\s*\()', f'{new_name}'))
            rules.append((rf'(?<=\bprotected\s){escaped_old}(?=\s*\()', f'{new_name}'))
            rules.append((rf'(?<=^\s*){escaped_old}(?=\s*\()', f'{new_name}'))  # 无修饰符
            
            # ===== 7. 对象实例化 =====
            rules.append((rf'(?<=\bnew\s){escaped_old}(?=\s*[(<\[])', f'{new_name}'))
            
            # ===== 8. 类型声明（变量、字段、参数）- 改进版 =====
            # 变量声明: ClassName var = ... (确保前面是类型位置)
            rules.append((rf'(?<![a-zA-Z0-9_.])\b{escaped_old}\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*([=;,)\]])', rf'{new_name} \1\2'))
            # 带修饰符的字段: public/private/protected/static/final ClassName field
            rules.append((rf'\b(public|private|protected|static|final|volatile|transient)\s+{escaped_old}\s+', rf'\1 {new_name} '))
            # 多个修饰符: public static ClassName field
            rules.append((rf'\b(public|private|protected)\s+(static|final)\s+{escaped_old}\s+', rf'\1 \2 {new_name} '))
            
            # ===== 9. 泛型类型参数（精确匹配，全面增强版） =====
            # 通用规则：匹配 < 和 > 之间的类名（最重要的规则）
            # 这个规则会匹配任何在尖括号内的类名
            rules.append((rf'(?<=<[^<>]{{0,500}})\b{escaped_old}\b(?=[^<>]{{0,500}}>)', f'{new_name}'))
            
            # 基础泛型声明: ClassName<...>
            rules.append((rf'\b{escaped_old}(?=\s*<)', f'{new_name}'))
            
            # 单个泛型参数: <ClassName>
            rules.append((rf'<\s*{escaped_old}\s*>', f'<{new_name}>'))
            
            # 第一个泛型参数: <ClassName, ...>
            rules.append((rf'<\s*{escaped_old}\s*,', f'<{new_name},'))
            
            # 最后一个泛型参数: <..., ClassName>
            rules.append((rf',\s*{escaped_old}\s*>', f', {new_name}>'))
            
            # 中间的泛型参数: <..., ClassName, ...>
            rules.append((rf',\s*{escaped_old}\s*,', f', {new_name},'))
            
            # 泛型通配符: <? extends ClassName>
            rules.append((rf'<\s*\?\s+extends\s+{escaped_old}\s*>', f'<? extends {new_name}>'))
            rules.append((rf'<\s*\?\s+extends\s+{escaped_old}\s*,', f'<? extends {new_name},'))
            
            # 泛型通配符: <? super ClassName>
            rules.append((rf'<\s*\?\s+super\s+{escaped_old}\s*>', f'<? super {new_name}>'))
            rules.append((rf'<\s*\?\s+super\s+{escaped_old}\s*,', f'<? super {new_name},'))
            
            # 泛型边界: <T extends ClassName>
            rules.append((rf'<\s*[A-Z]\s+extends\s+{escaped_old}\s*>', f'<T extends {new_name}>'))
            rules.append((rf'<\s*[A-Z]\s+extends\s+{escaped_old}\s*,', f'<T extends {new_name},'))
            
            # 泛型边界: <T super ClassName>
            rules.append((rf'<\s*[A-Z]\s+super\s+{escaped_old}\s*>', f'<T super {new_name}>'))
            rules.append((rf'<\s*[A-Z]\s+super\s+{escaped_old}\s*,', f'<T super {new_name},'))
            
            # ===== 10. 方法返回类型（改进版） =====
            # public/private/protected/static/final/abstract/synchronized ClassName methodName(...)
            for modifier in ['public', 'private', 'protected', 'static', 'final', 'abstract', 'synchronized']:
                rules.append((rf'\b{modifier}\s+{escaped_old}\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', rf'{modifier} {new_name} \1('))
            # 多个修饰符组合: public static ClassName methodName(...)
            rules.append((rf'\b(public|private|protected)\s+(static|final|abstract)\s+{escaped_old}\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', rf'\1 \2 {new_name} \3('))
            
            # ===== 11. 方法参数（改进版） =====
            # (ClassName param)
            rules.append((rf'\(\s*{escaped_old}\s+([a-zA-Z_][a-zA-Z0-9_]*)', rf'({new_name} \1'))
            # (, ClassName param)
            rules.append((rf',\s*{escaped_old}\s+([a-zA-Z_][a-zA-Z0-9_]*)', rf', {new_name} \1'))
            # (final ClassName param)
            rules.append((rf'\(\s*final\s+{escaped_old}\s+', rf'(final {new_name} '))
            # (, final ClassName param)
            rules.append((rf',\s*final\s+{escaped_old}\s+', rf', final {new_name} '))
            
            # ===== 12. 类型转换（改进版，全面覆盖） =====
            # 基础类型转换: (ClassName)
            rules.append((rf'\(\s*{escaped_old}\s*\)', f'({new_name})'))
            
            # 嵌套类型转换: ((ClassName))
            rules.append((rf'\(\s*\(\s*{escaped_old}\s*\)\s*\)', f'(({new_name}))'))
            
            # 类型转换后跟变量: (ClassName) var
            rules.append((rf'\(\s*{escaped_old}\s*\)\s+([a-zA-Z_])', rf'({new_name}) \1'))
            
            # 类型转换后跟方法调用: (ClassName) obj.method()
            rules.append((rf'\(\s*{escaped_old}\s*\)\s+([a-zA-Z_][a-zA-Z0-9_]*\.)', rf'({new_name}) \1'))
            
            # return 语句中的类型转换: return (ClassName) obj;
            rules.append((rf'\breturn\s+\(\s*{escaped_old}\s*\)', f'return ({new_name})'))
            
            # 赋值语句中的类型转换: var = (ClassName) obj;
            rules.append((rf'=\s*\(\s*{escaped_old}\s*\)', f'= ({new_name})'))
            
            # 方法参数中的类型转换: method((ClassName) obj)
            rules.append((rf'\(\s*\(\s*{escaped_old}\s*\)\s+', rf'(({new_name}) '))
            
            # 条件表达式中的类型转换: condition ? (ClassName) obj : null
            rules.append((rf'\?\s*\(\s*{escaped_old}\s*\)', rf'? ({new_name})'))
            rules.append((rf':\s*\(\s*{escaped_old}\s*\)', rf': ({new_name})'))
            
            # 数组访问中的类型转换: ((ClassName) array[i])
            rules.append((rf'\(\s*{escaped_old}\s*\)\s+([a-zA-Z_][a-zA-Z0-9_]*\[)', rf'({new_name}) \1'))
            
            # ===== 13. instanceof 和 .class（改进版） =====
            # instanceof 检查
            rules.append((rf'\binstanceof\s+{escaped_old}\b', f'instanceof {new_name}'))
            
            # .class 引用
            rules.append((rf'\b{escaped_old}\.class\b', f'{new_name}.class'))
            
            # ===== 14. 静态成员访问（改进版） =====
            # 这个规则需要非常小心，因为ClassName.method()可能被误匹配为variable.method()
            # 我们只在确定是类名的情况下才替换
            
            # 首先，检查前面是否有表明这是类名的上下文
            # 1. 前面是import、new、extends、implements、instanceof等关键字
            # 2. 前面是类型声明位置
            
            # 更安全的规则：只在特定上下文中替换
            # 避免替换变量名.方法()的情况
            
            # 只在前面是类名上下文的情况下替换
            # 1. 前面是空白或特定关键字
            # 2. 或者前面是点号但点号前面是包名
            
            # 安全的静态方法调用：包名.ClassName.method()
            # 只替换前面有包名的情况，避免替换变量名.方法()
            rules.append((rf'(?<=[a-zA-Z0-9_]\.){escaped_old}\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', rf'{new_name}.\1('))
            
            # 安全的常量访问：包名.ClassName.CONSTANT
            rules.append((rf'(?<=[a-zA-Z0-9_]\.){escaped_old}\.([A-Z_][A-Z0-9_]*)\b', rf'{new_name}.\1'))
            
            # 安全的内部类访问：包名.ClassName.InnerClass
            rules.append((rf'(?<=[a-zA-Z0-9_]\.){escaped_old}\.([A-Z][a-zA-Z0-9_]*)', rf'{new_name}.\1'))
            
            # 新增：简单类名的静态访问（但需要更严格的上下文检查）
            # 只匹配在特定上下文中的简单类名静态访问
            # 1. 前面是空白或特定关键字（import, new, extends, implements, instanceof, class, interface, enum）
            # 2. 前面是类型声明位置
            rules.append((rf'(?<=\b(import|new|extends|implements|instanceof|class|interface|enum|@interface|record)\s+){escaped_old}\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', rf'{new_name}.\2('))
            rules.append((rf'(?<=\b(public|private|protected|static|final|abstract|synchronized)\s+){escaped_old}\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', rf'{new_name}.\2('))
            
            # 重要：避免替换变量名.方法()的情况
            # 如果ClassName后面跟着小写字母的方法调用，很可能是变量实例
            # 我们不应该替换这种情况
            
            # ===== 15. 注解（改进版） =====
            # @ClassName
            rules.append((rf'@{escaped_old}\b', f'@{new_name}'))
            # @ClassName(...)
            rules.append((rf'@{escaped_old}\s*\(', f'@{new_name}('))
            
            # ===== 16. 数组声明 =====
            rules.append((rf'(?<!\w){escaped_old}(?=\s*\[\s*\])', f'{new_name}'))
            
            # ===== 17. 增强 for 循环（改进版） =====
            # for (ClassName var : collection)
            rules.append((rf'\bfor\s*\(\s*{escaped_old}\s+', f'for ({new_name} '))
            # for (final ClassName var : collection)
            rules.append((rf'\bfor\s*\(\s*final\s+{escaped_old}\s+', f'for (final {new_name} '))
            
            # ===== 18. Try-catch 异常声明 =====
            rules.append((rf'(?<=\bcatch\s*\(\s*){escaped_old}(?=\s+[a-zA-Z_])', f'{new_name}'))
            rules.append((rf'(?<=\bthrows\s+)([^{{]*?\b){escaped_old}(?=\b)', rf'\1{new_name}'))
            
            # ===== 19. Lambda 表达式和方法引用 =====
            rules.append((rf'(?<!\w){escaped_old}(?=::)', f'{new_name}'))
            rules.append((rf'(?<=\(\s*){escaped_old}(?=\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\)\s*->)', f'{new_name}'))
            
            # ===== 20. Kotlin 特有语法 =====
            rules.append((rf'(?<=\bval\s+[a-zA-Z_][a-zA-Z0-9_]*\s*:\s*){escaped_old}(?=\b)', f'{new_name}'))
            rules.append((rf'(?<=\bvar\s+[a-zA-Z_][a-zA-Z0-9_]*\s*:\s*){escaped_old}(?=\b)', f'{new_name}'))
            rules.append((rf'(?<=\bfun\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\)\s*:\s*){escaped_old}(?=\b)', f'{new_name}'))
            rules.append((rf'(?<=\bclass\s+[a-zA-Z_][a-zA-Z0-9_]*\s*:\s*){escaped_old}(?=\b)', f'{new_name}'))
            rules.append((rf'(?<=\bobject\s+[a-zA-Z_][a-zA-Z0-9_]*\s*:\s*){escaped_old}(?=\b)', f'{new_name}'))
            rules.append((rf'(?<=\bis\s){escaped_old}(?=\b)', f'{new_name}'))
            rules.append((rf'(?<=\bas\s){escaped_old}(?=\b)', f'{new_name}'))
            rules.append((rf'(?<=\bas\?\s){escaped_old}(?=\b)', f'{new_name}'))
        
        return rules

    
    def rename_class_files(self, java_files, mapping, preview_mode=False):
        """重命名Java类文件（同时更新文件内的类名声明）"""
        renamed_count = 0
        self.renamed_files.clear()
        
        for java_file in java_files:
            old_class_name = java_file.stem
            new_class_name = mapping.get(old_class_name)
            
            if not new_class_name or old_class_name == new_class_name:
                continue
            
            try:
                # 1. 读取文件内容并更新类名声明
                with open(java_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 更新文件内的类名声明（类、构造函数等）
                updated_content = self._update_class_declaration(content, old_class_name, new_class_name)
                
                # 2. 生成新文件路径
                new_file_path = java_file.parent / f"{new_class_name}.java"
                
                if preview_mode:
                    self.log(f"[预览] 将重命名: {java_file.name} -> {new_file_path.name}")
                else:
                    # 3. 写入更新后的内容到新文件
                    with open(new_file_path, 'w', encoding='utf-8') as f:
                        f.write(updated_content)
                    
                    # 4. 删除旧文件（如果新旧文件名不同）
                    if java_file != new_file_path:
                        java_file.unlink()
                    
                    self.renamed_files[str(java_file)] = str(new_file_path)
                    self.log(f"已重命名类文件: {java_file.name} -> {new_file_path.name}")
                
                renamed_count += 1
                
            except Exception as e:
                self.log(f"重命名类文件失败 {java_file}: {e}", "ERROR")
        
        return renamed_count
    
    def _update_class_declaration(self, content, old_name, new_name):
        """更新文件内的类名声明"""
        escaped_old = re.escape(old_name)
        
        # 更新类/接口/枚举声明
        patterns = [
            (rf'\bclass\s+{escaped_old}\b', f'class {new_name}'),
            (rf'\binterface\s+{escaped_old}\b', f'interface {new_name}'),
            (rf'\benum\s+{escaped_old}\b', f'enum {new_name}'),
            (rf'\b@interface\s+{escaped_old}\b', f'@interface {new_name}'),
            (rf'\brecord\s+{escaped_old}\b', f'record {new_name}'),
            # 构造函数
            (rf'\bpublic\s+{escaped_old}\s*\(', f'public {new_name}('),
            (rf'\bprivate\s+{escaped_old}\s*\(', f'private {new_name}('),
            (rf'\bprotected\s+{escaped_old}\s*\(', f'protected {new_name}('),
            (rf'^\s*{escaped_old}\s*\(', f'{new_name}('),  # 无修饰符构造函数
        ]
        
        updated_content = content
        for pattern, replacement in patterns:
            updated_content = re.sub(pattern, replacement, updated_content, flags=re.MULTILINE)
        
        return updated_content
    
    def update_import_statements(self, project_path, mapping):
        """更新所有文件中的import语句（处理包路径变化）"""
        updated_count = 0
        patterns = ['**/*.java', '**/*.kt']
        
        for pattern in patterns:
            for file_path in project_path.rglob(pattern):
                if 'build' in file_path.parts or '.idea' in file_path.parts:
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    new_content = content
                    for old_name, new_name in mapping.items():
                        # 更新import语句中的类名
                        new_content = re.sub(
                            rf'import\s+([a-zA-Z0-9_.]+)\.{re.escape(old_name)}\s*;',
                            rf'import \1.{new_name};',
                            new_content
                        )
                        new_content = re.sub(
                            rf'import\s+static\s+([a-zA-Z0-9_.]+)\.{re.escape(old_name)}\.',
                            rf'import static \1.{new_name}.',
                            new_content
                        )
                    
                    if new_content != content:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        updated_count += 1
                        self.log(f"更新import语句: {file_path}")
                
                except Exception as e:
                    continue
        
        return updated_count

    
    def verify_rename_completion(self, project_path, mapping):
        """验证重命名是否完成（单次遍历，按文件聚合）"""
        from utils.file_helper import FileHelper

        project_path = Path(project_path)
        check_names = {
            old: new for old, new in mapping.items() if old != new
        }
        if not check_names:
            return []

        patterns = {
            name: re.compile(rf'\b{re.escape(name)}\b')
            for name in check_names
        }
        hits_by_name = {name: [] for name in check_names}
        suffixes = {'.java', '.kt', '.xml'}

        for file_path in FileHelper.collect_project_files(project_path, suffixes):
            if file_path.suffix.lower() not in suffixes:
                continue
            try:
                content = file_path.read_text(encoding='utf-8')
            except (UnicodeDecodeError, OSError):
                continue

            if not any(name in content for name in check_names):
                continue

            for old_name, pattern in patterns.items():
                if not pattern.search(content):
                    continue
                line_numbers = [
                    i for i, line in enumerate(content.split('\n'), 1)
                    if pattern.search(line)
                ]
                if line_numbers:
                    hits_by_name[old_name].append({
                        'file': str(file_path),
                        'lines': line_numbers,
                    })

        issues = []
        for old_name, found_files in hits_by_name.items():
            if found_files:
                issues.append({
                    'old_name': old_name,
                    'new_name': check_names[old_name],
                    'files': found_files,
                })
        return issues
    
    def generate_verification_report(self, issues):
        """生成验证报告"""
        if not issues:
            return "✅ 验证通过：所有引用已成功更新"
        
        report = ["⚠️ 发现以下文件中仍有旧类名引用：\n"]
        
        for issue in issues:
            report.append(f"\n类名: {issue['old_name']} → {issue['new_name']}")
            report.append(f"发现 {len(issue['files'])} 个文件中仍有引用：")
            
            for file_info in issue['files'][:5]:  # 只显示前5个
                file_name = Path(file_info['file']).name
                lines = ', '.join(map(str, file_info['lines'][:10]))  # 只显示前10行
                report.append(f"  - {file_name} (行: {lines})")
            
            if len(issue['files']) > 5:
                report.append(f"  ... 还有 {len(issue['files']) - 5} 个文件")
        
        report.append("\n建议：")
        report.append("1. 检查上述文件中的引用")
        report.append("2. 可能是字符串字面量或注释中的引用")
        report.append("3. 使用 IDE 的 Find & Replace 手动修复")
        report.append("4. 查看 TROUBLESHOOTING_GUIDE.md 获取更多帮助")
        
        return '\n'.join(report)
