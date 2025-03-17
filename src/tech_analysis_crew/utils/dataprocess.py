"""
数据处理工具，用于处理时间序列数据
"""

import os
import json
import pandas as pd
import uuid
import csv
import re
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime


class DataProcessingTool:
    """数据处理工具类，包装DataProcessor的方法为CrewAI工具"""
    
    def __init__(self):
        self.processor = DataProcessor()
    
    def csv_to_json(self, file_path: str) -> str:
        """将CSV转换为JSON"""
        data = self.processor.csv_to_json(file_path)
        return json.dumps(data, ensure_ascii=False, indent=2)
        
    def save_json(self, data: Any, output_path: str) -> str:
        """保存数据为JSON文件"""
        return self.processor.save_json(data, output_path)
        
    def prepare_output_directories(self, job_id: str) -> Dict[str, str]:
        """准备输出目录"""
        return self.processor.prepare_output_directories(job_id)
    
class DataProcessor:
    """数据处理类，处理时间序列数据"""
    
    @staticmethod
    def generate_job_id() -> str:
        """生成唯一的作业ID"""
        return str(uuid.uuid4())[:8]
    
    @staticmethod
    def csv_to_json(file_path: str) -> List[Dict[str, Any]]:
        """
        将CSV文件转换为JSON格式
        
        Args:
            file_path: CSV文件路径
            
        Returns:
            包含字典的列表，每个字典对应CSV的一行
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
            
        try:
            # 读取CSV文件
            df = pd.read_csv(file_path)
            
            # 处理缺失值
            df = df.fillna("")
            
            # 转换为JSON格式
            records = df.to_dict(orient='records')
            return records
        except Exception as e:
            raise Exception(f"CSV转换JSON失败: {str(e)}")
    
    @staticmethod
    def save_json(data: Any, output_path: str) -> str:
        """
        保存数据为JSON文件
        
        Args:
            data: 要保存的数据
            output_path: 输出文件路径
            
        Returns:
            保存的文件路径
        """
        # 确保目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return output_path
        except Exception as e:
            raise Exception(f"保存JSON失败: {str(e)}")
    
    @staticmethod
    def prepare_output_directories(job_id: str) -> Dict[str, str]:
        """准备输出目录
        
        Args:
            job_id: 作业ID
            
        Returns:
            包含各目录路径的字典
        """
        # 准备路径
        timestamp = job_id.split('_')[1]  # 提取时间戳
        dir_name = f"{timestamp}_{job_id}"
        
        # 基础路径
        base_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "output",
            dir_name
        )
        
        # 子目录
        base_output_dir = base_path
        serper_output_dir = os.path.join(base_output_dir, "serper")
        memory_dir = os.path.join("memory", dir_name)
        final_report_dir = os.path.join(base_output_dir, "reports")
        cache_dir = os.path.join(base_output_dir, "cache")
        
        # 创建目录
        os.makedirs(base_output_dir, exist_ok=True)
        os.makedirs(serper_output_dir, exist_ok=True)
        os.makedirs(memory_dir, exist_ok=True)
        os.makedirs(final_report_dir, exist_ok=True)
        os.makedirs(cache_dir, exist_ok=True)
        
        return {
            "base_output_dir": base_output_dir,
            "serper_output_dir": serper_output_dir,
            "memory_dir": memory_dir,
            "final_report_dir": final_report_dir,
            "cache_dir": cache_dir
        }

    @staticmethod
    def process_input_file(input_file: str, job_id: str, cache_dir: str) -> Dict[str, Any]:
        """
        处理输入文件，转换为JSON格式并保存到缓存目录
        
        Args:
            input_file: 输入文件路径
            job_id: 作业ID
            cache_dir: 缓存目录路径
            
        Returns:
            处理结果信息
        """
        # 检查文件是否存在
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"文件不存在: {input_file}")
        
        # 读取CSV数据
        try:
            # 使用已有的CSV转JSON方法
            data = DataProcessor.csv_to_json(input_file)
            
            # 生成输出文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(cache_dir, f"{job_id}-{timestamp}-data.json")
            
            # 保存为JSON
            DataProcessor.save_json(data, output_file)
            
            return {
                "data": data,
                "output_file": output_file,
                "record_count": len(data)
            }
        except Exception as e:
            raise Exception(f"处理输入文件失败: {str(e)}")