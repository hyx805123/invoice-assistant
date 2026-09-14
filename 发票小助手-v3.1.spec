# -*- mode: python ; coding: utf-8 -*-
# 发票小助手 v3.1 打包配置
# 目标：单文件 EXE + 体积优化（排除未使用的二进制/数据）

from PyInstaller.building.build_main import Analysis, PYZ, EXE
from PyInstaller.building.datastruct import TOC
from PyInstaller.utils.hooks import collect_all


# 需要显式收集 rapidocr_onnxruntime 的模型与配置
datas = []
binaries = []
hiddenimports = ['rapidocr_onnxruntime', 'onnxruntime']
tmp_ret = collect_all('rapidocr_onnxruntime')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# 嵌入 logo（打包后程序运行时读取）
datas += [('logo.ico', '.'), ('logo.png', '.')]


a = Analysis(
    ['invoice_processor.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'scipy', 'pandas', 'PyQt5', 'PyQt6', 'IPython',
        'pytest', 'test', 'unittest', 'pycparser', 'setuptools', 'pip',
        'distutils', 'lib2to3', 'bdb', 'pdb', 'idlelib',
        'PIL._avif', 'PIL.features', 'tkinter.test', 'numpy._pyinstaller',
    ],
    noarchive=False,
    optimize=2,
)

# 在 Analysis 完成后、打包前，过滤掉体积大但未使用的二进制/数据文件
# 注意：此操作有风险，过滤后必须运行自检验证
def should_exclude_bin(name):
    # 1) PIL AVIF 插件：本工具仅生成 PNG/JPEG，不处理 AVIF 发票
    if 'PIL\\_avif' in name or 'PIL/_avif' in name:
        return True
    # 2) OpenCV FFmpeg 视频编解码器：发票识别只涉及静态图片，不涉及视频
    #    （cv2.pyd 本身保留，仅剥离可选的视频 I/O 插件）
    if 'opencv_videoio_ffmpeg' in name:
        return True
    # 3) numpy / pandas / scipy 测试数据
    if '\\tests\\' in name or '/tests/' in name:
        return True
    return False


def should_exclude_data(name):
    # 过滤 tk/tcl 的演示、测试、示例数据
    if '_tcl_data\\demos' in name or '_tcl_data\\tk8.6\\demos' in name:
        return True
    if '_tcl_data\\opt0.4' in name:
        return True
    # OpenCV 测试数据
    if 'cv2\\data\\' in name and 'haarcascade' in name:
        return True
    return False


a.binaries = TOC([b for b in a.binaries if not should_exclude_bin(b[0])])
a.datas = TOC([d for d in a.datas if not should_exclude_data(d[0])])

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='发票小助手-v3.1',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['logo.ico'],
)
