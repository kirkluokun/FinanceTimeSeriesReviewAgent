#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# 加载测试
from tests.test_llm_config_import import TestLLMConfigImport

# 运行测试
if __name__ == '__main__':
    unittest.main() 