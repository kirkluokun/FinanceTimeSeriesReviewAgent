"""
通用工具函数模块
包含配置加载、ID生成等通用功能
"""

import os
import yaml
import random
from datetime import datetime
from typing import Dict, Any
from crewai import Agent

def generate_job_id() -> str:
    """生成唯一的作业ID"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_suffix = ''.join(random.choices('0123456789', k=4))
    return f"job_{timestamp}_{random_suffix}"

def load_agents_config(config_path: str) -> Dict[str, Agent]:
    """加载agents配置"""
    agents = {}
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            agent_configs = yaml.safe_load(f)
        
        for agent_id, config in agent_configs.items():
            agents[agent_id] = Agent(
                role=config.get("role", ""),
                goal=config.get("goal", ""),
                backstory=config.get("backstory", ""),
                verbose=config.get("verbose", True),
                allow_delegation=config.get("allow_delegation", False)
            )
    except Exception as e:
        raise RuntimeError(f"加载agents配置失败: {str(e)}") from e
    return agents

def load_tasks_config(config_path: str) -> Dict[str, str]:
    """加载tasks配置"""
    tasks = {}
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            tasks_config = yaml.safe_load(f)
        tasks = {task_id: task_id for task_id in tasks_config}
    except Exception as e:
        raise RuntimeError(f"加载tasks配置失败: {str(e)}") from e
    return tasks

def get_config_path(file_name: str) -> str:
    """获取配置文件路径"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, "..", "config", file_name)