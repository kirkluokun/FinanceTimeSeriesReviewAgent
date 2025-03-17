"""LLM设置模块"""
from langchain.llms.base import LLM
from langchain.callbacks.manager import CallbackManagerForLLMRun
from typing import Any, List, Optional, Dict
import os
from dotenv import load_dotenv
import litellm
from litellm import completion
from pydantic import Field, PrivateAttr

# 加载.env文件
load_dotenv()

# 设置环境变量
os.environ["TELEMETRY"] = "False"    # 禁用 CrewAI 遥测
os.environ["OTEL_SDK_DISABLED"] = "true"  # 禁用 OpenTelemetry，参见 https://docs.crewai.com/telemetry
os.environ['LITELLM_LOG'] = 'DEBUG'  # 替代 set_verbose

class gpt4o_mini_llm(LLM):
    """gpt4o_mini_llm类，实现LangChain LLM接口"""
    
    model_name: str = Field(default="gpt-4o-mini")
    temperature: float = Field(default=0.7)
    _api_key: str = PrivateAttr()
    _api_base: str = PrivateAttr(default="https://api.openai.com/v1")

    def __init__(self):
        super().__init__()
        self._api_key = os.getenv("OPENAI_API_KEY")
        if not self._api_key:
            raise ValueError("请设置OPENAI_API_KEY环境变量")
        
        # 设置litellm配置
        litellm.api_base = self._api_base
        litellm.api_key = self._api_key
        
        # 设置请求头和其他配置
        litellm.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}"
        }

    @property
    def _llm_type(self) -> str:
        return "gpt4o"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """执行LLM调用"""
        try:
            # 构建消息
            messages = [
                {"role": "system", "content": "你是一个非常专业的分析师"},
                {"role": "user", "content": prompt}
            ]
            
            # 设置完整的请求参数
            params = {
                "model": self.model_name,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": 8000,
                "stream": False,
                "request_timeout": 60,
            }
            
            # 如果有stop参数，添加到请求中
            if stop:
                params["stop"] = stop
                
            # 发送请求
            response = completion(**params)
            
            # 检查响应
            if not response or not hasattr(response, 'choices') or not response.choices:
                raise ValueError("无效的API响应")
                
            # 返回生成的文本
            return response.choices[0].message.content
            
        except Exception as e:
            error_msg = f"GPT API调用失败: {str(e)}"
            print(f"错误详情: {error_msg}")  # 添加详细日志
            raise ValueError(error_msg)

class gpt4o_llm(LLM):
    """gpt4o_llm类，实现LangChain LLM接口"""
    
    model_name: str = Field(default="gpt-4o")
    temperature: float = Field(default=0.7)
    _api_key: str = PrivateAttr()
    _api_base: str = PrivateAttr(default="https://api.openai.com/v1")

    def __init__(self):
        super().__init__()
        self._api_key = os.getenv("OPENAI_API_KEY")
        if not self._api_key:
            raise ValueError("请设置OPENAI_API_KEY环境变量")
        
        # 设置litellm配置
        litellm.api_base = self._api_base
        litellm.api_key = self._api_key
        
        # 设置请求头和其他配置
        litellm.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}"
        }

    @property
    def _llm_type(self) -> str:
        return "gpt4o"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """执行LLM调用"""
        try:
            # 构建消息
            messages = [
                {"role": "system", "content": "你是一个非常专业的分析师"},
                {"role": "user", "content": prompt}
            ]
            
            # 设置完整的请求参数
            params = {
                "model": self.model_name,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": 8000,
                "stream": False,
                "request_timeout": 60,
            }
            
            # 如果有stop参数，添加到请求中
            if stop:
                params["stop"] = stop
                
            # 发送请求
            response = completion(**params)
            
            # 检查响应
            if not response or not hasattr(response, 'choices') or not response.choices:
                raise ValueError("无效的API响应")
                
            # 返回生成的文本
            return response.choices[0].message.content
            
        except Exception as e:
            error_msg = f"GPT API调用失败: {str(e)}"
            print(f"错误详情: {error_msg}")  # 添加详细日志
            raise ValueError(error_msg)

class claude_llm(LLM):
    """claude_llm类，实现LangChain LLM接口"""
    model_name: str = Field(default="anthropic/claude-3-5-sonnet-20240620")
    temperature: float = Field(default=0.7)
    _api_key: str = PrivateAttr()
    _api_base: str = PrivateAttr(default=None)  # 可配置Anthropic自定义Base URL

    def __init__(self):
        super().__init__()
        self._api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self._api_key:
            raise ValueError("请设置ANTHROPIC_API_KEY环境变量以使用claude_llm")

        # 这里不需要设置 litellm.api_base 时通常默认调用 Anthropic官方地址
        # 若有自定义路由，可添加: litellm.api_base = self._api_base
        litellm.api_key = self._api_key

    @property
    def _llm_type(self) -> str:
        return "claude"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """执行Anthropic LLM调用"""
        try:
            messages = [
                {"role": "system", "content": "你是一个友好的Claude助手"},
                {"role": "user", "content": prompt},
            ]
            params = {
                "model": self.model_name,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": 2048,
                "stream": False,
                "request_timeout": 60,
            }
            if stop:
                params["stop"] = stop

            response = litellm.completion(**params)
            if not response or not hasattr(response, 'choices') or not response.choices:
                raise ValueError("无效的Anthropic API响应")

            return response.choices[0].message.content

        except Exception as e:
            error_msg = f"Claude LLM调用失败: {str(e)}"
            print(f"错误详情: {error_msg}")
            raise ValueError(error_msg)

class deepseek_chat_llm(LLM):
    """deepseek_llm类，实现LangChain LLM接口"""
    
    model_name: str = Field(default="deepseek/deepseek-chat")
    temperature: float = Field(default=0.7)
    _api_key: str = PrivateAttr()
    _api_base: str = PrivateAttr(default="https://api.deepseek.com/v1")

    def __init__(self):
        super().__init__()
        self._api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self._api_key:
            raise ValueError("请设置DEEPSEEK_API_KEY环境变量")
        
        # 配置LiteLLM参数
        os.environ['LITELLM_LOG'] = 'DEBUG'  # 启用调试日志
        
        # 重置全局配置
        litellm.api_base = None
        litellm.api_key = None
        litellm.headers = None
        litellm.drop_params = True  # 添加这个配置，避免参数冲突

    @property
    def _llm_type(self) -> str:
        return "deepseek"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """执行Deepseek LLM调用"""
        try:
            messages = [
                {"role": "system", "content": "你是一个专业的AI助手"},
                {"role": "user", "content": prompt}
            ]
            
            # 构建请求参数
            completion_kwargs = {
                "model": self.model_name,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": 4096,
                "api_key": self._api_key,
                "api_base": self._api_base,
                "timeout": 60,
            }
            
            if stop:
                completion_kwargs["stop"] = stop
            
            # 使用litellm.completion
            try:
                response = litellm.completion(**completion_kwargs)
                
                # 处理响应
                if isinstance(response, (dict, litellm.ModelResponse)):
                    if hasattr(response, 'choices') and len(response.choices) > 0:
                        if hasattr(response.choices[0], 'message'):
                            return response.choices[0].message.content
                    elif isinstance(response, dict) and 'choices' in response:
                        return response['choices'][0]['message']['content']
                
                raise ValueError(f"无效的响应格式: {response}")
                
            except litellm.APIError as e:
                print(f"LiteLLM API错误: {str(e)}")
                raise
            except Exception as e:
                print(f"调用过程中发生错误: {str(e)}")
                raise
                
        except Exception as e:
            error_msg = f"Deepseek API调用失败: {str(e)}"
            print(f"错误详情: {error_msg}")
            raise ValueError(error_msg)

    # def get_num_tokens(self, text: str) -> int:
    #     """获取文本的token数量"""
    #     try:
    #         # 使用litellm的token计数功能
    #         return litellm.token_counter(model=self.model_name, text=text)
    #     except:
    #         # 如果失败，使用简单的估算（每4个字符约1个token）
    #         return len(text) // 4

class deepseek_reasoner_llm(LLM):
    """deepseek_reasoner_llm类，实现LangChain LLM接口"""
    
    model_name: str = Field(default="deepseek/deepseek-reasoner")
    temperature: float = Field(default=0.7)
    _api_key: str = PrivateAttr()
    _api_base: str = PrivateAttr(default="https://api.deepseek.com/v1")

    def __init__(self):
        super().__init__()
        self._api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self._api_key:
            raise ValueError("请设置DEEPSEEK_API_KEY环境变量")
        
        # 配置LiteLLM参数
        os.environ['LITELLM_LOG'] = 'DEBUG'  # 启用调试日志
        
        # 重置全局配置
        litellm.api_base = None
        litellm.api_key = None
        litellm.headers = None
        litellm.drop_params = True  # 添加这个配置，避免参数冲突

    @property
    def _llm_type(self) -> str:
        return "deepseek_reasoner"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """执行Deepseek Reasoner LLM调用"""
        try:
            # 构建消息列表
            messages = [
                {
                    "role": "system",
                    "content": """你是一个专业的推理助手。请按照以下步骤进行分析：
1. 仔细理解问题
2. 列出关键信息
3. 进行逻辑推理
4. 得出结论"""
                },
                {
                    "role": "user",
                    "content": prompt
                },
                {
                    "role": "assistant",
                    "content": "让我按步骤分析这个问题：\n\n",
                    "prefix_mode": True  # 启用prefix模式
                }
            ]
            
            # 构建请求参数
            completion_kwargs = {
                "model": self.model_name,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": 4096,
                "api_key": self._api_key,
                "api_base": self._api_base,
                "timeout": 60,
                "tools": [],  # 添加空的tools列表
                "tool_choice": "none",  # 禁用工具调用
            }
            
            if stop:
                completion_kwargs["stop"] = stop
            
            # 使用litellm.completion
            try:
                response = litellm.completion(**completion_kwargs)
                
                # 处理响应
                if isinstance(response, (dict, litellm.ModelResponse)):
                    if hasattr(response, 'choices') and len(response.choices) > 0:
                        choice = response.choices[0]
                        if hasattr(choice, 'message'):
                            content = choice.message.content
                            # 移除可能的前缀提示
                            content = content.replace("让我按步骤分析这个问题：\n\n", "")
                            return content
                    elif isinstance(response, dict) and 'choices' in response:
                        content = response['choices'][0]['message']['content']
                        content = content.replace("让我按步骤分析这个问题：\n\n", "")
                        return content
                
                raise ValueError(f"无效的响应格式: {response}")
                
            except litellm.BadRequestError as e:
                print(f"DeepSeek API请求错误: {str(e)}")
                # 如果prefix模式失败，尝试使用简单的用户消息
                if "must be a user message" in str(e):
                    completion_kwargs["messages"] = [{"role": "user", "content": prompt}]
                    response = litellm.completion(**completion_kwargs)
                    return response.choices[0].message.content
                raise
            except litellm.APIError as e:
                print(f"LiteLLM API错误: {str(e)}")
                raise
            except Exception as e:
                print(f"调用过程中发生错误: {str(e)}")
                raise
                
        except Exception as e:
            error_msg = f"Deepseek Reasoner API调用失败: {str(e)}"
            print(f"错误详情: {error_msg}")
            raise ValueError(error_msg)
