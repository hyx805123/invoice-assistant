@echo off
color 0A
title 自动安装Python环境

echo ================================================================
echo                自动安装Python环境工具
echo ================================================================
echo.
echo 此工具将自动下载并安装Python 3.10.11及所需依赖
echo.
echo 注意：安装过程中请保持网络连接，并允许管理员权限
echo.
echo 按任意键开始安装...
pause > nul

:: 检查是否已安装Python
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Python已安装在您的系统中。
    python --version
    
    echo.
    echo 是否仍要继续安装？(Y/N)
    choice /c YN /m "请选择"
    if %ERRORLEVEL% EQU 2 goto :check_dependencies
)

echo.
echo 正在下载Python 3.10.11安装程序...
echo.

:: 创建临时目录
md "%TEMP%\python_installer" 2>nul

:: 下载Python安装程序
powershell -Command "(New-Object System.Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe', '%TEMP%\python_installer\python-3.10.11-amd64.exe')"

if %ERRORLEVEL% NEQ 0 (
    color 0C
    echo 下载失败！请检查您的网络连接，或手动下载Python：
    echo https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe
    echo.
    pause
    exit /b 1
)

echo 下载完成！正在安装Python 3.10.11...
echo.
echo 注意：在安装窗口中，请确保勾选"Add Python to PATH"选项！
echo.

:: 运行安装程序，添加到PATH并安装pip
"%TEMP%\python_installer\python-3.10.11-amd64.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0

if %ERRORLEVEL% NEQ 0 (
    color 0C
    echo Python安装失败！请尝试手动安装。
    echo.
    pause
    exit /b 1
)

:: 刷新环境变量
setx PATH "%PATH%" > nul

echo Python 3.10.11安装完成！
echo.

:check_dependencies
echo 正在检查并安装所需依赖...

:: 等待一下，确保Python命令可用
timeout /t 2 > nul

:: 安装/更新pip
python -m ensurepip --upgrade

:: 安装依赖
python -m pip install -r requirements.txt

if %ERRORLEVEL% NEQ 0 (
    color 0E
    echo 依赖安装可能不完整，请检查错误信息。
) else (
    echo 所有依赖安装完成！
)

echo.
echo ================================================================
echo 安装过程已完成！现在您可以运行"启动.bat"来启动程序。
echo ================================================================
echo.

pause