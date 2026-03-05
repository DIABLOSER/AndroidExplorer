# Android 资源重命名工具 v3.2.1

一个功能强大的Android资源文件批量重命名工具，支持Drawable、Layout、String、ID和Java类的智能重命名，并自动更新所有引用。

## 🎉 v3.2.1 新特性

- ✅ **大幅改进类名引用更新** - 从 Lookahead/Lookbehind 改为直接匹配，更可靠
- ✅ **完善类型转换支持** - 12+ 条新规则，覆盖所有类型转换场景
- ✅ **增强 For 循环支持** - 修复循环中类型声明未更新的问题
- ✅ **改进泛型参数匹配** - 支持继承、实现、嵌套泛型等复杂场景
- ✅ **简化正则表达式** - 更简单、更易维护、更不容易出错
- ✅ **新增专项修复指南** - TYPE_CAST_FIX.md、FOR_LOOP_FIX.md、GENERIC_FIX_GUIDE.md

## 🔥 v3.2 核心特性

- ✅ **执行完成后自动重新扫描** - 文件列表实时更新
- ✅ **自动验证功能** - 检查是否还有未更新的引用
- ✅ **智能错误处理** - 单个规则失败不影响整体
- ✅ **详细的验证报告** - 精确定位未更新的文件和行号
- ✅ **完整的故障排查指南** - TROUBLESHOOTING_GUIDE.md

## 项目结构

```
.
├── core/                      # 核心业务逻辑
│   ├── __init__.py
│   ├── resource_scanner.py    # 资源文件扫描器
│   ├── resource_renamer.py    # 资源文件重命名器
│   └── class_renamer.py       # Java类重命名器
│
├── business/                  # 业务逻辑管理器
│   ├── __init__.py
│   └── scanner_manager.py     # 扫描管理器
│
├── ui/                        # UI相关组件
│   ├── __init__.py
│   ├── tooltip.py             # 工具提示组件
│   ├── theme.py               # 主题管理器
│   └── format_panels.py       # 格式面板构建器
│
├── utils/                     # 工具函数
│   ├── __init__.py
│   ├── format_helper.py       # 格式化辅助工具
│   └── file_helper.py         # 文件操作辅助工具
│
├── build/                     # 构建临时文件（打包生成）
├── dist/                      # 打包输出目录
│   └── Android Explorer.exe   # 打包后的可执行文件
│
├── app.py                     # 主程序入口（GUI）
├── app.spec                   # PyInstaller配置文件
├── applogo.ico                # 程序图标
└── README.md                  # 项目说明
```

## 模块说明

### core/ - 核心业务逻辑

- **resource_scanner.py**: 扫描Android项目中的资源文件（drawable、layout、strings.xml等）
- **resource_renamer.py**: 生成资源文件重命名映射，执行重命名操作
- **class_renamer.py**: 扫描和重命名Java/Kotlin类文件，更新AndroidManifest.xml和import引用

### business/ - 业务逻辑管理器

- **scanner_manager.py**: 统一管理所有资源扫描逻辑，协调各类资源的扫描流程

### ui/ - UI组件

- **tooltip.py**: 提供鼠标悬停提示功能，显示文件完整路径
- **theme.py**: 管理应用主题（Light/Dark），配置VS Code风格的UI样式
- **format_panels.py**: 构建各类资源的命名格式设置面板

### utils/ - 工具函数

- **format_helper.py**: 格式化相关工具（命名格式转换、预览生成、大小写转换等）
- **file_helper.py**: 文件操作工具（导入/导出映射、模块发现等）

### app.py - 主程序

包含主GUI界面和应用逻辑，整合所有模块功能，提供完整的用户交互界面。

## 使用方法

### 运行程序

```bash
python app.py
```

### 基本流程

1. **选择项目**: 点击顶部菜单栏的"文件"按钮，选择Android项目根目录
2. **选择模块**: 如果是多模块项目，可在顶部下拉框选择特定模块或"全部模块"
3. **选择资源类型**: 点击左侧按钮切换资源类型（资源/布局/字符/ID/类名）
4. **配置命名格式**: 在右侧面板设置前缀、关键词、后缀和格式类型
5. **生成映射**: 点击"生成映射"按钮，在中间区域查看映射预览
6. **编辑映射**: 可直接在中间文本区域编辑映射关系，点击"应用修改"保存
7. **执行重命名**: 点击"执行"按钮，确认后开始重命名操作

### 高级功能

- **预览模式**: 勾选"预览"选项，可在不实际修改文件的情况下查看操作结果
- **更新引用**: 勾选"更新引用"选项，自动更新所有XML、Java、Kotlin文件中的引用
- **导入/导出映射**: 支持保存和加载映射文件，便于团队协作或批量操作
- **反向映射**: 点击"反向映射"可将映射关系反转，用于还原操作
- **重置/清空**: 快速重置当前映射或清空所有映射

## 功能特性

### 支持的资源类型

- **Drawable**: 图片资源（png、jpg、webp等）
- **Layout**: 布局文件（XML）
- **String**: 字符串资源（strings.xml）
- **ID**: 控件ID（@+id/xxx）
- **Java类**: Java/Kotlin类文件

### 核心功能

- ✅ 批量重命名资源文件
- ✅ 自动更新所有引用（XML、Java、Kotlin、Gradle文件）
- ✅ 支持多模块Android项目
- ✅ 灵活的命名格式配置（前缀、关键词、后缀、序号、随机字符）
- ✅ 预览模式（不实际修改文件）
- ✅ 映射导入/导出（支持团队协作）
- ✅ 反向映射（快速还原）
- ✅ 自动导出映射表（操作完成后自动保存）
- ✅ 实时日志输出
- ✅ VS Code风格的现代化UI
- ✅ 文件路径工具提示
- ✅ 项目信息显示（路径+名称）

### 命名格式

支持三种命名格式：

1. **前缀_关键词_后缀**: `icon_home_0001`
2. **关键词_前缀_后缀**: `home_icon_0001`
3. **前缀_后缀_关键词**: `icon_0001_home`

占位符说明：

- `{name}`: 原文件名或关键词
- `{number:04d}`: 序号（如0001、0002）
- `{random}`: 随机字符串

### 引用更新

自动更新以下类型的引用：

- **Drawable**: `R.drawable.xxx`、`@drawable/xxx`
- **Layout**: `R.layout.xxx`、`@layout/xxx`、`XxxBinding`
- **String**: `R.string.xxx`、`@string/xxx`、`<string name="xxx">`
- **ID**: `R.id.xxx`、`@+id/xxx`、`@id/xxx`、`binding.xxx`
- **Class**: 
  - **基础引用**：import、类声明、构造函数、对象实例化
  - **类型声明**：变量、字段、方法参数、方法返回类型、数组
  - **类型转换**（v3.2.1 增强）：
    - 基础转换: `(ClassName) obj`
    - 链式调用: `((ClassName) obj).method()`
    - Return 语句: `return (ClassName) obj`
    - 赋值语句: `var = (ClassName) obj`
    - 方法参数: `method((ClassName) obj)`
    - 条件表达式: `condition ? (ClassName) obj : null`
  - **增强 For 循环**（v3.2.1 修复）：
    - `for (ClassName var : collection)`
    - `for (final ClassName var : collection)`
  - **泛型参数**（v3.2.1 增强）：
    - 继承: `extends BaseClass<Type1, ClassName>`
    - 实现: `implements Interface<ClassName>`
    - 嵌套泛型: `Observable<Response<ClassName>>`
    - 泛型边界: `<T extends ClassName>`
  - **Android 特定**：
    - AndroidManifest.xml 组件声明
    - 布局文件中的自定义 View
    - Fragment 标签和 tools:context 属性
  - **高级特性**：
    - 静态成员访问、Lambda、方法引用
    - instanceof 检查、.class 引用
    - 注解使用、异常声明

## 界面说明

### 顶部菜单栏

- **文件**: 选择项目路径
- **关于**: 查看作者信息
- **生成映射**: 根据当前格式生成映射
- **应用修改**: 应用中间区域的映射编辑
- **重置**: 重置为上次生成的映射
- **清空**: 清空当前映射
- **导入映射**: 从文件导入映射
- **反向映射**: 反转映射关系
- **导出映射**: 导出映射到文件
- **执行**: 执行重命名操作
- **模块下拉框**: 选择项目模块
- **选项**: 预览、更新引用、子目录

### 左侧边栏

显示当前选中资源类型的文件列表，支持：

- 点击查看映射关系
- 鼠标悬停显示完整路径
- 底部显示文件数量统计

### 中间工作区

- **上半部分**: 映射编辑区，显示和编辑映射关系（格式：`旧名称 = 新名称`）
- **下半部分**: 日志输出区，实时显示操作日志

### 右侧边栏

命名格式配置面板，包括：

- 格式类型选择（单选按钮）
- 前缀、关键词、后缀输入框
- 格式预览
- 预设按钮（仅Layout）
- 过滤字符（仅Class）

### 底部状态栏

显示当前状态、项目路径、文件统计等信息

## 注意事项

1. **备份重要数据**: 虽然工具提供预览模式，但建议在操作前备份项目
2. **测试环境**: 建议先在测试项目中验证效果
3. **引用更新**: 确保勾选"更新引用"选项，否则需要手动修复引用
4. **模块选择**: 多模块项目建议先选择特定模块，避免误操作
5. **映射检查**: 执行前仔细检查映射关系，避免命名冲突
6. **版本控制**: 建议使用Git等版本控制工具，便于回滚

## 常见问题

### Q: 类重命名后编译错误 "找不到符号"？

**原因**: 某些引用没有被自动更新

**解决方案**:
1. 查看工具的验证报告，定位未更新的文件和行号
2. 使用 `grep -rn "OldClassName" src/` 搜索旧类名
3. 参考以下文档手动修复：
   - `TYPE_CAST_FIX.md` - 类型转换未更新
   - `FOR_LOOP_FIX.md` - For 循环未更新
   - `GENERIC_FIX_GUIDE.md` - 泛型参数未更新
   - `TROUBLESHOOTING_GUIDE.md` - 完整故障排查

### Q: 泛型参数中的类名没有更新？

**示例**: `extends BaseClass<OldViewModel>` 没有更新为 `extends BaseClass<NewViewModel>`

**解决方案**:
1. 确保映射表中包含 `OldViewModel`
2. 确保勾选"更新引用"选项
3. 使用最新版本（v3.2.1 已大幅改进）
4. 参考 `GENERIC_FIX_GUIDE.md` 手动修复

### Q: 类型转换中的类名没有更新？

**示例**: `((OldActivity) activity)` 没有更新为 `((NewActivity) activity)`

**解决方案**:
1. 使用最新版本（v3.2.1 已修复）
2. 参考 `TYPE_CAST_FIX.md` 手动修复
3. 使用批量替换脚本（文档中提供）

### Q: For 循环中的类型声明没有更新？

**示例**: `for (OldClass item : items)` 没有更新

**解决方案**:
1. 使用最新版本（v3.2.1 已修复）
2. 参考 `FOR_LOOP_FIX.md` 手动修复

### Q: 如何验证所有引用都已更新？

**方法**:
1. 查看工具的自动验证报告
2. 搜索旧类名: `grep -rn "OldClassName" --include="*.java" --include="*.kt" --include="*.xml" src/`
3. 编译测试: `./gradlew clean assembleDebug`
4. 运行测试: `./gradlew test`

### Q: 如何回滚重命名操作？

**方法 1: 使用 Git**
```bash
git checkout .
```

**方法 2: 使用反向映射**
1. 导入原始映射表
2. 点击"反向映射"按钮
3. 勾选"更新引用"
4. 执行重命名

### Q: 工具支持哪些文件类型？

**支持的文件**:
- Java 文件 (*.java)
- Kotlin 文件 (*.kt)
- XML 文件 (*.xml)
- Gradle 文件 (*.gradle)

**排除的目录**:
- build/
- .idea/
- .gradle/

## 文档索引

### 核心文档
- `README.md` - 项目说明和使用指南（本文档）
- `CLASS_RENAME_IMPROVEMENTS.md` - 类重命名功能详细说明
- `TROUBLESHOOTING_GUIDE.md` - 完整的故障排查指南
- `QUICK_REFERENCE.md` - 快速参考指南

### 专项修复指南
- `TYPE_CAST_FIX.md` - 类型转换未更新的修复方法
- `FOR_LOOP_FIX.md` - For 循环未更新的修复方法
- `GENERIC_FIX_GUIDE.md` - 泛型参数未更新的修复方法

### 测试和示例
- `EXAMPLE_RENAME_TEST.md` - 完整的重命名示例
- `CUSTOM_VIEW_RENAME_TEST.md` - 自定义 View 重命名测试
- `GENERIC_PARAMETERS_TEST.md` - 泛型参数重命名测试

### 版本说明
- `IMPROVEMENTS_V3.2.md` - v3.2 版本改进说明
- `UPDATE_SUMMARY.md` - 更新总结

---

## 测试结果

以下是在真实项目中的测试结果，展示了工具的可靠性和准确性：

| 项目名称 | Drawable | Layout | String | ID | Class | 总体评价 |
|---------|----------|--------|--------|----|----|---------|
| **Project1** | 100% (94) | 100% (37) | 100% (114) | 100% (62) | 100% (90) | ✅ 完美 |
| **Project2** | 100% (109) | 100% (31) | 100% (122) | 100% (143) | 100% (68) | ✅ 完美 |
| **Project3** | 100% (123) | 100% (29) | 100% (61) | 98.11% (159) | 100% (69) | ✅ 优秀 |
| **Project4** | 100% (193) | 100% (49) | 100% (72) | 99.47% (383) | 92.2% (77) | ✅ 良好 |
| **Project5** | 100% (208) | 100% (62) | 100% (142) | 98.11% (372) | 99.09% (110) | ✅ 优秀 |

**说明**:
- 括号内数字表示处理的资源/类数量
- 百分比表示成功更新的引用比例
- Class 列的成功率受项目复杂度影响（泛型、类型转换等）

**测试环境**:
- 工具版本: v3.2.1
- 测试日期: 2024
- 项目类型: 真实商业项目
- 操作系统: Windows

**测试结论**:
1. ✅ Drawable、Layout、String 资源重命名成功率 100%
2. ✅ ID 重命名成功率 98%+ （极少数动态生成的 ID 需要手动处理）
3. ✅ Class 重命名成功率 92%+ （v3.2.1 大幅改进后）
4. ✅ 所有项目编译通过，运行正常
5. ⚠️ 少量未更新的引用主要是：
   - 字符串字面量中的类名（反射调用）
   - 注释中的类名
   - 动态生成的资源引用

**改进建议**:
- 使用最新版本（v3.2.1）获得最佳效果
- 勾选"更新引用"选项
- 查看验证报告，手动修复少量遗漏
- 使用版本控制，便于回滚

## 系统要求

- Python 3.7+
- tkinter（通常随Python安装）
- 支持Windows、macOS、Linux

## 作者

**大菠萝**  
邮箱: daboluo719@gmail.com

## 版本历史

### v3.2.1 (当前版本)

- **大幅改进类名引用更新的可靠性**
  - 从复杂的 Lookahead/Lookbehind 断言改为简单直接的匹配方式
  - 更可靠、更易维护、更不容易出错
  
- **完善类型转换支持**（12+ 条新规则）
  - 基础类型转换: `(ClassName) obj`
  - 嵌套类型转换: `((ClassName)) obj`
  - Return 语句: `return (ClassName) obj`
  - 赋值语句: `var = (ClassName) obj`
  - 方法参数: `method((ClassName) obj)`
  - 条件表达式: `condition ? (ClassName) obj : null`
  - 链式调用: `((ClassName) obj).method()`
  - 字段访问: `((ClassName) obj).field`
  
- **修复增强 For 循环类型声明**
  - `for (ClassName var : collection)`
  - `for (final ClassName var : collection)`
  
- **改进泛型参数匹配**
  - 继承时的泛型: `extends BaseClass<Type1, ClassName>`
  - 实现时的泛型: `implements Interface<ClassName>`
  - 嵌套泛型: `Observable<Response<ClassName>>`
  - 泛型边界: `<T extends ClassName>`
  
- **改进其他场景**
  - instanceof 检查
  - .class 引用
  - 静态成员访问
  - 注解使用
  
- **新增专项修复指南**
  - `TYPE_CAST_FIX.md` - 类型转换修复指南
  - `FOR_LOOP_FIX.md` - For 循环修复指南
  - `GENERIC_FIX_GUIDE.md` - 泛型参数修复指南

### v3.2

- **执行完成后自动重新扫描**
  - 重命名完成后自动刷新文件列表
  - 显示最新的文件名和数量统计
  
- **类名引用更新准确性改进**
  - 使用 Lookahead/Lookbehind 断言提高匹配精度
  - 改进的错误处理，单个规则失败不影响整体
  - 排除更多目录（.gradle）
  - 详细的错误日志
  - **增强泛型参数支持**：
    - 继承时的泛型参数: `extends BaseClass<OldClass, NewClass>`
    - 实现时的泛型参数: `implements Interface<OldClass>`
    - 嵌套泛型: `Observable<Response<OldClass>>`
    - 泛型边界: `<T extends OldClass>`
    - 多层泛型嵌套
  
- **自动验证功能**
  - 重命名后自动检查是否还有旧类名引用
  - 生成详细的验证报告（文件名+行号）
  - 智能提示：验证通过或有警告
  
- **新增文档**
  - `TROUBLESHOOTING_GUIDE.md` - 完整的故障排查指南
  - `IMPROVEMENTS_V3.2.md` - 详细的改进说明
  - `GENERIC_PARAMETERS_TEST.md` - 泛型参数重命名测试
  - `QUICK_REFERENCE.md` - 快速参考指南

### v3.1

- 重构代码结构，模块化设计
- 新增业务逻辑管理器
- 优化UI组件，提升用户体验
- 新增格式面板构建器
- 改进主题管理
- 优化扫描性能
- 新增自动导出映射表功能
- 改进状态栏显示（项目路径+名称）
- 移除备份功能（建议使用版本控制）
- 优化拖动条样式
- 移除不必要的边框和标题
- 关于信息移至菜单栏
- **重大改进：类重命名功能**
  - 60+ 条替换规则，全面覆盖 Java/Kotlin 引用场景
  - 自动重命名 .java 文件并同步更新类声明和构造函数
  - 支持布局文件中的自定义 View 引用更新
  - 支持 Fragment 标签和 tools:context 属性
  - 类似 Android Studio Refactor 的重命名效果
  - 详见 `CLASS_RENAME_IMPROVEMENTS.md` 和 `CUSTOM_VIEW_RENAME_TEST.md`

