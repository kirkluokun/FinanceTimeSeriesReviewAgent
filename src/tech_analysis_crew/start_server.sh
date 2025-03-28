#!/bin/bash

# 设置颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # 无颜色

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
WEB_DIR="$SCRIPT_DIR/web"
VENV_DIR="$SCRIPT_DIR/venv"

echo -e "${BLUE}=======================================${NC}"
echo -e "${GREEN}金融时间序列分析平台服务器启动脚本${NC}"
echo -e "${BLUE}=======================================${NC}"

# 检查是否有虚拟环境
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}创建虚拟环境...${NC}"
    python3 -m venv "$VENV_DIR"
fi

# 激活虚拟环境
echo -e "${YELLOW}激活虚拟环境...${NC}"
source "$VENV_DIR/bin/activate"

# 安装依赖
echo -e "${YELLOW}安装依赖...${NC}"
pip install -r "$WEB_DIR/requirements.txt"

# 确保静态文件目录存在
echo -e "${YELLOW}检查静态文件目录...${NC}"
mkdir -p "$SCRIPT_DIR/trendanalysis/static/images" "$SCRIPT_DIR/trendanalysis/static/files"

# 启动服务器
echo -e "${GREEN}启动服务器...${NC}"
echo -e "${BLUE}=======================================${NC}"
echo -e "${YELLOW}服务器将在 http://localhost:8080 上运行${NC}"
echo -e "${BLUE}=======================================${NC}"
cd "$SCRIPT_DIR" && python "web/server.py"

# 取消激活虚拟环境（这一行通常不会执行，因为服务器会一直运行）
deactivate 