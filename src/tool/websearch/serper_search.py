import requests
import json
import os
import time
import uuid
import datetime
from pathlib import Path
from dotenv import load_dotenv

# 获取当前脚本所在目录
SCRIPT_DIR = Path(__file__).parent.absolute()

# 加载环境变量
load_dotenv()

def serper_search(query, 
                 date_after=None, 
                 date_before=None, 
                 location="United States", 
                 num=10, 
                 page=1):
    """
    使用Serper API执行Google搜索
    
    参数:
        query (str): 搜索关键词
        date_after (str, 可选): 开始日期，格式 YYYY-MM-DD
        date_before (str, 可选): 结束日期，格式 YYYY-MM-DD
        location (str, 可选): 搜索位置，默认为"United States"
        num (int, 可选): 返回结果数量，默认为10
        page (int, 可选): 页码，默认为1
        
    返回:
        dict: 包含搜索结果和元数据的字典
    """
    # 构建完整的查询字符串
    full_query = query
    if date_after:
        full_query += f" after:{date_after}"
    if date_before:
        full_query += f" before:{date_before}"
    
    # 从环境变量获取API密钥
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        raise ValueError("找不到SERPER_API_KEY环境变量，请在.env文件中设置")
    
    # 请求URL
    url = "https://google.serper.dev/search"
    
    # 构建请求负载
    payload = json.dumps({
        "q": full_query,
        "location": location,
        "num": num,
        "page": page,
    })
    
    # 请求头
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }
    
    # 发送请求
    response = requests.request("POST", url, headers=headers, data=payload)
    
    # 解析响应
    search_results = response.json()
    
    # 生成唯一ID (时间戳+随机ID)
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    unique_id = f"{timestamp}_{uuid.uuid4().hex[:8]}"
    
    # 确保results目录存在
    results_dir = SCRIPT_DIR / "results"
    results_dir.mkdir(exist_ok=True)
    
    # 构建文件路径
    file_name = f"serper_search_{unique_id}.json"
    file_path = results_dir / file_name
    relative_path = f"results/{file_name}"
    
    # 添加元数据
    result_with_metadata = {
        "id": unique_id,
        "output_path": relative_path,
        "query": full_query,
        "timestamp": timestamp,
        **search_results  # 包含原始搜索结果
    }
    
    # 保存结果到文件
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(result_with_metadata, f, ensure_ascii=False, indent=2)
    
    return result_with_metadata