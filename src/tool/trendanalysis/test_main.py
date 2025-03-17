import unittest
import os
import pandas as pd
import tempfile
import shutil
from datetime import datetime, timedelta
import sys
import logging
import importlib.util

# 添加父目录到路径，以便导入模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 禁用日志输出，以便测试时不显示日志信息
logging.basicConfig(level=logging.ERROR)

# 动态导入main模块
current_dir = os.path.dirname(os.path.abspath(__file__))
main_path = os.path.join(current_dir, "main.py")
spec = importlib.util.spec_from_file_location("main", main_path)
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)


class TestMainFunctions(unittest.TestCase):
    """测试main.py中的功能"""
    
    def setUp(self):
        """测试前的准备工作"""
        # 创建临时目录
        self.test_dir = tempfile.mkdtemp()
        
        # 创建测试数据
        self.create_test_data()
    
    def tearDown(self):
        """测试后的清理工作"""
        # 删除临时目录
        shutil.rmtree(self.test_dir)
    
    def create_test_data(self):
        """创建测试数据"""
        # 创建原始价格数据
        dates = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(100)]
        prices = [100 + i * 0.5 + (i % 10) * 2 for i in range(100)]  # 创建一个有波动的价格序列
        
        self.original_data = pd.DataFrame({
            'date': dates,
            'close': prices
        })
        
        # 保存原始数据到CSV
        self.original_data_path = os.path.join(self.test_dir, 'test_data.csv')
        self.original_data.to_csv(self.original_data_path, index=False)
        
        # 创建输出目录
        self.output_dir = os.path.join(self.test_dir, 'results')
        os.makedirs(self.output_dir, exist_ok=True)
    
    def test_run_analysis(self):
        """测试run_analysis函数"""
        # 运行分析
        try:
            result_dir = main.run_analysis(self.original_data_path, self.output_dir)
            
            # 检查结果目录是否存在
            self.assertTrue(os.path.exists(result_dir))
            
            # 检查是否生成了敏感版和不敏感版的CSV文件
            files = os.listdir(result_dir)
            sensitive_csv_files = [f for f in files if 'sensitive-trend_analysis.csv' in f]
            insensitive_csv_files = [f for f in files if 'insensitive-trend_analysis.csv' in f]
            
            self.assertTrue(len(sensitive_csv_files) > 0, "未生成敏感版CSV文件")
            self.assertTrue(len(insensitive_csv_files) > 0, "未生成不敏感版CSV文件")
            
            # 检查是否生成了增强分析CSV文件
            sensitive_enhanced_files = [f for f in files if 'sensitive-enhanced_analysis.csv' in f]
            insensitive_enhanced_files = [f for f in files if 'insensitive-enhanced_analysis.csv' in f]
            
            self.assertTrue(len(sensitive_enhanced_files) > 0, "未生成敏感版增强分析CSV文件")
            self.assertTrue(len(insensitive_enhanced_files) > 0, "未生成不敏感版增强分析CSV文件")
            
            # 检查是否生成了图表文件
            sensitive_png_files = [f for f in files if 'sensitive-trend_visualization.png' in f]
            insensitive_png_files = [f for f in files if 'insensitive-trend_visualization.png' in f]
            
            self.assertTrue(len(sensitive_png_files) > 0, "未生成敏感版图表文件")
            self.assertTrue(len(insensitive_png_files) > 0, "未生成不敏感版图表文件")
            
            # 检查是否生成了报告文件
            report_files = [f for f in files if 'comparison_report.csv' in f]
            markdown_files = [f for f in files if 'detailed_report.md' in f]
            
            self.assertTrue(len(report_files) > 0, "未生成比较报告CSV文件")
            self.assertTrue(len(markdown_files) > 0, "未生成详细Markdown报告文件")
            
            # 检查增强分析CSV文件是否包含所需的列
            if len(sensitive_enhanced_files) > 0:
                enhanced_csv_path = os.path.join(result_dir, sensitive_enhanced_files[0])
                enhanced_df = pd.read_csv(enhanced_csv_path)
                
                self.assertIn('high_price_date', enhanced_df.columns, "增强分析CSV文件缺少high_price_date列")
                self.assertIn('low_price_date', enhanced_df.columns, "增强分析CSV文件缺少low_price_date列")
            
            # 检查Markdown报告是否包含区间价格分析部分
            if len(markdown_files) > 0:
                markdown_path = os.path.join(result_dir, markdown_files[0])
                with open(markdown_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.assertIn('## 区间价格分析', content, "Markdown报告缺少区间价格分析部分")
                self.assertIn('最高价日期', content, "Markdown报告缺少最高价日期信息")
                self.assertIn('最低价日期', content, "Markdown报告缺少最低价日期信息")
        
        except Exception as e:
            self.fail(f"运行分析时出错: {e}")


if __name__ == '__main__':
    unittest.main() 