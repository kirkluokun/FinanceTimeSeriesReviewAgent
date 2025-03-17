import functools
from typing import Dict, Optional
import google.generativeai as genai
from datetime import datetime

class TokenTracker:
    """
    通用的LLM token使用追踪器
    """
    def __init__(self):
        self._token_counts = {
            'gemini': {'input': 0, 'output': 0},
            # TODO: 其他模型的token计数器
            # 'openai': {'input': 0, 'output': 0},
            # 'claude': {'input': 0, 'output': 0},
        }
        self._start_time = datetime.now()
    
    def track_gemini(self, func):
        """
        追踪Gemini API调用的token使用情况的装饰器
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # 调用原始函数
                response = func(*args, **kwargs)
                
                # 获取token计数
                if hasattr(response, 'usage_metadata'):
                    # Gemini API的token计数在usage_metadata中
                    metadata = response.usage_metadata
                    self._token_counts['gemini']['input'] += metadata.prompt_token_count
                    self._token_counts['gemini']['output'] += metadata.candidates_token_count
                
                return response
            except Exception as e:
                print(f"Token tracking error: {str(e)}")
                return func(*args, **kwargs)
        return wrapper
    
    def count_prompt_tokens(self, prompt: str) -> int:
        """
        计算输入prompt的token数量
        """
        try:
            model = genai.GenerativeModel('gemini-1.5-pro')
            return model.count_tokens(prompt).total_tokens
        except Exception as e:
            print(f"Token counting error: {str(e)}")
            return 0
    
    def get_token_counts(self, model: Optional[str] = None) -> Dict:
        """
        获取指定模型或所有模型的token使用统计
        """
        if model:
            return self._token_counts.get(model, {})
        return self._token_counts
    
    def print_summary(self):
        """
        打印token使用统计摘要
        """
        duration = (datetime.now() - self._start_time).total_seconds()
        
        print("\n=== Token Usage Summary ===")
        print(f"Duration: {duration:.2f} seconds")
        
        for model, counts in self._token_counts.items():
            if counts['input'] > 0 or counts['output'] > 0:
                print(f"\n{model.upper()} API:")
                print(f"Input tokens:  {counts['input']}")
                print(f"Output tokens: {counts['output']}")
                print(f"Total tokens:  {counts['input'] + counts['output']}")
                print(f"Estimated cost: ${(counts['input'] + counts['output']) * 0.00001:.4f}")  # 假设每1000 tokens $0.01
        
        print("========================")

# 创建全局token追踪器实例
token_tracker = TokenTracker()

# 使用示例
if __name__ == "__main__":
    # 在需要追踪token的函数上使用装饰器
    @token_tracker.track_gemini
    def test_gemini_api():
        model = genai.GenerativeModel('gemini-1.5-pro')
        response = model.generate_content("Hello, how are you?")
        return response
    
    # 测试API调用
    test_gemini_api()
    
    # 打印统计信息
    token_tracker.print_summary()
