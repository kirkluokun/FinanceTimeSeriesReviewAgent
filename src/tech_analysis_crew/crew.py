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
import threading
import traceback
import re
# 导入CrewConfig
from src.tech_analysis_crew.config.crew_config import CrewConfig


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
        current_model = "gemini-2.0-flash"
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
    
    # @start()
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
    
    # @listen(initialize_job)
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
            
            if self.on_report_generation_complete:
                self.on_report_generation_complete(analysis_result.get("final_report_path", ""))
            
            return analysis_result
            
        except Exception as e:
            if self.on_error:
                self.on_error(str(e))
            raise
    
    # @listen(process_input_data)
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
        """爬取网页内容并生成分析报告
        
        按照时间段顺序处理：
        1. 对每个时间段，顺序处理其中的三种查询
        2. 对每种查询，并行爬取其包含的链接，生成内容总结
        3. 所有链接爬取完成后，对每种查询生成一个报告
        4. 汇总三个查询报告，生成时间段总结报告
        5. 拼接所有时间段报告生成最终报告
        """
        logger.info("开始按时间段顺序爬取网页内容并生成报告...")
        
        # 初始化结果收集
        period_reports = {}
        all_crawled_contents = {}
        
        # 按照时间段顺序处理
        for period_index, period in enumerate(summary["periods"]):
            logger.info(f"\n开始处理时间段 {period_index}/{len(summary['periods'])}: "
                  f"{period.get('start_date')} 到 {period.get('end_date')}")
            
            # 处理单个时间段（使用并行处理）
            period_result = self._process_period_parallel(period, period_index)
            
            # 收集结果
            period_reports[period_index] = period_result["period_report"]
            all_crawled_contents.update(period_result["crawled_contents"])
            
            logger.info(f"时间段 {period_index} 处理完成")
        
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
    
    def _process_period_parallel(self, period: Dict[str, Any], period_index: int) -> Dict[str, Any]:
        """并行处理单个时间段的所有查询和链接
        
        改进版：每种查询类型爬取完成后立即生成报告，而不是等待所有类型爬取完成再统一处理
        """
        logger.info(f"并行处理时间段 {period_index} 的查询...")
        
        # 确保cache目录存在
        cache_dir = self.state.output_dirs.get("cache_dir", "")
        if not cache_dir:
            cache_dir = os.path.join(self.state.output_dirs["base_output_dir"], "cache")
            self.state.output_dirs["cache_dir"] = cache_dir
            
        # 确保目录存在
        os.makedirs(cache_dir, exist_ok=True)
        logger.info(f"网页内容缓存目录: {cache_dir}")
        
        period_start_date = period.get("start_date")
        period_end_date = period.get("end_date")
        
        # 获取真实的市场数据
        market_data = None
        if period_index < len(self.state.time_series_data):
            market_data = self.state.time_series_data[period_index]
            logger.info(f"获取到时间段 {period_index} 的市场数据: {market_data['start_date']} - {market_data['end_date']}")
        else:
            logger.warning(f"无法获取时间段 {period_index} 的市场数据,索引超出范围")
        
        # 创建Agent
        crawler_agent = self._create_crawler_agent()
        report_agent = self._create_report_agent()
        conclusion_agent = self._create_conclusion_agent()
        
        # 存储所有查询类型的爬取结果和报告任务
        query_results = {}
        report_tasks = {}
        all_crawled_contents = {}
        
        # 使用线程池并行处理每种查询类型
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as query_executor:
            # 创建查询类型处理任务
            future_to_query_type = {}
            
            # 处理三种查询类型
            query_types = ["trend_query", "high_price_query", "low_price_query"]
            
            for query_type in query_types:
                if query_type in period["search_results"]:
                    # 获取查询及其链接
                    query_data = period["search_results"][query_type]
                    query = period["queries"].get(query_type, "")
                    
                    if not query or not query_data or "links" not in query_data or not query_data["links"]:
                        logger.info(f"没有找到有效的 {query_type} 查询或链接，跳过")
                        continue
                    
                    # 提交查询类型处理任务
                    future = query_executor.submit(
                        self._process_query_type,
                        query_type=query_type,
                        query=query,
                        links=query_data["links"],
                        crawler_agent=crawler_agent,
                        report_agent=report_agent,
                        period_index=period_index,
                        cache_dir=cache_dir,
                        market_data=market_data
                    )
                    future_to_query_type[future] = query_type
            
            # 收集每种查询类型的处理结果
            for future in concurrent.futures.as_completed(future_to_query_type):
                query_type = future_to_query_type[future]
                try:
                    # 获取处理结果
                    result = future.result()
                    query_results[query_type] = result["query_result"]
                    report_tasks[query_type] = result["report_task"]
                    
                    # 合并爬取内容
                    for url, content in result["crawled_contents"].items():
                        if content and url:
                            all_crawled_contents[url] = content
                    
                    logger.info(f"查询类型 {query_type} 处理完成，生成了报告任务")
                except Exception as e:
                    logger.error(f"处理查询类型 {query_type} 时出错: {str(e)}")
                    logger.error(traceback.format_exc())
        
        # 如果没有报告任务，返回空结果
        if not report_tasks:
            logger.error(f"时间段 {period_index} 没有生成任何报告任务")
            period_report = f"## 时间段 {period_index} 报告\n\n未能爬取到有效内容，请检查网络连接或调整查询条件。"
            
            # 保存空报告
            period_report_dir = os.path.join(self.state.output_dirs["final_report_dir"])
            os.makedirs(period_report_dir, exist_ok=True)
            period_report_path = os.path.join(period_report_dir, f"period_{period_index}_report.md")
            
            with open(period_report_path, 'w', encoding='utf-8') as f:
                f.write(period_report)
            
            return {
                "period_report": period_report,
                "crawled_contents": {}
            }
        
        # 创建总结任务
        conclusion_task = self._create_conclusion_task(
            conclusion_agent,
            list(report_tasks.values()),
            period_index,
            period_start_date,
            period_end_date
        )
        
        # 创建包含总结任务的Crew
        conclusion_crew = Crew(
            agents=[conclusion_agent],
            tasks=[conclusion_task],
            verbose=True
        )
        
        # 执行总结任务
        conclusion_crew.kickoff()
        
        # 收集所有完成的任务
        all_tasks = list(report_tasks.values()) + [conclusion_task]
        successful_tasks = [task for task in all_tasks if hasattr(task, 'output') and task.output]
        
        # 生成综合报告
        period_report = ""
        if successful_tasks:
            period_report = self._generate_period_report(successful_tasks, period_index)
        else:
            period_report = f"## 时间段 {period_index} 报告\n\n所有报告任务均失败，请检查网络连接或调整查询条件。"
            logger.error(f"时间段 {period_index} 所有报告任务均失败")
        
        # 保存时间段报告
        period_report_dir = os.path.join(self.state.output_dirs["final_report_dir"])
        os.makedirs(period_report_dir, exist_ok=True)
        period_report_path = os.path.join(period_report_dir, f"period_{period_index}_report.md")
        
        with open(period_report_path, 'w', encoding='utf-8') as f:
            f.write(period_report)
        
        logger.info(f"时间段 {period_index} 报告已保存至: {period_report_path}")
        
        return {
            "period_report": period_report,
            "crawled_contents": all_crawled_contents
        }
    
    def _process_query_type(self, query_type: str, query: str, links: List[Dict[str, Any]],
                           crawler_agent: Agent, report_agent: Agent, period_index: int, 
                           cache_dir: str, market_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """处理单个查询类型的完整流程：爬取链接并生成报告
        
        Args:
            query_type: 查询类型
            query: 查询内容
            links: 链接列表
            crawler_agent: 爬虫代理
            report_agent: 报告生成代理
            period_index: 时间段索引
            cache_dir: 缓存目录
            market_data: 时间段的市场数据
            
        Returns:
            包含爬取结果和报告任务的字典
        """
        logger.info(f"处理查询类型 {query_type}, 链接数: {len(links)}")
        
        # 1. 并行爬取该查询类型的所有链接
        crawl_results = self._parallel_crawl_links(
            query_type,
            query,
            links,
            crawler_agent,
            period_index,
            cache_dir,
            market_data
        )
        
        logger.info(f"查询类型 {query_type} 爬取完成，共 {len(crawl_results)} 个结果，开始生成报告")
        
        # 2. 创建报告任务
        report_task = self._create_report_from_crawl_results(
            report_agent,
            crawl_results,
            query,
            query_type
        )
        
        # 3. 执行报告任务
        report_crew = Crew(
            agents=[report_agent],
            tasks=[report_task],
            verbose=True
        )
        
        # 执行报告生成
        logger.info(f"开始生成查询类型 {query_type} 的报告")
        report_crew.kickoff()
        
        # 查看报告任务是否成功
        if hasattr(report_task, 'output') and report_task.output:
            logger.info(f"查询类型 {query_type} 的报告生成成功")
            
            # 保存报告到文件
            report_dir = os.path.join(self.state.output_dirs["final_report_dir"])
            os.makedirs(report_dir, exist_ok=True)
            report_path = os.path.join(report_dir, f"period_{period_index}_{query_type}_report.md")
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(f"# {query_type} 查询报告\n\n")
                f.write(str(report_task.output))
                
            logger.info(f"查询类型 {query_type} 的报告已保存至: {report_path}")
        else:
            logger.error(f"查询类型 {query_type} 的报告生成失败")
        
        # 4. 返回查询结果和报告任务
        query_result = {
            "query": query,
            "crawl_results": crawl_results,
            "links": links
        }
        
        return {
            "query_result": query_result,
            "report_task": report_task,
            "crawled_contents": crawl_results
        }

    def _parallel_crawl_links(self, query_type: str, query: str, links: List[Dict[str, Any]], 
                              crawler_agent: Agent, period_index: int, cache_dir: str, period_data: Dict[str, Any] = None) -> Dict[str, str]:
        """并行爬取多个链接
        
        改进版：增加批处理机制和缓存检查，提高并行效率
        
        Args:
            query_type: 查询类型
            query: 查询内容
            links: 链接列表
            crawler_agent: 爬虫代理
            period_index: 时间段索引
            cache_dir: 缓存目录
            period_data: 时间段的市场数据
            
        Returns:
            Dict[url, content] 爬取结果字典
        """
        logger.info(f"开始并行爬取 {query_type} 查询下的 {len(links)} 个链接...")
        
        # 结果集
        crawl_results = {}
        
        # 创建一个线程安全的锁
        lock = threading.Lock()
        
        # 检查URL缓存
        url_cache = {}
        cache_hits = 0
        
        # 创建爬取任务列表
        crawl_tasks = []
        
        # 为每个链接创建爬取任务
        for link in links:
            url = link.get("link", "")
            if not url:
                continue
            
            # 生成缓存文件名
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            cache_path = os.path.join(
                cache_dir, 
                f"period_{period_index}_{query_type}_crawler_{url_hash}.md"
            )
            
            # 检查缓存是否存在
            if os.path.exists(cache_path):
                try:
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # 跳过标题行，获取实际内容
                        if content and "# 爬取结果:" in content:
                            content = content.split("\n\n", 1)[1] if "\n\n" in content else content
                            crawl_results[url] = content
                            cache_hits += 1
                            logger.info(f"从缓存加载链接 {url} 的内容")
                            continue
                except Exception as e:
                    logger.error(f"从缓存加载 {url} 失败: {str(e)}")
                
            # 如果缓存不存在或无效，添加到爬取任务
            date = link.get("date", "")
            task = self._create_crawler_task(url, query, date, crawler_agent, query_type, period_data)
            crawl_tasks.append((task, url))
        
        if cache_hits > 0:
            logger.info(f"从缓存加载了 {cache_hits} 个链接内容，剩余 {len(crawl_tasks)} 个链接需要爬取")
        
        # 如果没有需要爬取的任务，直接返回缓存结果
        if not crawl_tasks:
            logger.info(f"所有链接已从缓存加载，无需爬取")
            return crawl_results
        
        # 创建批处理任务
        batch_size = 2  # 每批处理2个URL
        batched_tasks = [crawl_tasks[i:i+batch_size] for i in range(0, len(crawl_tasks), batch_size)]
        logger.info(f"将 {len(crawl_tasks)} 个爬取任务分成 {len(batched_tasks)} 个批次处理")
        
        # 创建一个线程池
        max_workers = min(3, len(batched_tasks))  # 限制最大并行数为3
        
        def execute_batch(batch):
            batch_results = {}
            for task, url in batch:
                try:
                    # 创建一个单任务的Crew
                    task_crew = Crew(
                        agents=[crawler_agent],
                        tasks=[task],
                        verbose=True
                    )
                    
                    # 执行爬取任务，添加超时控制
                    start_time = time.time()
                    max_time = 180  # 3分钟超时
                    result = None
                    
                    try:
                        # 执行爬取任务
                        result = task_crew.kickoff()
                        
                        # 检查执行时间
                        elapsed_time = time.time() - start_time
                        if elapsed_time > max_time:
                            logger.warning(f"链接 {url} 爬取时间过长: {elapsed_time:.2f}秒")
                    except Exception as timeout_e:
                        logger.error(f"链接 {url} 爬取超时或出错: {str(timeout_e)}")
                    
                    # 如果任务执行成功
                    if result and hasattr(task, 'output') and task.output:
                        content = str(task.output)
                        
                        # 生成缓存文件名
                        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                        crawler_report_path = os.path.join(
                            cache_dir, 
                            f"period_{period_index}_{query_type}_crawler_{url_hash}.md"
                        )
                        
                        # 将结果保存到文件
                        with open(crawler_report_path, 'w', encoding='utf-8') as f:
                            f.write(f"# 爬取结果: {url}\n\n")
                            f.write(content)
                        
                        logger.info(f"链接 {url} 爬取完成，结果已保存至: {crawler_report_path}")
                        
                        # 添加到批处理结果
                        batch_results[url] = content
                    else:
                        logger.error(f"链接 {url} 爬取失败，无有效输出")
                except Exception as e:
                    logger.error(f"爬取链接 {url} 时出错: {str(e)}")
                    logger.error(traceback.format_exc())
                
                # 添加短暂的间隔，避免API限制
                time.sleep(1)
            
            return batch_results
        
        # 使用线程池执行批处理任务
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for batch in batched_tasks:
                # 提交批处理任务
                future = executor.submit(execute_batch, batch)
                futures.append(future)
            
            # 等待所有批处理任务完成
            for future in concurrent.futures.as_completed(futures):
                try:
                    # 获取批处理结果
                    batch_results = future.result()
                    
                    # 合并结果
                    with lock:
                        crawl_results.update(batch_results)
                except Exception as e:
                    logger.error(f"处理批处理任务结果时出错: {str(e)}")
        
        logger.info(f"查询类型 {query_type} 的 {len(links)} 个链接处理完成，成功爬取 {len(crawl_results)} 个")
        
        return crawl_results
    
    def _create_report_from_crawl_results(self, agent: Agent, crawl_results: Dict[str, str], 
                                          query: str, query_type: str) -> Task:
        """从爬取结果创建报告任务
        
        Args:
            agent: 报告生成代理
            crawl_results: 爬取结果字典 {url: content}
            query: 查询内容
            query_type: 查询类型
            
        Returns:
            报告任务
        """
        # 直接创建描述，不使用mock对象，避免raw属性问题
        description = f"""
            [TASK_TYPE:report][QUERY_TYPE:{query_type}]
            Assume you are an absolute authority in the field related to {query.split("after:")[0].strip()}, please complete the following tasks:
            
            1. The following is a summary of the key points extracted from the web pages crawled regarding {query}.
            2. Based on these key points of objective information, generate a comprehensive summary report regarding {query}.
            3. Focus on analysis and organization: form the logic of trends (upward, downward, or turning points) and potential underlying reasons.
            4. When citing multiple sources of evidence around a particular viewpoint, ensure that each citation is followed by the source URL："[url link]".
            
            Please ensure that the report content is accurate, comprehensive, and provides valuable insights.

            The following is the crawled content:
            """
        
        # 添加爬取结果到描述中
        for url, content in crawl_results.items():
            # 不再限制内容长度，使用完整内容
            description += f"\n--- 来源: {url} ---\n\n{content}\n\n"
        
        # 直接创建Task对象
        return Task(
            description=description,
            expected_output=f"""
            A report analyzing {query}. The report is written in Chinese. 
            
            The report format should be in markdown, with paragraphs structured correctly. Use ## for level 1 headings, ### for level 2 headings, and number the paragraphs with Arabic numerals. The format for URL citations should be "[url link]".
            
            Report outline:
            Title: Create a title based on the context content
            1. Market situation: Describe the objective situation of {query.split("after:")[0].strip()} based on the description of the market in the report. (Notice: This section does not need to record the source URL.)

            2. Description of objective data: Summarize the key influences, objective events, data, and news that have a significant impact on {query.split("after:")[0].strip()}. (Do not reiterate market trend data.)

            3. The deep logic of {query.split("after:")[0].strip()}: Describe the deep logic behind the formation of {query.split("after:")[0].strip()} based on the logical description in the report

            4. Summary: Generate insightful conclusions based on the summary description in the report
            """,
            agent=agent,
            async_execution=False
        )

    def _create_crawler_agent(self) -> Agent:
        """创建爬取代理"""
        return CrewConfig.create_crawler_agent()
    
    def _create_report_agent(self) -> Agent:
        """创建报告生成代理"""
        return CrewConfig.create_report_agent()
    
    def _create_conclusion_agent(self) -> Agent:
        """创建总结代理"""
        return CrewConfig.create_conclusion_agent()
    
    def _create_crawler_task(self, url: str, query: str, date: str, agent: Agent, 
                             query_type: str, period_data: Dict[str, Any] = None) -> Task:
        """创建爬取任务
        
        Args:
            url: 爬取的URL
            query: 查询内容
            date: 相关日期
            agent: 爬虫代理
            query_type: 查询类型
            period_data: 时间段的市场数据
        """
        # 构建市场数据部分
        market_data_context = ""
        if period_data:
            market_data_context = f"""
            市场数据参考:
            - 区间: {period_data['start_date']} 至 {period_data['end_date']}
            - 价格变化: {period_data['start_price']} → {period_data['end_price']} ({period_data['pct_change']*100:.2f}%)
            - 最高价: {period_data['high_price']} (日期: {period_data['high_price_date']})
            - 最低价: {period_data['low_price']} (日期: {period_data['low_price_date']})
            - 持续天数: {period_data['duration']}天
            - 趋势类型: {period_data['trend_type']}
            """
        
        return CrewConfig.create_crawler_task(
            url=url,
            query=query,
            date=date,
            agent=agent,
            query_type=query_type,
            indicator_description=self.state.indicator_description,
            cache_dir=self.state.output_dirs.get("cache_dir", ""),
            market_data_context=market_data_context  # 新增参数
        )
    
    def _create_conclusion_task(self, agent: Agent, report_tasks: List[Task], 
                           period_index: int, start_date: str, end_date: str) -> Task:
        """创建时间段总结任务，依赖于报告任务"""
        return CrewConfig.create_conclusion_task(
            agent=agent,
            report_tasks=report_tasks,
            period_index=period_index,
            start_date=start_date,
            end_date=end_date,
            indicator_description=self.state.indicator_description
        )


    def _generate_final_markdown(self, period_reports: Dict[int, str]) -> str:
        """拼接所有时间段报告生成最终报告"""
        logger.info("生成最终Markdown报告...")
        
        # 报告标题
        final_report = f"# {self.state.indicator_description} 价格分析报告\n\n"
        final_report += "##\n\n"
        
        # 按时间段顺序拼接报告
        sorted_periods = sorted(period_reports.keys())
        
        for period_index in sorted_periods:
            period_report = period_reports[period_index]
            final_report += f"\n\n## 时间段 {period_index}\n\n"
            final_report += period_report
            final_report += "\n\n---\n\n"
        
        return final_report
    
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
        reports_dir = self.state.output_dirs["final_report_dir"]
        caches_dir = self.state.output_dirs["cache_dir"]
        os.makedirs(reports_dir, exist_ok=True)
        os.makedirs(caches_dir, exist_ok=True)
        
        # 分类任务
        crawler_tasks = []
        report_tasks = []
        conclusion_tasks = []
        
        # 打印所有任务的描述，用于调试
        for i, task in enumerate(tasks):
            task_desc = task.description[:100] + "..." if len(task.description) > 100 else task.description
            logger.info(f"任务 {i}: {task_desc}")
            
            # 使用任务描述中的标记来识别任务类型
            if "[TASK_TYPE:crawler]" in task.description:
                if hasattr(task, 'output') and task.output:
                    crawler_tasks.append(task)
                    logger.info(f"识别为爬取任务: {task_desc}")
            elif "[TASK_TYPE:report]" in task.description:
                report_tasks.append(task)
                logger.info(f"识别为报告任务: {task_desc}")
            elif "[TASK_TYPE:conclusion]" in task.description:
                conclusion_tasks.append(task)
                logger.info(f"识别为总结任务: {task_desc}")
            else:
                logger.info(f"未能识别任务类型: {task_desc}")
        
        logger.info(f"找到 {len(crawler_tasks)} 个爬取任务, {len(report_tasks)} 个报告任务, {len(conclusion_tasks)} 个复盘总结任务")
        
        # 按查询类型组织爬取任务
        query_type_crawler_tasks = {}
        
        # 保存爬取任务结果
        for i, task in enumerate(crawler_tasks):
            try:
                # 提取查询类型 - 优先使用[QUERY_TYPE:xxx]标记
                query_type = "unknown"
                if "[QUERY_TYPE:" in task.description:
                    query_type_start = task.description.find("[QUERY_TYPE:") + len("[QUERY_TYPE:")
                    query_type_end = task.description.find("]", query_type_start)
                    if query_type_end > query_type_start:
                        query_type = task.description[query_type_start:query_type_end].strip()
                
                # 确保query_type不是unknown
                if query_type == "unknown":
                    logger.warning(f"爬取任务 {i} 的查询类型无法识别，将尝试从描述中提取")
                    if "trend_query" in task.description.lower():
                        query_type = "trend_query"
                    elif "high_price_query" in task.description.lower():
                        query_type = "high_price_query"
                    elif "low_price_query" in task.description.lower():
                        query_type = "low_price_query"
                    else:
                        # 如果仍然无法识别，尝试最后的方法
                        for qt in ["trend_query", "high_price_query", "low_price_query"]:
                            if qt in str(task.output).lower():
                                query_type = qt
                                break
                
                # 提取URL
                url = None
                # 尝试不同的URL提取方法
                if "爬取URL的内容：" in task.description:
                    url = task.description.split("爬取URL的内容：")[1].split("\n")[0].strip()
                elif "URL:" in task.description:
                    url = task.description.split("URL:")[1].split("\n")[0].strip()
                elif "from the following URL:" in task.description:
                    url = task.description.split("from the following URL:")[1].split("\n")[0].strip()
                
                # 如果无法提取URL，使用索引号代替
                if not url:
                    url = f"unknown_url_{i}"
                
                # 使用URL哈希作为文件名的一部分
                url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                
                # 将爬取任务添加到对应查询类型的列表中
                if query_type not in query_type_crawler_tasks:
                    query_type_crawler_tasks[query_type] = []
                query_type_crawler_tasks[query_type].append((task, url, url_hash))
                
                # 保存爬取结果到文件，确保文件名中包含正确的query_type
                crawler_report_path = os.path.join(caches_dir, f"period_{period_index}_{query_type}_crawler_{url_hash}.md")
                with open(crawler_report_path, 'w', encoding='utf-8') as f:
                    f.write(f"# 爬取结果: {url}\n\n")
                    f.write(str(task.output))
                
                logger.info(f"爬取任务结果已保存至: {crawler_report_path}, 查询类型: {query_type}")
            except Exception as e:
                logger.error(f"保存爬取任务结果时出错: {str(e)}")
                logger.error(traceback.format_exc())
        
        # 创建查询类型汇总报告
        for query_type, tasks_info in query_type_crawler_tasks.items():
            try:
                # 如果查询类型下有多个爬取任务，创建一个汇总报告
                if len(tasks_info) > 1:
                    conclusion_path = os.path.join(reports_dir, f"period_{period_index}_{query_type}_crawler_combined.md")
                    with open(conclusion_path, 'w', encoding='utf-8') as f:
                        f.write(f"# {query_type} 爬取结果汇总\n\n")
                        for task_info in tasks_info:
                            task, url, url_hash = task_info
                            f.write(f"## 来源: {url}\n\n")
                            f.write(str(task.output))
                            f.write("\n\n---\n\n")
                    logger.info(f"{query_type} 爬取结果汇总已保存至: {conclusion_path}")
            except Exception as e:
                logger.error(f"创建{query_type}爬取结果汇总时出错: {str(e)}")
                logger.error(traceback.format_exc())
        
        # 保存查询报告结果
        query_reports = {}
        for i, task in enumerate(report_tasks):
            try:
                # 提取查询类型 - 优先使用[QUERY_TYPE:xxx]标记
                query_type = "unknown"
                if "[QUERY_TYPE:" in task.description:
                    query_type_start = task.description.find("[QUERY_TYPE:") + len("[QUERY_TYPE:")
                    query_type_end = task.description.find("]", query_type_start)
                    if query_type_end > query_type_start:
                        query_type = task.description[query_type_start:query_type_end].strip()
                
                # 如果无法从标记中提取，尝试从任务描述中提取
                if query_type == "unknown":
                    logger.warning(f"报告任务 {i} 的查询类型无法从标记中识别，将尝试从描述中提取")
                    if "trend_query" in task.description.lower():
                        query_type = "trend_query"
                    elif "high_price_query" in task.description.lower():
                        query_type = "high_price_query"
                    elif "low_price_query" in task.description.lower():
                        query_type = "low_price_query"
                    else:
                        # 如果仍然无法识别，尝试从输出中提取
                        for qt in ["trend_query", "high_price_query", "low_price_query"]:
                            if qt in str(task.output).lower():
                                query_type = qt
                                break
                
                # 如果仍无法确定查询类型，使用索引号
                if query_type == "unknown":
                    query_type = f"query_type_{i}"
                
                # 保存查询报告
                query_report_path = os.path.join(reports_dir, f"period_{period_index}_{query_type}_report.md")
                with open(query_report_path, 'w', encoding='utf-8') as f:
                    f.write(f"# {query_type} 查询报告\n\n")
                    f.write(str(task.output))
                
                # 存储报告内容
                query_reports[query_type] = str(task.output)
                
                logger.info(f"查询报告 {query_type} 已保存至: {query_report_path}")
            except Exception as e:
                logger.error(f"保存查询报告结果时出错: {str(e)}")
                logger.error(traceback.format_exc())
        
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
                logger.error(traceback.format_exc())
        
        # 生成综合报告 - 只在有查询报告或总结报告时创建
        if query_reports or period_conclusion:
            combined_report = f"# 时间段 {period_index} 综合报告\n\n"
            
            # 添加各查询报告 - 只在有查询报告时添加
            if query_reports:
                combined_report += "## 查询报告\n\n"
                for query_type, report in query_reports.items():
                    # 使用完整的报告内容
                    combined_report += f"### {query_type}\n\n{report}\n\n---\n\n"
            
            # 添加总结报告 - 只在有总结报告时添加
            if period_conclusion:
                combined_report += "## 综合分析\n\n"
                combined_report += period_conclusion
            else:
                combined_report += "## 综合分析\n\n未能生成综合分析。"
            
            # 保存综合报告 - 现在直接作为period_report返回
            period_report_path = os.path.join(reports_dir, f"period_{period_index}_report.md")
            with open(period_report_path, 'w', encoding='utf-8') as f:
                f.write(combined_report)
            
            logger.info(f"时间段报告已保存至: {period_report_path}")
            
            return combined_report
        else:
            # 如果没有任何报告，返回一个默认报告
            default_report = f"# 时间段 {period_index} 报告\n\n未能生成任何报告内容。"
            
            # 保存默认报告
            default_report_path = os.path.join(reports_dir, f"period_{period_index}_report.md")
            with open(default_report_path, 'w', encoding='utf-8') as f:
                f.write(default_report)
            
            logger.info(f"默认时间段报告已保存至: {default_report_path}")
            
            return default_report

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
        logger.info(f"为时间段 {self.period_index} 生成搜索查询...")
        
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
        high_before_date = self._date_offset(high_price_date, -3)
        high_after_date = self._date_offset(high_price_date, 5)
        high_price_query = f"{indicator} hit peak after:{high_before_date} before:{high_after_date}"
        
        # 计算低价日期前后7天的时间范围
        low_before_date = self._date_offset(low_price_date, -3)
        low_after_date = self._date_offset(low_price_date, 5)
        low_price_query = f"{indicator} bottom out after:{low_before_date} before:{low_after_date}"
        
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