# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['app.py'],  # 主程序文件
    pathex=[],   # 当前路径
    binaries=[],
    datas=[  # 在这里添加所有需要打包的资源文件
        ('applogo.ico', '.'),  # 包含图标文件到根目录
        # ('源文件夹', '目标文件夹')
        # 如果有资源文件夹，按下面的格式添加
        # ('resources', 'resources'),  # 如果存在resources文件夹
        # ('config', 'config'),        # 如果存在config文件夹
    ],
    hiddenimports=[],  # 如果有动态导入的模块，在这里声明
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Android Exploere',  # 
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # False表示无控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='applogo.ico'  # 这里设置图标
)
