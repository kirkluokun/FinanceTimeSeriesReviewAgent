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
git clone https://github.com/your-username/crewai-agent.git
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
OPENAI_API_KEY=sk-your-openai-api-key
GEMINI_API_KEY=your-gemini-api-key
DEEPSEEK_API_KEY=your-deepseek-api-key
SERPER_API_KEY=your-serper-api-key
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

### 步骤六：验证安装

```bash
# 运行简单的测试确认环境设置正确
python -c "import crewai; import pandas; import matplotlib; print('环境配置成功！')"
```

如果看到"环境配置成功！"消息，则说明基本环境已配置完成。

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

### OpenAI API
获取地址：https://platform.openai.com/api-keys
```
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_MODEL=gpt-4-turbo  # 可选，默认使用gpt-4-turbo
```

### Google Gemini API
获取地址：https://ai.google.dev/
```
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-pro  # 可选，默认使用gemini-pro
```

### DeepSeek API
获取地址：https://platform.deepseek.com/
```
DEEPSEEK_API_KEY=your-deepseek-api-key
```

### Serper API (用于网络搜索)
获取地址：https://serper.dev/
```
SERPER_API_KEY=your-serper-api-key
```

### 代理设置（可选，在某些网络环境下需要）
```
HTTP_PROXY=http://your-proxy-address:port
HTTPS_PROXY=http://your-proxy-address:port
```

## 数据格式要求

### 原始价格数据CSV格式

用于趋势分析组件的输入文件应至少包含以下列：

```
date,close
2023-01-01,100.5
2023-01-02,102.3
2023-01-03,101.7
...
```

其中：
- `date`: 日期列，格式为YYYY-MM-DD
- `close`: 收盘价格（或任意其他价格列，将自动识别）

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

## 常见问题

### 数据格式问题

如果遇到数据格式错误，请确保：
1. 原始价格数据CSV至少包含`date`列和一个价格列
2. 趋势区间CSV包含所有必需的列（见"区间数据验证与调整"部分）
3. 日期格式为标准的ISO格式（YYYY-MM-DD）

### API密钥问题

如果分析过程中出现API错误，请检查：
1. 环境变量是否正确配置
2. API密钥是否有效
3. 是否达到API使用限制

### 内存问题

大型数据集可能导致内存问题，可尝试：
1. 减少数据集大小
2. 增加系统内存
3. 调整分析参数，如减少API调用次数

### 网络问题

如果遇到网络连接问题：
1. 检查网络连接是否正常
2. 如果在限制网络环境中，配置适当的代理设置
3. 考虑增加API调用超时时间

## 可选功能

### 使用Streamlit界面（如已安装）

```bash
# 启动Streamlit界面
cd crewai-agent
streamlit run src/tech_analysis_crew/streamlit_app/app.py
```

这将启动一个Web界面，您可以通过浏览器访问`http://localhost:8501`来操作系统。

### 离线模式

如果您需要在离线环境中运行（不使用外部API），可以：

1. 修改配置文件：`src/tech_analysis_crew/config/agent.yaml`
2. 将`use_local_llm`设置为`true`
3. 配置本地模型路径

## 支持与咨询

如果您遇到任何问题或需要支持，请通过以下方式联系我们：

- 提交GitHub issue
- 发送电子邮件至：support@example.com

## 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request 