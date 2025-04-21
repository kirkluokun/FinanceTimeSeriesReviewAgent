# 金融时间序列分析平台

这是一个基于CrewAI的金融时间序列数据分析平台，能够对金融商品数据进行趋势分析、技术分析和市场洞察。

## 项目概述

该项目使用CrewAI框架构建了一个智能Agent系统，能够自动分析金融时间序列数据，提取关键指标，搜索相关市场信息，生成综合分析报告。项目特点：

- 自动提取关键指标并生成分析查询
- 智能搜索相关市场信息和新闻
- 爬取和分析网页内容
- 生成高质量的分析报告
- 提供Web界面进行交互

## 系统要求

- Python 3.10+（建议使用Python 3.10-3.12）
- Node.js 14+（可选，用于前端开发）
- 虚拟环境（推荐）
- 必要的API密钥

## 安装步骤

### 1. 克隆仓库到本地

```bash
git clone <仓库地址>
cd crewai-agent
```

### 2. 安装Python环境

#### Linux/MacOS:

```bash
# 创建虚拟环境
python -m venv .venv
# 激活虚拟环境
source .venv/bin/activate
# 安装依赖
pip install -r requirements.txt
```

#### Windows:

```batch
# 创建虚拟环境
python -m venv .venv
# 激活虚拟环境
.venv\Scripts\activate
# 安装依赖
pip install -r requirements.txt
```

### 3. 安装Node.js（可选，用于前端开发）

访问 [Node.js官网](https://nodejs.org/) 下载并安装适合您操作系统的版本。

### 4. 配置环境变量

在项目根目录创建`.env`文件，添加以下内容：

```
# 必须配置
TAVILY_API_KEY=tvly-xxx          # Tavily搜索API
SERPER_API_KEY=xxx               # Serper搜索API（可选，建议作为备用）
FIRECRAWL_API_KEY=fc-xxx         # Firecrawl网页爬虫API

# LLM选择（至少配置一个）
OPENAI_API_KEY=sk-xxx            # OpenAI API密钥
ANTHROPIC_API_KEY=sk-ant-xxx     # Anthropic Claude API密钥
GEMINI_API_KEY=xxx               # Google Gemini API密钥

# 可选配置
CREWAI_DISABLE_TELEMETRY=true    # 禁用CrewAI遥测
SEARCH_API=tavily                # 设置默认搜索API提供商
```

## 启动服务器

### Linux/MacOS:

1. 进入项目目录

```bash
cd crewai-agent/src/tech_analysis_crew
```

2. 运行启动脚本

```bash
chmod +x start_server.sh
./start_server.sh
```

### Windows:

1. 进入项目目录

```batch
cd crewai-agent\src\tech_analysis_crew
```

2. 运行启动脚本

```batch
start_server.bat
```

服务器将在 http://localhost:8080 上启动。

## 使用流程

Web界面分为数据预处理和复盘分析两个主要步骤：

### 第一步：数据预处理

1. 上传原始CSV格式的时间序列数据文件
   - CSV文件需包含日期列和价格列
   - 日期格式应为标准格式（如YYYY-MM-DD）
   - 价格列应为数值格式

2. 进行数据预处理设置：
   - 选择日期列和价格列
   - 设置分析时间段（**注意：最多选择5个时间段**）
   - 调整其他数据预处理参数

3. 点击"开始预处理"按钮

4. 等待预处理完成并下载处理后的数据文件

### 第二步：复盘分析

1. 在复盘分析区域上传预处理后的数据文件
2. 选择需要分析的时间段（已在预处理阶段设定）
3. 输入分析查询（例如："分析铜价走势"）
4. 点击"开始分析"按钮
5. 等待分析完成，查看生成的报告

## 命令行使用方式

除了Web界面，您还可以通过命令行使用该工具：

```bash
# 进入目录
cd crewai-agent/src/tech_analysis_crew

# 运行分析脚本
python run_backend.py --input input/your_data.csv --query "分析铜价走势"

# 输出到指定目录
python run_backend.py --input input/your_data.csv --query "分析铜价走势" --output-dir ./custom_output
```

## API密钥获取方法

### Tavily API密钥
1. 访问 [Tavily官网](https://tavily.com/)
2. 注册账号并登录
3. 导航到API密钥页面获取免费API密钥

### Firecrawl API密钥
1. 访问 [Firecrawl官网](https://firecrawl.dev/)
2. 注册账号并登录
3. 导航到API密钥页面获取API密钥

### OpenAI API密钥
1. 访问 [OpenAI平台](https://platform.openai.com/)
2. 注册账号并登录
3. 导航到API密钥页面获取密钥

### Google Gemini API密钥
1. 访问 [Google AI Studio](https://makersuite.google.com/app/apikey)
2. 使用Google账号登录
3. 点击"创建API密钥"获取Gemini API密钥
4. 或访问 [Google AI for Developers](https://ai.google.dev/) 了解更多信息和使用限制

## 故障排除

- **API错误**：请检查API密钥是否正确设置
- **网络爬虫失败**：可能是由于目标网站限制，尝试减少并发请求数
- **预处理失败**：
  - 检查原始CSV数据格式是否正确（需要包含日期列和价格列）
  - 确保CSV文件编码为UTF-8
- **无法上传预处理文件**：
  - 确保文件格式正确，为预处理步骤生成的格式
  - 检查文件大小是否超过系统限制（通常为10MB）
- **报告生成失败**：
  - 确保分析的时间段数量不超过5个（系统限制）
  - 检查预处理后的数据文件是否完整
- **处理时间过长**：对于大型数据集，可考虑减少分析时间段的数量

## 项目结构

```
crewai-agent/
├── src/
│   ├── tech_analysis_crew/      # 主程序目录
│   │   ├── backend.py           # 后端实现
│   │   ├── crew.py              # CrewAI团队定义
│   │   ├── run_backend.py       # 命令行工具
│   │   ├── start_server.sh      # Linux/Mac启动脚本
│   │   ├── start_server.bat     # Windows启动脚本
│   │   ├── web/                 # Web界面
│   │   │   ├── server.py        # Web服务器
│   │   │   ├── index.html       # 前端页面
│   │   │   ├── script.js        # 前端脚本
│   │   │   └── styles.css       # 样式表
│   │   ├── trendanalysis/       # 趋势分析工具
│   │   ├── utils/               # 工具类
│   │   ├── input/               # 输入数据目录
│   │   └── output/              # 输出数据目录
│   └── llm/                     # LLM接口
├── tests/                       # 测试目录
├── requirements.txt             # 依赖列表
├── pyproject.toml               # 项目配置
└── README.md                    # 项目说明
```

## 测试

运行测试套件：

```bash
pytest tests/
```

## 贡献

欢迎贡献代码、报告问题或提出改进建议。

## 许可证

本项目采用私有许可，未经授权不得用于商业用途。
