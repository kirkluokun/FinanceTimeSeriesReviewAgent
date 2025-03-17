#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Firecrawl API 封装脚本，提供网页抓取、网站爬取、结构化数据提取和搜索功能。
专为CrewAI设计，可作为Agent工具使用。

功能：
1. scrape: 单个URL内容抓取
2. crawl: 网站递归爬取
3. llm_extract: 使用LLM提取结构化数据
4. search: 搜索并抓取结果

所有功能支持单个URL或批量URL处理，支持并行处理和请求频率限制。
"""

import os
import json
import time
import uuid
import asyncio
import datetime
import aiohttp
import requests
from typing import List, Dict, Any, Union, Optional
from pathlib import Path
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

# 获取当前脚本所在目录
SCRIPT_DIR = Path(__file__).parent.absolute()

# 加载环境变量
load_dotenv()

# 常量
DEFAULT_API_URL = "https://api.firecrawl.dev/v0"
DEFAULT_CONCURRENT_REQUESTS = 5  # 默认并发请求数
DEFAULT_RATE_LIMIT = 20  # 默认每分钟请求次数限制
REQUEST_TIMEOUT = 60  # 请求超时时间（秒）


class RateLimiter:
    """请求频率限制器"""
    
    def __init__(self, max_calls: int, period: int = 60):
        """
        初始化频率限制器
        
        参数:
            max_calls (int): 指定时间段内允许的最大请求数
            period (int): 时间段长度（秒），默认60秒
        """
        self.max_calls = max_calls
        self.period = period
        self.calls = []
    
    async def acquire(self):
        """
        获取请求许可，如果达到速率限制则等待
        """
        now = time.time()
        # 清理过期的调用记录
        self.calls = [call_time for call_time in self.calls if now - call_time < self.period]
        
        if len(self.calls) >= self.max_calls:
            # 需要等待，直到最早的调用过期
            earliest_call = self.calls[0]
            wait_time = earliest_call + self.period - now
            if wait_time > 0:
                print(f"速率限制: 等待 {wait_time:.2f} 秒...")
                await asyncio.sleep(wait_time)
            self.calls.pop(0)  # 移除最早的调用
        
        self.calls.append(time.time())


class FirecrawlAPI:
    """Firecrawl API 客户端"""
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        api_url: str = DEFAULT_API_URL, 
        concurrent_requests: int = DEFAULT_CONCURRENT_REQUESTS,
        rate_limit: int = DEFAULT_RATE_LIMIT
    ):
        """
        初始化 Firecrawl API 客户端
        
        参数:
            api_key (str, 可选): Firecrawl API 密钥，如果为None则从环境变量获取
            api_url (str, 可选): API 基础URL，默认为 https://api.firecrawl.dev/v0
            concurrent_requests (int, 可选): 最大并发请求数，默认为5
            rate_limit (int, 可选): 每分钟最大请求数，默认为20
        """
        # 获取API密钥
        self.api_key = api_key if api_key else os.getenv("FIRECRAWL_API_KEY")
        if not self.api_key:
            raise ValueError("找不到FIRECRAWL_API_KEY环境变量，请在.env文件中设置")
        
        self.api_url = api_url
        self.concurrent_requests = concurrent_requests
        self.rate_limiter = RateLimiter(rate_limit)
        
        # 请求头
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 结果目录
        self.results_dir = SCRIPT_DIR / "results"
        self.results_dir.mkdir(exist_ok=True)
    
    def _generate_job_id(self) -> str:
        """生成唯一作业ID"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        unique_id = f"{timestamp}_{uuid.uuid4().hex[:8]}"
        return unique_id
    
    def _save_result(self, result: Dict[str, Any], job_type: str) -> Dict[str, Any]:
        """
        保存结果到文件
        
        参数:
            result (dict): 结果数据
            job_type (str): 作业类型 (scrape, crawl, extract, search)
            
        返回:
            dict: 添加了元数据的结果
        """
        # 生成唯一ID和文件名
        job_id = self._generate_job_id()
        timestamp = job_id.split("_")[0]
        file_name = f"firecrawl_{job_type}_{job_id}.json"
        file_path = self.results_dir / file_name
        relative_path = f"results/{file_name}"
        
        # 添加元数据
        result_with_metadata = {
            "id": job_id,
            "output_path": relative_path,
            "timestamp": timestamp,
            "job_type": job_type,
            "data": result
        }
        
        # 保存到文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(result_with_metadata, f, ensure_ascii=False, indent=2)
        
        return result_with_metadata
    
    async def _make_api_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送API请求到Firecrawl
        
        参数:
            endpoint (str): API端点
            data (dict): 请求数据
            
        返回:
            dict: API响应
        """
        await self.rate_limiter.acquire()  # 频率限制检查
        
        url = f"{self.api_url}/{endpoint}"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, 
                headers=self.headers, 
                json=data,
                timeout=REQUEST_TIMEOUT
            ) as response:
                # 检查响应状态
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Firecrawl API错误 ({response.status}): {error_text}")
                
                return await response.json()
    
    async def _process_job_completion(self, job_id: str, endpoint: str) -> Dict[str, Any]:
        """
        检查作业完成状态
        
        参数:
            job_id (str): 作业ID
            endpoint (str): 检查状态的端点
            
        返回:
            dict: 完成的作业结果
        """
        while True:
            await self.rate_limiter.acquire()
            
            url = f"{self.api_url}/{endpoint}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, 
                    headers=self.headers,
                    params={"jobId": job_id},
                    timeout=REQUEST_TIMEOUT
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"检查作业状态错误 ({response.status}): {error_text}")
                    
                    status_data = await response.json()
                    
                    if status_data["status"] == "completed":
                        return status_data
                    elif status_data["status"] == "failed":
                        raise Exception(f"作业失败: {status_data.get('error', '未知错误')}")
                    
                    # 继续等待
                    progress = status_data.get("current", 0) / status_data.get("total", 1) * 100
                    print(f"作业 {job_id} 进行中: {progress:.1f}% ({status_data.get('current', 0)}/{status_data.get('total', 1)})")
                    await asyncio.sleep(2)  # 等待2秒后再次检查

    async def scrape_url_async(
        self, 
        url: str, 
        only_main_content: bool = True,
        javascript: bool = True
    ) -> Dict[str, Any]:
        """
        异步抓取单个URL内容
        
        参数:
            url (str): 要抓取的URL
            only_main_content (bool, 可选): 是否只抓取主要内容，默认为True
            javascript (bool, 可选): 是否执行JavaScript，默认为True
            
        返回:
            dict: 抓取结果
        """
        data = {
            "url": url,
            "pageOptions": {
                "onlyMainContent": only_main_content,
                "javascript": javascript
            }
        }
        
        response = await self._make_api_request("scrape", data)
        
        if not response.get("success"):
            raise Exception(f"抓取失败: {response.get('error', '未知错误')}")
        
        return self._save_result(response.get("data", {}), "scrape")
    
    async def process_urls_batch(
        self,
        urls: List[str],
        process_func,
        *args,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        批量处理多个URL
        
        参数:
            urls (list): URL列表
            process_func (callable): 用于处理每个URL的函数
            *args, **kwargs: 传递给process_func的其他参数
            
        返回:
            list: 处理结果列表
        """
        semaphore = asyncio.Semaphore(self.concurrent_requests)
        
        async def process_with_semaphore(url):
            async with semaphore:
                try:
                    return await process_func(url, *args, **kwargs)
                except Exception as e:
                    print(f"处理 {url} 出错: {str(e)}")
                    return {"url": url, "error": str(e), "success": False}
        
        tasks = [process_with_semaphore(url) for url in urls]
        return await asyncio.gather(*tasks)
    
    def scrape_url(
        self, 
        url: Union[str, List[str]], 
        only_main_content: bool = True,
        javascript: bool = True
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        抓取URL内容（同步版本）
        
        参数:
            url (str 或 list): 要抓取的URL或URL列表
            only_main_content (bool, 可选): 是否只抓取主要内容，默认为True
            javascript (bool, 可选): 是否执行JavaScript，默认为True
            
        返回:
            dict 或 list: 单个抓取结果或结果列表
        """
        async def _run():
            if isinstance(url, list):
                return await self.process_urls_batch(
                    url, 
                    self.scrape_url_async, 
                    only_main_content=only_main_content,
                    javascript=javascript
                )
            else:
                return await self.scrape_url_async(
                    url, 
                    only_main_content=only_main_content,
                    javascript=javascript
                )
        
        return asyncio.run(_run())
    
    async def crawl_url_async(
        self,
        url: str,
        exclude_patterns: List[str] = None,
        include_patterns: List[str] = None,
        max_pages: int = 50,
        max_depth: int = 3,
        javascript: bool = True
    ) -> Dict[str, Any]:
        """
        异步爬取网站
        
        参数:
            url (str): 起始URL
            exclude_patterns (list, 可选): 要排除的URL模式列表，例如 ['blog/*', '*.pdf']
            include_patterns (list, 可选): 要包含的URL模式列表
            max_pages (int, 可选): 最大爬取页面数，默认50
            max_depth (int, 可选): 最大爬取深度，默认3
            javascript (bool, 可选): 是否执行JavaScript，默认True
            
        返回:
            dict: 爬取结果
        """
        # 配置爬取选项
        data = {
            "url": url,
            "crawlerOptions": {
                "maxPages": max_pages,
                "maxDepth": max_depth
            },
            "pageOptions": {
                "javascript": javascript
            }
        }
        
        # 添加排除模式
        if exclude_patterns:
            data["crawlerOptions"]["excludes"] = exclude_patterns
        
        # 添加包含模式
        if include_patterns:
            data["crawlerOptions"]["includes"] = include_patterns
        
        # 提交爬取作业
        response = await self._make_api_request("crawl", data)
        
        if "jobId" not in response:
            raise Exception(f"爬取作业提交失败: {response.get('error', '未知错误')}")
        
        job_id = response["jobId"]
        print(f"爬取作业已提交，作业ID: {job_id}")
        
        # 等待作业完成
        result = await self._process_job_completion(job_id, "crawl-status")
        
        return self._save_result(result.get("data", []), "crawl")
    
    def crawl_url(
        self,
        url: Union[str, List[str]],
        exclude_patterns: List[str] = None,
        include_patterns: List[str] = None,
        max_pages: int = 50,
        max_depth: int = 3,
        javascript: bool = True
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        爬取网站（同步版本）
        
        参数:
            url (str 或 list): 起始URL或URL列表
            exclude_patterns (list, 可选): 要排除的URL模式列表，例如 ['blog/*', '*.pdf']
            include_patterns (list, 可选): 要包含的URL模式列表
            max_pages (int, 可选): 最大爬取页面数，默认50
            max_depth (int, 可选): 最大爬取深度，默认3
            javascript (bool, 可选): 是否执行JavaScript，默认True
            
        返回:
            dict 或 list: 单个爬取结果或结果列表
        """
        async def _run():
            if isinstance(url, list):
                return await self.process_urls_batch(
                    url, 
                    self.crawl_url_async, 
                    exclude_patterns=exclude_patterns,
                    include_patterns=include_patterns,
                    max_pages=max_pages,
                    max_depth=max_depth,
                    javascript=javascript
                )
            else:
                return await self.crawl_url_async(
                    url, 
                    exclude_patterns=exclude_patterns,
                    include_patterns=include_patterns,
                    max_pages=max_pages,
                    max_depth=max_depth,
                    javascript=javascript
                )
        
        return asyncio.run(_run())
    
    async def extract_data_async(
        self,
        url: str,
        extraction_schema: Dict[str, Any],
        extraction_prompt: str = None,
        only_main_content: bool = True,
        javascript: bool = True
    ) -> Dict[str, Any]:
        """
        使用LLM从URL异步提取结构化数据
        
        参数:
            url (str): 要提取数据的URL
            extraction_schema (dict): JSON Schema定义的提取模式
            extraction_prompt (str, 可选): 自定义提取提示
            only_main_content (bool, 可选): 是否只使用主要内容，默认为True
            javascript (bool, 可选): 是否执行JavaScript，默认为True
            
        返回:
            dict: 提取的数据
        """
        # 配置提取选项
        data = {
            "url": url,
            "extractorOptions": {
                "mode": "llm-extraction",
                "extractionSchema": extraction_schema
            },
            "pageOptions": {
                "onlyMainContent": only_main_content,
                "javascript": javascript
            }
        }
        
        # 添加自定义提取提示
        if extraction_prompt:
            data["extractorOptions"]["extractionPrompt"] = extraction_prompt
        
        # 发送请求
        response = await self._make_api_request("scrape", data)
        
        if not response.get("success"):
            raise Exception(f"数据提取失败: {response.get('error', '未知错误')}")
        
        return self._save_result(response.get("data", {}), "extract")
    
    def extract_data(
        self,
        url: Union[str, List[str]],
        extraction_schema: Dict[str, Any],
        extraction_prompt: str = None,
        only_main_content: bool = True,
        javascript: bool = True
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        使用LLM从URL提取结构化数据（同步版本）
        
        参数:
            url (str 或 list): 要提取数据的URL或URL列表
            extraction_schema (dict): JSON Schema定义的提取模式
            extraction_prompt (str, 可选): 自定义提取提示
            only_main_content (bool, 可选): 是否只使用主要内容，默认为True
            javascript (bool, 可选): 是否执行JavaScript，默认为True
            
        返回:
            dict 或 list: 提取的数据或数据列表
        """
        async def _run():
            if isinstance(url, list):
                return await self.process_urls_batch(
                    url, 
                    self.extract_data_async, 
                    extraction_schema=extraction_schema,
                    extraction_prompt=extraction_prompt,
                    only_main_content=only_main_content,
                    javascript=javascript
                )
            else:
                return await self.extract_data_async(
                    url, 
                    extraction_schema=extraction_schema,
                    extraction_prompt=extraction_prompt,
                    only_main_content=only_main_content,
                    javascript=javascript
                )
        
        return asyncio.run(_run())
    
    async def search_async(
        self,
        query: str,
        fetch_page_content: bool = True,
        num_results: int = 5,
        only_main_content: bool = True
    ) -> Dict[str, Any]:
        """
        异步执行搜索并抓取结果页面
        
        参数:
            query (str): 搜索查询
            fetch_page_content (bool, 可选): 是否抓取结果页面内容，默认为True
            num_results (int, 可选): 返回结果数量，默认为5
            only_main_content (bool, 可选): 是否只抓取主要内容，默认为True
            
        返回:
            dict: 搜索结果
        """
        # 配置搜索选项
        data = {
            "query": query,
            "pageOptions": {
                "fetchPageContent": fetch_page_content,
                "onlyMainContent": only_main_content
            },
            "numResults": num_results
        }
        
        # 发送请求
        response = await self._make_api_request("search", data)
        
        if not response.get("success"):
            raise Exception(f"搜索失败: {response.get('error', '未知错误')}")
        
        return self._save_result(response.get("data", []), "search")
    
    def search(
        self,
        query: str,
        fetch_page_content: bool = True,
        num_results: int = 5,
        only_main_content: bool = True
    ) -> Dict[str, Any]:
        """
        执行搜索并抓取结果页面（同步版本）
        
        参数:
            query (str): 搜索查询
            fetch_page_content (bool, 可选): 是否抓取结果页面内容，默认为True
            num_results (int, 可选): 返回结果数量，默认为5
            only_main_content (bool, 可选): 是否只抓取主要内容，默认为True
            
        返回:
            dict: 搜索结果
        """
        async def _run():
            return await self.search_async(
                query,
                fetch_page_content=fetch_page_content,
                num_results=num_results,
                only_main_content=only_main_content
            )
        
        return asyncio.run(_run())


# ======= 外部调用封装函数 =======

def firecrawl_scrape(
    url: Union[str, List[str]], 
    only_main_content: bool = True,
    javascript: bool = True,
    concurrent_requests: int = DEFAULT_CONCURRENT_REQUESTS,
    rate_limit: int = DEFAULT_RATE_LIMIT
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    抓取URL内容
    
    参数:
        url (str 或 list): 要抓取的URL或URL列表
        only_main_content (bool, 可选): 是否只抓取主要内容，默认为True
        javascript (bool, 可选): 是否执行JavaScript，默认为True
        concurrent_requests (int, 可选): 并发请求数，默认为5
        rate_limit (int, 可选): 每分钟请求次数限制，默认为20
        
    返回:
        dict 或 list: 抓取结果
    """
    api = FirecrawlAPI(concurrent_requests=concurrent_requests, rate_limit=rate_limit)
    return api.scrape_url(url, only_main_content=only_main_content, javascript=javascript)


def firecrawl_crawl(
    url: Union[str, List[str]],
    exclude_patterns: List[str] = None,
    include_patterns: List[str] = None,
    max_pages: int = 50,
    max_depth: int = 3,
    javascript: bool = True,
    concurrent_requests: int = DEFAULT_CONCURRENT_REQUESTS,
    rate_limit: int = DEFAULT_RATE_LIMIT
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    爬取网站
    
    参数:
        url (str 或 list): 起始URL或URL列表
        exclude_patterns (list, 可选): 要排除的URL模式列表，例如 ['blog/*', '*.pdf']
        include_patterns (list, 可选): 要包含的URL模式列表
        max_pages (int, 可选): 最大爬取页面数，默认50
        max_depth (int, 可选): 最大爬取深度，默认3
        javascript (bool, 可选): 是否执行JavaScript，默认True
        concurrent_requests (int, 可选): 并发请求数，默认为5
        rate_limit (int, 可选): 每分钟请求次数限制，默认为20
        
    返回:
        dict 或 list: 爬取结果
    """
    api = FirecrawlAPI(concurrent_requests=concurrent_requests, rate_limit=rate_limit)
    return api.crawl_url(
        url, 
        exclude_patterns=exclude_patterns,
        include_patterns=include_patterns,
        max_pages=max_pages,
        max_depth=max_depth,
        javascript=javascript
    )


def firecrawl_extract(
    url: Union[str, List[str]],
    extraction_schema: Dict[str, Any],
    extraction_prompt: str = None,
    only_main_content: bool = True,
    javascript: bool = True,
    concurrent_requests: int = DEFAULT_CONCURRENT_REQUESTS,
    rate_limit: int = DEFAULT_RATE_LIMIT
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    使用LLM从URL提取结构化数据
    
    参数:
        url (str 或 list): 要提取数据的URL或URL列表
        extraction_schema (dict): JSON Schema定义的提取模式
        extraction_prompt (str, 可选): 自定义提取提示
        only_main_content (bool, 可选): 是否只使用主要内容，默认为True
        javascript (bool, 可选): 是否执行JavaScript，默认为True
        concurrent_requests (int, 可选): 并发请求数，默认为5
        rate_limit (int, 可选): 每分钟请求次数限制，默认为20
        
    返回:
        dict 或 list: 提取的数据
    """
    api = FirecrawlAPI(concurrent_requests=concurrent_requests, rate_limit=rate_limit)
    return api.extract_data(
        url, 
        extraction_schema=extraction_schema,
        extraction_prompt=extraction_prompt,
        only_main_content=only_main_content,
        javascript=javascript
    )


def firecrawl_search(
    query: str,
    fetch_page_content: bool = True,
    num_results: int = 5,
    only_main_content: bool = True,
    rate_limit: int = DEFAULT_RATE_LIMIT
) -> Dict[str, Any]:
    """
    执行搜索并抓取结果页面
    
    参数:
        query (str): 搜索查询
        fetch_page_content (bool, 可选): 是否抓取结果页面内容，默认为True
        num_results (int, 可选): 返回结果数量，默认为5
        only_main_content (bool, 可选): 是否只抓取主要内容，默认为True
        rate_limit (int, 可选): 每分钟请求次数限制，默认为20
        
    返回:
        dict: 搜索结果
    """
    api = FirecrawlAPI(rate_limit=rate_limit)
    return api.search(
        query,
        fetch_page_content=fetch_page_content,
        num_results=num_results,
        only_main_content=only_main_content
    )


# ======= 测试函数 =======

def test_scrape():
    """测试网页抓取功能"""
    print("=== 测试网页抓取功能 ===")
    try:
        # 测试单个URL
        result = firecrawl_scrape("https://docs.firecrawl.dev/")
        print(f"✅ 单个URL抓取成功: {result['id']}")
        print(f"✅ 结果保存在: {result['output_path']}")
        
        # 测试多个URL
        urls = [
            "https://docs.firecrawl.dev/features/scrape",
            "https://docs.firecrawl.dev/features/crawl"
        ]
        results = firecrawl_scrape(urls)
        print(f"✅ 批量抓取成功: 处理了 {len(results)} 个URL")
        
        return result
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return None


def test_crawl():
    """测试网站爬取功能"""
    print("\n=== 测试网站爬取功能 ===")
    try:
        # 配置爬取
        result = firecrawl_crawl(
            "https://docs.firecrawl.dev/",
            exclude_patterns=["blog/*"],
            max_pages=10,
            max_depth=2
        )
        print(f"✅ 爬取成功: {result['id']}")
        print(f"✅ 结果保存在: {result['output_path']}")
        print(f"✅ 爬取了 {len(result['data'])} 个页面")
        
        return result
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return None


def test_extract():
    """测试结构化数据提取功能"""
    print("\n=== 测试结构化数据提取功能 ===")
    try:
        # 定义提取模式
        schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "features": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["title", "description"]
        }
        
        result = firecrawl_extract(
            "https://docs.firecrawl.dev/",
            extraction_schema=schema
        )
        print(f"✅ 数据提取成功: {result['id']}")
        print(f"✅ 结果保存在: {result['output_path']}")
        
        return result
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return None


def test_search():
    """测试搜索功能"""
    print("\n=== 测试搜索功能 ===")
    try:
        result = firecrawl_search(
            "web scraping api",
            num_results=3
        )
        print(f"✅ 搜索成功: {result['id']}")
        print(f"✅ 结果保存在: {result['output_path']}")
        print(f"✅ 找到 {len(result['data'])} 个结果")
        
        return result
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return None


if __name__ == "__main__":
    print("==== Firecrawl 测试 ====")
    
    test_scrape()
    test_crawl()
    test_extract()
    test_search()
    
    print("\n==== 测试完成 ====")
