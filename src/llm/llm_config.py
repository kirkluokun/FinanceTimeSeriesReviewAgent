"""
LLM 配置模块
提供不同 LLM 模型的配置和获取方法
"""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class LLMConfig:
    """LLM 配置类，管理不同的 LLM 模型"""
    
    def __init__(self):
        """初始化 LLM 配置"""
        # 设置默认模型
        self.default_model = "gemini-2.0-flash"
        
        # 确保环境变量已设置
        self._check_api_keys()
        
        # 初始化模型配置
        self.models = {
            "gemini-2.0-flash": {
                "provider": "gemini",
                "model": "gemini/gemini-2.0-flash",
                "api_key": os.environ.get("GEMINI_API_KEY"),
            },
            "gpt-4o-mini": {
                "provider": "openai",
                "model": "openai/gpt-4o-mini",
                "api_key": os.environ.get("OPENAI_API_KEY"),
            },
            "deepseek": {
                "provider": "deepseek",
                "model": "deepseek/deepseek-chat",
                "api_key": os.environ.get("DEEPSEEK_API_KEY"),
            },
            "gemini-1.5-pro": {
                "provider": "gemini",
                "model": "gemini/gemini-1.5-pro",
                "api_key": os.environ.get("GEMINI_API_KEY"),
            },
            "deepseek-v3-ARK": {
                "provider": "deepseek-v3-ARK",
                "model": "openai/deepseek-v3-241226",
                "api_key": os.environ.get("ARK_API_KEY"),
                "base_url": "https://ark.cn-beijing.volces.com/api/v3",
            },
            "deepseek-v3-togetherai": {
                "provider": "deepseek-v3-togetherai",
                "model": "together_ai/deepseek-ai/DeepSeek-V3",
                "api_key": os.environ.get("TOGETHER_API_KEY"),
                "base_url": "https://api.together.xyz/v1",
                "temperature": 0.7,
                "max_tokens": 8000
            }
        }
        
        # 备用模型映射
        self.backup_models = {
            "gemini": "deepseek",
            "gpt4o-mini": "deepseek",
        }
    
    def _check_api_keys(self):
        """检查必要的 API 密钥是否已设置"""
        if not os.environ.get("GEMINI_API_KEY"):
            print("警告: GEMINI_API_KEY 未设置，Gemini 模型可能无法使用")
        
        if not os.environ.get("OPENAI_API_KEY"):
            print("警告: OPENAI_API_KEY 未设置，OpenAI 模型可能无法使用")
        
        if not os.environ.get("DEEPSEEK_API_KEY"):
            print("警告: DEEPSEEK_API_KEY 未设置，DeepSeek 模型可能无法使用")
    
    def get_model(self, model_name: Optional[str] = None) -> Dict[str, Any]:
        """
        获取指定的 LLM 模型配置
        
        Args:
            model_name: 模型名称，如果为 None 则使用默认模型
            
        Returns:
            模型配置字典
        """
        # 如果未指定模型名称，使用默认模型
        if model_name is None:
            model_name = self.default_model
        
        # 如果指定的模型不存在，使用默认模型
        if model_name not in self.models:
            print(f"警告: 模型 {model_name} 不存在，使用默认模型 {self.default_model}")
            model_name = self.default_model
        
        return self.models[model_name]
    
    def get_backup_model(self, model_name: str) -> Dict[str, Any]:
        """
        获取指定模型的备用模型配置
        
        Args:
            model_name: 主模型名称
            
        Returns:
            备用模型配置字典
        """
        backup_name = self.backup_models.get(model_name, self.default_model)
        print(f"切换到备用模型: {backup_name}")
        return self.models[backup_name]
    
    def set_default_model(self, model_name: str):
        """
        设置默认模型
        
        Args:
            model_name: 模型名称
        """
        if model_name in self.models:
            self.default_model = model_name
            print(f"默认模型已设置为 {model_name}")
        else:
            print(f"错误: 模型 {model_name} 不存在，默认模型未更改")


# 创建全局 LLM 配置实例
llm_config = LLMConfig()