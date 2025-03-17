from typing import Any, Dict, Optional, Type, Union
import re
import json
from crewai_tools import FirecrawlScrapeWebsiteTool
from crewai.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr


class FirecrawlScrapeMdCleanToolSchema(BaseModel):
    url: str = Field(description="Website URL")
    timeout: Optional[int] = Field(
        default=60000,
        description="Timeout in milliseconds for the scraping operation. The default value is 30000.",
    )


class FirecrawlScrapeMdCleanTool(FirecrawlScrapeWebsiteTool):
    """
    扩展FirecrawlScrapeWebsiteTool，只保留markdown、description和sourceURL字段。
    不进行其他清理操作，将这三个字段作为JSON返回给agent的LLM来处理。
    """
    model_config = ConfigDict(
        arbitrary_types_allowed=True, validate_assignment=True, frozen=False
    )
    name: str = "Firecrawl web scrape with markdown cleaning tool"
    description: str = "Scrape webpages using Firecrawl, extract only markdown, description and sourceURL fields"
    args_schema: Type[BaseModel] = FirecrawlScrapeMdCleanToolSchema

    def _clean_markdown(self, content: Union[str, Dict]) -> Union[str, Dict]:
        """
        只保留markdown、description和sourceURL字段
        """
        if isinstance(content, str):
            # 如果内容是字符串，直接返回
            return content
        elif isinstance(content, dict):
            # 创建一个新的字典，只包含需要的字段
            cleaned_content = {}
            
            # 保留markdown字段
            if 'markdown' in content:
                cleaned_content['markdown'] = content['markdown']
            
            # 保留description字段（从metadata中提取）
            if 'metadata' in content and 'description' in content['metadata']:
                cleaned_content['description'] = content['metadata']['description']
            
            # 保留sourceURL字段（从metadata中提取）
            if 'metadata' in content and 'sourceURL' in content['metadata']:
                cleaned_content['sourceURL'] = content['metadata']['sourceURL']
            elif 'metadata' in content and 'url' in content['metadata']:
                cleaned_content['sourceURL'] = content['metadata']['url']
            
            # 将结果转换为JSON字符串
            return json.dumps(cleaned_content, ensure_ascii=False)
        else:
            # 其他类型直接返回
            return content

    def _run(
        self,
        url: str,
        timeout: Optional[int] = 30000,
    ):
        """
        重写_run方法，只保留需要的字段
        """
        # 调用父类的_run方法获取原始结果
        result = super()._run(url=url, timeout=timeout)
        
        # 只保留需要的字段
        cleaned_result = self._clean_markdown(result)
        
        return cleaned_result


try:
    from firecrawl import FirecrawlApp

    # Must rebuild model after class is defined
    if not hasattr(FirecrawlScrapeMdCleanTool, "_model_rebuilt"):
        FirecrawlScrapeMdCleanTool.model_rebuild()
        FirecrawlScrapeMdCleanTool._model_rebuilt = True
except ImportError:
    """
    When this tool is not used, then exception can be ignored.
    """
