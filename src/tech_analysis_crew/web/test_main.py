#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试main.py的运行情况
"""
import os
import sys
import subprocess
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("TestMain")

# 获取当前目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取tech_analysis_crew目录
tech_analysis_dir = os.path.dirname(current_dir)
# 获取趋势分析工具目录 - 修正路径
trend_analysis_dir = os.path.join(tech_analysis_dir, 'trendanalysis')

# 创建测试CSV文件
test_csv_path = os.path.join(trend_analysis_dir, 'test_data.csv')
with open(test_csv_path, 'w') as f:
    f.write("date,price\n")
    f.write("2023-01-01,100\n")
    f.write("2023-01-02,102\n")
    f.write("2023-01-03,101\n")
    f.write("2023-01-04,103\n")
    f.write("2023-01-05,105\n")

# 配置路径
main_script = os.path.join(trend_analysis_dir, 'main.py')
results_dir = os.path.join(trend_analysis_dir, 'results')

# 确保目录存在
os.makedirs(results_dir, exist_ok=True)

# 运行趋势分析
logger.info(f"运行趋势分析: {main_script} {test_csv_path} --output-dir {results_dir}")

try:
    # 调用主分析脚本，执行趋势分析
    result = subprocess.run(
        [sys.executable, main_script, test_csv_path, '--output-dir', results_dir],
        capture_output=True,
        text=True,
        check=True
    )
    
    logger.info(f"趋势分析输出: {result.stdout}")
    logger.info("测试成功！")
    
except subprocess.CalledProcessError as e:
    logger.error(f"趋势分析执行错误: {e}")
    logger.error(f"错误输出: {e.stderr}")
    
except Exception as e:
    logger.exception(f"测试过程中出现错误: {e}")

# 检查结果目录
results_files = os.listdir(results_dir)
logger.info(f"结果文件列表: {results_files}")

# 删除测试文件
os.remove(test_csv_path)
logger.info("测试完成，已删除测试数据") 