#!/bin/bash
# 时间序列分析API测试脚本

echo "===== 时间序列分析API测试 ====="
echo "开始测试..."

# 设置工作目录
cd "$(dirname "$0")"
CURRENT_DIR=$(pwd)
echo "当前工作目录: $CURRENT_DIR"

# 设置日志文件
LOG_FILE="$CURRENT_DIR/api_server.log"
ERROR_FILE="$CURRENT_DIR/.api_error"
PORT_FILE="$CURRENT_DIR/.api_port"
STARTING_FILE="$CURRENT_DIR/.api_starting"

# 函数: 清理进程
cleanup() {
  echo "清理进程..."
  if [ ! -z "$API_PID" ]; then
    echo "终止API服务 (PID: $API_PID)"
    kill $API_PID 2>/dev/null
    sleep 2
    # 确保进程被终止
    if ps -p $API_PID > /dev/null 2>&1; then
      echo "强制终止API服务 (PID: $API_PID)"
      kill -9 $API_PID 2>/dev/null
    fi
  fi
  
  # 删除标记文件
  rm -f "$PORT_FILE" "$ERROR_FILE" "$STARTING_FILE"
  
  # 清理临时任务脚本
  echo "清理临时脚本文件..."
  find "$CURRENT_DIR/output" -name "task_*.py" -type f -delete 2>/dev/null
  
  exit $1
}

# 捕获中断信号
trap 'cleanup 1' INT TERM

# 检查Python环境
if ! command -v python3 &> /dev/null; then
  echo "错误: 未找到python3命令"
  exit 1
fi

# 先检查并清理可能存在的旧进程
echo "检查是否存在旧的API服务进程..."
rm -f "$PORT_FILE" "$ERROR_FILE" "$STARTING_FILE" # 移除旧的标记文件

# 清理可能存在的uvicorn进程
ps -ef | grep "uvicorn run_backend:app" | grep -v grep | awk '{print $2}' | xargs -r kill -9
# 清理可能存在的临时Python脚本进程
ps -ef | grep "task_.*\.py" | grep -v grep | awk '{print $2}' | xargs -r kill -9
# 清理旧的临时脚本文件
find "$CURRENT_DIR/output" -name "task_*.py" -type f -delete 2>/dev/null
echo "已清理旧进程和临时文件"

# 检查必要的包
echo "检查必要的Python包..."
python3 -m pip install -q fastapi uvicorn requests curl-cffi

# 启动API服务
echo "启动API服务..."
python3 run_api.py > "$LOG_FILE" 2>&1 &
API_PID=$!

# 等待服务启动标记
echo "等待服务初始化..."
MAX_WAIT=90
COUNT=0

# 等待启动标记文件或错误文件
while [ ! -f "$STARTING_FILE" ] && [ ! -f "$ERROR_FILE" ] && [ $COUNT -lt 30 ]; do
  sleep 1
  COUNT=$((COUNT+1))
  echo -n "."
done
echo ""

# 检查是否有错误
if [ -f "$ERROR_FILE" ]; then
  echo "错误: API服务启动过程中出错"
  echo "错误信息: $(cat "$ERROR_FILE")"
  echo "日志内容:"
  cat "$LOG_FILE"
  cleanup 1
fi

# 等待端口文件生成
while [ ! -f "$PORT_FILE" ] && [ $COUNT -lt $MAX_WAIT ]; do
  sleep 1
  COUNT=$((COUNT+1))
  echo -n "."
done
echo ""

if [ ! -f "$PORT_FILE" ]; then
  echo "错误: API服务启动失败，端口文件未生成"
  echo "日志内容:"
  cat "$LOG_FILE"
  cleanup 1
fi

# 获取API端口
API_PORT=$(cat "$PORT_FILE")
echo "API服务正在启动 (PID: $API_PID) 使用端口: $API_PORT"

# 检查服务是否正常运行
if ! ps -p $API_PID > /dev/null; then
  echo "错误: API服务进程已退出"
  echo "日志内容:"
  cat "$LOG_FILE"
  cleanup 1
fi

# 等待端口可访问
echo "等待API服务端口可访问..."
MAX_RETRY=60
for i in $(seq 1 $MAX_RETRY); do
  if curl -s "http://localhost:$API_PORT/" >/dev/null 2>&1; then
    echo "API服务端口 $API_PORT 已可访问!"
    break
  fi
  
  if [ $i -eq $MAX_RETRY ]; then
    echo "错误: API服务端口 $API_PORT 在 $MAX_RETRY 次尝试后仍不可访问"
    echo "日志内容:"
    cat "$LOG_FILE"
    cleanup 1
  fi
  
  echo "尝试 $i/$MAX_RETRY: 端口 $API_PORT 不可访问，等待2秒..."
  sleep 2
done

echo "API服务已成功启动并可访问 (PID: $API_PID, 端口: $API_PORT)"
echo "等待额外10秒以确保服务完全初始化..."
sleep 10

# 运行测试脚本
echo "运行API测试..."
python3 test_api.py

# 测试完成，清理进程
echo "测试完成"
cleanup 0 