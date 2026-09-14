@echo off
chcp 65001 >nul
echo ========================================
echo   发票小助手 v3.1 - 打包脚本
echo ========================================
echo.

REM 使用当前 Python 环境（推荐系统 Python 3.12 venv）
set "PYTHON=python"

REM 检查 PyInstaller 是否已安装
%PYTHON% -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装 PyInstaller...
    %PYTHON% -m pip install "pyinstaller>=6.0"
    if errorlevel 1 (
        echo [错误] PyInstaller 安装失败，请检查 Python 和 pip 环境。
        pause
        exit /b 1
    )
)

REM 检查 logo 文件
if not exist "logo.ico" (
    echo [错误] 未找到 logo.ico，请确认项目根目录存在 logo.ico。
    pause
    exit /b 1
)
if not exist "发票小助手-v3.1.spec" (
    echo [错误] 未找到 发票小助手-v3.1.spec 打包配置。
    pause
    exit /b 1
)

set "NEW_NAME=发票小助手-v3.1"

REM 探测 UPX 位置：优先项目目录，其次系统路径
set "UPX_PATH="
if exist "upx.exe" (
    set "UPX_PATH=%CD%"
) else if exist "C:\Program Files\UPX\upx.exe" (
    set "UPX_PATH=C:\Program Files\UPX"
)

echo [1/2] 正在按自定义 spec 打包单文件 EXE（含 OCR，请耐心等待）...
echo        旧版 InvoiceSorter.exe 位于 dist 目录，不会被覆盖。

if defined UPX_PATH (
    echo        已检测到 UPX（%UPX_PATH%），打包时会自动压缩内部二进制，体积更小。
    %PYTHON% -m PyInstaller --noconfirm --upx-dir "%UPX_PATH%" "发票小助手-v3.1.spec"
) else (
    %PYTHON% -m PyInstaller --noconfirm "发票小助手-v3.1.spec"
)

if errorlevel 1 (
    echo.
    echo [错误] 打包失败！请检查错误信息。
    pause
    exit /b 1
)

echo.
echo [2/2] 打包成功！
for %%F in ("dist\%NEW_NAME%.exe") do (
    echo   EXE: %%~nF%%~xF  =  %%~zF bytes
)
echo.

if defined UPX_PATH (
    echo [提示] UPX 已启用，体积已较无 UPX 时进一步缩小。
) else (
    echo [提示] 未检测到 UPX。若本机可访问外网，可从以下地址下载：
    echo        https://github.com/upx/upx/releases
    echo        将 upx.exe 放在本脚本同级目录或 C:\Program Files\UPX\upx.exe，
    echo        重新运行本脚本可再压缩 30%%~40%%。
)

echo.
echo ========================================
echo   新版本发布完成！
echo   EXE 文件: dist\%NEW_NAME%.exe
echo   旧版 InvoiceSorter.exe 已保留
echo ========================================
echo.
pause
