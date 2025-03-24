#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
时间序列分析后端
提供统一的接口，封装整个时间序列分析工作流
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import concurrent.futures

# 导入所需模块
from src.tech_analysis_crew.crew import TimeSeriesAnalysisCrew, TimeSeriesAnalysisFlow
from src.tech_analysis_crew.utils.dataprocess import DataProcessor
from src.tech_analysis_crew.utils.serper_tool import SerperDevTool
from src.tech_analysis_crew.utils.firecrawl_scrape_web_md_clean import FirecrawlScrapeMdCleanTool


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("RunTechAnalysisBackend")


# 自定义异常类
class IndicatorExtractionError(Exception):
    """指标提取失败异常"""
    pass


class ProgressCallback:
    """进度回调处理器"""
    
    def __init__(self, backend):
        """初始化回调处理器
        
        Args:
            backend: RunTechAnalysisBackend 实例
        """
        self.backend = backend
    
    def on_start(self, flow_instance: TimeSeriesAnalysisFlow):
        """流程开始回调"""
        logger.info("分析流程开始")
        self.backend._update_progress("started", "分析流程开始")
    
    def on_indicator_extracted(self, indicator: str):
        """指标提取完成回调"""
        logger.info(f"指标提取完成: {indicator}")
        self.backend._update_progress("indicator_extracted", f"已提取指标: {indicator}")
        self.backend.progress["indicator"] = indicator
    
    def on_period_start(self, period_index: int, total_periods: int):
        """时间段分析开始回调"""
        logger.info(f"开始分析时间段 {period_index+1}/{total_periods}")
        self.backend._update_progress(
            "analyzing_time_periods",
            f"正在分析时间段 {period_index+1}/{total_periods}"
        )
    
    def on_period_complete(self, period_index: int, total_periods: int):
        """时间段分析完成回调"""
        logger.info(f"时间段 {period_index+1}/{total_periods} 分析完成")
    
    def on_crawl_start(self, url: str):
        """网页爬取开始回调"""
        logger.info(f"开始爬取: {url}")
        self.backend._update_progress("crawling", f"正在爬取: {url}")
    
    def on_crawl_complete(self, url: str):
        """网页爬取完成回调"""
        logger.info(f"爬取完成: {url}")
    
    def on_report_generation_start(self):
        """报告生成开始回调"""
        logger.info("开始生成报告")
        self.backend._update_progress("generating_report", "正在生成报告")
    
    def on_report_generation_complete(self, report_path: str):
        """报告生成完成回调"""
        logger.info(f"报告生成完成: {report_path}")
        self.backend._update_progress("completed", "分析完成")
        self.backend.progress["output_file"] = report_path
    
    def on_error(self, error: str):
        """错误回调"""
        logger.error(f"发生错误: {error}")
        self.backend._update_progress("error", f"发生错误: {error}")


class RunTechAnalysisBackend:
    """
    技术分析后端
    封装整个时间序列分析工作流，提供统一的接口
    """
    
    def __init__(self):
        """初始化后端"""
        # 初始化数据处理器
        self.data_processor = DataProcessor()
        
        # 初始化工具
        self.serper_tool = SerperDevTool()
        self.firecrawl_tool = FirecrawlScrapeMdCleanTool()
        
        # 初始化Crew
        self.crew = TimeSeriesAnalysisCrew()
        
        # 设置默认输入/输出路径
        self.default_input_path = os.path.join(
            os.path.dirname(__file__), "input", "test.csv"
        )
        self.output_dir = os.path.join(os.path.dirname(__file__), "output")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 初始化进度状态
        self.progress = {
            "status": "initialized",
            "current_step": "",
            "total_steps": 5,
            "current_step_index": 0,
            "error": None,
            "job_id": "",
            "output_file": "",
            "start_time": "",
            "end_time": "",
            "indicator": ""
        }
        
        # 创建回调处理器
        self.callback = ProgressCallback(self)
        
        logger.info("技术分析后端初始化完成")
    
    def extract_indicator(self, user_query: str) -> str:
        """
        从用户查询中提取指标
        
        Args:
            user_query: 用户输入的查询字符串
            
        Returns:
            提取的指标字符串
            
        Raises:
            IndicatorExtractionError: 当指标提取失败时抛出
        """
        logger.info(f"从用户查询中提取指标: {user_query}")
        self._update_progress("extracting_indicator", "正在提取指标...")
        
        try:
            # 使用Crew中的方法提取指标，添加超时控制
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(self.crew._extract_indicator_with_agent, user_query)
                try:
                    # 设置60秒超时
                    indicator = future.result(timeout=60)
                    
                    if not indicator or indicator == "fail":
                        error_msg = "指标提取失败，无法继续分析"
                        logger.error(error_msg)
                        self._update_progress("error", error_msg)
                        raise IndicatorExtractionError(error_msg)
                    
                    logger.info(f"提取的指标: {indicator}")
                    self.progress["indicator"] = indicator
                    return indicator
                    
                except concurrent.futures.TimeoutError:
                    error_msg = "指标提取超时，无法继续分析"
                    logger.error(error_msg)
                    self._update_progress("error", error_msg)
                    raise IndicatorExtractionError(error_msg)
            
        except Exception as e:
            error_msg = f"提取指标时出错: {str(e)}"
            logger.error(error_msg)
            self._update_progress("error", error_msg)
            raise IndicatorExtractionError(error_msg)
    
    def analyze(self, input_file: Optional[str] = None, user_query: str = "") -> Dict[str, Any]:
        """
        执行完整的时间序列分析
        
        Args:
            input_file: 输入CSV文件路径，如果为None则使用默认路径
            user_query: 用户查询字符串，用于提取指标
            
        Returns:
            包含分析结果和状态信息的字典
        """
        # 记录开始时间
        start_time = datetime.now()
        self.progress["start_time"] = start_time.isoformat()
        
        # 生成作业ID
        job_id = self.data_processor.generate_job_id()
        self.progress["job_id"] = job_id
        
        logger.info(f"开始分析任务 [作业ID: {job_id}]")
        
        # 设置输入文件路径
        if input_file is None or not os.path.exists(input_file):
            input_file = self.default_input_path
            logger.info(f"使用默认输入文件: {input_file}")
        else:
            logger.info(f"使用指定输入文件: {input_file}")
        
        try:
            # 1. 提取指标
            try:
                indicator = self.extract_indicator(user_query)
            except IndicatorExtractionError as e:
                # 指标提取失败，终止程序
                logger.error(f"指标提取失败，终止分析: {str(e)}")
                self._update_progress("error", f"指标提取失败，终止分析: {str(e)}")
                
                # 记录结束时间
                end_time = datetime.now()
                self.progress["end_time"] = end_time.isoformat()
                
                # 返回错误信息
                return {
                    "status": "error",
                    "job_id": job_id,
                    "error": str(e),
                    "progress": self.progress
                }
            
            # 2. 创建并配置分析流程
            flow = TimeSeriesAnalysisFlow(input_file, indicator)
            
            # 3. 注册回调
            flow.on_start = self.callback.on_start
            flow.on_indicator_extracted = self.callback.on_indicator_extracted
            flow.on_period_start = self.callback.on_period_start
            flow.on_period_complete = self.callback.on_period_complete
            flow.on_crawl_start = self.callback.on_crawl_start
            flow.on_crawl_complete = self.callback.on_crawl_complete
            flow.on_report_generation_start = self.callback.on_report_generation_start
            flow.on_report_generation_complete = self.callback.on_report_generation_complete
            flow.on_error = self.callback.on_error
            
            # 4. 启动分析流程
            result = flow.kickoff()
            
            # 记录结束时间
            end_time = datetime.now()
            self.progress["end_time"] = end_time.isoformat()
            
            # 计算总耗时
            duration = (end_time - start_time).total_seconds()
            logger.info(f"分析任务完成 [作业ID: {job_id}] 总耗时: {duration:.2f}秒")
            
            # 返回结果
            return {
                "status": "success",
                "job_id": job_id,
                "indicator": indicator,
                "input_file": input_file,
                "output_file": result.get("final_report_path", ""),
                "summary_file": result.get("summary_path", ""),
                "progress": self.progress,
                "duration": duration
            }
            
        except Exception as e:
            logger.error(f"分析过程中出错: {str(e)}")
            self._update_progress("error", f"分析过程中出错: {str(e)}")
            
            # 记录结束时间
            end_time = datetime.now()
            self.progress["end_time"] = end_time.isoformat()
            
            # 返回错误信息
            return {
                "status": "error",
                "job_id": job_id,
                "error": str(e),
                "progress": self.progress
            }
    
    def _update_progress(self, status: str, message: str) -> None:
        """
        更新进度状态
        
        Args:
            status: 状态标识
            message: 状态消息
        """
        self.progress["status"] = status
        self.progress["current_step"] = message
        
        # 更新步骤索引
        step_indices = {
            "initialized": 0,
            "started": 1,
            "extracting_indicator": 2,
            "indicator_extracted": 3,
            "analyzing_time_periods": 4,
            "crawling": 5,
            "generating_report": 6,
            "completed": 7,
            "error": -1
        }
        
        self.progress["current_step_index"] = step_indices.get(status, 0)
        
        # 如果是错误状态，记录错误信息
        if status == "error":
            self.progress["error"] = message
        
        logger.info(f"进度更新: {status} - {message}")


# 如果直接运行此脚本，执行示例分析
if __name__ == "__main__":
    # 禁用CrewAI遥测以避免SSL错误
    os.environ["OTEL_SDK_DISABLED"] = "true"
    
    # 解析命令行参数
    import argparse
    
    parser = argparse.ArgumentParser(description="时间序列分析后端")
    parser.add_argument("--input", type=str, help="输入CSV文件路径")
    parser.add_argument("--query", type=str, default="分析铜价走势", help="用户查询")
    
    args = parser.parse_args()
    
    # 创建后端实例
    backend = RunTechAnalysisBackend()
    
    # 执行分析
    result = backend.analyze(args.input, args.query)
    
    # 打印结果
    print(json.dumps(result, ensure_ascii=False, indent=2))