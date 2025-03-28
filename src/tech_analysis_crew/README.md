# 金融时间序列分析平台

## 系统介绍

金融时间序列分析平台是一个基于FastAPI和Python的Web应用，用于分析金融时间序列数据，生成趋势图和分析报告。系统支持上传CSV文件，自动处理数据并生成可视化结果。

## 目录结构

```
crewai-agent/src/tech_analysis_crew/
├── web/                    # Web服务器和前端文件
│   ├── server.py           # FastAPI服务器
│   ├── index.html          # 前端页面
│   ├── styles.css          # 样式文件
│   ├── script.js           # 前端脚本
│   └── requirements.txt    # 依赖包列表
├── trendanalysis/          # 趋势分析工具
│   ├── main.py             # 主分析脚本
│   ├── trend-sensitive.py  # 敏感版分析模块
│   ├── trend-insensitive.py# 不敏感版分析模块
│   ├── cache/              # 上传文件缓存目录
│   ├── results/            # 原始分析结果保存目录
│   └── static/             # 静态文件目录（生成的图片和文件）
│       ├── images/         # 生成的图片文件
│       └── files/          # 生成的CSV和报告文件
├── input/                  # 输入文件目录
├── output/                 # 输出文件目录
├── start_server.sh         # 服务器启动脚本
├── test_process_flow.py    # 处理流程测试脚本
└── README.md               # 说明文档
```

## 使用方法

### 安装依赖

```bash
cd crewai-agent/src/tech_analysis_crew
pip install -r web/requirements.txt
```

### 启动服务器

```bash
cd crewai-agent/src/tech_analysis_crew
./start_server.sh
```

服务器将在 http://localhost:8080 上运行。

### 使用Web界面

1. 打开浏览器访问 http://localhost:8080
2. 在"上传CSV数据"区域上传您的CSV文件（需要包含日期列和价格列）
3. 点击"处理CSV数据"按钮
4. 系统将自动处理数据并生成分析结果
5. 在"分析结果"区域查看生成的趋势图和分析报告

### 复盘分析

1. 在"上传已处理的分析数据"区域上传已处理的CSV文件
2. 输入分析查询内容
3. 点击"开始复盘分析"按钮
4. 在"分析日志"区域查看分析进度和结果

## 测试

运行测试脚本验证系统功能：

```bash
cd crewai-agent/src/tech_analysis_crew
python test_process_flow.py
```

## 技术架构

- 前端：HTML, CSS, JavaScript
- 后端：FastAPI, Python
- 数据分析：Pandas, Matplotlib
- 文件处理：Python标准库

## 开发与维护

- 确保服务器启动前，静态文件目录已正确创建
- 所有生成的图片保存在 `trendanalysis/static/images` 目录
- 所有生成的CSV和报告保存在 `trendanalysis/static/files` 目录
- 测试脚本可用于验证整个处理流程是否正常工作

## 常见问题

### 路径中包含空格和特殊字符的问题

如果您的项目路径中包含空格或特殊字符（如中文），可能会导致主分析脚本无法正确执行。这是因为在命令行中，包含空格和特殊字符的路径需要特殊处理。

**问题症状**：
- 上传CSV文件后，处理失败
- 错误日志显示："No such file or directory"
- 命令行尝试执行时路径被空格分割

**解决方案**：
1. 在server.py中，使用列表方式传递参数给subprocess.run，不使用shell=True：
```python
cmd = [
    sys.executable,
    main_script,
    cache_path,
    '--output-dir',
    output_path
]
result = subprocess.run(
    cmd,
    shell=False,  # 不使用shell执行命令
    capture_output=True,
    text=True,
    check=True
)
```

2. 避免使用引号包装路径，因为这可能会导致引号被视为路径的一部分

3. 如果您遇到类似问题，可以运行测试脚本验证解决方案：
```bash
python test_fix.py
```

**技术说明**：
在Python中，使用列表方式传递参数给subprocess.run时，每个参数会被单独传递给命令，不受空格影响。而使用shell=True时，命令会被传递给shell解释器，容易受到空格和特殊字符的影响。 