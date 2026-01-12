@echo off
REM PaperReader2 Backend 启动脚本

echo ====================================
echo   PaperReader2 Backend Service
echo   AI-Powered Paper Reader
echo ====================================
echo.

REM 检查虚拟环境是否存在
if not exist "venv\" (
    echo [错误] 虚拟环境不存在!
    echo 请先运行: python -m venv venv
    pause
    exit /b 1
)

REM 激活虚拟环境
echo [启动] 激活虚拟环境...
call venv\Scripts\activate.bat

REM 检查依赖是否已安装
python -c "import fastapi" 2>nul
if errorlevel 1 (
    echo [安装] 依赖未安装,正在安装...
    pip install -r requirements.txt
)

REM 启动服务
echo.
echo [启动] 启动FastAPI服务...
echo [信息] API文档: http://127.0.0.1:8000/api/docs
echo [信息] 健康检查: http://127.0.0.1:8000/api/v1/health
echo.
echo 按 Ctrl+C 停止服务
echo.

python -m app.main

pause
