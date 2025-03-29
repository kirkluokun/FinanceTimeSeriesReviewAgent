
python src/tech_analysis_crew/rbc.py --input src/tech_analysis_crew/input/cu.csv --query "帮我复盘comex铜价"
python src/tech_analysis_crew/run_backend.py --input src/tech_analysis_crew/input/rmb.csv --query "帮我复盘离岸美元兑人民币汇率走势"
python src/tech_analysis_crew/run_backend.py --input src/tech_analysis_crew/input/hu_tong.csv --query "帮我复盘沪铜价格"  


# 时间序列分析与趋势挖掘系统

一个完整的时间序列数据分析系统，结合了趋势自动识别和基于CrewAI的深度原因分析。该系统能够自动处理CSV格式的时间序列数据，识别价格趋势，并分析价格变动原因。

## 功能特点

- 自动识别价格趋势区间（敏感版和不敏感版）
- 趋势区间统计与可视化
- 基于CrewAI的价格变动原因分析
- 使用搜索引擎查找相关新闻和事件
- 爬取网页内容进行信息提取
- 生成详细的分析报告
- 支持多种LLM模型（OpenAI、Gemini、DeepSeek等）

## 系统安装与环境配置

### 前置要求

- Python 3.10或更高版本
- Git
- Pip包管理器
- 足够的磁盘空间（建议至少1GB）
- 网络连接（用于API调用和数据获取）

### 步骤一：获取代码

```bash
# 克隆仓库
git clone https://github.com/kirkluokun/FinanceTimeSeriesReviewAgent.git
cd crewai-agent
```

### 步骤二：创建虚拟环境

推荐使用虚拟环境隔离依赖：

```bash
# 创建虚拟环境
python -m venv .crewai

# 激活虚拟环境（Linux/macOS）
source .crewai/bin/activate

# 激活虚拟环境（Windows）
# .crewai\Scripts\activate
```

### 步骤三：安装依赖

```bash
# 安装基础依赖
pip install -r requirements.txt

# 安装趋势分析组件依赖
pip install pandas matplotlib numpy scipy scikit-learn

# 安装CrewAI和相关依赖
pip install crewai langchain beautifulsoup4 requests-html 

# 安装可视化和界面依赖
pip install streamlit rich
```

### 步骤四：配置API密钥

在项目根目录创建`.env`文件，添加必要的API密钥：

```bash
# 创建环境变量文件
touch .env
```

在`.env`文件中添加以下内容（替换为您的实际API密钥）：

```
GEMINI_API_KEY=your-gemini-api-key
- https://ai.google.dev/gemini-api/docs/models?hl=zh-cn#gemini-2.0-flash
DEEPSEEK_API_KEY=your-deepseek-api-key
- https://api-docs.deepseek.com/zh-cn/
SERPER_API_KEY=your-serper-api-key
- https://serper.dev
FIRECRAWL_API_KEY=
- https://www.firecrawl.dev/app

```

### 步骤五：创建必要的目录结构

```bash
# 创建输入/输出目录
mkdir -p src/tech_analysis_crew/input
mkdir -p src/tech_analysis_crew/output
mkdir -p results

# 设置权限（Linux/macOS）
chmod -R 755 src/tech_analysis_crew/input
chmod -R 755 src/tech_analysis_crew/output
chmod -R 755 results
```


## 系统组件

系统由两个主要组件组成：

1. **趋势分析组件** (`trendanalysis`): 处理原始时间序列数据，自动识别价格趋势区间
2. **趋势原因分析组件** (`tech_analysis_crew`): 基于CrewAI，分析趋势区间的形成原因

## 完整分析流程

### 第一步：趋势识别与区间划分

首先使用趋势分析组件处理原始价格数据：

```bash
# 进入项目根目录
cd crewai-agent

# 运行趋势分析
python src/tool/trendanalysis/main.py 你的价格数据.csv --output-dir ./results
```

这一步将生成多个文件：
- 敏感版趋势分析CSV: `timestamp_filename-sensitive-trend_analysis.csv`
- 敏感版增强分析CSV: `timestamp_filename-sensitive-enhanced_analysis.csv`
- 不敏感版趋势分析CSV: `timestamp_filename-insensitive-trend_analysis.csv`
- 不敏感版增强分析CSV: `timestamp_filename-insensitive-enhanced_analysis.csv`
- 趋势可视化图表: `timestamp_filename-sensitive-trend_visualization.png` 和 `timestamp_filename-insensitive-trend_visualization.png`
- 分析比较报告: `timestamp_filename-comparison_report.csv`
- 详细Markdown报告: `timestamp_filename-detailed_report.md`

### 第二步：区间数据验证与调整

1. 检查生成的趋势区间CSV文件（敏感版或不敏感版），根据您的需求选择一个版本
2. 打开选定的增强分析CSV文件（`*-enhanced_analysis.csv`）
3. 验证趋势划分是否合理，必要时手动调整以下字段：
   - `start_date`: 开始日期
   - `end_date`: 结束日期
   - `trend_type`: 趋势类型（up/down/consolidation）
4. 保存修改后的CSV文件到`src/tech_analysis_crew/input/`目录

**注意**：CSV文件必须包含以下列：
- `start_date`: 开始日期
- `end_date`: 结束日期
- `start_price`: 开始价格
- `end_price`: 结束价格
- `low_price`: 最低价格
- `high_price`: 最高价格
- `pct_change`: 价格变化百分比
- `trend_type`: 趋势类型（up/down/consolidation）

### 第三步：趋势原因分析

使用CrewAI分析趋势区间形成的原因：

```bash
# 进入项目根目录
cd crewai-agent

# 运行原因分析
python src/tech_analysis_crew/run_backend.py --input src/tech_analysis_crew/input/你的趋势区间文件.csv --query "分析XX价格走势"
```

参数说明：
- `--input`: 指定输入的趋势区间CSV文件路径
- `--query`: 分析查询，例如"帮我复盘vlcc price"或"分析铜价走势"
- `--output-dir`: 可选，指定输出目录路径
- `--debug`: 可选，启用调试模式

示例：
```bash
# VLCC价格分析
python src/tech_analysis_crew/run_backend.py --input src/tech_analysis_crew/input/vlcc_trends.csv --query "帮我复盘vlcc price"

# 铜价分析
python src/tech_analysis_crew/run_backend.py --input src/tech_analysis_crew/input/cu_trends.csv --query "帮我复盘comex copper价格"
```

分析完成后，将在输出目录生成分析报告和摘要文件。

## 环境变量详细配置

系统依赖多个外部API服务，需要在`.env`文件中配置相应的密钥：

### Google Gemini API

```
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-pro  # 可选，默认使用gemini-pro
```

### DeepSeek API

```
DEEPSEEK_API_KEY=your-deepseek-api-key
```

### Serper API (用于网络搜索)

```
SERPER_API_KEY=your-serper-api-key
```

## 数据格式要求

### 原始价格数据CSV格式

用于趋势分析组件的输入文件应包含至少两列数据：

```csv
date,price
2023-01-01,100.5
2023-01-02,102.3
2023-01-03,101.7
...
```

要求：
- 第一列必须是日期数据，支持多种日期格式（如YYYY-MM-DD、MM/DD/YYYY等）
- 第二列必须是数值数据
- CSV文件必须至少包含这两列
- 列名可以是任意文本，程序会自动处理
- 如果CSV包含多列，默认使用第二列作为数值数据
- 无效的日期或数值行会被自动清理掉
- 数据会按日期自动排序

注意：
- 程序会自动清理无效数据，包括：
  - 无法解析的日期
  - 非数值的价格数据
  - 重复的日期记录（保留最后一条）
- 清理过程中会打印提示信息，说明删除了多少无效数据

### 趋势区间数据格式

用于CrewAI分析的输入文件必须包含以下列：

```
start_date,end_date,start_price,end_price,low_price,high_price,pct_change,trend_type
2023-01-01,2023-01-15,100.5,110.3,98.2,112.5,0.0975,up
2023-01-16,2023-02-01,110.3,105.8,103.1,111.2,-0.0408,down
...
```

## 目录结构

```
crewai-agent/
├── src/
│   ├── tool/
│   │   └── trendanalysis/          # 趋势分析组件
│   │       ├── main.py             # 趋势分析入口点
│   │       ├── trend-sensitive.py  # 敏感版趋势识别算法
│   │       ├── trend-insensitive.py # 不敏感版趋势识别算法
│   │       ├── duration_price_analysis.py # 区间价格分析模块
│   │       └── test_main.py        # 测试脚本
│   │
│   └── tech_analysis_crew/         # 趋势原因分析组件
│       ├── config/                 # 配置文件
│       │   ├── agent.yaml          # Agent配置
│       │   └── tasks.yaml          # 任务配置
│       ├── input/                  # 输入数据（放置趋势区间CSV）
│       ├── output/                 # 输出目录
│       ├── memory/                 # 内存存储
│       ├── utils/                  # 工具函数
│       ├── run_backend.py          # 后端运行脚本
│       ├── backend.py              # 后端实现
│       └── crew.py                 # CrewAI编排与协调
```

## 测试

各组件的测试运行方法：

```bash
# 趋势分析组件测试
cd crewai-agent
python -m unittest src/tool/trendanalysis/test_main.py

# 趋势原因分析组件测试
cd crewai-agent
python -m unittest src/tech_analysis_crew/test/test_crew.py
```
