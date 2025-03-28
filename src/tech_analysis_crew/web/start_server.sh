#!/bin/bash

# 设置当前目录为脚本所在目录
cd "$(dirname "$0")"

# 检查是否有虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "安装依赖..."
pip install -r requirements.txt

# 启动服务器
echo "启动服务器..."
python server.py

# 取消激活虚拟环境
deactivate 