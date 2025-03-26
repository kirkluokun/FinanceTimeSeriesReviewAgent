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

# 设置matplotlib字体
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Helvetica', 'Lucida Grande', 'Verdana']
plt.rcParams['axes.unicode_minus'] = False

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


def clean_data(df):
    """
    清理数据，去除无效的日期和数值
    
    参数:
    df: 包含日期索引和数值的DataFrame
    
    返回:
    清理后的DataFrame
    """
    # 尝试转换日期列，将无效日期的行标记为 NaT
    try:
        df.index = pd.to_datetime(df.index, errors='coerce')
    except Exception as e:
        print(f"警告: 日期转换过程中出现错误: {e}")
        return None
    
    # 删除日期无效的行
    invalid_dates = df.index.isna()
    if invalid_dates.any():
        invalid_count = invalid_dates.sum()
        print(f"发现 {invalid_count} 行包含无效日期，将被删除")
        df = df[~invalid_dates]
    
    # 确保数值列是数值类型
    numeric_col = df.columns[0]  # 第一列应该是数值列
    df[numeric_col] = pd.to_numeric(df[numeric_col], errors='coerce')
    
    # 删除数值无效的行
    invalid_values = df[numeric_col].isna()
    if invalid_values.any():
        invalid_count = invalid_values.sum()
        print(f"发现 {invalid_count} 行包含无效数值，将被删除")
        df = df[~invalid_values]
    
    # 按日期排序
    df = df.sort_index()
    
    # 如果清理后数据为空，返回 None
    if len(df) == 0:
        print("错误: 清理后没有剩余有效数据")
        return None
        
    print(f"数据清理完成，保留了 {len(df)} 行有效数据")
    return df


def run_analysis(input_path, output_dir='results'):
    """
    运行两种趋势分析方法并比较结果
    
    参数:
    input_path: CSV文件路径
    output_dir: 输出目录
    """
    # 读取数据，不指定列名，让pandas自动使用数字索引作为列名
    try:
        df = pd.read_csv(input_path)
    except Exception as e:
        print(f"错误: 无法读取CSV文件: {e}")
        return None
    
    # 检查是否至少有两列
    if len(df.columns) < 2:
        print("错误: CSV文件必须至少包含两列：日期列和数值列")
        return None
    
    # 将第一列设置为索引，不管其列名是什么
    df.set_index(df.columns[0], inplace=True)
    
    # 清理数据
    df = clean_data(df)
    if df is None:
        print("错误: 数据清理失败，请检查输入文件格式")
        return None
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成时间戳
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 获取输入文件名（不含扩展名）
    input_filename = pathlib.Path(input_path).stem
    
    # 使用与analyze相同的价格列
    price_col = 'close'
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
    sensitive_trends['duration_days'] = (
        (sensitive_trends['end_date'] - sensitive_trends['start_date']).dt.days)
    insensitive_trends['duration_days'] = (
        (insensitive_trends['end_date'] - insensitive_trends['start_date']).dt.days)
    
    # 统计基本信息
    sensitive_stats = {
        "总区间数": len(sensitive_trends),
        "上升趋势数": len(sensitive_trends[sensitive_trends['trend_type'] == 'up']),
        "下降趋势数": len(sensitive_trends[sensitive_trends['trend_type'] == 'down']),
        "震荡区间数": len(
            sensitive_trends[sensitive_trends['trend_type'] == 'consolidation']),
        "平均区间长度(天)": sensitive_trends['duration_days'].mean(),
        "最长区间(天)": sensitive_trends['duration_days'].max(),
        "最短区间(天)": sensitive_trends['duration_days'].min(),
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
        "平均区间长度(天)": insensitive_trends['duration_days'].mean(),
        "最长区间(天)": insensitive_trends['duration_days'].max(),
        "最短区间(天)": insensitive_trends['duration_days'].min(),
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
        f"{df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")
    total_days = (df.index[-1] - df.index[0]).days
    
    # 生成Markdown内容
    md_content = f"""# Trend Analysis Comparison Report

**Analysis Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Data File:** {input_filename}  
**Data Period:** {data_period} ({total_days} days)

## Statistical Comparison

| Metric | Sensitive Analysis | Insensitive Analysis | Difference | Difference % |
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
## Sensitive Version Trend Distribution

| Start Date | End Date | Trend Type | Duration (Days) | Price Change (%) | High Price Date | Low Price Date |
|----------|----------|----------|----------|------------|-----------|-----------|
"""
    
    # 添加敏感版的每个趋势，转换趋势类型显示
    for _, trend in sensitive_trends.iterrows():
        price_change = trend['pct_change'] * 100
        # 转换趋势类型为英文显示
        trend_type_display = (
            "Up" if trend['trend_type'] == 'up' 
            else "Down" if trend['trend_type'] == 'down' 
            else "Consolidation"
        )
        
        # 获取最高价和最低价日期，如果存在的话
        high_price_date = trend.get('high_price_date', '')
        low_price_date = trend.get('low_price_date', '')
        
        md_content += (
            f"| {trend['start_date'].strftime('%Y-%m-%d')} | "
            f"{trend['end_date'].strftime('%Y-%m-%d')} | "
            f"{trend_type_display} | "
            f"{trend['duration_days']} | "
            f"{price_change:.2f}% | "
            f"{high_price_date} | "
            f"{low_price_date} |\n"
        )
    
    # 添加不敏感版趋势分布表格
    md_content += """
## Insensitive Version Trend Distribution

| Start Date | End Date | Trend Type | Duration (Days) | Price Change (%) | High Price Date | Low Price Date |
|----------|----------|----------|----------|------------|-----------|-----------|
"""
    
    # 添加不敏感版的每个趋势，转换趋势类型显示
    for _, trend in insensitive_trends.iterrows():
        price_change = trend['pct_change'] * 100
        # 转换趋势类型为英文显示
        trend_type_display = (
            "Up" if trend['trend_type'] == 'up' 
            else "Down" if trend['trend_type'] == 'down' 
            else "Consolidation"
        )
        
        # 获取最高价和最低价日期，如果存在的话
        high_price_date = trend.get('high_price_date', '')
        low_price_date = trend.get('low_price_date', '')
        
        md_content += (
            f"| {trend['start_date'].strftime('%Y-%m-%d')} | "
            f"{trend['end_date'].strftime('%Y-%m-%d')} | "
            f"{trend_type_display} | "
            f"{trend['duration_days']} | "
            f"{price_change:.2f}% | "
            f"{high_price_date} | "
            f"{low_price_date} |\n"
        )
    
    # 添加趋势分布比较
    md_content += """
## Trend Analysis Comparison Conclusion

- Sensitive analysis tends to capture more minor fluctuations, thus typically generating more intervals.
- Insensitive analysis focuses on larger trend changes, filtering out short-term fluctuations, typically producing fewer but longer intervals.
- Both methods have their advantages and disadvantages:
  - Sensitive version is suitable for short-term trading strategies, capturing more trading opportunities.
  - Insensitive version is suitable for medium to long-term trend tracking, reducing false signals.
- In practical applications, the appropriate method can be chosen based on trading cycle and risk preference.

## Interval Price Analysis

- The highest and lowest prices within each trend interval help understand price fluctuation extremes.
- High price dates and low price dates show when prices reached extremes within the interval.
- This information is valuable for understanding trend formation and turning points.
- In trading strategies, this information can be used to set stop-loss and take-profit levels.
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
