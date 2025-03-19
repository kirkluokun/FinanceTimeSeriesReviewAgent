#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import pandas as pd
import argparse
import datetime
import pathlib
import matplotlib.pyplot as plt
import numpy as np
import warnings

# 导入两个分析模块
# 注意：Python导入模块时不能包含短横线，需要进行特殊处理
import importlib.util

# 获取当前目录路径
current_dir = os.path.dirname(os.path.abspath(__file__))
# 将当前目录添加到模块搜索路径
sys.path.append(current_dir)

# 动态导入带短横线的模块
sensitive_path = os.path.join(current_dir, "trend-sensitive.py")
insensitive_path = os.path.join(current_dir, "trend-insensitive.py")

# 动态加载带短横线的模块
spec_sensitive = importlib.util.spec_from_file_location(
    "trend_sensitive", sensitive_path)
trend_sensitive = importlib.util.module_from_spec(spec_sensitive)
spec_sensitive.loader.exec_module(trend_sensitive)

spec_insensitive = importlib.util.spec_from_file_location(
    "trend_insensitive", insensitive_path)
trend_insensitive = importlib.util.module_from_spec(spec_insensitive)
spec_insensitive.loader.exec_module(trend_insensitive)

# 从模块获取所需的类和函数
SensitiveTrendAnalyzer = trend_sensitive.TrendAnalyzer
sensitive_plot_trends = trend_sensitive.plot_trends
InsensitiveTrendAnalyzer = trend_insensitive.TrendAnalyzer
insensitive_plot_trends = trend_insensitive.plot_trends

# 导入区间价格分析模块
from duration_price_analysis import analyze_trend_intervals  # noqa: E402

# 禁止图表相关警告
warnings.filterwarnings("ignore", category=UserWarning)
plt.ioff()  # 关闭交互模式，防止图表显示


def run_analysis(input_path, output_dir='results'):
    """
    运行两种趋势分析方法并比较结果
    
    参数:
    input_path: CSV文件路径
    output_dir: 输出目录
    """
    # 读取数据
    df = pd.read_csv(input_path, parse_dates=['date'], index_col='date')
    df = df.sort_index()
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成时间戳
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 获取输入文件名（不含扩展名）
    input_filename = pathlib.Path(input_path).stem
    
    # 使用与analyze相同的价格列
    price_col = 'value'
    if price_col not in df.columns and len(df.columns) > 0:
        price_col = df.columns[0]
    
    # 运行敏感版分析
    print("正在运行敏感版分析...")
    sensitive_analyzer = SensitiveTrendAnalyzer(atr_period=14, swing_threshold=0.618)
    sensitive_trends = sensitive_analyzer.analyze(df, price_col=price_col)
    
    # 保存敏感版CSV结果
    sensitive_csv_filename = (
        f"{timestamp}_{input_filename}-sensitive-trend_analysis.csv")
    sensitive_csv_path = os.path.join(output_dir, sensitive_csv_filename)
    sensitive_trends.to_csv(sensitive_csv_path, index=False, float_format='%.4f')
    
    # 生成敏感版图表
    sensitive_png_filename = (
        f"{timestamp}_{input_filename}-sensitive-trend_visualization.png")
    sensitive_plot_path = os.path.join(output_dir, sensitive_png_filename)
    
    # 使用禁止verbose输出的方式调用绘图函数
    plt.figure(figsize=(12, 8))
    with open(os.devnull, 'w') as f:
        original_stdout = sys.stdout
        sys.stdout = f  # 重定向标准输出到null
        sensitive_plot_trends(
            df, sensitive_trends, sensitive_plot_path, 
            price_col=price_col, dpi=800
        )
        sys.stdout = original_stdout  # 恢复标准输出
    plt.close()
    
    # 运行不敏感版分析
    print("正在运行不敏感版分析...")
    insensitive_analyzer = InsensitiveTrendAnalyzer(
        atr_period=14, swing_threshold=0.618)
    insensitive_trends = insensitive_analyzer.analyze(df, price_col=price_col)
    
    # 保存不敏感版CSV结果
    insensitive_csv_filename = (
        f"{timestamp}_{input_filename}-insensitive-trend_analysis.csv")
    insensitive_csv_path = os.path.join(output_dir, insensitive_csv_filename)
    insensitive_trends.to_csv(
        insensitive_csv_path, index=False, float_format='%.4f')
    
    # 生成不敏感版图表
    insensitive_png_filename = (
        f"{timestamp}_{input_filename}-insensitive-trend_visualization.png")
    insensitive_plot_path = os.path.join(output_dir, insensitive_png_filename)
    
    # 使用禁止verbose输出的方式调用绘图函数
    plt.figure(figsize=(12, 8))
    with open(os.devnull, 'w') as f:
        original_stdout = sys.stdout
        sys.stdout = f  # 重定向标准输出到null
        insensitive_plot_trends(
            df, insensitive_trends, insensitive_plot_path, 
            price_col=price_col, dpi=800
        )
        sys.stdout = original_stdout  # 恢复标准输出
    plt.close()
    
    # 调用区间价格分析模块处理敏感版和不敏感版的CSV文件
    print("正在进行区间价格分析...")
    
    # 处理敏感版CSV
    sensitive_enhanced_csv_filename = (
        f"{timestamp}_{input_filename}-sensitive-enhanced_analysis.csv")
    sensitive_enhanced_csv_path = os.path.join(
        output_dir, sensitive_enhanced_csv_filename)
    sensitive_enhanced_trends = analyze_trend_intervals(
        sensitive_csv_path, 
        input_path, 
        sensitive_enhanced_csv_path
    )
    
    # 处理不敏感版CSV
    insensitive_enhanced_csv_filename = (
        f"{timestamp}_{input_filename}-insensitive-enhanced_analysis.csv")
    insensitive_enhanced_csv_path = os.path.join(
        output_dir, insensitive_enhanced_csv_filename)
    insensitive_enhanced_trends = analyze_trend_intervals(
        insensitive_csv_path, 
        input_path, 
        insensitive_enhanced_csv_path
    )
    
    # 生成合并报告
    generate_comparison_report(
        df, 
        (sensitive_enhanced_trends 
         if sensitive_enhanced_trends is not None 
         else sensitive_trends), 
        (insensitive_enhanced_trends 
         if insensitive_enhanced_trends is not None 
         else insensitive_trends), 
        output_dir,
        timestamp,
        input_filename
    )
    
    print(f"\n分析完成! 结果保存到 {output_dir} 文件夹")
    print(f"敏感版CSV文件: {sensitive_csv_filename}")
    print(f"敏感版增强分析CSV文件: {sensitive_enhanced_csv_filename}")
    print(f"敏感版图表文件: {sensitive_png_filename}")
    print(f"不敏感版CSV文件: {insensitive_csv_filename}")
    print(f"不敏感版增强分析CSV文件: {insensitive_enhanced_csv_filename}")
    print(f"不敏感版图表文件: {insensitive_png_filename}")
    
    return output_dir


def generate_comparison_report(df, sensitive_trends, insensitive_trends, 
                               output_dir, timestamp, input_filename):
    """生成比较两种方法的统计报告"""
    print("正在生成比较报告...")
    
    # 处理日期列
    for df_trends in [sensitive_trends, insensitive_trends]:
        if isinstance(df_trends['start_date'].iloc[0], str):
            df_trends['start_date'] = pd.to_datetime(df_trends['start_date'])
        if isinstance(df_trends['end_date'].iloc[0], str):
            df_trends['end_date'] = pd.to_datetime(df_trends['end_date'])
    
    # 计算持续天数
    sensitive_trends['持续天数'] = (
        (sensitive_trends['end_date'] - sensitive_trends['start_date']).dt.days)
    insensitive_trends['持续天数'] = (
        (insensitive_trends['end_date'] - insensitive_trends['start_date']).dt.days)
    
    # 统计基本信息
    sensitive_stats = {
        "总区间数": len(sensitive_trends),
        "上升趋势数": len(sensitive_trends[sensitive_trends['trend_type'] == 'up']),
        "下降趋势数": len(sensitive_trends[sensitive_trends['trend_type'] == 'down']),
        "震荡区间数": len(
            sensitive_trends[sensitive_trends['trend_type'] == 'consolidation']),
        "平均区间长度(天)": sensitive_trends['持续天数'].mean(),
        "最长区间(天)": sensitive_trends['持续天数'].max(),
        "最短区间(天)": sensitive_trends['持续天数'].min(),
        "平均变动幅度(%)": sensitive_trends['pct_change'].abs().mean() * 100,
        "最大上涨幅度(%)": sensitive_trends['pct_change'].max() * 100,
        "最大下跌幅度(%)": sensitive_trends['pct_change'].min() * 100
    }
    
    insensitive_stats = {
        "总区间数": len(insensitive_trends),
        "上升趋势数": len(insensitive_trends[insensitive_trends['trend_type'] == 'up']),
        "下降趋势数": len(insensitive_trends[insensitive_trends['trend_type'] == 'down']),
        "震荡区间数": len(
            insensitive_trends[insensitive_trends['trend_type'] == 'consolidation']),
        "平均区间长度(天)": insensitive_trends['持续天数'].mean(),
        "最长区间(天)": insensitive_trends['持续天数'].max(),
        "最短区间(天)": insensitive_trends['持续天数'].min(),
        "平均变动幅度(%)": insensitive_trends['pct_change'].abs().mean() * 100,
        "最大上涨幅度(%)": insensitive_trends['pct_change'].max() * 100,
        "最大下跌幅度(%)": insensitive_trends['pct_change'].min() * 100
    }
    
    # 创建比较DataFrame
    comparison = pd.DataFrame({
        '敏感版分析': sensitive_stats,
        '不敏感版分析': insensitive_stats
    })
    
    # 添加差异列
    comparison['差异'] = comparison['敏感版分析'] - comparison['不敏感版分析']
    # 避免除以零的情况
    comparison['差异百分比'] = (
        (comparison['差异'] / comparison['不敏感版分析'].replace(0, float('nan')) * 100)
        .round(2).fillna(0).astype(str) + '%'
    )
    
    # 保存比较报告CSV
    report_filename = f"{timestamp}_{input_filename}-comparison_report.csv"
    report_path = os.path.join(output_dir, report_filename)
    comparison.to_csv(report_path, float_format='%.2f')
    
    # 生成Markdown报告
    generate_markdown_report(
        df, 
        sensitive_trends, 
        insensitive_trends, 
        comparison, 
        output_dir, 
        timestamp, 
        input_filename
    )
    
    print(f"比较报告已保存: {report_filename}")


def generate_markdown_report(df, sensitive_trends, insensitive_trends, comparison,
                            output_dir, timestamp, input_filename):
    """生成详细的Markdown报告"""
    report_filename = f"{timestamp}_{input_filename}-detailed_report.md"
    report_path = os.path.join(output_dir, report_filename)
    
    # 计算额外统计信息
    data_period = (
        f"{df.index[0].strftime('%Y-%m-%d')} 至 {df.index[-1].strftime('%Y-%m-%d')}")
    total_days = (df.index[-1] - df.index[0]).days
    
    # 生成Markdown内容
    md_content = f"""# 趋势分析比较报告

**分析日期:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**数据文件:** {input_filename}  
**数据周期:** {data_period} ({total_days}天)

## 统计比较

| 指标 | 敏感版分析 | 不敏感版分析 | 差异 | 差异百分比 |
|------|------------|--------------|------|------------|
"""
    
    # 添加每一行统计数据
    for idx, row in comparison.iterrows():
        sens_val = row['敏感版分析']
        insens_val = row['不敏感版分析']
        diff_val = row['差异']
        
        # 格式化数值
        if isinstance(sens_val, float):
            sens_val = f"{sens_val:.2f}"
        if isinstance(insens_val, float):
            insens_val = f"{insens_val:.2f}"
        if isinstance(diff_val, float):
            diff_val = f"{diff_val:.2f}"
            
        md_content += (
            f"| {idx} | {sens_val} | {insens_val} | {diff_val} | "
            f"{row['差异百分比']} |\n"
        )
    
    # 添加敏感版趋势分布表格
    md_content += """
## 敏感版趋势分布

| 开始日期 | 结束日期 | 趋势类型 | 持续天数 | 价格变动(%) | 最高价日期 | 最低价日期 |
|----------|----------|----------|----------|------------|-----------|-----------|
"""
    
    # 添加敏感版的每个趋势，转换趋势类型显示
    for _, trend in sensitive_trends.iterrows():
        price_change = trend['pct_change'] * 100
        # 转换趋势类型为中文显示
        trend_type_display = (
            "上升" if trend['trend_type'] == 'up' 
            else "下降" if trend['trend_type'] == 'down' 
            else "震荡"
        )
        
        # 获取最高价和最低价日期，如果存在的话
        high_price_date = trend.get('high_price_date', '')
        low_price_date = trend.get('low_price_date', '')
        
        md_content += (
            f"| {trend['start_date'].strftime('%Y-%m-%d')} | "
            f"{trend['end_date'].strftime('%Y-%m-%d')} | "
            f"{trend_type_display} | "
            f"{trend['持续天数']} | "
            f"{price_change:.2f}% | "
            f"{high_price_date} | "
            f"{low_price_date} |\n"
        )
    
    # 添加不敏感版趋势分布表格
    md_content += """
## 不敏感版趋势分布

| 开始日期 | 结束日期 | 趋势类型 | 持续天数 | 价格变动(%) | 最高价日期 | 最低价日期 |
|----------|----------|----------|----------|------------|-----------|-----------|
"""
    
    # 添加不敏感版的每个趋势，转换趋势类型显示
    for _, trend in insensitive_trends.iterrows():
        price_change = trend['pct_change'] * 100
        # 转换趋势类型为中文显示
        trend_type_display = (
            "上升" if trend['trend_type'] == 'up' 
            else "下降" if trend['trend_type'] == 'down' 
            else "震荡"
        )
        
        # 获取最高价和最低价日期，如果存在的话
        high_price_date = trend.get('high_price_date', '')
        low_price_date = trend.get('low_price_date', '')
        
        md_content += (
            f"| {trend['start_date'].strftime('%Y-%m-%d')} | "
            f"{trend['end_date'].strftime('%Y-%m-%d')} | "
            f"{trend_type_display} | "
            f"{trend['持续天数']} | "
            f"{price_change:.2f}% | "
            f"{high_price_date} | "
            f"{low_price_date} |\n"
        )
    
    # 添加趋势分布比较
    md_content += """
## 趋势分析对比结论

- 敏感版分析倾向于捕捉更多的小波动，因此通常会产生更多的区间数量。
- 不敏感版分析专注于更大的趋势变化，过滤掉短期波动，通常产生更少、更长的区间。
- 两种方法各有优缺点：
  - 敏感版适合短期交易策略，能捕捉更多交易机会。
  - 不敏感版适合中长期趋势跟踪，减少错误信号。
- 实际应用中可根据交易周期和风险偏好选择合适的方法。

## 区间价格分析

- 每个趋势区间内的最高价和最低价可以帮助理解价格波动的极值。
- 最高价日期和最低价日期显示了区间内价格达到极值的时间点。
- 这些信息对于理解趋势的形成和转折点非常有价值。
- 在交易策略中，可以利用这些信息设置止损和止盈点位。
"""
    
    # 写入Markdown文件
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    print(f"详细Markdown报告已保存: {report_filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="运行敏感和不敏感版本的趋势分析并生成比较报告")
    parser.add_argument("input_path", help="输入CSV文件的路径")
    parser.add_argument(
        "--output-dir", default="results", help="输出目录，默认为results")
    
    args = parser.parse_args()
    
    run_analysis(args.input_path, args.output_dir)
