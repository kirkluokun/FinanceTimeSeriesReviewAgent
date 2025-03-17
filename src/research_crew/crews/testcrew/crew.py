#!/usr/bin/env python
# -*- coding: utf-8 -*-

# 必须出现在所有import之前
import os
import sys
from importlib import reload  # <-- 新增，修复reload未定义
from dotenv import load_dotenv

# 确保使用UTF-8编码
if sys.getdefaultencoding() != 'utf-8':
    reload(sys)
    sys.setdefaultencoding('utf-8')

# 环境变量设置
os.environ["TELEMETRY"] = "False"    # 禁用 CrewAI 遥测
os.environ["OTEL_SDK_DISABLED"] = "true"  # 禁用 OpenTelemetry
os.environ['LITELLM_LOG'] = 'DEBUG'  # 替代 set_verbose

# 标准库导入
from datetime import datetime
# from typing import Optional  # <-- 移除未使用的Optional

# 第三方库导入
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool, WebsiteSearchTool
# from datetime import datetime  # <-- 移除重复导入
from .config.llmsetting import gpt4o_llm, claude_llm, deepseek_chat_llm, deepseek_reasoner_llm, gpt4o_mini_llm
import requests.exceptions
import urllib3.exceptions
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter
)

# If you want to run a snippet of code before or after the crew starts, 
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

load_dotenv()

@CrewBase
class ResearchAgent():
	"""ResearchAgent crew"""

	# Learn more about YAML configuration files here:
	# Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
	# Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
	agents_config = 'config/agents.yaml'
	tasks_config = 'config/tasks.yaml'

	# 初始化Deepseek Chat模型
	def __init__(self, topic="default"):
				"""初始化ResearchAgent

		Args:
			topic (str): 研究主题
		"""
		# 禁用OpenTelemetry
		trace.set_tracer_provider(TracerProvider())
		trace.get_tracer_provider().add_span_processor(
			BatchSpanProcessor(ConsoleSpanExporter())
		)
		# 确保在实例化时也禁用遥测
		os.environ["TELEMETRY"] = "False"
		self.topic = topic
		
		try:
			# 初始化所有模型
			# self.llm_claude = claude_llm()
			self.llm_gpt4o = gpt4o_llm()
			self.llm_gpt4o_mini = gpt4o_mini_llm()
			# self.llm_deepseek_chat = deepseek_chat_llm()
			# self.llm_deepseek_reasoner = deepseek_reasoner_llm()
			
		except Exception as e:
			error_msg = f"初始化LLM时发生错误: {str(e)}"
			print(f"错误详情: {error_msg}")
			raise ValueError(error_msg)




	# If you would like to add tools to your agents, you can learn more about it here:
	# https://docs.crewai.com/concepts/agents#agent-tools
	@agent
	def researcher(self) -> Agent:
		return Agent(
			config=self.agents_config['researcher'],
			llm=self.llm_gpt4o_mini,  # 使用DeepSeek Chat模型
			tools=[SerperDevTool()],
		)
	
	
	@agent
	def reporting_analyst(self) -> Agent:
		return Agent(
			config=self.agents_config['reporting_analyst'],
			llm=self.llm_gpt4o,  
			tools=[SerperDevTool(), WebsiteSearchTool()],
		)
	
	# @agent
	# def deep_researcher(self) -> Agent:
	# 	return Agent(
	# 		config=self.agents_config['deep_researcher'],
	# 		llm=self.llm_gpt4o,
	# 	)
	
	@agent
	def manager(self) -> Agent:
		"""创建管理者agent"""
		return Agent(
			config=self.agents_config['manager'],
			llm=self.llm_gpt4o, 
			verbose=True,
			allow_delegation=True
		)

	# To learn more about structured task outputs, 
	# task dependencies, and task callbacks, check out the documentation:
	# https://docs.crewai.com/concepts/tasks#overview-of-a-task
	@task
	def research_task(self) -> Task:
		return Task(
			config=self.tasks_config['research_task'],
		)

	@task
	def reporting_task(self) -> Task:
		# 生成带时间戳的报告文件名
		timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
		report_filename = f"report_{timestamp}_{self.topic}.md"
		
		return Task(
			config=self.tasks_config['reporting_task'],
			output_file=report_filename
		)
	
	@task
	def framework_task(self) -> Task:
		return Task(
			config=self.tasks_config['framework_task'],
		)

	@crew
	def crew(self) -> Crew:
		"""Creates the ResearchAgent crew"""
		try:
			manager = self.manager()
			crew = Crew(
				agents=[
					self.researcher(),
					# self.deep_researcher(),
					self.reporting_analyst(),
				],
				tasks=[
					# self.framework_task(),
					self.research_task(),
					self.reporting_task()
				],
				manager_agent=manager,
				manager_llm=self.llm_gpt4o,
				process=Process.hierarchical,
				verbose=True,
				planning=True,
				planning_llm=self.llm_gpt4o
			)
			return crew
		except Exception as e:
			raise Exception(f"创建Crew时发生错误: {str(e)}")
