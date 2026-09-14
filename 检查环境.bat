@echo off
color 0A
title Python环境检查工具

echo ================================================================
echo                    Python环境检查工具
echo ================================================================
echo.
echo 正在检查Python环境...
echo.

:: 检查Python是否已安装
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    color 0C
    echo [未安装] Python未安装或未添加到系统PATH
    echo.
    echo 请按照以下步骤安装Python：
    echo 1. 访问 https://www.python.org/downloads/ 下载最新版Python
    echo 2. 安装时勾选"Add Python to PATH"选项
    echo 3. 安装完成后重新运行本程序
    echo.
    echo 详细安装步骤请查看"Python安装指南.txt"文件
) else (
    for /f "tokens=*" %%a in ('python --version 2^>^&1') do set pyver=%%a
    echo [已安装] %pyver%
    
    :: 检查PyMuPDF是否已安装
    pip show PyMuPDF >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo [未安装] PyMuPDF模块未安装
        echo.
        echo 是否要安装所需的依赖包？(Y/N)
        choice /c YN /m "请选择"
        if %ERRORLEVEL% EQU 1 (
            echo.
            echo 正在安装依赖包...
            pip install -r requirements.txt
            if %ERRORLEVEL% NEQ 0 (
                color 0C
                echo 安装失败！请尝试手动安装：
                echo pip install -r requirements.txt
            ) else (
                echo 依赖包安装成功！
            )
        )
    ) else (
        echo [已安装] PyMuPDF模块
    )
    
    :: 检查rapidocr-onnxruntime是否已安装
    pip show rapidocr-onnxruntime >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo [未安装] rapidocr-onnxruntime模块未安装
    ) else (
        echo [已安装] rapidocr-onnxruntime模块（OCR）
    )
    
    :: 检查pillow是否已安装
    pip show pillow >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo [未安装] pillow模块未安装
    ) else (
        echo [已安装] pillow模块
    )
    
    :: 检查tkinter
    python -c "import tkinter" >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo [未安装] tkinter模块未安装
        echo 注意：tkinter通常随Python一起安装，如果未安装，可能需要重新安装Python
    ) else (
        echo [已安装] tkinter模块
    )
)

echo.
echo ================================================================
echo 检查完成！如需运行程序，请双击"启动.bat"文件
echo ================================================================

pause