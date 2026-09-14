@echo off
color 0A
title 发票智能分类重命名工具 v3.0

echo ================================================================
echo            发票智能分类重命名工具 v3.0
echo ================================================================
echo.

:: 检查Python是否已安装
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    color 0C
    echo ================================================================
    echo                      错误提示
    echo ================================================================
    echo.
    echo 未检测到Python安装！
    echo 本程序需要Python环境才能运行。
    echo.
    echo 您可以选择以下操作：
    echo.
    echo [1] 自动下载安装Python（推荐）
    echo [2] 手动安装Python
    echo [3] 退出程序
    echo.
    choice /c 123 /m "请选择操作"
    
    if %ERRORLEVEL% EQU 1 (
        :: 自动安装Python
        start "" "自动安装Python.bat"
        exit /b 0
    ) else if %ERRORLEVEL% EQU 2 (
        :: 显示手动安装指南
        echo.
        echo 请按照以下步骤安装Python：
        echo 1. 访问 https://www.python.org/downloads/ 下载最新版Python
        echo 2. 安装时勾选"Add Python to PATH"选项
        echo 3. 安装完成后重新运行本程序
        echo.
        echo 更详细的安装指南请查看"Python安装指南.txt"文件
        echo.
        start "" notepad "Python安装指南.txt"
    ) else (
        :: 退出程序
        exit /b 0
    )
    
    echo ================================================================
    pause
    exit /b 1
)

:: 如果Python已安装，则运行主启动脚本
start 启动程序.bat