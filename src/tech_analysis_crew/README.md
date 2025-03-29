
# 金融时间序列分析平台

## 系统介绍

金融时间序列分析平台是一个基于FastAPI和Python的Web应用，用于分析金融时间序列数据，生成趋势图和分析报告。系统支持上传CSV文件，使用CrewAI进行智能数据分析并生成可视化结果。

## 目录结构

```
crewai-agent/src/tech_analysis_crew/
├── run_api.py           # API服务启动脚本
├── run_backend.py       # 后端API实现（FastAPI）
├── rbc.py               # 命令行分析工具（原run_backend.py）
├── test_api.py          # API测试脚本
├── input/               # 输入文件目录
│   └── cu.csv           # 示例铜价数据
├── output/              # 输出文件目录
│   └── [job_id]/        # 每个任务的输出目录
│       ├── reports/     # 生成的分析报告
│       └── cache/       # 数据处理缓存
├── run_test.sh          # 测试脚本
└── README.md            # 说明文档
```

## 使用方法

### 安装依赖

```bash
cd crewai-agent/src/tech_analysis_crew
pip install -r requirements.txt
```

### 启动API服务

API服务提供REST接口，用于接收分析请求并返回结果：

```bash
cd crewai-agent/src/tech_analysis_crew
python run_api.py
```

服务将自动查找可用端口并启动，默认为8000-8100之间的可用端口。API文档可访问：`http://localhost:[port]/docs`

### API使用方法（run_backend.py）

run_backend.py提供以下API端点：

- `GET /` - 获取API基本信息
- `POST /api/analysis` - 创建新的分析任务
  - 参数：`{"query": "分析查询", "input_file": "文件路径"}`
- `GET /api/analysis/{job_id}` - 获取任务状态
- `GET /api/analysis/{job_id}/result` - 获取分析结果
- `GET /api/tasks` - 列出所有任务
- `DELETE /api/analysis/{job_id}` - 删除任务

示例请求：
```bash
curl -X POST "http://localhost:8001/api/analysis" \
  -H "Content-Type: application/json" \
  -d '{"query": "帮我复盘comex铜价", "input_file": "input/cu.csv"}'
```

### 命令行工具使用方法（rbc.py）

rbc.py是原来的run_backend.py，提供命令行接口直接执行分析：

```bash
cd crewai-agent/src/tech_analysis_crew
python rbc.py --input input/cu.csv --query "复盘comex铜价" --output-dir ./output
```

选项:
- `--input PATH` - 输入CSV文件路径
- `--query TEXT` - 分析查询（默认：分析铜价走势）
- `--output-dir DIR` - 输出目录路径
- `--debug` - 启用调试模式

## 测试

运行测试脚本验证系统功能：

```bash
cd crewai-agent/src/tech_analysis_crew
./run_test.sh
```

或手动测试API服务：

```bash
cd crewai-agent/src/tech_analysis_crew
python test_api.py
```

## 技术架构

- 前端：可选择使用HTML、CSS、JavaScript
- 后端：FastAPI、Python
- 数据分析：CrewAI、Pandas、Matplotlib
- 文件处理：Python标准库

## 输出结果

分析结果包含多个组件：
- `reports/final_report.md` - 最终分析报告
- `reports/period_x_report.md` - 各时期分析报告
- `reports/period_x_conclusion.md` - 各时期结论

## 常见问题

### 接口返回空结果

如果调用API获取结果时发现summary_file为空，请确保：
1. 分析任务已完成（状态为"success"或"completed"）
2. 检查输出目录中是否存在final_report.md文件
3. 可能需要重新启动API服务

### 端口冲突问题

如果遇到端口已被占用的问题：
1. 系统会自动寻找可用端口
2. 检查之前的API服务是否仍在运行，可使用`pkill -f "python run_api.py"`关闭
3. 如果测试脚本连接失败，请确认.api_port文件中的端口是否与实际运行端口一致
