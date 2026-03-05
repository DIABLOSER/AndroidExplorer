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
        """生成类名替换规则（全面覆盖所有Java/Kotlin引用场景，优化准确性）"""
        rules = []
        
        for old_name, new_name in mapping.items():
            escaped_old = re.escape(old_name)
            
            # ===== 1. Import 语句（最高优先级，精确匹配） =====
            # 标准 import
            rules.append((rf'(?<=import\s)([a-zA-Z0-9_.]+)\.{escaped_old}(?=\s*;)', rf'\1.{new_name}'))
            # static import
            rules.append((rf'(?<=import\s+static\s)([a-zA-Z0-9_.]+)\.{escaped_old}(?=\.)', rf'\1.{new_name}'))
            # 通配符 import
            rules.append((rf'(?<=import\s)([a-zA-Z0-9_.]+)\.{escaped_old}(?=\.\*\s*;)', rf'\1.{new_name}'))
            
            # ===== 2. Package 和 AndroidManifest.xml =====
            # android:name 属性（Activity/Service/Receiver/Provider）
            rules.append((rf'(?<=android:name=")([a-zA-Z0-9_.]*\.)?{escaped_old}(?=")', rf'\1{new_name}'))
            rules.append((rf'(?<=android:name="\.)({escaped_old})(?=")', rf'{new_name}'))
            
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
            # 变量声明: ClassName var = ...
            rules.append((rf'\b{escaped_old}\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*([=;,)\]])', rf'{new_name} \1\2'))
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
            # ClassName.staticMethod()
            rules.append((rf'\b{escaped_old}\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', rf'{new_name}.\1('))
            # ClassName.CONSTANT
            rules.append((rf'\b{escaped_old}\.([A-Z_][A-Z0-9_]*)\b', rf'{new_name}.\1'))
            # ClassName.field
            rules.append((rf'\b{escaped_old}\.([a-z][a-zA-Z0-9_]*)\b', rf'{new_name}.\1'))
            # ClassName.InnerClass
            rules.append((rf'\b{escaped_old}\.([A-Z][a-zA-Z0-9_]*)', rf'{new_name}.\1'))
            
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
        """验证重命名是否完成（检查是否还有旧类名引用）"""
        issues = []
        
        for old_name, new_name in mapping.items():
            # 搜索旧类名
            found_files = []
            
            for pattern in ['**/*.java', '**/*.kt', '**/*.xml']:
                for file_path in project_path.rglob(pattern):
                    if 'build' in file_path.parts or '.idea' in file_path.parts:
                        continue
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # 使用词边界匹配，避免误报
                        if re.search(rf'\b{re.escape(old_name)}\b', content):
                            # 记录文件和行号
                            lines = content.split('\n')
                            line_numbers = []
                            for i, line in enumerate(lines, 1):
                                if re.search(rf'\b{re.escape(old_name)}\b', line):
                                    line_numbers.append(i)
                            
                            found_files.append({
                                'file': str(file_path),
                                'lines': line_numbers
                            })
                    except:
                        continue
            
            if found_files:
                issues.append({
                    'old_name': old_name,
                    'new_name': new_name,
                    'files': found_files
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
