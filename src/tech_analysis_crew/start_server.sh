@ -0,0 +1,44 @@
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
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." &> /dev/null && pwd )"

echo -e "${BLUE}=======================================${NC}"
echo -e "${GREEN}金融时间序列分析平台服务器启动脚本${NC}"
echo -e "${BLUE}=======================================${NC}"

# # # 检查是否有虚拟环境
# if [ ! -d "$VENV_DIR" ]; then
#     echo -e "${YELLOW}创建虚拟环境...${NC}"
#     python3 -m venv "$VENV_DIR"
# fi

# 激活虚拟环境
echo -e "${YELLOW}激活虚拟环境...${NC}"
source "$VENV_DIR/bin/activate"

# # 安装依赖
# echo -e "${YELLOW}更新pip...${NC}"
# pip install --upgrade pip

# echo -e "${YELLOW}清理pip缓存...${NC}"
# pip cache purge

# echo -e "${YELLOW}卸载可能冲突的包...${NC}"
# pip uninstall -y crewai langchain langchain-core langsmith pydantic

# echo -e "${YELLOW}安装基本依赖...${NC}"
# pip install -r "$WEB_DIR/requirements.txt" --no-cache-dir

# # # 验证crewai版本和flow模块
# echo -e "${YELLOW}验证crewai版本...${NC}"
# python -c "import crewai; print(f'CrewAI版本: {crewai.__version__}'); print('查找flow模块:'); print(dir(crewai))"

# # # 在安装依赖后添加
# echo -e "${YELLOW}检查关键包版本...${NC}"
# pip list | grep -E "crewai|langchain|pydantic|setuptools"

# 添加环境变量禁用CrewAI遥测
echo -e "${YELLOW}禁用CrewAI遥测...${NC}"
export OTEL_SDK_DISABLED=true

# 确保静态文件目录存在
echo -e "${YELLOW}检查静态文件目录...${NC}"
mkdir -p "$SCRIPT_DIR/trendanalysis/static/images" "$SCRIPT_DIR/trendanalysis/static/files"

# 添加项目根目录到PYTHONPATH
echo -e "${YELLOW}设置Python路径...${NC}"
export PYTHONPATH="$PROJECT_ROOT"
echo -e "${YELLOW}PYTHONPATH设置为: ${NC}$PYTHONPATH"

# # 添加调试信息
echo -e "${YELLOW}检查模块路径...${NC}"
python -c "import sys; print('Python搜索路径:'); [print(p) for p in sys.path]"

# # 显示路径信息
echo -e "${YELLOW}项目根目录: ${NC}$PROJECT_ROOT"
echo -e "${YELLOW}PYTHONPATH: ${NC}$PYTHONPATH"

# # 安装CrewAI工具包
echo -e "${YELLOW}安装CrewAI工具包...${NC}"
pip install crewai-tools --no-cache-dir

# 启动服务器
echo -e "${GREEN}启动服务器...${NC}"
echo -e "${BLUE}=======================================${NC}"
echo -e "${YELLOW}服务器将在 http://localhost:8080 上运行${NC}"
echo -e "${BLUE}=======================================${NC}"
cd "$SCRIPT_DIR" && python "web/server.py"

# 取消激活虚拟环境（这一行通常不会执行，因为服务器会一直运行）
deactivate 