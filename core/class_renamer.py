#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from pathlib import Path
from collections import OrderedDict


class ClassRenamer:
    """Java类文件重命名工具"""
    
    def __init__(self, log_func=None):
        self.log = log_func or (lambda msg, level='INFO': None)
    
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
    
    def filter_class_name(self, class_name, filter_chars):
        """从类名中过滤指定字符"""
        if not filter_chars:
            return class_name
        
        filtered_name = class_name
        for char in filter_chars.split(','):
            char = char.strip()
            if char:
                filtered_name = filtered_name.replace(char, '')
        
        return filtered_name if filtered_name else class_name
    
    def generate_class_mapping(self, java_files, format_string, filter_chars):
        """生成类名映射"""
        mapping = OrderedDict()
        existing_names = set()
        
        for java_file in java_files:
            old_class_name = java_file.stem
            filtered_name = self.filter_class_name(old_class_name, filter_chars)
            
            counter = 1
            while True:
                try:
                    new_class_name = format_string.format(name=filtered_name, number=counter)
                except (KeyError, ValueError):
                    new_class_name = format_string.replace('{name}', filtered_name).replace('{number}', str(counter))
                
                if new_class_name not in existing_names:
                    break
                counter += 1
            
            mapping[old_class_name] = new_class_name
            existing_names.add(new_class_name)
        
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
    
    def get_class_replace_rules(self, java_files, mapping, project_path):
        """生成类名替换规则（增强版，覆盖更多使用场景）"""
        rules = []
        
        for old_name, new_name in mapping.items():
            # 1. import语句
            rules.append((rf'import\s+([a-zA-Z0-9_.]+)\.{re.escape(old_name)}\s*;', rf'import \1.{new_name};'))
            rules.append((rf'import\s+static\s+([a-zA-Z0-9_.]+)\.{re.escape(old_name)}\.', rf'import static \1.{new_name}.'))
            
            # 2. AndroidManifest.xml 中的引用
            rules.append((rf'android:name="([a-zA-Z0-9_.]*\.)?{re.escape(old_name)}"', rf'android:name="\1{new_name}"'))
            rules.append((rf'<activity[^>]*android:name="\.{re.escape(old_name)}"', rf'<activity android:name=".{new_name}"'))
            
            # 3. 类声明
            rules.append((rf'\bclass\s+{re.escape(old_name)}\b', f'class {new_name}'))
            rules.append((rf'\binterface\s+{re.escape(old_name)}\b', f'interface {new_name}'))
            rules.append((rf'\benum\s+{re.escape(old_name)}\b', f'enum {new_name}'))
            
            # 4. 继承和实现
            rules.append((rf'\bextends\s+{re.escape(old_name)}\b', f'extends {new_name}'))
            rules.append((rf'\bimplements\s+([^{{]*\b){re.escape(old_name)}\b', rf'implements \1{new_name}'))
            
            # 5. 构造函数
            rules.append((rf'\bpublic\s+{re.escape(old_name)}\s*\(', f'public {new_name}('))
            rules.append((rf'\bprivate\s+{re.escape(old_name)}\s*\(', f'private {new_name}('))
            rules.append((rf'\bprotected\s+{re.escape(old_name)}\s*\(', f'protected {new_name}('))
            
            # 6. 实例化 (new关键字)
            rules.append((rf'\bnew\s+{re.escape(old_name)}\s*\(', f'new {new_name}('))
            rules.append((rf'\bnew\s+{re.escape(old_name)}\s*<', f'new {new_name}<'))
            
            # 7. 增强for循环中的类型声明 - 新增
            rules.append((rf'\bfor\s*\(\s*{re.escape(old_name)}\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*:', rf'for ({new_name} \1:'))
            
            # 8. 类型声明 (变量、参数、返回值)
            rules.append((rf'\b{re.escape(old_name)}\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*([=;,)\[])', rf'{new_name} \1\2'))
            rules.append((rf'\b{re.escape(old_name)}\s*<', f'{new_name}<'))  # 泛型
            
            # 9. 泛型类型参数
            rules.append((rf'<\s*{re.escape(old_name)}\s*>', f'<{new_name}>'))
            rules.append((rf'<\s*{re.escape(old_name)}\s*,', f'<{new_name},'))
            rules.append((rf',\s*{re.escape(old_name)}\s*>', f', {new_name}>'))
            rules.append((rf',\s*{re.escape(old_name)}\s*,', f', {new_name},'))
            
            # 10. .class 引用
            rules.append((rf'\b{re.escape(old_name)}\.class\b', f'{new_name}.class'))
            
            # 11. instanceof 检查
            rules.append((rf'\binstanceof\s+{re.escape(old_name)}\b', f'instanceof {new_name}'))
            
            # 12. 类型转换
            rules.append((rf'\(\s*{re.escape(old_name)}\s*\)', f'({new_name})'))
            
            # 13. 静态成员访问（方法、字段、常量、内部类、枚举） - 增强
            # 匹配 ClassName.CONSTANT, ClassName.method(), ClassName.InnerClass, ClassName.EnumValue
            rules.append((rf'\b{re.escape(old_name)}\.([A-Z_][A-Z0-9_]*)\b', rf'{new_name}.\1'))  # 静态常量（大写）
            rules.append((rf'\b{re.escape(old_name)}\.([a-z][a-zA-Z0-9_]*)\s*\(', rf'{new_name}.\1('))  # 静态方法（小写开头）
            rules.append((rf'\b{re.escape(old_name)}\.([A-Z][a-zA-Z0-9_]*)', rf'{new_name}.\1'))  # 内部类/枚举（大写开头）
            
            # 14. 注解中的引用
            rules.append((rf'@{re.escape(old_name)}\b', f'@{new_name}'))
            
            # 15. 数组声明
            rules.append((rf'\b{re.escape(old_name)}\s*\[\s*\]', f'{new_name}[]'))
            
            # 16. 方法返回类型
            rules.append((rf'\bpublic\s+{re.escape(old_name)}\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', rf'public {new_name} \1('))
            rules.append((rf'\bprivate\s+{re.escape(old_name)}\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', rf'private {new_name} \1('))
            rules.append((rf'\bprotected\s+{re.escape(old_name)}\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', rf'protected {new_name} \1('))
            rules.append((rf'\bstatic\s+{re.escape(old_name)}\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', rf'static {new_name} \1('))
            rules.append((rf'\bfinal\s+{re.escape(old_name)}\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', rf'final {new_name} \1('))
            
            # 17. Kotlin 特有语法
            rules.append((rf'\bval\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*{re.escape(old_name)}\b', rf'val \1: {new_name}'))
            rules.append((rf'\bvar\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*{re.escape(old_name)}\b', rf'var \1: {new_name}'))
            rules.append((rf'\bfun\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*:\s*{re.escape(old_name)}\b', rf'fun \1(): {new_name}'))
            
            # 18. 方法参数中的类型
            rules.append((rf'\(\s*{re.escape(old_name)}\s+([a-zA-Z_][a-zA-Z0-9_]*)', rf'({new_name} \1'))
            rules.append((rf',\s*{re.escape(old_name)}\s+([a-zA-Z_][a-zA-Z0-9_]*)', rf', {new_name} \1'))
            
            # 19. 三元运算符和条件表达式中的类型转换
            rules.append((rf'\?\s*\(\s*{re.escape(old_name)}\s*\)', rf'? ({new_name})'))
            rules.append((rf':\s*\(\s*{re.escape(old_name)}\s*\)', rf': ({new_name})'))
            
            # 20. 变量声明时的null检查
            rules.append((rf'\bif\s*\(\s*{re.escape(old_name)}\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*!=\s*null', rf'if ({new_name} \1 != null'))
            rules.append((rf'\bif\s*\(\s*{re.escape(old_name)}\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*==\s*null', rf'if ({new_name} \1 == null'))
        
        return rules
