# 金融时间序列分析平台

这是一个用于支持时间序列数据分析和复盘的Web界面，专为金融数据分析设计。平台整合了趋势分析工具和复盘分析功能，通过直观的用户界面帮助分析师进行数据处理和分析。

## 功能特性

1. **时间序列初始化处理**
   - 上传CSV数据文件
   - 自动处理和分析时间序列数据
   - 生成敏感版和不敏感版趋势分析结果
   - 可视化分析结果并提供下载功能
   - 在线编辑CSV数据

2. **趋势复盘分析**
   - 上传已处理的CSV文件
   - 运行深度分析和复盘
   - 实时显示分析进度和日志
   - 获取详细的分析报告

## 安装说明

### 前提条件

- Python 3.8+
- pip 包管理器

### 安装步骤

1. 克隆项目仓库（如果已经克隆，请跳过此步骤）

2. 安装依赖
   ```bash
   cd crewai-agent/src/tech_analysis_crew/web
   pip install -r requirements.txt
   ```

3. 确保文件目录结构正确
   ```
   crewai-agent/
   ├── src/
   │   ├── tech_analysis_crew/
   │   │   ├── web/
   │   │   │   ├── index.html
   │   │   │   ├── styles.css
   │   │   │   ├── script.js
   │   │   │   ├── server.py
   │   │   │   ├── requirements.txt
   │   │   │   └── static/
   │   │   │       ├── images/
   │   │   │       └── files/
   │   │   ├── input/
   │   │   └── output/
   │   └── tool/
   │       └── trendanalysis/
   ```

## 使用方法

### 启动服务器

```bash
cd crewai-agent/src/tech_analysis_crew
python web/server.py
```

服务器将在 http://localhost:8080 上启动。

### 使用流程

1. **时间序列初始化处理**
   - 上传CSV文件（格式：第一列为日期，第二列为数值）
   - 点击"处理CSV数据"按钮
   - 等待处理完成后查看结果
   - 可以下载分析结果或可视化图表

2. **趋势复盘分析**
   - 上传已处理好的CSV文件（包含趋势区间划分）
   - 在"分析查询"框中输入分析目标
   - 点击"开始复盘分析"按钮
   - 在日志区域查看分析进度和结果

## 系统架构

### 前端
- 纯HTML/CSS/JavaScript实现
- 使用Bootstrap 5样式框架
- 使用AG-Grid处理CSV编辑功能

### 后端
- Flask Web服务器
- 与已有的分析脚本集成
- RESTful API接口

## 开发说明

### API接口

- `POST /api/process-csv`: 上传并处理CSV文件
- `POST /api/save-processed-csv`: 保存已处理的CSV文件到input目录
- `POST /api/run-analysis`: 运行复盘分析
- `GET /api/analysis-status/<job_id>`: 获取分析任务状态

### 文件存储

- 原始CSV文件存储在 `input/` 目录
- 分析结果存储在 `output/` 目录
- 静态文件（图像和分析文件）存储在 `web/static/` 目录

## 故障排除

- 如果遇到权限问题，请确保相关目录有正确的读写权限
- 如果无法启动服务器，请检查端口8080是否被占用
- 如果处理CSV文件失败，请确保文件格式正确（第一列为日期，第二列为数值）
- 如果下载文件失败，请检查static/images和static/files目录是否存在并有访问权限

## 许可证

本项目采用私有许可，未经授权不得用于商业用途。 