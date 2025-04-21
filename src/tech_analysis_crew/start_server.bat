@echo off
REM 金融时间序列分析平台服务器启动脚本 (Windows版本)

REM 设置颜色
setlocal EnableDelayedExpansion
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "NC=[0m"

REM 获取脚本所在目录
set "SCRIPT_DIR=%~dp0"
set "WEB_DIR=%SCRIPT_DIR%web"
set "VENV_DIR=%SCRIPT_DIR%venv"
set "PROJECT_ROOT=%SCRIPT_DIR%..\..\"

REM 去除路径中的尾部反斜杠
if "%SCRIPT_DIR:~-1%" == "\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
if "%WEB_DIR:~-1%" == "\" set "WEB_DIR=%WEB_DIR:~0,-1%"
if "%VENV_DIR:~-1%" == "\" set "VENV_DIR=%VENV_DIR:~0,-1%"
if "%PROJECT_ROOT:~-1%" == "\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"

echo %BLUE%=======================================%NC%
echo %GREEN%金融时间序列分析平台服务器启动脚本%NC%
echo %BLUE%=======================================%NC%

REM 检查虚拟环境是否存在
if not exist "%VENV_DIR%" (
    echo %YELLOW%创建虚拟环境...%NC%
    python -m venv "%VENV_DIR%"
)

REM 激活虚拟环境
echo %YELLOW%激活虚拟环境...%NC%
call "%VENV_DIR%\Scripts\activate"

REM 添加环境变量禁用CrewAI遥测
echo %YELLOW%禁用CrewAI遥测...%NC%
set OTEL_SDK_DISABLED=true

REM 确保静态文件目录存在
echo %YELLOW%检查静态文件目录...%NC%
if not exist "%SCRIPT_DIR%\trendanalysis\static\images" mkdir "%SCRIPT_DIR%\trendanalysis\static\images"
if not exist "%SCRIPT_DIR%\trendanalysis\static\files" mkdir "%SCRIPT_DIR%\trendanalysis\static\files"

REM 添加项目根目录到PYTHONPATH
echo %YELLOW%设置Python路径...%NC%
set "PYTHONPATH=%PROJECT_ROOT%;%PYTHONPATH%"
echo %YELLOW%PYTHONPATH设置为: %NC%%PYTHONPATH%

REM 添加调试信息
echo %YELLOW%检查模块路径...%NC%
python -c "import sys; print('Python搜索路径:'); [print(p) for p in sys.path]"

REM 显示路径信息
echo %YELLOW%项目根目录: %NC%%PROJECT_ROOT%
echo %YELLOW%PYTHONPATH: %NC%%PYTHONPATH%

REM 安装CrewAI工具包
echo %YELLOW%安装CrewAI工具包...%NC%
pip install crewai-tools --no-cache-dir

REM 启动服务器
echo %GREEN%启动服务器...%NC%
echo %BLUE%=======================================%NC%
echo %YELLOW%服务器将在 http://localhost:8080 上运行%NC%
echo %BLUE%=======================================%NC%
cd "%SCRIPT_DIR%" && python "web/server.py"

REM 取消激活虚拟环境（这一行通常不会执行，因为服务器会一直运行）
call deactivate 