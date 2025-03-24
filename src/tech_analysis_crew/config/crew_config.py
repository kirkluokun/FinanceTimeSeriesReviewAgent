"""
Agent和Task的配置模块
定义时间序列分析中使用的Agents和Tasks
"""

from typing import Dict, List, Any
from crewai import Agent, Task, LLM
from src.tech_analysis_crew.utils.firecrawl_scrape_web_md_clean import FirecrawlScrapeMdCleanTool
from src.llm.llm_config import llm_config
import os
import hashlib

class CrewConfig:
    """
    CrewAI配置类
    包含创建Agents和Tasks的方法
    """
    
    @staticmethod
    def create_crawler_agent() -> Agent:
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
            role="Web Content Crawling Expert",
            goal="Accurately extract key information related to specified questions from web content, save original content as MD files, and provide concise summaries",
            backstory="""You are a professional web content intelligence specialist, skilled at extracting critical information from web pages with specific questions in mind.
            Your job is to crawl content from specified URLs, summarize key points for each page, and extract essential information.
            Important data from web pages must be recorded. You need to ensure the extracted content is accurate and complete, and provide summaries that precisely address the core issues.""",
            verbose=True,
            allow_delegation=False,
            tools=crawl_tools,
            llm=gemini_llm
        )
        
        return crawler_agent
    
    @staticmethod
    def create_report_agent() -> Agent:
        """创建报告生成代理"""
        
        # 使用 LLMConfig 获取模型配置
        model_config = llm_config.get_model("gemini-2.0-pro")
        
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
    
    @staticmethod
    def create_conclusion_agent() -> Agent:
        """创建总结代理"""
        
        # 使用 LLMConfig 获取模型配置
        model_config = llm_config.get_model("deepseek-v3-ARK")
        
        # 创建LLM配置
        conclusion_llm = LLM(
            provider=model_config["provider"],
            model=model_config["model"],
            temperature=0.7,
            api_key=model_config["api_key"],
            base_url=model_config["base_url"]
        )
        
        # 创建总结代理
        conclusion_agent = Agent(
            role="Comprehensive Analysis Expert",
            goal="Synthesize multiple reports, extract core insights, and generate in-depth comprehensive analysis",
            backstory="""You are a seasoned comprehensive analysis expert, skilled at examining issues from multiple perspectives and forming holistic views.
            You can organically integrate information from different reports, identify commonalities and differences, and reveal underlying patterns.
            You excel at grasping macro trends while paying attention to micro details, enabling readers to fully understand the logic behind market changes.
            Your analysis has both historical depth and forward-looking vision, providing readers with comprehensive and valuable market insights.""",
            verbose=True,
            allow_delegation=False,
            llm=conclusion_llm
        )
        
        return conclusion_agent
    
    @staticmethod
    def create_crawler_task(url: str, query: str, date: str, agent: Agent, query_type: str, indicator_description: str, cache_dir: str) -> Task:
        """创建爬取任务"""
        # 生成唯一的文件名
        # 使用URL、查询关键词和日期的组合创建哈希，确保文件名唯一性
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        query_hash = hashlib.md5(query.encode()).hexdigest()[:4]
        date_str = date.replace('-', '') if date else "nodate"
        cache_filename = f"{url_hash}_{query_hash}_{date_str}.md"
        cache_path = os.path.join(cache_dir, cache_filename)

        return Task(
            description=f"""
            [TASK_TYPE:crawler][QUERY_TYPE:{query_type}]

            Use the Firecrawl tool to scrape content from the following URL: {url}
            
            Please complete the following tasks:
            1. Use the FirecrawlScrapeMdCleanTool to scrape the page content
            2. Analyze the content with the question "{query}" in mind, noting that the article was published on "{date}", please consider the historical context
            3. Summarize key information related to the "{indicator_description}" financial indicator from the page content, including important events, significant data, and key viewpoints, especially focusing on content that reflects deep-level logic
            4. Ensure the content is accurate and comprehensive. Do not include your own opinions or fabricate facts.
            
            Note: You must save the original scraped webpage content in Markdown format to the specified file path. This is an important step to ensure the analysis process is traceable and reproducible.
            """,
            expected_output=f"""
            A retrospective analysis report based on the page content about "{query}", focusing on analyzing factors affecting the {indicator_description} financial indicator.
            The report should include the source URL at the end, formatted as:
            # Source URL
            [https://www.google.com](https://www.google.com)
            """,
            agent=agent,
            # 增加执行控制参数
            max_execution_time=30,  # 30秒超时
        )
    
    @staticmethod
    def create_report_task(agent: Agent, crawl_tasks: List[Task], query: str, query_type: str = None) -> Task:
        """Create a report generation task, dependent on crawl tasks"""
        return Task(
            description=f"""
            [TASK_TYPE:report][QUERY_TYPE:{query_type}]
            Assuming you are the absolute authority expert in the field related to {query.split("after:")[0].strip()}, please complete the following tasks:
            
            1. The context is the objective content of multiple web pages crawled by previous links.
            2. Based on the analysis of multiple web page contents crawled previously, generate a comprehensive summary report targeting {query}.
            3. Focus on analysis and organization: form the logic of trends (rise, fall, or turning points), and the underlying deep-seated reasons.
            4. When citing evidence from multiple sources around a certain viewpoint, ensure each citation is followed by the URL source, and accuracy is a must.
            
            Please ensure the report content is accurate, comprehensive, and provides valuable insights.
            """,
            expected_output=f"""
            A structurally complete report on the causal analysis of {query.split("after:")[0].strip()}. The report is written in Chinese.
            """,
            agent=agent,
            context=crawl_tasks  # Use crawl tasks as context
        )
    
    @staticmethod
    def create_conclusion_task(agent: Agent, report_tasks: List[Task], period_index: int, 
                              start_date: str, end_date: str, indicator_description: str) -> Task:
        """创建时间段总结任务，依赖于报告任务"""
        
        # 创建任务描述
        task_description = f"""
        [TASK_TYPE:conclusion]
        基于三种查询(trend_query, high_price_query, low_price_query)的分析报告，
        为时间段{period_index}({start_date}至{end_date})撰写一份区间内全面的复盘总结报告。
        
        请完成以下工作：
        1. 综合分析三种查询报告的内容
        2. 详细阐述该时间区间{indicator_description}价格走势的逻辑
        3. 深入分析区间高点和低点所发生的重要事件及其影响
        4. 揭示价格变动背后的根本原因和市场逻辑
        5. 提炼出该时间段最关键的洞察和结论
        
        请确保报告内容系统、全面、深入，并给出有价值的市场洞察。报告使用中文撰写。
        """
        
        expected_output = f"""
        一份markdown格式的报告，针对{start_date}至{end_date}期间{indicator_description}价格走势的全面复盘总结报告，
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
