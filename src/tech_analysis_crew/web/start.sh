#!/bin/bash

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
TECH_ANALYSIS_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$(dirname "$TECH_ANALYSIS_DIR")")"

# 确保目录结构存在
mkdir -p "$SCRIPT_DIR/static/images"
mkdir -p "$SCRIPT_DIR/static/files"
mkdir -p "$TECH_ANALYSIS_DIR/input"
mkdir -p "$TECH_ANALYSIS_DIR/output"

# 打印启动信息
echo "================================"
echo "金融时间序列分析平台启动程序"
echo "================================"
echo "项目根目录: $PROJECT_ROOT"
echo "分析工具目录: $TECH_ANALYSIS_DIR"
echo "Web界面目录: $SCRIPT_DIR"
echo "--------------------------------"

# 检查Python环境
if command -v python3 &> /dev/null
then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null
then
    PYTHON_CMD="python"
else
    echo "错误: 未找到Python解释器，请安装Python 3.8或更高版本"
    exit 1
fi

# 打印Python版本
echo "使用Python: $($PYTHON_CMD --version)"
echo "--------------------------------"

# 检查依赖包
echo "检查依赖包..."
if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    $PYTHON_CMD -m pip install -r "$SCRIPT_DIR/requirements.txt"
    if [ $? -ne 0 ]; then
        echo "警告: 依赖包安装可能不完整，可能会影响服务运行"
    else
        echo "依赖包安装完成"
    fi
else
    echo "警告: 未找到requirements.txt文件，跳过依赖安装"
fi
echo "--------------------------------"

# 启动Web服务器
echo "正在启动Web服务器..."
echo "服务器将在 http://localhost:8080 上运行"
echo "按Ctrl+C停止服务"
echo "================================"

# 切换到tech_analysis_crew目录并启动服务器
cd "$TECH_ANALYSIS_DIR"
$PYTHON_CMD "$SCRIPT_DIR/server.py" 