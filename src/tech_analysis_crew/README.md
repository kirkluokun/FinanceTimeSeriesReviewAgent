python src/tech_analysis_crew/run_backend.py --input src/tech_analysis_crew/input/vlcc.csv --query "帮我复盘vlcc price"

python3 src/tech_analysis_crew/run_backend.py --input src/tech_analysis_crew/input/cu.csv --query "帮我复盘comex copper价格"


# 时间序列分析工作流

基于CrewAI Flow的时间序列数据分析工作流，用于分析时间序列数据中的价格变化原因。

## 功能特点

- 自动处理CSV格式的时间序列数据
- 使用搜索引擎查找相关新闻和信息
- 爬取网页内容并进行分析
- 生成详细的分析报告
- 支持多种LLM模型（OpenAI、Gemini、DeepSeek等）

## 目录结构

```
tech_analysis_crew/
├── config/             # 配置文件
│   ├── agent.yaml      # Agent配置
│   └── tasks.yaml      # 任务配置
├── input/              # 输入数据
│   └── vlcc.csv        # 示例数据
├── memory/             # 内存存储
├── output/             # 输出目录
├── test/               # 测试脚本
│   ├── test_flow.py    # 工作流测试
│   └── test_crew.py    # Crew测试
├── utils/              # 工具函数
│   └── dataprocess.py  # 数据处理工具
├── main.py             # 项目入口点
├── crew.py             # Crew编排与协调
└── README.md           # 说明文档
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 环境变量配置

在项目根目录创建`.env`文件，配置以下环境变量：

```
OPENAI_API_KEY=your_openai_api_key
GEMINI_API_KEY=your_gemini_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
SERPER_API_KEY=your_serper_api_key
```

## 使用方法

### 命令行运行

基本用法：

```bash
cd crewAI-agent
python -m src.tech_analysis_crew.main
```

指定输入文件和指标：

```bash
python -m src.tech_analysis_crew.main --input path/to/your/data.csv --indicator "VLCC价格指数"
```

测试模式（只处理数据不执行分析）：

```bash
python -m src.tech_analysis_crew.main test --input path/to/your/data.csv
```

生成工作流程图：

```bash
python -m src.tech_analysis_crew.main plot
```

### 在代码中使用

```python
from src.tech_analysis_crew.crew import TimeSeriesAnalysisCrew

# 创建Crew实例
crew = TimeSeriesAnalysisCrew()

# 执行完整分析
result = crew.analyze(
    input_file="path/to/your/data.csv",
    indicator_description="VLCC价格指数"
)

# 测试数据处理
test_result = crew.test(input_file="path/to/your/data.csv")

# 生成工作流程图
crew.plot()
```

## 数据格式

输入CSV文件应包含以下列：

- `start_date`: 开始日期
- `end_date`: 结束日期
- `start_price`: 开始价格
- `end_price`: 结束价格
- `low_price`: 最低价格
- `high_price`: 最高价格
- `pct_change`: 价格变化百分比
- `trend_type`: 趋势类型（up/down/consolidation）

## 开发计划

- [x] 基础框架搭建
- [x] 数据处理功能
- [x] 配置文件设计
- [x] 测试脚本编写
- [x] 项目结构优化
- [ ] 实现时间段分析子流程
- [ ] 实现网页爬取和内容分析
- [ ] 实现报告生成功能
- [ ] 添加更多测试用例
- [ ] 优化性能和稳定性

## 测试

运行测试：

```bash
cd crewAI-agent
# 测试工作流
python -m unittest src.tech_analysis_crew.test.test_flow
# 测试Crew
python -m unittest src.tech_analysis_crew.test.test_crew
```

## 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request 

# 技术分析Crew模块

## 任务状态判断问题修复

### 问题描述

在原始代码中，任务状态判断逻辑存在问题：
- 使用了`task.was_successful()`方法来判断任务是否成功完成
- 但CrewAI的Task类中实际上没有此方法
- 导致即使任务实际执行成功并有输出，系统也会认为所有任务都失败
- 从而生成错误的报告信息："所有链接爬取均超时或失败"

### 解决方案

经过分析和测试，我们采用了简单有效的解决方案：直接检查任务的`output`属性，而不依赖`was_successful()`方法。

具体修改如下：
1. 将`task.was_successful()`改为`hasattr(task, 'output') and task.output`
2. 修改了以下几处代码：
   - `_process_period`方法中的失败链接提取
   - 成功任务筛选逻辑
   - `_generate_period_report`方法中的爬取任务过滤

### 测试验证

我们创建了专门的测试脚本`test_task_output_judgment.py`来验证这一修复方案，测试包括：
- 成功任务筛选逻辑测试
- 报告生成逻辑测试
- 失败链接提取逻辑测试
- 爬虫任务过滤逻辑测试

所有测试均通过，证明这一简单的修复方案能够有效解决问题。

### 理念

这种方法符合"鸭子类型"的编程理念：
- 如果一个任务有output，那它就可以被视为成功的任务
- 不关心任务内部的状态标志，只关心它是否产生了有价值的输出

### 应用

此修复已应用到以下文件：
- `crew.py`: 修改了任务状态判断逻辑

要验证修复效果，可运行测试：
```bash
python -m unittest src/tech_analysis_crew/test/test_task_output_judgment.py
``` 