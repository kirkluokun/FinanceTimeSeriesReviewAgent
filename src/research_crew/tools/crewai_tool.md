# CrewAI 工具集总结

## 网页和搜索相关工具

### 1. Browserbase Web Loader
- 功能：加载和解析网页内容
- 特点：
  - 提供可靠的无头浏览器服务
  - 支持隐身模式和自动验证码解决
  - 包含会话调试器和实时调试功能
- 配置：需要设置 `BROWSERBASE_API_KEY` 和 `BROWSERBASE_PROJECT_ID`

- 使用场景：
  - 需要抓取动态加载的网页内容
  - 需要处理需要登录的网站
  - 需要绕过反爬虫机制的网站
  
- 调用示例：
```python
from crewai.tools import BrowserbaseWebLoader

# 初始化工具
loader = BrowserbaseWebLoader(
    api_key="your_browserbase_api_key",
    project_id="your_project_id"
)

# 基础使用
webpage_content = loader.load("https://example.com")

# 高级配置使用
webpage_content = loader.load(
    "https://example.com",
    incognito=True,  # 使用隐身模式
    wait_for_selector=".main-content",  # 等待特定元素加载
    timeout=30  # 设置超时时间
)
```

### 2. EXA Search Web Loader
- 功能：使用EXA搜索引擎进行网页搜索和加载
- 特点：
  - 支持高级搜索功能和内容提取
  - 基于嵌入的语义搜索
  - 精确的内容解析和清洗
  - 支持相似内容发现

#### 1. 搜索功能 (Search)
- 使用场景：
  - 需要进行语义相关的复杂查询
  - 需要精确的关键词匹配
  - 需要大规模网页内容检索
  - 需要自动优化搜索提示

- 基础搜索示例：
```python
from crewai.tools import EXASearchWebLoader

# 初始化搜索工具
exa_loader = EXASearchWebLoader()

# 自动搜索（默认模式）
results = exa_loader.search(
    query="AI developments 2024",
    type="auto"  # 自动选择最佳搜索类型
)

# 神经网络搜索
results = exa_loader.search(
    query="创新的气候变化解决方案",
    type="neural",  # 使用嵌入模型进行语义搜索
    num_results=5
)

# 关键词搜索
results = exa_loader.search(
    query="Python 3.12 new features",
    type="keyword",  # 精确关键词匹配
    include_domains=["python.org", "github.com"]
)

# 短语过滤搜索
results = exa_loader.search(
    query="机器学习最佳实践",
    type="neural",
    include_text="TensorFlow",  # 必须包含的关键短语
    exclude_text="legacy"  # 必须排除的内容
)
```

#### 2. 内容提取 (Contents)
- 使用场景：
  - 需要获取完整的网页内容
  - 需要清洗和结构化的文本数据
  - 需要提取特定段落或重点内容

- 内容提取示例：
```python
# 基础内容提取
content = exa_loader.get_contents(
    url="https://example.com",
    output_format="text"  # 或 "html", "markdown"
)

# 带高亮的内容提取
content = exa_loader.get_contents(
    url="https://example.com",
    highlights=True,  # 提取相关度最高的片段
    max_highlights=3
)

# 组合搜索和内容提取
results = exa_loader.search_and_contents(
    query="量子计算最新进展",
    text=True,  # 自动获取搜索结果的完整内容
    highlights=True,
    num_results=3
)
```

#### 3. 相似内容发现 (Find Similar)
- 使用场景：
  - 需要找到相关的参考资料
  - 需要发现相似主题的内容
  - 需要进行竞品分析

- 相似内容搜索示例：
```python
# 基于URL查找相似内容
similar_pages = exa_loader.find_similar(
    url="https://example.com/article",
    num_results=5,
    min_similarity=0.7
)

# 基于文本查找相似内容
similar_pages = exa_loader.find_similar_by_text(
    text="这是一段描述人工智能技术的文本...",
    domains=["research-papers", "tech-blogs"],
    exclude_domains=["social-media"]
)

# 组合使用示例
async def research_topic(topic):
    # 首先搜索主题
    results = exa_loader.search(topic, type="neural")
    
    # 获取首个结果的详细内容
    content = exa_loader.get_contents(results[0].url)
    
    # 查找相似内容
    similar = exa_loader.find_similar(results[0].url)
    
    return {
        "main_content": content,
        "related_resources": similar
    }
```

#### 4. 高级功能
- 写作续写查询：
```python
# 基于现有内容查找相关资源
current_text = """
人工智能在医疗领域的应用已经显示出巨大潜力。
从辅助诊断到药物研发，AI技术正在改变传统医疗模式。
"""
continuation_query = current_text + " Here is a great resource to continue writing this piece:"
results = exa_loader.search(continuation_query, type="neural")
```

- 长文本查询：
```python
# 使用长文本进行相似内容匹配
long_query = """
本研究探讨了量子机器学习在药物发现中的应用。
我们提出了一种新的量子-经典混合方法，利用量子退火进行特征选择，
并使用量子启发的张量网络进行模型训练...
"""
results = exa_loader.search(
    long_query,
    type="neural",
    use_autoprompt=False  # 对于长文本查询，禁用自动提示
)
```

- 自动日期处理：
```python
# 自动处理时间范围
results = exa_loader.search(
    "过去一周的AI创业公司新闻",
    use_autoprompt=True  # 自动处理日期范围
)
```

#### 5. 在Agent中的应用示例
```python
from crewai import Agent, Task

# 创建研究代理
research_agent = Agent(
    role='研究分析师',
    goal='深入研究特定主题并生成报告',
    tools=[EXASearchWebLoader()],
    verbose=True
)

# 创建研究任务
task = Task(
    description="""
    1. 搜索主题相关内容
    2. 提取关键信息
    3. 查找相似资源
    4. 生成研究报告
    """,
    agent=research_agent
)

# 执行任务
result = research_agent.execute(task)
```

[参考链接：Exa API 文档](https://docs.exa.ai/reference/getting-started)

### 3. Firecrawl 系列工具
- Firecrawl Crawl Website：完整网站爬取
- Firecrawl Scrape Website：单页面抓取
- Firecrawl Search：内容搜索
- 特点：支持复杂的爬虫任务和数据提取

#### Firecrawl Crawl Website
- 使用场景：
  - 需要完整爬取整个网站内容
  - 需要保持网站结构的爬取
  - 大规模数据采集

- 调用示例：
```python
from crewai.tools import FirecrawlCrawlWebsite

# 初始化爬虫
crawler = FirecrawlCrawlWebsite()

# 开始爬取
results = crawler.crawl(
    url="https://example.com",
    max_pages=100,
    follow_links=True,
    depth=2
)
```

#### Firecrawl Scrape Website
- 使用场景：
  - 需要精确抓取单个页面的特定内容
  - 需要处理复杂的页面结构

- 调用示例：
```python
from crewai.tools import FirecrawlScrapeWebsite

# 初始化抓取工具
scraper = FirecrawlScrapeWebsite()

# 抓取特定内容
content = scraper.scrape(
    url="https://example.com",
    selectors={
        "title": "h1",
        "content": ".main-content",
        "date": ".publish-date"
    }
)
```

#### Firecrawl Search
- 使用场景：
  - 在已爬取的内容中搜索特定信息
  - 需要对网站内容进行结构化分析

- 调用示例：
```python
from crewai.tools import FirecrawlSearch

# 初始化搜索工具
searcher = FirecrawlSearch()

# 执行搜索
results = searcher.search(
    query="specific topic",
    filters={
        "date_range": "last_week",
        "content_type": ["article", "blog"]
    }
)
```

#### 4. Firecrawl API 服务
- 使用场景：
  - 需要更强大的网站爬取能力
  - 需要处理复杂的动态网页
  - 需要高可靠性的数据采集
  - 需要结构化数据提取

- 基础配置：
```python
from crewai.tools import FirecrawlAPI
import os

# 初始化API客户端
firecrawl_api = FirecrawlAPI(
    api_key=os.getenv("FIRECRAWL_API_KEY"),
    base_url="https://api.firecrawl.dev/v1"
)
```

- 单页面抓取示例：
```python
# 基础网页抓取
response = firecrawl_api.scrape(
    url="https://example.com",
    output_format="markdown"  # 支持 markdown, html, structured_data
)

# 高级抓取配置
response = firecrawl_api.scrape(
    url="https://example.com",
    config={
        "wait_for": ".dynamic-content",  # 等待特定元素加载
        "exclude_tags": ["nav", "footer"],  # 排除特定标签
        "extract_metadata": True,  # 提取页面元数据
        "custom_headers": {  # 自定义请求头
            "User-Agent": "Custom Bot",
            "Authorization": "Bearer token"
        }
    }
)
```

- 网站爬取示例：
```python
# 提交爬取任务
crawl_job = firecrawl_api.crawl(
    url="https://example.com",
    config={
        "max_pages": 100,
        "max_depth": 3,
        "follow_patterns": ["*/blog/*", "*/docs/*"],
        "exclude_patterns": ["*/login", "*/admin"],
        "respect_robots_txt": True,
        "crawl_delay": 1.0  # 爬取延迟（秒）
    }
)

# 获取爬取结果
job_id = crawl_job["id"]
results = firecrawl_api.get_crawl_results(job_id)

# 异步爬取监控
async def monitor_crawl(job_id):
    while True:
        status = await firecrawl_api.acheck_status(job_id)
        if status["status"] == "completed":
            return await firecrawl_api.aget_results(job_id)
        await asyncio.sleep(5)
```

- 结构化数据提取：
```python
# 使用预定义schema提取数据
schema = {
    "title": "str",
    "price": "float",
    "description": "str",
    "specifications": "List[Dict]"
}

extracted_data = firecrawl_api.extract(
    url="https://example.com/product",
    schema=schema,
    config={
        "extract_tables": True,
        "extract_lists": True,
        "extract_images": False
    }
)

# 使用自然语言提示提取数据
extracted_data = firecrawl_api.extract(
    url="https://example.com/product",
    prompt="提取产品的名称、价格、主要特点和技术规格"
)
```

- 高级功能示例：
```python
# 页面交互和动态内容处理
response = firecrawl_api.scrape(
    url="https://example.com",
    actions=[
        {"type": "click", "selector": "#load-more"},
        {"type": "wait", "time": 2},
        {"type": "scroll", "amount": 1000},
        {"type": "input", "selector": "#search", "value": "query"},
        {"type": "screenshot", "selector": ".results"}
    ]
)

# 批量URL处理
urls = ["https://example1.com", "https://example2.com"]
async def batch_scrape(urls):
    tasks = []
    for url in urls:
        task = firecrawl_api.ascrape(url)
        tasks.append(task)
    return await asyncio.gather(*tasks)

# 自定义数据处理管道
class CustomProcessor:
    def process_content(self, content):
        # 自定义处理逻辑
        return processed_content

processor = CustomProcessor()
response = firecrawl_api.scrape(
    url="https://example.com",
    processors=[processor]
)
```

- 在Agent中集成使用：
```python
from crewai import Agent, Task
from crewai.tools import FirecrawlAPI

# 创建网站研究代理
research_agent = Agent(
    role='网站研究专家',
    goal='深入分析网站内容并提取关键信息',
    tools=[FirecrawlAPI()],
    verbose=True
)

# 创建研究任务
task = Task(
    description="""
    1. 爬取目标网站的所有相关页面
    2. 提取结构化数据
    3. 分析内容关联性
    4. 生成研究报告
    """,
    agent=research_agent
)

# 执行任务
result = research_agent.execute(task)
```

- 错误处理和重试机制：
```python
from crewai.tools.exceptions import FirecrawlAPIError

try:
    result = firecrawl_api.scrape(url)
except FirecrawlAPIError as e:
    if e.status_code == 429:  # 速率限制
        time.sleep(60)
        result = firecrawl_api.scrape(url)
    elif e.status_code == 403:  # 访问受限
        result = firecrawl_api.scrape(url, proxy=get_next_proxy())
    else:
        logger.error(f"爬取失败: {str(e)}")
```

- 性能优化建议：
```python
# 并发控制
semaphore = asyncio.Semaphore(5)  # 限制并发数

async def controlled_scrape(url):
    async with semaphore:
        return await firecrawl_api.ascrape(url)

# 结果缓存
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_scrape(url):
    return firecrawl_api.scrape(url)

# 批量处理优化
async def optimized_batch_process(urls):
    chunks = [urls[i:i+10] for i in range(0, len(urls), 10)]
    for chunk in chunks:
        tasks = [firecrawl_api.ascrape(url) for url in chunk]
        await asyncio.gather(*tasks)
        await asyncio.sleep(1)  # 请求间隔
```

- API 使用最佳实践：
1. 合理设置爬取参数：
```python
crawl_config = {
    "max_pages": 1000,        # 设置合理的页面限制
    "max_depth": 3,           # 控制爬取深度
    "crawl_delay": 1.0,       # 遵守网站爬取规则
    "timeout": 30,            # 设置超时时间
    "retry_count": 3,         # 失败重试次数
    "concurrent_requests": 5   # 并发请求数
}
```

2. 数据质量控制：
```python
def validate_crawl_results(results):
    valid_results = []
    for result in results:
        if len(result["content"]) > 100 and  # 内容长度检查
           "error" not in result and         # 错误检查
           result["status_code"] == 200:     # 状态码检查
            valid_results.append(result)
    return valid_results
```

3. 资源管理：
```python
async with FirecrawlAPI() as api:
    results = await api.scrape_batch(urls)
```

### 4. Google Serper Search
- 功能：通过Google Serper API进行网络搜索
- 特点：提供Google搜索结果的结构化数据
- 配置：需要 Serper API 密钥

- 使用场景：
  - 需要高质量的搜索结果
  - 需要结构化的搜索数据
  - 需要实时的网络信息获取

- 调用示例：
```python
from crewai.tools import GoogleSerperSearch

# 初始化搜索工具
search_tool = GoogleSerperSearch(api_key="your_serper_api_key")

# 基础搜索
results = search_tool.search("AI latest developments")

# 高级搜索配置
results = search_tool.search(
    query="AI developments",
    num_results=5,
    search_type="news",  # news, images, places
    tbs="qdr:d"  # 时间范围：过去24小时
)
```
# 深层次问题检索工作流 API 设计指南

## 目标
构建一个能够对输入问题进行深层次检索的系统，工作流如下：
1. **初始检索**：对原始问题进行搜索（例如使用 Google Serper API），获取结果（建议取前 3 页）。
2. **内容抓取与摘要**：针对每个检索结果，抓取全文内容并利用 AI 模型生成摘要。
3. **补充问题提取**：分析摘要内容，识别出需要补充的后续问题。
4. **迭代检索**：使用提取的新问题进行后续搜索，再次生成摘要与问题，循环迭代（最多 5 次）。
5. **结果整合与溯源**：每次搜索都记录详细的摘要、观点及其来源信息，最终针对每个问题形成综合结论。

## 系统模块与功能

### 1. 输入处理与初始搜索模块
- **功能**：接收原始问题，对输入进行预处理，并调用搜索 API 。
- **API 接口设计**：  
  ```python
  def search_web(query: str, num_pages: int = 3) -> List[dict]:
      """
      使用 Google Serper API 搜索指定问题，返回搜索结果列表。
      每个结果包含网页 URL、标题、摘要预览、时间戳等元数据。
      """
      results = []
      for page in range(1, num_pages + 1):
          page_results = google_serper_api.search(query, page=page)
          results.extend(page_results)
      return results
  ```
- **注意**：确保 API 密钥等配置信息安全存储（参考 [Google Serper API 使用指南](https://python.langchain.com/docs/integrations/tools/google_serper/)）。

### 2. 内容抓取模块
- **功能**：对搜索结果中的每个 URL 进行网页抓取，获取详细内容。
- **API 接口设计**：  
  ```python
  def fetch_page_content(url: str) -> str:
      """
      使用 Firecrawl API 或其他抓取工具，对指定 URL 进行网页内容抓取，
      返回网页的文本内容。
      """
      content = firecrawl_api.scrape(url, output_format="text")
      return content
  ```
- **注意**：可以支持异步抓取，以提高检索效率。

### 3. 摘要生成模块
- **功能**：利用 AI 模型对抓取到的网页内容生成摘要。
- **API 接口设计**：  
  ```python
  def summarize_content(content: str) -> str:
      """
      使用 AI 模型（例如 GPT 模型）对网页全文内容生成摘要，
      返回文本摘要。
      """
      summary = ai_model.summarize(content)
      return summary
  ```
- **注意**：可为不同模块定义摘要粒度和摘要长度的参数。

### 4. 补充问题提取模块
- **功能**：从已生成的摘要中提取需要补充的新问题。
- **API 接口设计**：  
  ```python
  def extract_followup_questions(summary: str) -> List[str]:
      """
      分析输入摘要，利用自然语言生成模型生成后续需要补充的问题列表。
      """
      questions = ai_model.generate_questions(prompt=summary)
      return questions
  ```
- **注意**：此处可以采用上下文敏感的模型，使提取结果更为准确。

### 5. 迭代检索与聚合控制模块
- **功能**：对初始问题及后续生成的补充问题进行多轮检索和摘要，直至达到最大迭代次数（例如 5 次）或无新增问题。
- **API 接口设计**：  
  ```python
  def iterative_deep_search(initial_query: str, max_iterations: int = 5) -> dict:
      """
      主协调函数：
      - 第一次检索：使用原始问题获取结果，抓取内容、生成摘要。
      - 从摘要中提取补充问题。
      - 对补充问题重复上述过程，循环至最大迭代次数。
      - 每轮均记录详细的摘要与来源信息。
      - 返回聚合后的最终结论及所有来源记录。
      """
      aggregated_results = {
          "iterations": [],
          "final_conclusions": {},
      }
      queries = [initial_query]

      for iteration in range(max_iterations):
          iteration_data = {"queries": [], "summaries": [], "followup_questions": []}
          print(f"Iteration {iteration + 1}")
          current_queries = queries
          queries = []  # 清空，准备收集新问题

          for query in current_queries:
              iteration_data["queries"].append(query)
              search_results = search_web(query)
              for result in search_results:
                  url = result.get("url")
                  content = fetch_page_content(url)
                  summary = summarize_content(content)
                  iteration_data["summaries"].append({
                      "query": query,
                      "url": url,
                      "summary": summary,
                      "source_metadata": result
                  })
                  # 从摘要中提取潜在的补充问题
                  new_questions = extract_followup_questions(summary)
                  iteration_data["followup_questions"].extend(new_questions)

          aggregated_results["iterations"].append(iteration_data)
          # 如果没有生成新问题，则可提前停止迭代
          if not iteration_data["followup_questions"]:
              break
          queries = list(set(iteration_data["followup_questions"]))  # 去重

      # 整合最终结论
      final_conclusions = aggregate_conclusions(aggregated_results)
      aggregated_results["final_conclusions"] = final_conclusions
      return aggregated_results

  def aggregate_conclusions(aggregated_data: dict) -> dict:
      """
      对每一轮的摘要进行整合，形成最终答案。
      可采用简单合并或调用 AI 模型进一步总结归纳。
      """
      conclusions = {}
      for iteration in aggregated_data["iterations"]:
          for summary_item in iteration["summaries"]:
              key = summary_item["query"]
              if key not in conclusions:
                  conclusions[key] = []
              conclusions[key].append(summary_item["summary"])
      # 例如对每个问题使用 AI 模型进一步归纳形成最终结论
      final = {q: ai_model.summarize(" ".join(summaries)) for q, summaries in conclusions.items()}
      return final
  ```
- **注意**：整个迭代过程中，务必保存每个信息点对应的来源（如 URL、搜索元数据等），方便后续引用和结果审计。

### 6. 日志与溯源管理
- **功能**：记录每个步骤的详情，包括原始查询、抓取结果、摘要、生成的问题及对应的来源。
- **数据结构示例**：
  ```python
  {
      "iterations": [
          {
              "queries": ["原始问题"],
              "summaries": [{
                  "query": "原始问题",
                  "url": "https://example.com",
                  "summary": "网页摘要内容",
                  "source_metadata": { ... }
              }],
              "followup_questions": ["补充问题1", "补充问题2"]
          },
          ...
      ],
      "final_conclusions": {
           "原始问题": "综合结论文本"
      }
  }
  ```

## 最佳实践
1. **异步处理**：对网络请求和内容抓取均采用异步（如 `asyncio`）技术，实现更高效的处理。
2. **缓存策略**：对结果进行本地缓存，避免重复请求相同内容。
3. **错误重试**：实现健壮的错误处理和重试机制，以应对网络或解析失败情况。
4. **详细日志**：记录所有操作的详细日志，便于后续数据溯源和问题排查。
5. **安全性**：确保 API 密钥及用户数据安全存储，不在日志中泄露敏感信息。

## 参考链接
- [Google Serper API 使用指南](https://python.langchain.com/docs/integrations/tools/google_serper/)
- [Firecrawl API 文档](https://docs.firecrawl.dev/introduction)

以上就是在工具 API 层面实现深层次问题检索工作流的设计指南。通过各模块协同工作，可以实现对原始问题的多轮深入检索、摘要生成、后续问题拓展以及综合结论输出，同时始终记录每个信息点的来源，确保结果的透明性与可追踪性。 




### 5. 网页抓取工具
#### Scrape Website
- 使用场景：
  - 基础的网页内容抓取
  - 静态网页内容提取
  - 简单的数据采集任务

- 调用示例：
```python
from crewai.tools import ScrapeWebsite

# 初始化抓取工具
scraper = ScrapeWebsite()

# 基础抓取
content = scraper.scrape("https://example.com")

# 配置抓取选项
content = scraper.scrape(
    url="https://example.com",
    elements={
        "title": "h1",
        "content": "article",
        "date": ".published-date"
    }
)
```

#### Selenium Scraper
- 使用场景：
  - 需要处理JavaScript渲染的页面
  - 需要模拟用户交互
  - 需要处理动态加载内容

- 调用示例：
```python
from crewai.tools import SeleniumScraper

# 初始化Selenium抓取工具
scraper = SeleniumScraper()

# 配置抓取选项
content = scraper.scrape(
    url="https://example.com",
    wait_for=".dynamic-content",  # 等待元素加载
    scroll=True,  # 自动滚动页面
    actions=[  # 定义交互操作
        {"type": "click", "selector": ".load-more"},
        {"type": "wait", "time": 2},
    ]
)
```

#### Spider Scraper
- 使用场景：
  - 需要递归爬取网站
  - 需要遵循特定的链接模式
  - 大规模数据采集

- 调用示例：
```python
from crewai.tools import SpiderScraper

# 初始化爬虫工具 
spider = SpiderScraper()

# 配置爬虫规则
results = spider.crawl(
    start_url="https://example.com",
    patterns=["category/*", "product/*"],
    max_pages=100,
    extract_rules={
        "title": "h1",
        "price": ".product-price",
        "description": ".product-desc"
    }
)
```

### 6. ScrapeElementFromWebsiteTool
- 使用场景：
  - 需要精确提取特定网页元素
  - 需要处理复杂的DOM结构
  - 需要提取动态更新的内容

- 调用示例：
```python
from crewai.tools import ScrapeElementFromWebsiteTool

# 初始化元素抓取工具
element_scraper = ScrapeElementFromWebsiteTool()

# 使用CSS选择器提取
element = element_scraper.scrape(
    url="https://example.com",
    selector=".specific-element"
)

# 使用XPath提取
element = element_scraper.scrape(
    url="https://example.com",
    xpath="//div[@class='specific-element']",
    wait_for_xpath=True
)

# 高级配置
element = element_scraper.scrape(
    url="https://example.com",
    selector=".dynamic-content",
    wait_time=5,  # 等待时间
    attributes=["text", "href", "data-id"],  # 提取特定属性
    multiple=True  # 提取多个匹配元素
)
```

### 7. RagTool
- 使用场景：
  - 需要智能文档检索
  - 需要上下文感知的搜索
  - 需要处理大规模文档集合

- 调用示例：
```python
from crewai.tools import RagTool

# 初始化RAG工具
rag_tool = RagTool()

# 添加文档到知识库
rag_tool.add_documents([
    "document1.pdf",
    "document2.txt",
    "document3.docx"
])

# 执行语义搜索
results = rag_tool.search(
    query="查找关于AI发展的内容",
    top_k=5,  # 返回前5个最相关结果
    threshold=0.7  # 相似度阈值
)

# 获取上下文增强的回答
answer = rag_tool.query(
    question="AI在医疗领域的应用是什么？",
    context_window=3  # 使用3个相关文档作为上下文
)
```

#### 文本预处理功能
- 使用场景：
  - 需要对文档进行清洗和标准化
  - 需要自定义文本分块策略
  - 需要优化向量化效果

- 预处理示例：
```python
from crewai.tools import RagTool
from crewai.tools.rag.processors import TextProcessor, ChunkingStrategy

# 初始化RAG工具
rag_tool = RagTool()

# 自定义文本处理器
class CustomTextProcessor(TextProcessor):
    def clean_text(self, text: str) -> str:
        # 自定义清洗逻辑
        text = text.replace('\n\n', ' ')
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

# 配置预处理选项
rag_tool.configure(
    text_processor=CustomTextProcessor(),
    chunking_strategy=ChunkingStrategy(
        chunk_size=500,  # 每个块的最大字符数
        chunk_overlap=50,  # 块之间的重叠字符数
        separator='\n'    # 分块分隔符
    )
)

# 添加文档时应用预处理
rag_tool.add_documents(
    documents=["document1.pdf", "document2.txt"],
    preprocessing_config={
        "remove_headers": True,      # 移除页眉页脚
        "remove_empty_lines": True,  # 移除空行
        "normalize_whitespace": True,# 标准化空白字符
        "remove_urls": True,         # 移除URL
        "language": "zh"            # 指定文档语言
    }
)

# 自定义分块处理
rag_tool.process_chunks(
    chunk_processor=lambda chunk: {
        "text": chunk,
        "metadata": {
            "length": len(chunk),
            "keywords": extract_keywords(chunk)
        }
    }
)

# 向量化配置
rag_tool.configure_embedding(
    model="text-embedding-3-small",  # 指定嵌入模型
    batch_size=32,                  # 批处理大小
    dimensions=1536                 # 向量维度
)

# 高级搜索示例
results = rag_tool.search(
    query="AI医疗应用",
    preprocessing={
        "remove_stopwords": True,    # 移除停用词
        "apply_stemming": True,      # 应用词干提取
        "expand_synonyms": True      # 同义词扩展
    },
    filters={
        "date_range": ["2023-01-01", "2024-12-31"],
        "document_type": ["research", "case_study"],
        "confidence_score": 0.7
    }
)

# 批量处理文档
async def process_documents(file_paths):
    tasks = []
    for file_path in file_paths:
        task = asyncio.create_task(
            rag_tool.aprocess_document(
                file_path,
                preprocessing_config={
                    "custom_cleaner": custom_clean_function,
                    "chunk_size": 1000,
                    "overlap": 100
                }
            )
        )
        tasks.append(task)
    return await asyncio.gather(*tasks)

# 保存和加载处理后的文档
rag_tool.save_processed_documents(
    output_dir="processed_docs/",
    format="jsonl",           # 输出格式
    include_metadata=True     # 包含元数据
)

# 加载预处理后的文档
rag_tool.load_processed_documents(
    input_dir="processed_docs/",
    validate_schema=True      # 验证文档格式
)
```

#### 预处理最佳实践

1. 文本清洗：
```python
def clean_text(text: str) -> str:
    # 移除特殊字符
    text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', text)
    
    # 标准化空白字符
    text = ' '.join(text.split())
    
    # 移除HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    
    return text
```

2. 智能分块：
```python
def smart_chunk(text: str, max_chunk_size: int = 500) -> List[str]:
    # 按句子分割
    sentences = re.split(r'[。！？]', text)
    
    chunks = []
    current_chunk = []
    current_size = 0
    
    for sentence in sentences:
        sentence_size = len(sentence)
        if current_size + sentence_size > max_chunk_size:
            # 当前块已满，保存并开始新块
            chunks.append(''.join(current_chunk))
            current_chunk = [sentence]
            current_size = sentence_size
        else:
            # 添加到当前块
            current_chunk.append(sentence)
            current_size += sentence_size
    
    # 添加最后一个块
    if current_chunk:
        chunks.append(''.join(current_chunk))
    
    return chunks
```

3. 元数据提取：
```python
def extract_metadata(text: str) -> Dict:
    return {
        "length": len(text),
        "language": detect_language(text),
        "keywords": extract_keywords(text),
        "created_at": datetime.now().isoformat(),
        "summary": generate_summary(text)
    }
```

4. 质量控制：
```python
def validate_chunk(chunk: str) -> bool:
    # 检查块的质量
    if len(chunk) < 50:  # 太短的块
        return False
    if len(re.findall(r'\w+', chunk)) < 10:  # 实际词数太少
        return False
    if len(chunk) > 1000:  # 块太大
        return False
    return True
```

### 8. LlamaIndexTool
- 功能：集成LlamaIndex功能
- 特点：
  - 高效数据索引
  - 支持复杂查询
  - 文档结构保持
  - 多模态数据处理

- 使用场景：
  - 需要处理大规模文档集合
  - 需要构建知识图谱
  - 需要处理多种数据源
  - 需要高级查询功能

- 基础使用示例：
```python
from crewai.tools import LlamaIndexTool
from llama_index import SimpleDirectoryReader, VectorStoreIndex

# 初始化工具
llama_tool = LlamaIndexTool()

# 加载文档
documents = SimpleDirectoryReader('data/').load_data()
index = VectorStoreIndex.from_documents(documents)

# 配置工具
llama_tool.configure(
    index=index,
    response_mode="tree_summarize",  # 使用树状结构总结
    verbose=True
)

# 执行查询
response = llama_tool.query("什么是机器学习？")
```

- 高级使用示例：
```python
from llama_index import (
    VectorStoreIndex,
    ServiceContext,
    StorageContext,
    load_index_from_storage
)
from llama_index.node_parser import SimpleNodeParser
from llama_index.embeddings import OpenAIEmbedding

# 自定义索引配置
service_context = ServiceContext.from_defaults(
    embed_model=OpenAIEmbedding(),
    chunk_size=512,
    chunk_overlap=20
)

# 创建存储上下文
storage_context = StorageContext.from_defaults()

# 配置节点解析器
parser = SimpleNodeParser.from_defaults(
    chunk_size=512,
    chunk_overlap=20
)

# 创建和保存索引
index = VectorStoreIndex(
    nodes=parser.get_nodes_from_documents(documents),
    service_context=service_context,
    storage_context=storage_context
)

# 保存索引
index.storage_context.persist("index_storage")

# 加载已存在的索引
loaded_index = load_index_from_storage(
    StorageContext.from_defaults(persist_dir="index_storage")
)

# 配置查询引擎
query_engine = loaded_index.as_query_engine(
    similarity_top_k=5,  # 返回最相似的5个结果
    response_mode="tree_summarize"
)

# 在工具中使用自定义索引
llama_tool.configure(
    index=loaded_index,
    query_engine=query_engine
)
```

- 多数据源集成示例：
```python
from llama_index.readers import (
    PDFReader,
    DocxReader,
    JSONReader,
    WikipediaReader
)

# 配置多种数据源读取器
readers = {
    "pdf": PDFReader(),
    "docx": DocxReader(),
    "json": JSONReader(),
    "wiki": WikipediaReader()
}

# 加载不同类型的文档
documents = []
documents.extend(readers["pdf"].load_data("docs/paper.pdf"))
documents.extend(readers["docx"].load_data("docs/report.docx"))
documents.extend(readers["json"].load_data("docs/data.json"))
documents.extend(readers["wiki"].load_data(pages=["Machine Learning"]))

# 创建混合索引
hybrid_index = VectorStoreIndex.from_documents(
    documents,
    service_context=service_context
)

# 配置工具使用混合索引
llama_tool.configure(index=hybrid_index)
```

- 知识图谱构建示例：
```python
from llama_index.indices.knowledge_graph import KnowledgeGraphIndex
from llama_index.graph_stores import NetworkxGraphStore

# 创建图存储
graph_store = NetworkxGraphStore()

# 构建知识图谱索引
kg_index = KnowledgeGraphIndex.from_documents(
    documents,
    graph_store=graph_store,
    max_triplets_per_chunk=10
)

# 使用知识图谱进行查询
kg_query_engine = kg_index.as_query_engine(
    response_mode="tree_summarize",
    verbose=True
)

# 在工具中使用知识图谱
llama_tool.configure(
    index=kg_index,
    query_engine=kg_query_engine
)
```

- 查询优化示例：
```python
# 配置高级查询选项
response = llama_tool.query(
    "深度学习的应用场景有哪些？",
    response_mode="tree_summarize",
    similarity_top_k=3,
    max_tokens=500,
    temperature=0.7,
    filters={
        "date_range": ["2023-01-01", "2024-12-31"],
        "source_type": ["academic", "research"],
        "confidence_score": 0.8
    }
)

# 获取查询的相关上下文
context = llama_tool.get_context(
    query="深度学习",
    num_chunks=5
)

# 获取相似文档
similar_docs = llama_tool.get_similar_documents(
    text="机器学习算法",
    top_k=3
)
```

- 性能优化建议：
1. 索引优化：
```python
# 使用压缩索引减少内存使用
from llama_index.indices.vector_store import CompressedVectorStoreIndex

compressed_index = CompressedVectorStoreIndex.from_documents(
    documents,
    compression_ratio=0.1  # 压缩比例
)
```

2. 批量处理：
```python
# 批量添加文档
async def load_documents(file_paths):
    tasks = []
    for path in file_paths:
        task = asyncio.create_task(
            llama_tool.aload_document(path)
        )
        tasks.append(task)
    return await asyncio.gather(*tasks)

# 使用缓存加速重复查询
rag_tool.configure(
    cache_dir=".cache",
    cache_index=True,
    cache_embeddings=True
)
```

2. 内存管理：
```python
# 使用流式处理处理大文件
def process_large_file(file_path):
    with rag_tool.stream_load(file_path) as stream:
        for chunk in stream:
            process_chunk(chunk)
```

3. 查询优化：
```python
# 使用批处理优化多查询
results = rag_tool.batch_search(
    queries=["查询1", "查询2", "查询3"],
    batch_size=3,
    parallel=True
)
```

## 文件处理工具

### 1. RAG搜索系列
所有RAG工具支持以下特性：
- 文本分块和向量化
- 相似度搜索
- 上下文感知检索

#### 基础使用示例
```python
from crewai.tools import (
    CSVRAGSearch,
    DOCXRAGSearch,
    JSONRAGSearch,
    PDFRAGSearch
)

# 初始化工具
csv_search = CSVRAGSearch()
docx_search = DOCXRAGSearch()
json_search = JSONRAGSearch()
pdf_search = PDFRAGSearch()

# 加载文档
csv_search.load("data.csv")
docx_search.load("document.docx")
json_search.load("data.json")
pdf_search.load("document.pdf")

# 执行搜索
results = csv_search.search("销售数据", top_k=5)
```

#### 高级配置示例
```python
# 配置向量化参数
search_tool = PDFRAGSearch(
    embedding_model="text-embedding-3-small",
    chunk_size=500,
    chunk_overlap=50,
    similarity_threshold=0.7
)

# 自定义预处理
search_tool.configure(
    preprocessing={
        "remove_headers": True,
        "remove_footers": True,
        "normalize_text": True
    }
)

# 添加元数据
search_tool.add_document(
    "document.pdf",
    metadata={
        "author": "张三",
        "date": "2024-03-20",
        "category": "技术文档"
    }
)
```

#### 文件格式特定功能

1. CSV RAG Search：
```python
from crewai.tools import CSVRAGSearch

# 初始化CSV搜索工具
csv_tool = CSVRAGSearch()

# 加载并配置
csv_tool.load(
    "sales_data.csv",
    column_config={
        "text_columns": ["description", "comments"],
        "metadata_columns": ["date", "category"],
        "ignore_columns": ["id"]
    }
)

# 高级搜索
results = csv_tool.search(
    query="高价值客户",
    filters={
        "date": ["2024-01-01", "2024-12-31"],
        "category": "VIP"
    },
    aggregation="sum"  # 支持数值列聚合
)
```

2. DOCX RAG Search：
```python
from crewai.tools import DOCXRAGSearch

# 初始化Word文档搜索工具
docx_tool = DOCXRAGSearch()

# 加载并配置
docx_tool.load(
    "report.docx",
    extract_images=True,  # 提取图片
    parse_tables=True,   # 解析表格
    keep_formatting=True # 保留格式信息
)

# 结构化搜索
results = docx_tool.search(
    query="项目进展",
    sections=["摘要", "结论"],  # 限定搜索范围
    include_tables=True,       # 包含表格内容
    include_images=False       # 排除图片描述
)
```

3. JSON RAG Search：
```python
from crewai.tools import JSONRAGSearch

# 初始化JSON搜索工具
json_tool = JSONRAGSearch()

# 加载并配置
json_tool.load(
    "api_data.json",
    path_config={
        "text_paths": ["$.description", "$.comments"],
        "metadata_paths": ["$.metadata", "$.tags"],
        "flatten": True  # 扁平化嵌套结构
    }
)

# 高级查询
results = json_tool.search(
    query="API错误",
    json_path="$.errors[*]",  # 使用JSONPath查询
    filter_expression="status >= 400"
)
```

4. PDF RAG Search：
```python
from crewai.tools import PDFRAGSearch

# 初始化PDF搜索工具
pdf_tool = PDFRAGSearch()

# 加载并配置
pdf_tool.load(
    "technical_doc.pdf",
    ocr=True,             # 启用OCR
    extract_tables=True,  # 提取表格
    extract_images=True   # 提取图片
)

# 高级搜索
results = pdf_tool.search(
    query="技术架构",
    page_range=[10, 20],     # 限定页面范围
    include_tables=True,     # 包含表格内容
    min_confidence=0.8,      # OCR置信度阈值
    context_window=2         # 上下文窗口大小
)
```

#### 批量处理示例
```python
from crewai.tools import RAGToolchain

# 创建工具链
rag_chain = RAGToolchain([
    CSVRAGSearch(),
    DOCXRAGSearch(),
    PDFRAGSearch()
])

# 批量加载文档
rag_chain.load_documents({
    "sales": "sales_2024.csv",
    "report": "annual_report.docx",
    "specs": "technical_specs.pdf"
})

# 跨文档搜索
results = rag_chain.search(
    query="2024年销售业绩",
    sources=["sales", "report"],
    combine_method="merge"
)
```

#### 在Agent中使用RAG工具
```python
from crewai import Agent
from crewai.tools import PDFRAGSearch, DOCXRAGSearch

# 创建文档分析代理
doc_agent = Agent(
    role='文档分析师',
    goal='分析技术文档并提取关键信息',
    tools=[PDFRAGSearch(), DOCXRAGSearch()],
    verbose=True
)

# 创建任务
task = Task(
    description="分析技术文档中的系统架构部分",
    agent=doc_agent
)

# 执行任务
result = doc_agent.execute("""
1. 加载技术文档
2. 搜索系统架构相关内容
3. 提取关键组件信息
4. 生成架构总结报告
""")
```

#### 性能优化建议

1. 索引优化：
```python
# 使用异步加载提高性能
async def load_documents(file_paths):
    tasks = []
    for path in file_paths:
        task = asyncio.create_task(
            rag_tool.aload_document(path)
        )
        tasks.append(task)
    return await asyncio.gather(*tasks)

# 使用缓存加速重复查询
rag_tool.configure(
    cache_dir=".cache",
    cache_index=True,
    cache_embeddings=True
)
```

2. 内存管理：
```python
# 使用流式处理处理大文件
def process_large_file(file_path):
    with rag_tool.stream_load(file_path) as stream:
        for chunk in stream:
            process_chunk(chunk)
```

3. 查询优化：
```python
# 使用批处理优化多查询
results = rag_tool.batch_search(
    queries=["查询1", "查询2", "查询3"],
    batch_size=3,
    parallel=True
)
```

## 数据库工具

### 1. MySQL RAG Search
- 功能：MySQL数据库内容检索
- 特点：
  - 支持复杂SQL查询
  - 结果向量化搜索
  - 自动连接池管理

- 使用场景：
  - 需要对大规模结构化数据进行语义搜索
  - 需要结合SQL和向量检索的混合查询
  - 需要对历史数据进行智能分析

- 基础使用示例：
```python
from crewai.tools import MySQLRAGSearch
import os

# 初始化搜索工具
mysql_search = MySQLRAGSearch(
    host=os.getenv("MYSQL_HOST"),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DATABASE")
)

# 基础搜索
results = mysql_search.search(
    query="查找最近一个月的高价值订单",
    table="orders",
    columns=["order_id", "customer_name", "total_amount"]
)

# 高级配置搜索
results = mysql_search.search(
    query="查找购买过电子产品的VIP客户",
    config={
        "tables": ["orders", "customers", "products"],
        "joins": [
            ("orders.customer_id", "customers.id"),
            ("orders.product_id", "products.id")
        ],
        "filters": {
            "products.category": "electronics",
            "customers.vip_status": True
        },
        "vector_search": True,  # 启用向量搜索
        "top_k": 10,           # 返回前10个最相关结果
        "min_similarity": 0.7   # 最小相似度阈值
    }
)
```

- 高级功能示例：
```python
# 自定义向量化配置
mysql_search.configure_embedding(
    model="text-embedding-3-small",
    dimension=1536,
    pooling_method="mean"
)

# 混合查询（SQL + 向量搜索）
results = mysql_search.hybrid_search(
    text_query="客户反馈很好的产品",
    sql_conditions="price > 1000 AND stock > 0",
    table="products",
    weight_text=0.7,    # 文本搜索权重
    weight_sql=0.3      # SQL条件权重
)

# 批量处理
async def process_queries(queries):
    tasks = []
    for query in queries:
        task = mysql_search.asearch(query)
        tasks.append(task)
    return await asyncio.gather(*tasks)
```

### 2. PG RAG Search
- 功能：PostgreSQL数据库检索
- 特点：
  - 支持全文搜索
  - JSON数据类型支持
  - 高级查询优化

- 使用场景：
  - 需要处理复杂的非结构化数据
  - 需要对JSON/JSONB数据进行搜索
  - 需要高性能的全文搜索

- 基础使用示例：
```python
from crewai.tools import PGRAGSearch

# 初始化工具
pg_search = PGRAGSearch(
    connection_string="postgresql://user:pass@host:port/db"
)

# 基础全文搜索
results = pg_search.search(
    query="技术文档",
    table="documents",
    text_columns=["title", "content"]
)

# JSON数据搜索
results = pg_search.search(
    query="用户偏好",
    table="user_data",
    json_columns=["preferences", "settings"],
    json_path="$.preferences.theme"
)
```

- 高级功能示例：
```python
# 配置全文搜索
pg_search.configure_fts(
    language="chinese",
    weights={
        "title": "A",
        "content": "B",
        "tags": "C"
    }
)

# 向量相似度搜索
results = pg_search.vector_search(
    query="创新产品设计",
    table="products",
    vector_column="description_embedding",
    metadata_columns=["name", "category", "price"]
)

# 混合查询
results = pg_search.hybrid_search(
    text_query="环保材料",
    vector_query="可持续发展",
    table="materials",
    condition="price_per_unit < 1000"
)
```

### 3. NL2SQL Tool
- 功能：自然语言转SQL
- 特点：
  - 支持多种数据库方言
  - 上下文理解
  - SQL优化建议

- 使用场景：
  - 需要将自然语言转换为SQL查询
  - 需要优化复杂SQL查询
  - 需要数据库查询的自然语言接口

- 基础使用示例：
```python
from crewai.tools import NL2SQLTool

# 初始化工具
nl2sql = NL2SQLTool(
    dialect="mysql",  # 或 "postgresql"
    schema_path="path/to/schema.json"
)

# 基础转换
sql = nl2sql.convert(
    "显示最近30天销售额最高的5个产品"
)

# 带上下文的转换
sql = nl2sql.convert(
    query="显示他们的购买历史",
    context="我们正在分析VIP客户",
    tables=["orders", "customers"]
)
```

- 高级功能示例：
```python
# 配置模型参数
nl2sql.configure(
    model="gpt-4",
    temperature=0.3,
    max_tokens=500
)

# 生成优化建议
optimization = nl2sql.get_optimization_suggestions(
    sql="SELECT * FROM orders WHERE date > '2024-01-01'"
)

# 批量处理
results = nl2sql.batch_convert(
    queries=[
        "查找活跃用户",
        "统计月度收入",
        "分析产品退货率"
    ],
    context="业务分析报告"
)

# 交互式SQL生成
async def interactive_sql_generation():
    while True:
        query = await get_user_input()
        sql = nl2sql.convert(query)
        feedback = await get_user_feedback()
        if feedback == "satisfied":
            break
        nl2sql.learn_from_feedback(query, sql, feedback)
```

### 数据库工具最佳实践

1. 连接池管理：
```python
# 配置连接池
tool.configure_pool(
    max_connections=10,
    min_connections=2,
    timeout=30
)
```

2. 错误处理：
```python
try:
    results = db_tool.search(query)
except DBConnectionError:
    # 重试连接
    await db_tool.reconnect()
except QueryTimeoutError:
    # 优化查询
    results = await db_tool.search(query, timeout=60)
```

3. 性能监控：
```python
# 启用查询性能监控
with db_tool.monitor_performance() as monitor:
    results = db_tool.search(query)
    metrics = monitor.get_metrics()
```

4. 缓存策略：
```python
# 配置查询缓存
db_tool.configure_cache(
    cache_type="redis",
    ttl=3600,  # 缓存1小时
    max_size=1000  # 最多缓存1000条查询
)
```

5. 安全性考虑：
```python
# 配置安全选项
db_tool.configure_security(
    ssl_required=True,
    encrypt_results=True,
    audit_queries=True
)
```

这些数据库工具可以结合使用，例如：
```python
from crewai import Agent, Task
from crewai.tools import MySQLRAGSearch, NL2SQLTool

# 创建数据分析代理
analyst_agent = Agent(
    role='数据分析师',
    goal='分析业务数据并生成报告',
    tools=[MySQLRAGSearch(), NL2SQLTool()]
)

# 创建分析任务
task = Task(
    description="分析过去一个季度的销售趋势",
    agent=analyst_agent
)

# 执行任务
result = analyst_agent.execute(task)
```

## 多媒体工具

### 1. DALL-E Tool
- 功能：AI图像生成
- 特点：
  - 支持多种图像风格
  - 自定义图像大小
  - 批量生成功能

### 2. Vision Tool
- 功能：图像分析和处理
- 特点：
  - 物体识别
  - 场景理解
  - OCR文字提取
  - 图像描述生成

### 3. YouTube工具
- YouTube Channel RAG Search：
  - 频道数据完整索引
  - 评论数据分析
  - 订阅者统计
  - 频道增长趋势分析
- YouTube Video RAG Search：
  - 视频内容深度分析
  - 字幕多语言支持
  - 视觉内容识别
  - 观众互动数据分析

## 开发工具

### 1. Github Search
- 功能：GitHub仓库搜索
- 特点：
  - 代码搜索
  - Issue追踪
  - 仓库分析
  - README解析

### 2. Code Interpreter
- 功能：代码解释和执行
- 特点：
  - 多语言支持
  - 安全沙箱环境
  - 交互式执行

### 3. Code Docs RAG Search
- 功能：技术文档搜索
- 特点：
  - API文档索引
  - 代码示例检索
  - 多语言文档支持

### 4. 网站分析工具
- Firecrawl系列：
  - Crawl Website：
    - 完整站点映射
    - 自动处理重定向
    - 并发爬取控制
  - Scrape Website：
    - 智能内容提取
    - 反爬虫绕过
    - 数据清洗
  - Search：
    - 全文检索
    - 相关性排序
    - 结果过滤

## 工具集成和扩展

### 1. 自定义工具开发
```python
from crewai.tools import BaseTool

class CustomTool(BaseTool):
    name = "自定义工具名称"
    description = "工具描述"
    
    def _run(self, input_data: str) -> str:
        # 实现工具逻辑
        return "处理结果"
```

### 2. 工具链组合
```python
from crewai.tools import ComposioTool

# 创建工具链
tool_chain = ComposioTool(
    tools=[tool1, tool2, tool3],
    chain_type="sequential"
)
```

## 工具使用最佳实践

### 1. 性能优化
- 使用适当的缓存策略
- 实现并发处理
- 优化资源使用

### 2. 错误处理
```python
try:
    result = tool.run(input_data)
except ToolException as e:
    # 实现错误处理逻辑
    fallback_result = handle_error(e)
```

### 3. 监控和日志
```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def tool_with_logging(input_data):
    logger.info(f"Processing input: {input_data}")
    result = tool.run(input_data)
    logger.info(f"Result: {result}")
    return result
```

## 完整工具使用示例

```python
from crewai import Agent
from crewai.tools import (
    SerperDevTool,
    WebsiteRAGTool,
    BrowserbaseLoadTool,
    DallETool,
    YoutubeChannelSearchTool,
    FileReadTool,
    ComposioTool
)

# 工具配置
search_tool = SerperDevTool(api_key="your-api-key")
website_tool = WebsiteRAGTool()
browser_tool = BrowserbaseLoadTool()
youtube_tool = YoutubeChannelSearchTool()
file_tool = FileReadTool()

# 创建工具链
tool_chain = ComposioTool(
    tools=[search_tool, website_tool, youtube_tool],
    chain_type="parallel"
)

# 在Agent中使用工具
agent = Agent(
    role='研究分析师',
    goal='全面研究特定主题并生成多媒体报告',
    tools=[tool_chain, browser_tool, file_tool],
    verbose=True
)

# 执行复杂任务
result = agent.execute("""
1. 搜索相关信息
2. 分析网页内容
3. 查找相关视频
4. 生成综合报告
""")
```

## 注意事项

1. 工具使用前的依赖安装：
```bash
pip install 'crewai[tools]'
# 特定工具可能需要额外依赖
pip install 'crewai[youtube]'  # YouTube工具
pip install 'crewai[selenium]' # Selenium相关工具
```

2. 环境变量配置：
```bash
export BROWSERBASE_API_KEY="your-key"
export SERPER_API_KEY="your-key"
export OPENAI_API_KEY="your-key"
```

3. 系统要求：
- Python 3.8+
- 足够的系统内存（建议8GB+）
- 特定工具可能需要额外的系统组件（如Chrome驱动）

4. 安全考虑：
- API密钥安全存储
- 访问权限控制
- 数据隐私保护

5. 性能优化建议：
- 合理使用缓存
- 实现并发处理
- 优化资源使用
- 监控工具性能

### 工具组合使用示例
```python
from crewai import Agent, Task, Crew
from crewai.tools import (
    BrowserbaseWebLoader,
    FirecrawlCrawlWebsite,
    FirecrawlSearch
)

# 创建研究代理
research_agent = Agent(
    role='网络研究员',
    goal='收集和分析网络内容',
    tools=[BrowserbaseWebLoader(), FirecrawlCrawlWebsite()]
)

# 创建分析代理
analysis_agent = Agent(
    role='内容分析师',
    goal='分析和总结收集的信息',
    tools=[FirecrawlSearch()]
)

# 创建任务
task1 = Task(
    description="爬取目标网站的所有相关内容",
    agent=research_agent
)

task2 = Task(
    description="分析和总结收集到的信息",
    agent=analysis_agent
)

# 创建和执行Crew
crew = Crew(
    agents=[research_agent, analysis_agent],
    tasks=[task1, task2]
)

result = crew.kickoff()
```

### 工具使用注意事项
1. 性能优化：
```python
# 使用异步方式处理大量请求
async def process_urls(urls):
    tasks = []
    for url in urls:
        task = asyncio.create_task(loader.aload(url))
        tasks.append(task)
    return await asyncio.gather(*tasks)
```

2. 错误处理：
```python
from crewai.exceptions import ToolException

try:
    result = loader.load(url)
except ToolException as e:
    logger.error(f"加载失败: {str(e)}")
    # 实现重试逻辑
    result = retry_load(url)
```

3. 资源管理：
```python
# 使用上下文管理器确保资源正确释放
with BrowserbaseWebLoader() as loader:
    result = loader.load(url)
```
