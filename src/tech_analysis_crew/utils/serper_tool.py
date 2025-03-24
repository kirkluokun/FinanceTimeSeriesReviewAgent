"""
Serper.dev API 搜索工具
"""

import os
import json
import requests
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from crewai.tools import BaseTool

# 加载环境变量
load_dotenv()


class SerperDevTool(BaseTool):
    """
    使用Serper.dev API进行谷歌搜索的工具
    """
    
    name: str = "SerperDevTool"
    description: str = "使用Serper.dev API在Google上执行搜索查询"
    
    # 声明其他必要的属性
    api_key: str = ""
    base_url: str = "https://google.serper.dev/search"
    headers: Dict[str, str] = {}
    
    def __init__(self):
        """初始化Serper搜索工具"""
        super().__init__()
        # 设置API密钥
        api_key = os.environ.get("SERPER_API_KEY", "")
        if not api_key:
            print("警告: SERPER_API_KEY 环境变量未设置")
        
        # 使用属性赋值而不是直接设置字段
        self.__dict__["api_key"] = api_key
        self.__dict__["headers"] = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json"
        }
    
    def _run(self, query: str, mock: bool = False) -> Dict[str, Any]:
        """
        执行搜索查询
        
        Args:
            query: 搜索查询字符串
            mock: 是否使用模拟数据（用于测试）
            
        Returns:
            搜索结果字典
        """
        if mock:
            # 模拟响应用于测试
            return self._get_mock_response(query)
        
        try:
            # 构建请求体
            payload = {
                "q": query,
                "gl": "us",  # 地理位置：美国
                "hl": "en",  # 语言：英文
                "num": 1  # 搜索结果数量
            }
            
            # 发送请求
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload
            )
            
            # 检查响应状态
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            
            # 添加元数据
            result["_metadata"] = {
                "query": query,
                "timestamp": self._get_timestamp()
            }
            
            return result
        except Exception as e:
            return {
                "error": str(e),
                "_metadata": {
                    "query": query,
                    "timestamp": self._get_timestamp(),
                    "status": "error"
                }
            }
    
    def _get_mock_response(self, query: str) -> Dict[str, Any]:
        """
        生成模拟搜索响应（用于测试）
        
        Args:
            query: 搜索查询字符串
            
        Returns:
            模拟搜索结果
        """
        return {
            "searchParameters": {
                "q": query,
                "gl": "cn",
                "hl": "zh-cn",
                "num": 10
            },
            "organic": [
                {
                    "title": "模拟搜索结果1",
                    "link": "https://example.com/result1",
                    "snippet": f"这是关于 {query} 的模拟搜索结果1。",
                    "position": 1
                },
                {
                    "title": "模拟搜索结果2",
                    "link": "https://example.com/result2",
                    "snippet": f"这是关于 {query} 的模拟搜索结果2。",
                    "position": 2
                }
            ],
            "_metadata": {
                "query": query,
                "timestamp": self._get_timestamp(),
                "status": "mock"
            }
        }
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
    # 实现CrewAI工具所需的接口
    def run(self, query: str, mock: bool = False) -> Dict[str, Any]:
        """
        执行搜索查询（公开方法）
        
        Args:
            query: 搜索查询字符串
            mock: 是否使用模拟数据（用于测试）
            
        Returns:
            搜索结果字典
        """
        return self._run(query, mock)
    
    # 别名方法
    def search(self, query: str, mock: bool = False) -> Dict[str, Any]:
        """
        执行搜索查询（更具描述性的别名）
        
        Args:
            query: 搜索查询字符串
            mock: 是否使用模拟数据（用于测试）
            
        Returns:
            搜索结果字典
        """
        return self.run(query, mock)

