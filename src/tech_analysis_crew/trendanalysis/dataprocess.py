#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import pandas as pd
import argparse
import numpy as np
import re
from pathlib import Path
import datetime


def standardize_csv(input_path):
    """
    将CSV文件标准化为date和value两列格式
    
    参数:
    input_path: 输入CSV文件路径
    
    返回:
    标准化后的DataFrame
    """
    print(f"正在处理文件: {input_path}")
    
    # 尝试读取CSV文件
    try:
        # 首先尝试自动检测分隔符
        df = pd.read_csv(input_path, sep=None, engine='python')
        
        # 如果只有一列，可能是其他分隔符
        if df.shape[1] == 1:
            # 尝试其他常见分隔符
            for sep in ['\t', ';', '|']:
                try:
                    df = pd.read_csv(input_path, sep=sep)
                    if df.shape[1] > 1:
                        break
                except:
                    continue
    except Exception as e:
        print(f"读取文件失败: {e}")
        return None
    
    print(f"原始数据形状: {df.shape}")
    print(f"原始列名: {df.columns.tolist()}")
    
    # 如果列数小于2，可能是格式问题
    if df.shape[1] < 2:
        print("错误: 输入CSV文件必须至少包含两列（日期和值）")
        return None
    
    # 找出日期列和值列
    date_col = None
    value_col = None
    
    # 尝试识别日期列
    for col in df.columns:
        # 将列转换为字符串类型以便处理
        df[col] = df[col].astype(str)
        
        # 检查列中的值是否像日期
        date_count = 0
        for val in df[col].iloc[:20]:  # 检查前20个值
            # 尝试多种常见日期格式
            if re.match(r'\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2}', val) or \
               re.match(r'\d{1,2}[-/\.]\d{1,2}[-/\.]\d{4}', val) or \
               re.match(r'\d{4}\d{2}\d{2}', val) or \
               re.match(r'\d{2}[-/\.]\d{2}[-/\.]\d{2}', val):
                date_count += 1
        
        if date_count > 5:  # 如果超过5个值像日期，就认为这是日期列
            date_col = col
            break
    
    # 如果没找到日期列，使用第一列
    if date_col is None:
        date_col = df.columns[0]
    
    # 值列就是非日期列
    for col in df.columns:
        if col != date_col:
            value_col = col
            break
    
    print(f"识别到的日期列: {date_col}")
    print(f"识别到的值列: {value_col}")
    
    # 创建新的DataFrame，只包含日期列和值列
    new_df = pd.DataFrame({
        'date': df[date_col],
        'value': df[value_col]
    })
    
    # 处理值列
    new_df['value'] = new_df['value'].apply(clean_value)
    
    # 将值列转换为数值
    new_df['value'] = pd.to_numeric(new_df['value'], errors='coerce')
    
    # 处理空值，使用前一个有效值填充
    new_df['value'] = new_df['value'].ffill()
    
    # 逐行处理日期列
    date_series = process_dates_row_by_row(new_df['date'])
    if date_series is not None:
        new_df['date'] = date_series
    
    print(f"标准化后数据形状: {new_df.shape}")
    
    return new_df


def process_dates_row_by_row(date_series):
    """
    逐行处理日期，对每行尝试不同的日期格式
    """
    # 复制一个新的Series以避免修改原始数据
    processed_dates = date_series.copy()
    
    # 常用的日期格式列表
    date_formats = common_date_formats()
    
    # 对每一行单独处理
    for i, date_str in enumerate(date_series):
        if pd.isna(date_str) or str(date_str).strip() == '':
            continue
        
        date_str = str(date_str).strip()
        converted = False
        
        # 1. 尝试直接转换
        try:
            date_obj = pd.to_datetime(date_str)
            processed_dates.iloc[i] = date_obj.strftime('%Y-%m-%d')
            converted = True
        except:
            # 2. 尝试各种格式
            for fmt in date_formats:
                try:
                    date_obj = datetime.datetime.strptime(date_str, fmt)
                    processed_dates.iloc[i] = date_obj.strftime('%Y-%m-%d')
                    converted = True
                    break
                except:
                    continue
        
        # 3. 特殊情况处理
        if not converted:
            # 3.1 处理中文日期
            if '年' in date_str and '月' in date_str:
                try:
                    date_str = date_str.replace('年', '-').replace('月', '-').replace('日', '')
                    date_obj = pd.to_datetime(date_str)
                    processed_dates.iloc[i] = date_obj.strftime('%Y-%m-%d')
                    converted = True
                except:
                    pass
            
            # 3.2 处理仅有数字的情况
            if not converted and re.match(r'^\d+$', date_str):
                # 尝试 YYYYMMDD
                if len(date_str) == 8:
                    try:
                        date_obj = datetime.datetime.strptime(date_str, '%Y%m%d')
                        processed_dates.iloc[i] = date_obj.strftime('%Y-%m-%d')
                        converted = True
                    except:
                        pass
                
                # 尝试 YYMMDD
                elif len(date_str) == 6:
                    try:
                        date_obj = datetime.datetime.strptime(date_str, '%y%m%d')
                        processed_dates.iloc[i] = date_obj.strftime('%Y-%m-%d')
                        converted = True
                    except:
                        pass
    
    return processed_dates


def detect_and_convert_dates(df):
    """尝试检测日期格式并转换"""
    
    # 尝试直接自动转换
    try:
        dates = pd.to_datetime(df['date'], errors='coerce')
        if dates.notna().mean() > 0.5:  # 如果超过50%的日期能被解析
            df['date'] = dates
            return True
    except:
        pass
    
    # 检查常见日期格式和模式
    patterns_and_formats = [
        # 美国格式 MM/DD/YYYY
        (r'^\d{1,2}/\d{1,2}/\d{4}$', '%m/%d/%Y'),
        # 欧洲格式 DD/MM/YYYY
        (r'^\d{1,2}/\d{1,2}/\d{4}$', '%d/%m/%Y'),
        # 带连字符的美国格式 MM-DD-YYYY
        (r'^\d{1,2}-\d{1,2}-\d{4}$', '%m-%d-%Y'),
        # 带连字符的欧洲格式 DD-MM-YYYY
        (r'^\d{1,2}-\d{1,2}-\d{4}$', '%d-%m-%Y'),
        # ISO格式 YYYY-MM-DD
        (r'^\d{4}-\d{1,2}-\d{1,2}$', '%Y-%m-%d'),
        # 带点的格式 YYYY.MM.DD
        (r'^\d{4}\.\d{1,2}\.\d{1,2}$', '%Y.%m.%d'),
        # 带点的格式 DD.MM.YYYY
        (r'^\d{1,2}\.\d{1,2}\.\d{4}$', '%d.%m.%Y'),
        # 紧凑格式 YYYYMMDD
        (r'^\d{8}$', '%Y%m%d')
    ]
    
    # 对每种格式尝试转换一个小样本
    sample_dates = df['date'].dropna().head(10).astype(str)
    best_format = None
    best_success_rate = 0
    
    for pattern, date_format in patterns_and_formats:
        # 检查样本中有多少符合此模式
        matches = [bool(re.match(pattern, date)) for date in sample_dates]
        match_rate = sum(matches) / len(matches) if matches else 0
        
        if match_rate > 0.5:  # 如果超过50%符合模式
            try:
                # 尝试用此格式转换
                test_convert = pd.to_datetime(sample_dates, format=date_format, errors='coerce')
                success_rate = test_convert.notna().mean()
                
                if success_rate > best_success_rate:
                    best_format = date_format
                    best_success_rate = success_rate
            except:
                continue
    
    # 如果找到最佳格式，应用于整个数据集
    if best_format:
        try:
            df['date'] = pd.to_datetime(df['date'], format=best_format, errors='coerce')
            return True
        except:
            pass
    
    # 特殊情况处理
    # 1. 处理YYMMDD格式 (没有世纪的年份)
    if df['date'].astype(str).str.match(r'^\d{6}$').any():
        try:
            df['date'] = pd.to_datetime(df['date'], format='%y%m%d', errors='coerce')
            return True
        except:
            pass
    
    # 2. 处理可能的中文日期格式
    if df['date'].astype(str).str.contains('年|月|日').any():
        try:
            temp = df['date'].astype(str)
            temp = temp.str.replace('年', '-').str.replace('月', '-').str.replace('日', '')
            dates = pd.to_datetime(temp, errors='coerce')
            if dates.notna().mean() > 0.5:
                df['date'] = dates
                return True
        except:
            pass
    
    # 如果上述方法都失败，尝试一些通用的格式
    for fmt in common_date_formats():
        try:
            dates = pd.to_datetime(df['date'], format=fmt, errors='coerce')
            if dates.notna().mean() > 0.5:
                df['date'] = dates
                return True
        except:
            continue
    
    # 最后尝试pandas的通用解析
    try:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        if df['date'].notna().mean() > 0.5:
            return True
    except:
        pass
    
    print("警告: 无法识别日期格式，保留原始日期字符串")
    return False


def common_date_formats():
    """返回常见的日期格式列表"""
    return [
        '%Y-%m-%d', '%Y/%m/%d', '%Y.%m.%d', 
        '%d-%m-%Y', '%d/%m/%Y', '%d.%m.%Y',
        '%m-%d-%Y', '%m/%d/%Y', '%m.%d.%Y',
        '%Y%m%d', '%d%m%Y', '%m%d%Y',
        '%b %d, %Y', '%B %d, %Y',  # 月份名称格式
        '%d %b %Y', '%d %B %Y',
        '%Y年%m月%d日'  # 中文格式
    ]


def clean_value(val):
    """
    清理并转换值
    - 移除千位分隔符
    - 处理百分比
    - 移除货币符号
    """
    if not isinstance(val, str):
        return val
    
    # 移除空白字符
    val = val.strip()
    
    # 如果是空字符串，返回NaN
    if val == '' or val.lower() in ('nan', 'null', 'none', '-', 'n/a'):
        return np.nan
    
    # 移除货币符号
    val = re.sub(r'[$¥€£₽₹]', '', val)
    
    # 移除千位分隔符（仅处理数字中的逗号）
    if re.match(r'^-?[\d,]+\.?\d*%?$', val):
        val = val.replace(',', '')
    
    # 处理百分比
    if '%' in val:
        val = val.replace('%', '')
        try:
            return float(val) / 100
        except:
            return np.nan
    
    # 尝试转换为浮点数
    try:
        return float(val)
    except:
        return np.nan


def main(input_path, output_dir='crewai-agent/src/tech_analysis_crew/trendanalysis/results'):
    """
    主函数，处理输入文件并生成标准化后的CSV
    
    参数:
    input_path: 输入CSV文件路径
    output_dir: 输出目录，默认与输入文件相同
    """
    # 获取文件路径信息
    input_path = os.path.abspath(input_path)
    input_dir = os.path.dirname(input_path)
    filename = os.path.basename(input_path)
    name, ext = os.path.splitext(filename)
    
    # 如果没有指定输出目录，使用输入文件目录
    if output_dir is None:
        output_dir = input_dir
    else:
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
    
    # 标准化后的文件名
    std_filename = f"{name}_std{ext}"
    output_path = os.path.join(output_dir, std_filename)
    
    # 标准化CSV
    std_df = standardize_csv(input_path)
    
    if std_df is not None:
        # 保存标准化后的CSV
        std_df.to_csv(output_path, index=False)
        print(f"标准化完成! 结果已保存至: {output_path}")
        return output_path
    else:
        print("标准化失败!")
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CSV数据标准化工具")
    parser.add_argument("input_path", help="输入CSV文件的路径")
    parser.add_argument("--output-dir", help="输出目录，默认与输入文件相同")
    
    args = parser.parse_args()
    
    main(args.input_path, args.output_dir)
