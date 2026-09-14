@echo off
echo 正在启动发票智能分类重命名工具 v3.0...
echo.

:: 检查Python是否已安装
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ======================================================
    echo 错误: 未检测到Python安装！
    echo 请先安装Python 3.8或更高版本，然后再运行此程序。
    echo 您可以从 https://www.python.org/downloads/ 下载Python。
    echo ======================================================
    echo.
    pause
    exit /b 1
)

:: 检查依赖是否已安装
echo 正在检查依赖...
pip show PyMuPDF >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 未检测到必要的依赖，正在尝试安装...
    pip install -r requirements.txt
    if %ERRORLEVEL% NEQ 0 (
        echo 依赖安装失败！请手动运行以下命令安装依赖：
        echo pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )
    echo 依赖安装成功！
)

:: 启动程序
echo 正在启动程序...
python invoice_processor.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 程序运行出错！
    echo 如果问题持续存在，请联系技术支持。
    echo.
    pause
) else (
    echo 程序已正常退出。
    timeout /t 2 >nul
    exit
)