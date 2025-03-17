"""
技术分析Crew主执行文件
实现基于CrewAI Flow的工作流
这个版本用firecrawl来爬虫
后面要改成用crawl4ai
"""

import os
import sys
import yaml
import json
import logging
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from crewai.flow.flow import Flow, listen, start
from crewai import Agent, Task, Crew, Process
from dotenv import load_dotenv
from datetime import datetime, timedelta
from src.tech_analysis_crew.utils.firecrawl_scrape_web_md_clean import FirecrawlScrapeMdCleanTool
from src.llm.llm_config import llm_config
from crewai import LLM
import hashlib
import time
import concurrent.futures

# 添加项目根目录到系统路径
current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if project_root not in sys.path:
    sys.path.append(project_root)

# 配置日志
current_dir = os.path.dirname(current_file)
log_dir = os.path.join(current_dir, "log")
os.makedirs(log_dir, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(log_dir, f"crew_crawler_test_{timestamp}.log")

# 配置文件处理器
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.INFO)

# 配置控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# 配置格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# 获取logger并添加处理器
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# 确保日志正常工作
logger.info(f"日志文件已创建: {log_file}")
logger.info("技术分析Crew日志系统初始化完成")

# 导入自定义工具和配置
try:
    from src.llm.llm_config import llm_config
    from src.tech_analysis_crew.utils.dataprocess import DataProcessor, DataProcessingTool
    from src.tech_analysis_crew.utils.serper_tool import SerperDevTool
    from .utils.utility import (
        generate_job_id,
        load_agents_config,
        load_tasks_config,
        get_config_path
    )
    
except ModuleNotFoundError:
    # 如果上面的导入失败，尝试相对导入
    sys.path.append(os.path.join(project_root, "src"))
    from llm.llm_config import llm_config
    from tech_analysis_crew.utils.dataprocess import DataProcessor, DataProcessingTool
    from tech_analysis_crew.utils.serper_tool import SerperDevTool
    from .utils.utility import (
        generate_job_id,
        load_agents_config,
        load_tasks_config,
        get_config_path
    )
    

# 加载环境变量
load_dotenv()



class TimeSeriesAnalysisState(BaseModel):
    """时间序列分析状态模型"""
    job_id: str = ""
    input_file: str = ""
    indicator_description: str = ""  # 默认指标描述
    key_terms: List[str] = []
    time_series_data: List[Dict[str, Any]] = []
    current_period_index: int = 0
    current_period_data: Dict[str, Any] = {}
    search_results: Dict[str, Any] = {}
    crawled_contents: Dict[str, str] = {}
    content_analyses: List[Dict[str, Any]] = []
    period_analyses: List[Dict[str, Any]] = []
    final_report: str = ""
    output_dirs: Dict[str, str] = {}


class TimeSeriesAnalysisCrew:
    """时间序列分析Crew，负责编排和协调分析工作流
    """
    
    def __init__(self):
        """初始化时间序列分析团队"""
        
        # 设置输出目录
        self.output_dir = os.path.join(os.path.dirname(__file__), "output")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 初始化数据处理工具
        self.data_processor = DataProcessor()
        self.agents = self._load_agents_config()
        self.tasks = self._load_tasks_config()
    
    def _load_agents_config(self):
        """加载agents配置"""
        try:
            agent_config_path = get_config_path("agent.yaml")
            return load_agents_config(agent_config_path)
        except Exception as e:
            print(str(e))
            return {}
    
    def _load_tasks_config(self):
        """加载tasks配置"""
        try:
            task_config_path = get_config_path("tasks.yaml")
            return load_tasks_config(task_config_path)
        except Exception as e:
            print(str(e))
            return {}
    
    def analyze(self, input_file: str, indicator_description: str) -> Dict[str, Any]:
        """
        执行完整的时间序列分析
        
        Args:
            input_file: 输入CSV文件路径
            indicator_description: 指标描述
            
        Returns:
            分析结果信息
        """
        # 创建并启动工作流
        flow = TimeSeriesAnalysisFlow(input_file, indicator_description)
        flow.kickoff()
        
        # 构建返回结果
        final_result = {
            "job_id": flow.state.job_id,
            "report_path": os.path.join(
                flow.state.output_dirs.get("final_report_dir", ""),
                "final_report.md"
            ),
            "periods_analyzed": len(flow.state.time_series_data),
            "status": "completed"
        }
        
        return final_result
    
    def _extract_indicator_with_agent(self, user_query: str) -> str:
        """
        使用query_agent从用户查询中提取关键指标
        
        Args:
            user_query: 用户查询
                
        Returns:
            提取的关键指标，失败则返回"fail"
        """
        # 检查查询是否为空
        if not user_query or not user_query.strip():
            return "fail"
        
        # 检查是否有query_agent
        if "query_agent" not in self.agents:
            print("未找到query_agent")
            return "fail"
        
        # 最大重试次数
        max_retries = 3
        retry_count = 0
        
        # 当前使用的模型
        current_model = "gemini"
        use_backup = False
        
        # 记录错误信息
        error_message = ""
        
        # 设置API调用超时时间（秒）
        api_timeout = 30
        
        while retry_count < max_retries:
            try:
                # 选择模型
                model_config = llm_config.get_backup_model(current_model) if use_backup else llm_config.get_model(current_model)
                
                print(f"尝试 {retry_count+1}/{max_retries}，使用模型: {model_config['model']}")
                
                # 创建简单的crew来执行提取任务
                crew = Crew(
                    agents=[self.agents["query_agent"]],
                    tasks=[Task(
                        description=f"从用户查询'{user_query}'中提取关键指标，并翻译为英文",
                        expected_output="英文指标名",
                        agent=self.agents["query_agent"]
                    )],
                    verbose=True,
                    llm=model_config,
                )
                
                # 使用并发执行带超时的API调用
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(crew.kickoff)
                    try:
                        # 设置超时时间
                        result = future.result(timeout=api_timeout)
                        result_text = str(result)
                        
                        # 如果有结果，直接返回
                        if result_text and isinstance(result_text, str):
                            # 直接返回处理后的结果，不再处理indicator前缀
                            indicator_query = result_text.strip().lower()
                            print(f"返回最终结果: {indicator_query}")
                            return indicator_query
                    except concurrent.futures.TimeoutError:
                        print(f"API调用超时（{api_timeout}秒），尝试重试或切换模型")
                        # 如果超时，直接切换到备用模型
                        if not use_backup:
                            use_backup = True
                            print("由于超时，切换到备用模型")
                
                # 如果没有有效结果，重试
                print(f"无有效结果，进行第{retry_count+1}次重试")
                retry_count += 1
                
                # 如果已经尝试了一半的次数，切换到备用模型
                if retry_count >= max_retries // 2 and not use_backup:
                    use_backup = True
                    print("切换到备用模型")
                
            except Exception as e:
                # 记录错误
                error_message = str(e)
                print(f"提取指标时发生错误: {error_message}")
                retry_count += 1
                
                # 如果发生错误，立即切换到备用模型
                if not use_backup:
                    use_backup = True
                    print("发生错误，切换到备用模型")
                
                # 短暂等待后重试
                time.sleep(1)
        
        # 所有重试都失败
        print(f"所有重试均失败，最后错误: {error_message}")
        return f"fail: {error_message}" if error_message else "fail"

    def _save_crawled_content(self, url: str, content: str, query: str, date: str) -> str:
        """保存爬取的内容到文件
        
        Args:
            url: 爬取的URL
            content: 爬取的内容
            query: 查询关键词
            date: 相关日期
            
        Returns:
            保存的文件路径
        """
        # 确保cache目录存在
        cache_dir = self.state.output_dirs.get("cache_dir", "")
        if not cache_dir:
            cache_dir = os.path.join(self.state.output_dirs["base_output_dir"], "cache")
            self.state.output_dirs["cache_dir"] = cache_dir
        
        os.makedirs(cache_dir, exist_ok=True)
        
        # 生成唯一的文件名
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        query_hash = hashlib.md5(query.encode()).hexdigest()[:4]
        date_str = date.replace('-', '') if date else "nodate"
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        cache_filename = f"{url_hash}_{query_hash}_{date_str}_{timestamp}.md"
        cache_path = os.path.join(cache_dir, cache_filename)
        
        # 添加Markdown头信息
        md_content = f"""---
url: {url}
query: {query}
date: {date}
crawl_time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
---

{content}
"""
        
        # 保存内容
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
            logger.info(f"爬取内容已保存到: {cache_path}")
            return cache_path
        except Exception as e:
            logger.error(f"保存爬取内容失败: {str(e)}")
            return ""

class TimeSeriesAnalysisFlow():
    """时间序列分析工作流"""
    
    def __init__(self, input_file: str, indicator_description: str = "comex copper price"):
        """初始化工作流"""
        super().__init__()
        self.input_file = input_file
        self.indicator_description = indicator_description
        self.data_processor = DataProcessor()
        
        # 初始化状态对象
        self.state = TimeSeriesAnalysisState()
        self.state.input_file = input_file
        self.state.indicator_description = indicator_description
        
        # 加载配置
        self.agents_config = self._load_config("config/agent.yaml")
        self.tasks_config = self._load_config("config/tasks.yaml")
        
        # 初始化工具
        self.tools = {
            "SerperDevTool": SerperDevTool(),
            "FirecrawlScrapeWebsiteTool": FirecrawlScrapeMdCleanTool()
        }
        
        # 初始化Agents
        self.agents = self._initialize_agents()
        
        # 初始化回调函数
        self.on_start = None
        self.on_indicator_extracted = None
        self.on_period_start = None
        self.on_period_complete = None
        self.on_crawl_start = None
        self.on_crawl_complete = None
        self.on_report_generation_start = None
        self.on_report_generation_complete = None
        self.on_error = None
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载YAML配置文件"""
        full_path = os.path.join(os.path.dirname(__file__), config_path)
        with open(full_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _initialize_agents(self) -> Dict[str, Agent]:
        """初始化所有Agent"""
        agents = {}
        
        for agent_id, config in self.agents_config.items():
            # 获取工具列表
            agent_tools = []
            for tool_name in config.get("tools", []):
                if tool_name in self.tools and self.tools[tool_name] is not None:
                    # 确保工具是有效的BaseTool实例
                    tool = self.tools[tool_name]
                    if hasattr(tool, 'name') and hasattr(tool, 'description'):
                        agent_tools.append(tool)
                    else:
                        print(f"警告: 工具 {tool_name} 不是有效的BaseTool实例，已跳过")
            
            # 创建Agent
            agents[agent_id] = Agent(
                role=config["role"],
                goal=config["goal"],
                backstory=config["backstory"],
                verbose=config.get("verbose", True),
                allow_delegation=config.get("allow_delegation", False),
                tools=agent_tools,
                # 使用配置的LLM
                llm=llm_config.get_model()
            )
        
        return agents
    
    def _create_task(self, task_id: str) -> Task:
        """创建任务"""
        task_config = self.tasks_config[task_id]
        agent = self.agents[task_config["agent"]]
        
        return Task(
            description=task_config["description"],
            expected_output=task_config["expected_output"],
            agent=agent,
            async_execution=task_config.get("async_execution", False)
        )
    
    @start()
    def initialize_job(self):
        """初始化作业，生成作业ID并准备目录"""
        print("初始化作业...")
        
        # 生成作业ID
        job_id = generate_job_id()
        self.state.job_id = job_id
        self.state.input_file = self.input_file
        self.state.indicator_description = self.indicator_description
        
        # 准备输出目录
        output_dirs = self.data_processor.prepare_output_directories(job_id)
        self.state.output_dirs = output_dirs
        
        print(f"作业ID: {job_id}")
        print(f"输入文件: {self.input_file}")
        print(f"指标描述: {self.indicator_description}")
        print(f"输出目录: {output_dirs['base_output_dir']}")
        
        return job_id
    
    @listen(initialize_job)
    def process_input_data(self, job_id: str):
        """处理输入数据
        
        输入数据：csv文件
        start_date,end_date,start_price,end_price,low_price,high_price,pct_change,duration,trend_type,high_price_date,low_price_date


        输出数据：json文件
        {
            "job_id": "job_id",
            "input_file": "input_file",
            "indicator_description": "indicator_description",
            "time_series_data": "time_series_data"
        }
        """
        print(f"处理输入数据: {self.state.input_file}")
        
        # 转换CSV为JSON
        time_series_data = self.data_processor.csv_to_json(self.state.input_file)
        self.state.time_series_data = time_series_data
        
        # 保存处理后的数据
        output_path = os.path.join(
            self.state.output_dirs["base_output_dir"], 
            "processed_data.json"
        )
        
        self.data_processor.save_json(time_series_data, output_path)
        
        print(f"处理完成，共 {len(time_series_data)} 条时间序列数据")
        
        return {
            "time_series_data": time_series_data,
        }
    
    def kickoff(self) -> Dict[str, Any]:
        """启动分析流程"""
        try:
            # 触发开始回调
            if self.on_start:
                self.on_start(self)
            
            # 1. 初始化作业
            job_id = self.initialize_job()
            
            # 2. 处理输入数据
            processed_data = self.process_input_data(job_id)
            
            # 3. 分析时间段
            analysis_result = self.analyze_time_periods(processed_data)
            
            # 4. 生成最终报告
            if self.on_report_generation_start:
                self.on_report_generation_start()
            
            final_report = self.generate_final_report(analysis_result)
            
            if self.on_report_generation_complete:
                self.on_report_generation_complete(final_report.get("final_report_path", ""))
            
            return final_report
            
        except Exception as e:
            if self.on_error:
                self.on_error(str(e))
            raise
    
    @listen(process_input_data)
    def analyze_time_periods(self, processed_data: Dict[str, Any]):
        """分析所有时间段"""
        print("开始分析时间段...")
        
        # 获取时间序列数据
        time_series_data = processed_data["time_series_data"]
        total_periods = len(time_series_data)
        
        # 为每个时间段创建子流程
        for index, period_data in enumerate(time_series_data):
            # 触发时间段开始回调
            if self.on_period_start:
                self.on_period_start(index, total_periods)
            
            # 创建并运行子流程
            period_flow = TimePeriodAnalysisFlow(
                parent_flow=self,
                period_data=period_data,
                period_index=index
            )
            
            # 传递回调
            period_flow.on_crawl_start = self.on_crawl_start
            period_flow.on_crawl_complete = self.on_crawl_complete
            
            # 执行时间段分析
            period_result = period_flow.kickoff()
            
            # 保存时间段分析结果
            self.state.period_analyses.append(period_result)
            
            # 触发时间段完成回调
            if self.on_period_complete:
                self.on_period_complete(index, total_periods)
        
        print("所有时间段分析完成")
        
        # 创建结构化摘要
        summary = self._create_structured_summary()
        
        # 保存结构化摘要
        summary_path = os.path.join(
            self.state.output_dirs["serper_output_dir"],
            "all_periods_summary.json"
        )
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"结构化摘要已保存至: {summary_path}")
        
        # 执行网页爬取流程
        crawl_result = self.crawl_web_content(summary)
        
        return {
            "period_analyses": self.state.period_analyses,
            "summary": summary,
            "summary_path": summary_path,
            "crawl_result": crawl_result
        }
    
    def _create_structured_summary(self) -> Dict[str, Any]:
        """创建结构化摘要数据"""
        logger.info("创建结构化摘要数据...")
        
        structured_summary = {
            "job_id": self.state.job_id,
            "indicator": self.state.indicator_description,
            "total_periods": len(self.state.time_series_data),
            "periods": []
        }
        
        # 为每个时间段提取关键信息
        for index, period_data in enumerate(self.state.time_series_data):
            logger.info(f"处理时间段 {index} 的摘要数据")
            
            # 提取该时间段的关键信息
            period_summary = {
                "period_index": index,
                "start_date": period_data.get("start_date"),
                "end_date": period_data.get("end_date"),
                "trend_type": period_data.get("trend_type"),
                "queries": {},
                "search_results": {}
            }
            
            # 尝试从保存的文件加载搜索结果
            query_types = ["trend_query", "high_price_query", "low_price_query"]
            
            # 首先尝试从period_summary.json加载查询
            try:
                summary_path = os.path.join(
                    self.state.output_dirs["serper_output_dir"],
                    f"period_{index}_summary.json"
                )
                if os.path.exists(summary_path):
                    logger.info(f"从 {summary_path} 加载摘要数据")
                    with open(summary_path, 'r', encoding='utf-8') as f:
                        summary_data = json.load(f)
                        if "queries" in summary_data:
                            period_summary["queries"] = summary_data["queries"]
                        if "links" in summary_data:
                            # 临时存储链接信息
                            period_links = summary_data["links"]
            except Exception as e:
                logger.error(f"加载摘要文件出错: {str(e)}")
            
            # 然后加载每种查询的搜索结果
            for query_type in query_types:
                try:
                    result_path = os.path.join(
                        self.state.output_dirs["serper_output_dir"],
                        f"period_{index}_{query_type}_results.json"
                    )
                    
                    if os.path.exists(result_path):
                        logger.info(f"加载 {query_type} 搜索结果: {result_path}")
                        with open(result_path, 'r', encoding='utf-8') as f:
                            search_result = json.load(f)
                            
                            # 提取查询
                            if "_metadata" in search_result and "query" in search_result["_metadata"]:
                                if query_type not in period_summary["queries"]:
                                    period_summary["queries"][query_type] = search_result["_metadata"]["query"]
                            
                            # 提取链接
                            links = []
                            if "organic" in search_result:
                                for result in search_result["organic"]:
                                    if "link" in result:
                                        links.append({
                                            "title": result.get("title", ""),
                                            "link": result["link"],
                                            "snippet": result.get("snippet", ""),
                                            "date": result.get("date", "")
                                        })
                            
                            # 如果存在answerBox，也提取其链接
                            if "answerBox" in search_result and "link" in search_result["answerBox"]:
                                links.append({
                                    "title": search_result["answerBox"].get("title", ""),
                                    "link": search_result["answerBox"]["link"],
                                    "snippet": search_result["answerBox"].get("snippet", ""),
                                    "date": search_result["answerBox"].get("date", "")
                                })
                            
                            period_summary["search_results"][query_type] = {
                                "query": period_summary["queries"].get(query_type, ""),
                                "links": links,
                                "result_path": result_path,
                                "link_count": len(links)
                            }
                except Exception as e:
                    logger.error(f"加载 {query_type} 搜索结果出错: {str(e)}")
            
            # 如果我们已经有了period_analyses中的数据，也用它来补充
            if index < len(self.state.period_analyses):
                period_analysis = self.state.period_analyses[index]
                
                # 提取查询和搜索结果
                if "search_results" in period_analysis:
                    for query_type, results in period_analysis["search_results"].items():
                        # 保存查询
                        if "query" in results and query_type not in period_summary["queries"]:
                            period_summary["queries"][query_type] = results["query"]
                        
                        # 只有当我们还没有从文件加载链接时才使用内存中的链接
                        if query_type not in period_summary["search_results"] or not period_summary["search_results"][query_type]["links"]:
                            # 提取有用的链接信息
                            links = []
                            if "links" in results:
                                for link_info in results["links"]:
                                    links.append({
                                        "title": link_info.get("title", ""),
                                        "link": link_info.get("link", ""),
                                        "snippet": link_info.get("snippet", ""),
                                        "date": link_info.get("date", "")
                                    })
                            
                            period_summary["search_results"][query_type] = {
                                "query": results.get("query", ""),
                                "links": links,
                                "result_path": results.get("result_path", ""),
                                "link_count": len(links)
                            }
            
            structured_summary["periods"].append(period_summary)
            logger.info(f"时间段 {index} 摘要数据处理完成，查询数: {len(period_summary['queries'])}, 链接数: {sum(sr['link_count'] for sr in period_summary['search_results'].values())}")
        
        return structured_summary
    

    def crawl_web_content(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        """1爬取网页内容并生成分析报告
        
        按照时间段顺序处理：
        1. 对每个时间段，顺序处理其中的三种查询
        2. 对每种查询，分别爬取其包含的链接，生成内容总结
        3. 对每种查询生成一个报告
        4. 汇总三个查询报告，生成时间段总结报告
        5. 拼接所有时间段报告生成最终报告
        """
        logger.info("开始按时间段顺序爬取网页内容并生成报告...")
        
        # 初始化结果收集
        period_reports = {}
        all_crawled_contents = {}
        
        # 按照时间段顺序处理
        for period_index, period in enumerate(summary["periods"]):
            logger.info(f"\n开始处理时间段 {period_index+1}/{len(summary['periods'])}: "
                  f"{period.get('start_date')} 到 {period.get('end_date')}")
            
            # 处理单个时间段
            period_result = self._process_period(period, period_index)
            
            # 收集结果
            period_reports[period_index] = period_result["period_report"]
            all_crawled_contents.update(period_result["crawled_contents"])
            
            logger.info(f"时间段 {period_index+1} 处理完成")
        
        # 保存所有爬取内容
        crawl_result_path = os.path.join(
            self.state.output_dirs["final_report_dir"],
            "crawled_contents.json"
        )
        
        with open(crawl_result_path, 'w', encoding='utf-8') as f:
            # 将结果转换为可序列化的形式
            serializable_results = {url: str(result) for url, result in all_crawled_contents.items()}
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"所有网页爬取结果已保存至: {crawl_result_path}")
        
        # 生成最终报告
        final_report = self._generate_final_markdown(period_reports)
        final_report_path = os.path.join(
            self.state.output_dirs["final_report_dir"],
            "final_report.md"
        )
        
        with open(final_report_path, 'w', encoding='utf-8') as f:
            f.write(final_report)
        
        logger.info(f"最终报告已保存至: {final_report_path}")
        
        return {
            "period_reports": period_reports,
            "crawled_contents": all_crawled_contents,
            "crawl_result_path": crawl_result_path,
            "final_report_path": final_report_path
        }
    
    def _process_period(self, period: Dict[str, Any], period_index: int) -> Dict[str, Any]:
        """处理单个时间段的所有查询和链接"""
        logger.info(f"处理时间段 {period_index} 的查询...")
        
        # 确保cache目录存在
        cache_dir = self.state.output_dirs.get("cache_dir", "")
        if not cache_dir:
            # 如果cache_dir不存在，创建一个
            cache_dir = os.path.join(self.state.output_dirs["base_output_dir"], "cache")
            self.state.output_dirs["cache_dir"] = cache_dir
            
        # 确保目录存在
        os.makedirs(cache_dir, exist_ok=True)
        logger.info(f"网页内容缓存目录: {cache_dir}")
        
        period_start_date = period.get("start_date")
        period_end_date = period.get("end_date")
        
        
        # 创建爬虫和报告生成Agent
        crawler_agent = self._create_crawler_agent()
        report_agent = self._create_report_agent()
        conclusion_agent = self._create_conclusion_agent()
        
        # 收集所有任务
        all_tasks = []
        query_tasks = {}  # 按查询类型存储任务
        
        # 处理三种查询类型
        query_types = ["trend_query", "high_price_query", "low_price_query"]
        
        for query_type in query_types:
            if query_type in period["search_results"]:
                logger.info(f"处理查询类型: {query_type}")
                
                # 获取查询及其链接
                query_data = period["search_results"][query_type]
                query = period["queries"].get(query_type, "")
                
                if not query or not query_data or "links" not in query_data or not query_data["links"]:
                    logger.info(f"没有找到有效的 {query_type} 查询或链接，跳过")
                    continue
                
                # 创建该查询的所有爬取任务
                crawl_tasks = self._create_query_tasks(
                    query_type, 
                    query, 
                    query_data["links"], 
                    crawler_agent,
                    period_index
                )
                
                # 添加到所有任务列表
                all_tasks.extend(crawl_tasks)
                
                # 创建报告任务，依赖于爬取任务
                report_task = self._create_report_task(report_agent, crawl_tasks, query)
                all_tasks.append(report_task)
                
                # 存储报告任务
                query_tasks[query_type] = report_task
        
        # 创建总结任务，依赖于所有报告任务
        conclusion_task = self._create_conclusion_task(
            conclusion_agent, 
            list(query_tasks.values()),
            period_index,
            period_start_date,
            period_end_date
        )
        all_tasks.append(conclusion_task)
        
        # 创建 Crew 来执行所有任务
        period_crew = Crew(
            agents=[crawler_agent, report_agent, conclusion_agent],
            tasks=all_tasks,
            verbose=True
        )
        
        # 执行所有任务
        try:
            crew_result = period_crew.kickoff()
        except Exception as e:
            logger.error(f"任务执行超时或失败: {str(e)}")
            # 记录失败的任务信息
            failed_links = [task.description.split("URL的内容：")[1].split("\n")[0].strip() 
                           for task in all_tasks if not (hasattr(task, 'output') and task.output)]
            logger.warning(f"以下链接处理失败: {failed_links}")
        
        # 获取成功完成的任务结果
        successful_tasks = [task for task in all_tasks if hasattr(task, 'output') and task.output]
        
        # 获取总结报告
        period_report = ""
        if successful_tasks:
            # 获取总结报告
            period_report = self._generate_period_report(successful_tasks, period_index)
        else:
            period_report = f"## 时间段 {period_index} 报告\n\n所有链接爬取均超时或失败，请检查网络连接或调整查询条件。"
            logger.error(f"时间段 {period_index} 所有任务均失败")
        
        # 保存时间段报告
        period_report_dir = os.path.join(self.state.output_dirs["final_report_dir"])
        os.makedirs(period_report_dir, exist_ok=True)
        period_report_path = os.path.join(period_report_dir, f"period_{period_index}_report.md")
        
        with open(period_report_path, 'w', encoding='utf-8') as f:
            f.write(period_report)
        
        logger.info(f"时间段 {period_index} 报告已保存至: {period_report_path}")
        
        # 记录cache目录中保存的文件数量
        if os.path.exists(cache_dir):
            cached_files = [f for f in os.listdir(cache_dir) if f.endswith('.md')]
            logger.info(f"缓存目录 {cache_dir} 中共有 {len(cached_files)} 个网页内容文件")
        
        return {
            "period_report": period_report,
            "crawled_contents": {}  # 不再需要存储爬取内容
        }
    
    def _create_query_tasks(self, query_type: str, query: str, links: List[Dict[str, Any]], 
                       crawler_agent: Agent, period_index: int) -> List[Task]:
        """创建单个查询的所有爬取任务"""
        logger.info(f"为查询 '{query}' 创建 {len(links)} 个爬取任务...")
        
        crawl_tasks = []
        
        # 为每个链接创建爬取任务
        for link_index, link in enumerate(links):
            url = link.get("link", "")
            
            if not url:
                logger.info(f"链接 {link_index} 无效，跳过")
                continue
            
            logger.info(f"为链接 {link_index+1}/{len(links)} 创建爬取任务: {url}")
            
            # 创建爬取任务
            date = link.get("date", "")
            crawl_task = self._create_crawler_task(url, query, date, crawler_agent)
            crawl_tasks.append(crawl_task)
        
        return crawl_tasks
    
    def _generate_final_markdown(self, period_reports: Dict[int, str]) -> str:
        """拼接所有时间段报告生成最终报告"""
        logger.info("生成最终Markdown报告...")
        
        # 报告标题
        final_report = f"# {self.state.indicator_description} 价格分析报告\n\n"
        final_report += f"分析日期: {datetime.now().strftime('%Y-%m-%d')}\n\n"
        final_report += "---\n\n"
        
        # 按时间段顺序拼接报告
        sorted_periods = sorted(period_reports.keys())
        
        for period_index in sorted_periods:
            period_report = period_reports[period_index]
            final_report += f"\n\n## 时间段 {period_index+1}\n\n"
            final_report += period_report
            final_report += "\n\n---\n\n"
        
        return final_report
    
    def _create_crawler_agent(self) -> Agent:
        """创建爬取代理"""
        
        # 使用 LLMConfig 获取模型配置
        model_config = llm_config.get_model("gemini")
        
        # 创建LLM配置
        gemini_llm = LLM(
            provider=model_config["provider"],
            model=model_config["model"],
            temperature=0.7,
            api_key=model_config["api_key"]
        )
        
        # 创建爬取工具
        crawl_tools = [FirecrawlScrapeMdCleanTool(
            page_options={
                "onlyMainContent": True,
                "saveToFile": True,  # 启用保存到文件功能
                "outputFormat": "markdown"  # 设置输出格式为markdown
            }
        )]
        
        # 创建爬取代理
        crawler_agent = Agent(
            role="网页内容爬取专家",
            goal="准确的从网页内容中提取与指定问题相关的关键信息，将原始内容保存为MD文件，并提供切中要点的总结",
            backstory="""你是一名专业的网页内容情报搜集专家，擅长带着问题从网页中提取关键重要信息。
            你的工作是爬取指定URL的内容，将原始内容保存为Markdown文件，并对每个页面进行要点总结，提取关键信息。
            重要的数据要记录下来，你需要确保提取的内容准确完整，并提供切中问题要害的总结。
            你总是会严格按照要求将原始网页内容以Markdown格式保存到指定的文件路径，这是你工作流程中不可或缺的一步。""",
            verbose=True,
            allow_delegation=False,
            tools=crawl_tools,
            llm=gemini_llm
        )
        
        return crawler_agent
    
    def _create_report_agent(self) -> Agent:
        """创建报告生成代理"""
        
        # 使用 LLMConfig 获取模型配置
        model_config = llm_config.get_model("gemini")
        
        # 创建LLM配置
        report_llm = LLM(
            provider=model_config["provider"],
            model=model_config["model"],
            temperature=0.7,
            api_key=model_config["api_key"]
        )
        
        # 创建报告代理
        return Agent(
            role="Skilled Financial Report Writer",
            goal="Integrate intelligence information and generate comprehensive reports",
            backstory="""You are a financial analyst skilled at writing reports, with expertise in integrating and analyzing information.
            Your job is to take the prepared intelligence information from searches and write a complete report.
            You need to ensure the report has a clear structure, accurate content, and provides valuable, in-depth insights.""",
            verbose=True,
            allow_delegation=False,
            llm=report_llm
        )

        # return Agent(
        #     role="善于撰写报告的金融分析师",
        #     goal="整合情报信息，生成全面的报告",
        #     backstory="""你是一名善于撰写报告的金融分析师，擅长整合和分析信息。
        #     你的工作是将已经准备好的检索的情报信息，撰写一份完整的报告。
        #     你需要确保报告结构清晰，内容准确，并提供有价值、深度的见解。""",
        #     verbose=True,
        #     allow_delegation=False,
        #     llm=report_llm
        # )
    
    def _create_conclusion_agent(self) -> Agent:
        """创建总结代理"""
        
        # 使用 LLMConfig 获取模型配置
        model_config = llm_config.get_model("deepseek")
        
        # 创建LLM配置
        conclusion_llm = LLM(
            provider=model_config["provider"],
            model=model_config["model"],
            temperature=0.7,
            api_key=model_config["api_key"]
        )
        
        # 创建总结代理
        conclusion_agent = Agent(
            role="汇总分析专家",
            goal="综合多份报告，提炼核心洞察，生成全面深入的综合分析",
            backstory="""你是一位资深的综合分析专家，擅长从多角度分析问题并形成整体观点。
            你能够将不同报告中的信息有机整合，识别共性和差异，揭示深层规律。
            你长于把握宏观大势，同时注重微观细节，能够让读者全面理解市场变化背后的逻辑。
            你的分析既有历史纵深感，又有前瞻性，为读者提供全面且有价值的市场洞察。""",
            verbose=True,
            allow_delegation=False,
            llm=conclusion_llm
        )
        
        return conclusion_agent
    
    def _create_crawler_task(self, url: str, query: str, date: str, agent: Agent) -> Task:
        """创建爬取任务"""
        # 生成唯一的文件名
        # 使用URL、查询关键词和日期的组合创建哈希，确保文件名唯一性
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        query_hash = hashlib.md5(query.encode()).hexdigest()[:4]
        date_str = date.replace('-', '') if date else "nodate"
        cache_filename = f"{url_hash}_{query_hash}_{date_str}.md"
        cache_path = os.path.join(self.state.output_dirs["cache_dir"], cache_filename)
        
        return Task(
            description=f"""
            Use the Firecrawl tool to scrape content from the following URL: {url}
            
            Please complete the following tasks:
            1. Use the FirecrawlScrapeMdCleanTool to scrape the page content
            2. Analyze the content with the question "{query}" in mind, noting that the article was published on "{date}", please consider the historical context
            3. Summarize key information related to the "{self.state.indicator_description}" financial indicator from the page content, including important events, significant data, and key viewpoints
            4. Objectively extract from the page the deeper logic, reasons, factors, and objective events related to the indicator trends mentioned in the query
            5. The output will be used to generate the final retrospective report, so please ensure the content is accurate and comprehensive. Do not include your own opinions or fabricate facts.
            
            Note: You must save the original scraped webpage content in Markdown format to the specified file path. This is an important step to ensure the analysis process is traceable and reproducible.

            """,
            expected_output=f"""
            A retrospective analysis report based on the page content about "{query}", focusing on analyzing factors affecting the {self.state.indicator_description} financial indicator. The report structure should include: important influencing factors, events, data, and the logic affecting the financial indicator, with the source URL noted at the end of the report.
            """,
            agent=agent,
            # 增加执行控制参数
            max_execution_time=30,  # 30秒超时
        )

        # return Task(
        #     description=f"""
        #     使用Firecrawl工具爬取以下URL的内容：{url}
            
        #     请完成以下工作：
        #     1. 使用FirecrawlScrapeMdCleanTool工具爬取页面内容
        #     2. 带着问题"{query}"进行分析，注意该文章发布于"{date}"，请考虑文章的时间背景
        #     3. 总结该页面内容中与"{self.state.indicator_description}"金融指标相关的关键信息，包括重要事件、重要数据、重要观点等。
        #     4. 把query涉及的指标走势的深层次逻辑、原因、因素、客观事件等，客观的从页面中提取出来。
        #     5. 输出将被用于生成最终复盘报告，请确保内容准确、全面。不要带有自己的观点、不要编造事实。
            
        #     注意：必须将原始爬取的网页内容以Markdown格式保存到指定的文件路径中。这是确保分析过程可追溯和可复现的重要步骤。

        #     """,
        #     expected_output=f"""
        #     一份基于页面内容的、关于"{query}"的复盘分析报告，重点分析影响{self.state.indicator_description}金融指标相关的因素。报告结构中包括：重要影响因素、事件、数据、影响金融指标的逻辑，报告最后注明来源的url。
        #     """,
        #     agent=agent,
        #     # 增加执行控制参数
        #     max_execution_time=30,  # 30秒超时
        # )
    
    
    def _create_report_task(self, agent: Agent, crawl_tasks: List[Task], query: str) -> Task:
        """创建报告生成任务，依赖于爬取任务"""
        # from crewai import Task
        
        return Task(
            description=f"""
            Based on the analysis of multiple previously crawled web pages, generate a comprehensive summary report for {query}.
            
            Please complete the following tasks:
            1. Your context consists of objective content and subjective opinions from previously crawled web pages from multiple links
            2. Analyze and understand the context with "{query}" in mind, summarizing and compiling various objective and subjective information
            3. If there are contradictions in the information, conduct a dialectical analysis, assuming you are an absolute authority expert in the field related to the query, and provide reasonable explanations based on your knowledge
            4. Attach the source URL after each viewpoint, ensuring accuracy. You don't need to limit yourself to one viewpoint or one piece of data per paragraph; you can cite extensively, referencing multiple sources of evidence, data, or expert opinions around a particular viewpoint
            
            Please ensure the report content is accurate, comprehensive, and provides valuable insights.
            """,
            expected_output=f"""
            A structurally complete causal analysis report about {query.split("after:")[0].strip()}. The report should be written in Chinese.
            """,
            agent=agent,
            context=crawl_tasks  # 使用爬取任务作为上下文
        )
    
        # return Task(
        #     description=f"""
        #     基于之前爬取的多篇网页内容分析，生成一份针对{query}的全面的汇总报告。
            
        #     请完成以下工作：
        #     1. 你的上下文是之前多个links所爬取的网页的客观内容、主观观点
        #     2. 带着"{query}"进行对上下文的理解和分析，总结、汇总多方面的客观和主观信息
        #     3. 信息中如果有矛盾的地方，要进行辩证的分析，则假设你自己是query涉及的领域的绝对权威专家，根据你自己的知识理解给出合理的解释。
        #     4. 每个观点后面要附上url来源，务必要求准确。不一定是一个观点、一个数据一个段落，你可以旁征博引，在围绕某一个观点引用多个来源的证据、数据或者专家的观点。
            
        #     请确保报告内容准确、全面，并提供有价值的见解。
        #     """,
        #     expected_output=f"""
        #     一份结构完整的关于{query.split("after:")[0].strip()}的原因分析报告。报告使用中文撰写。
        #     """,
        #     agent=agent,
        #     context=crawl_tasks  # 使用爬取任务作为上下文
        # )
    
    def _create_conclusion_task(self, agent: Agent, report_tasks: List[Task], 
                           period_index: int, start_date: str, end_date: str) -> Task:
        """创建时间段总结任务，依赖于报告任务"""
        from crewai import Task
        
        # 创建任务描述
        task_description = f"""
        基于三种查询(trend_query, high_price_query, low_price_query)的分析报告，
        为时间段{period_index}({start_date}至{end_date})撰写一份区间内全面的复盘总结报告。
        
        请完成以下工作：
        1. 综合分析三种查询报告的内容
        2. 详细阐述该时间区间{self.state.indicator_description}价格走势的逻辑
        3. 深入分析区间高点和低点所发生的重要事件及其影响
        4. 揭示价格变动背后的根本原因和市场逻辑
        5. 提炼出该时间段最关键的洞察和结论
        
        请确保报告内容系统、全面、深入，并给出有价值的市场洞察。报告使用中文撰写。
        """
        
        expected_output = f"""
        一份针对{start_date}至{end_date}期间{self.state.indicator_description}价格走势的全面复盘总结报告，
        深入分析期间价格变动的原因、高低点事件及市场驱动的底层逻辑。报告使用中文撰写。观点来源url附在报告最后。
        """
        
        # 创建总结任务
        conclusion_task = Task(
            description=task_description,
            expected_output=expected_output,
            agent=agent,
            context=report_tasks  # 使用报告任务作为上下文
        )
        
        return conclusion_task

    def generate_final_report(self, crawl_result: Dict[str, Any]):
        """生成最终报告(此方法由crawl_web_content内部逻辑替代)"""
        logger.info("最终报告已由crawl_web_content生成")
        
        return {
            "status": "completed",
            "final_report_path": crawl_result.get("final_report_path", "")
        }

    def _generate_period_report(self, tasks: List[Task], period_index: int) -> str:
        """
        生成单个时间段的综合报告，汇总所有查询的报告
        
        Args:
            tasks: 成功完成的任务列表
            period_index: 时间段索引
            
        Returns:
            汇总后的报告文本
        """
        logger.info(f"生成时间段 {period_index} 的综合报告...")
        
        # 初始化报告目录
        reports_dir = os.path.join(self.state.output_dirs["final_report_dir"], "reports")
        os.makedirs(reports_dir, exist_ok=True)
        
        # 分类任务
        crawler_tasks = []
        report_tasks = []
        conclusion_tasks = []
        
        for task in tasks:
            if "爬取URL的内容" in task.description:
                # 只处理成功的爬取任务
                if hasattr(task, 'output') and task.output:
                    crawler_tasks.append(task)
            elif "生成查询报告" in task.description:
                report_tasks.append(task)
            elif "撰写一份区间内全面的复盘总结报告" in task.description:
                conclusion_tasks.append(task)
        
        logger.info(f"找到 {len(crawler_tasks)} 个爬取任务, {len(report_tasks)} 个报告任务, {len(conclusion_tasks)} 个总结任务")
        
        # 保存爬取任务结果
        for i, task in enumerate(crawler_tasks):
            try:
                # 提取URL
                url = task.description.split("URL的内容：")[1].split("\n")[0].strip()
                url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                
                # 保存爬取结果
                crawler_report_path = os.path.join(reports_dir, f"period_{period_index}_crawler_{i}_{url_hash}.md")
                with open(crawler_report_path, 'w', encoding='utf-8') as f:
                    f.write(f"# 爬取结果: {url}\n\n")
                    f.write(str(task.output))
                
                logger.info(f"爬取任务 {i} 结果已保存至: {crawler_report_path}")
            except Exception as e:
                logger.error(f"保存爬取任务 {i} 结果时出错: {str(e)}")
        
        # 保存查询报告结果
        query_reports = {}
        for i, task in enumerate(report_tasks):
            try:
                # 提取查询类型
                query_type = "unknown"
                if "trend_query" in task.description.lower():
                    query_type = "trend_query"
                elif "high_price_query" in task.description.lower():
                    query_type = "high_price_query"
                elif "low_price_query" in task.description.lower():
                    query_type = "low_price_query"
                
                # 保存查询报告
                query_report_path = os.path.join(reports_dir, f"period_{period_index}_{query_type}_report.md")
                with open(query_report_path, 'w', encoding='utf-8') as f:
                    f.write(f"# {query_type} 查询报告\n\n")
                    f.write(str(task.output))
                
                # 存储报告内容
                query_reports[query_type] = str(task.output)
                
                logger.info(f"查询报告 {query_type} 已保存至: {query_report_path}")
            except Exception as e:
                logger.error(f"保存查询报告 {i} 结果时出错: {str(e)}")
        
        # 获取总结报告
        period_conclusion = ""
        if conclusion_tasks:
            try:
                period_conclusion = str(conclusion_tasks[0].output)
                
                # 保存总结报告
                conclusion_report_path = os.path.join(reports_dir, f"period_{period_index}_conclusion.md")
                with open(conclusion_report_path, 'w', encoding='utf-8') as f:
                    f.write(f"# 时间段 {period_index} 总结报告\n\n")
                    f.write(period_conclusion)
                
                logger.info(f"总结报告已保存至: {conclusion_report_path}")
            except Exception as e:
                logger.error(f"保存总结报告时出错: {str(e)}")
        
        # 生成汇总报告
        combined_report = f"# 时间段 {period_index} 综合报告\n\n"
        
        # 添加各查询报告摘要
        combined_report += "## 查询报告摘要\n\n"
        for query_type, report in query_reports.items():
            # 提取报告的前300个字符作为摘要
            summary = report[:300] + "..." if len(report) > 300 else report
            combined_report += f"### {query_type}\n\n{summary}\n\n"
        
        # 添加总结报告
        if period_conclusion:
            combined_report += "## 综合分析\n\n"
            combined_report += period_conclusion
        else:
            combined_report += "## 综合分析\n\n未能生成综合分析。"
        
        # 保存汇总报告
        combined_report_path = os.path.join(reports_dir, f"period_{period_index}_combined_report.md")
        with open(combined_report_path, 'w', encoding='utf-8') as f:
            f.write(combined_report)
        
        logger.info(f"汇总报告已保存至: {combined_report_path}")
        
        return combined_report

class TimePeriodAnalysisFlow(Flow):
    """时间段分析子流程"""
    
    def __init__(self, parent_flow: TimeSeriesAnalysisFlow, period_data: Dict[str, Any], period_index: int):
        """初始化子流程"""
        super().__init__()
        self.parent_flow = parent_flow
        self.period_data = period_data
        self.period_index = period_index
        self.key_terms = parent_flow.state.key_terms
        self.output_dirs = parent_flow.state.output_dirs
        self.job_id = parent_flow.state.job_id
        
        # 需要的工具
        self.data_processor = parent_flow.data_processor
        self.serper_tool = SerperDevTool()
        
        # 初始化回调函数
        self.on_crawl_start = None
        self.on_crawl_complete = None
    
    @start()
    def generate_search_query(self):
        """生成搜索查询"""
        logger.info(f"为时间段 {self.period_index+1} 生成搜索查询...")
        
        # 获取时间段数据
        period_data = self.period_data
        indicator = self.parent_flow.indicator_description
        
        # 获取关键日期
        start_date = period_data.get('start_date', '')
        end_date = period_data.get('end_date', '')
        high_price_date = period_data.get('high_price_date', '')
        low_price_date = period_data.get('low_price_date', '')
        trend_type = period_data.get('trend_type', 'unknown')
        
        # 生成针对趋势类型的查询
        trend_query = ""
        if trend_type == "up":
            trend_query = f"{indicator} rise up after:{start_date} before:{end_date}"
        elif trend_type == "down":
            trend_query = f"{indicator} dropped after:{start_date} before:{end_date}"
        elif trend_type == "consolidation":
            trend_query = f"{indicator} volatile after:{start_date} before:{end_date}"
        else:
            trend_query = f"{indicator} after:{start_date} before:{end_date}"
            
        # 计算高价日期前后7天的时间范围
        high_before_date = self._date_offset(high_price_date, -7)
        high_after_date = self._date_offset(high_price_date, 7)
        high_price_query = f"{indicator} hit peak after:{high_before_date} before:{high_after_date}"
        
        # 计算低价日期前后7天的时间范围
        low_before_date = self._date_offset(low_price_date, -7)
        low_after_date = self._date_offset(low_price_date, 7)
        low_price_query = f"{indicator} dropped after:{low_before_date} before:{low_after_date}"
        
        # 组合三种查询
        queries = {
            "trend_query": trend_query,
            "high_price_query": high_price_query,
            "low_price_query": low_price_query
        }
        
        logger.info(f"生成的查询: {queries}")
        
        return queries
    
    def _date_offset(self, date_str, days):
        """计算日期偏移"""
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            new_date = date_obj + timedelta(days=days)
            return new_date.strftime('%Y-%m-%d')
        except:
            # 如果日期格式不正确，返回原始日期
            return date_str
    
    @listen(generate_search_query)
    def search_news(self, queries: dict):
        """搜索新闻和信息"""
        logger.info(f"执行搜索，共 {len(queries)} 个查询...")
        
        all_search_results = {}
        extracted_links = {}
        
        # 为每个查询执行搜索
        for query_type, query in queries.items():
            logger.info(f"执行 {query_type} 查询: {query}")
            
            # 使用SerperDevTool执行搜索
            search_results = self.serper_tool.search(query, mock=False)
            
            # 提取链接
            links = []
            if "organic" in search_results:
                for result in search_results["organic"]:
                    if "link" in result:
                        links.append({
                            "title": result.get("title", ""),
                            "link": result["link"],
                            "snippet": result.get("snippet", ""),
                            "date": result.get("date", "")
                        })
            
            # 如果存在answerBox，也提取其链接
            if "answerBox" in search_results and "link" in search_results["answerBox"]:
                links.append({
                    "title": search_results["answerBox"].get("title", ""),
                    "link": search_results["answerBox"]["link"],
                    "snippet": search_results["answerBox"].get("snippet", ""),
                    "date": search_results["answerBox"].get("date", "")
                })
            
            # 记录提取的链接
            extracted_links[query_type] = links
            
            # 添加元数据
            search_results["_metadata"] = {
                "query_type": query_type,
                "query": query,
                "job_id": self.job_id,
                "period_index": self.period_index,
                "period_start_date": self.period_data.get("start_date"),
                "period_end_date": self.period_data.get("end_date"),
                "trend_type": self.period_data.get("trend_type"),
                "result_count": len(links)
            }
            
            # 保存搜索结果
            result_path = os.path.join(
                self.output_dirs["serper_output_dir"],
                f"period_{self.period_index}_{query_type}_results.json"
            )
            self.data_processor.save_json(search_results, result_path)
            
            all_search_results[query_type] = search_results
            logger.info(f"{query_type} 搜索完成，找到 {len(links)} 个链接，结果保存到: {result_path}")
        
        # 创建汇总结果
        summary = {
            "job_id": self.job_id,
            "start_date": self.period_data.get("start_date"),
            "end_date": self.period_data.get("end_date"),
            "trend_type": self.period_data.get("trend_type"),
            "queries": queries,
            "links": extracted_links
        }
        
        # 保存汇总结果
        summary_path = os.path.join(
            self.output_dirs["serper_output_dir"],
            f"period_{self.period_index}_summary.json"
        )
        self.data_processor.save_json(summary, summary_path)
        logger.info(f"汇总结果保存到: {summary_path}")
        
        return {
            "search_results": all_search_results,
            "extracted_links": extracted_links,
            "summary_path": summary_path
        }