#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tavily API 调用脚本
实现 search 和 extract 功能，用于信息检索和网页内容提取

search: 适合做问题检索，tavily会总结页面内容，适合做内容预筛选或者内容提炼总结
extract: 适合提取指定URL的完整内容，获取原始数据
"""
import os
import json
import requests
from datetime import datetime
from typing import Dict, List, Union, Optional, Any
from dotenv import load_dotenv

#####################################
# 可配置参数 - 方便修改
#####################################

# 基础配置
TAVILY_API_BASE_URL = "https://api.tavily.com"
RESULTS_DIR = "results"  # 结果保存目录

# Search 功能配置
SEARCH_ENDPOINT = "/search"
DEFAULT_TOPIC = "general"  # 可选: general, news
DEFAULT_SEARCH_DEPTH = "basic"  # 可选: basic, advanced
DEFAULT_MAX_RESULTS = 5  # 范围: 0-20
DEFAULT_TIME_RANGE = "day"  # 可选: day, week, month, year, d, w, m, y
DEFAULT_DAYS = 3  # 仅当 topic 为 news 时使用
DEFAULT_INCLUDE_ANSWER = True  # 是否包含AI生成的答案
DEFAULT_INCLUDE_RAW_CONTENT = False  # 是否包含原始内容
DEFAULT_INCLUDE_IMAGES = False  # 是否包含图片
DEFAULT_INCLUDE_IMAGE_DESCRIPTIONS = False  # 是否包含图片描述

# Extract 功能配置
EXTRACT_ENDPOINT = "/extract"
DEFAULT_EXTRACT_DEPTH = "basic"  # 可选: basic, advanced
DEFAULT_INCLUDE_IMAGES_EXTRACT = False  # 是否包含图片

#####################################
# 功能实现
#####################################

# 初始化 - 加载环境变量
load_dotenv()

# 获取API密钥
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
if not TAVILY_API_KEY:
    raise ValueError("未找到TAVILY_API_KEY环境变量，请在.env文件中设置")

# 确保结果目录存在
os.makedirs(RESULTS_DIR, exist_ok=True)


def search(
    query: str,
    topic: str = DEFAULT_TOPIC,
    search_depth: str = DEFAULT_SEARCH_DEPTH,
    max_results: int = DEFAULT_MAX_RESULTS,
    time_range: str = DEFAULT_TIME_RANGE,
    days: int = DEFAULT_DAYS,
    include_answer: bool = DEFAULT_INCLUDE_ANSWER,
    include_raw_content: bool = DEFAULT_INCLUDE_RAW_CONTENT,
    include_images: bool = DEFAULT_INCLUDE_IMAGES,
    include_image_descriptions: bool = DEFAULT_INCLUDE_IMAGE_DESCRIPTIONS,
    include_domains: List[str] = None,
    exclude_domains: List[str] = None,
) -> Dict[str, Any]:
    """
    使用Tavily Search API进行信息检索

    Args:
        query (str): 搜索查询字符串
        topic (str, optional): 搜索主题。默认为"general"
        search_depth (str, optional): 搜索深度，basic或advanced。默认为"basic"
        max_results (int, optional): 最大返回结果数量。默认为5
        time_range (str, optional): 时间范围过滤。默认为"day"
        days (int, optional): 回溯的天数，仅当topic为news时有效。默认为3
        include_answer (bool, optional): 是否包含AI生成的答案。默认为True
        include_raw_content (bool, optional): 是否包含原始内容。默认为False
        include_images (bool, optional): 是否包含图片。默认为False
        include_image_descriptions (bool, optional): 是否包含图片描述。默认为False
        include_domains (List[str], optional): 指定包含的域名列表。默认为None
        exclude_domains (List[str], optional): 指定排除的域名列表。默认为None

    Returns:
        Dict[str, Any]: 搜索结果，包含查询、答案、结果列表等
    """
    # 构建API请求URL
    url = f"{TAVILY_API_BASE_URL}{SEARCH_ENDPOINT}"
    
    # 构建请求头
    headers = {
        "Authorization": f"Bearer {TAVILY_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 构建请求体
    data = {
        "query": query,
        "topic": topic,
        "search_depth": search_depth,
        "max_results": max_results,
        "time_range": time_range,
        "days": days,
        "include_answer": include_answer,
        "include_raw_content": include_raw_content,
        "include_images": include_images,
        "include_image_descriptions": include_image_descriptions,
        "include_domains": include_domains or [],
        "exclude_domains": exclude_domains or []
    }
    
    # 发送请求
    print(f"正在搜索: {query}")
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # 如果响应状态码不是200，抛出异常
        
        # 解析结果
        result = response.json()
        
        # 保存结果
        save_result(result, "search")
        
        return result
    
    except Exception as e:
        error_result = {"error": str(e), "query": query}
        save_result(error_result, "search_error")
        print(f"搜索出错: {str(e)}")
        return error_result


def extract(
    urls: Union[str, List[str]],
    include_images: bool = DEFAULT_INCLUDE_IMAGES_EXTRACT,
    extract_depth: str = DEFAULT_EXTRACT_DEPTH
) -> Dict[str, Any]:
    """
    使用Tavily Extract API提取指定URL的内容

    Args:
        urls (Union[str, List[str]]): 单个URL或URL列表
        include_images (bool, optional): 是否包含图片。默认为False
        extract_depth (str, optional): 提取深度，basic或advanced。默认为"basic"

    Returns:
        Dict[str, Any]: 提取结果，包含URL内容、图片等
    """
    # 构建API请求URL
    url = f"{TAVILY_API_BASE_URL}{EXTRACT_ENDPOINT}"
    
    # 构建请求头
    headers = {
        "Authorization": f"Bearer {TAVILY_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 构建请求体
    data = {
        "urls": urls,
        "include_images": include_images,
        "extract_depth": extract_depth
    }
    
    # 发送请求
    print(f"正在提取内容: {urls}")
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # 如果响应状态码不是200，抛出异常
        
        # 解析结果
        result = response.json()
        
        # 保存结果
        save_result(result, "extract")
        
        return result
    
    except Exception as e:
        error_result = {"error": str(e), "urls": urls}
        save_result(error_result, "extract_error")
        print(f"提取内容出错: {str(e)}")
        return error_result


def save_result(result: Dict[str, Any], result_type: str) -> str:
    """
    将结果保存为JSON文件

    Args:
        result (Dict[str, Any]): 要保存的结果
        result_type (str): 结果类型，用于文件命名

    Returns:
        str: 保存的文件路径
    """
    # 生成时间戳和唯一ID
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = hash(str(result) + timestamp) % 10000  # 简单的hash值
    
    # 构建文件名和路径
    filename = f"{result_type}_{timestamp}_{unique_id}.json"
    filepath = os.path.join(RESULTS_DIR, filename)
    
    # 保存为JSON文件
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"结果已保存到: {filepath}")
    return filepath


def main():
    """
    主函数，用于测试
    """
    # 测试search功能
    search_result = search(
        query="什么是人工智能 site:",
        topic="general",
        max_results=3
    )
    print(f"搜索结果: {search_result.get('answer', '')[:100]}...")
    
    # 测试extract功能
    # extract_result = extract(
    #     urls="https://en.wikipedia.org/wiki/Artificial_intelligence"
    # )
    # content_preview = extract_result.get("results", [{}])[0].get("raw_content", "")[:100]
    # print(f"提取内容: {content_preview}...")


if __name__ == "__main__":
    main()