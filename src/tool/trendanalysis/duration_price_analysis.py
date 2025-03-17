import pandas as pd
import os
import argparse
import sys
import csv
import logging


# 配置日志系统
def setup_logger(log_level=logging.INFO):
    """设置日志系统"""
    logger = logging.getLogger('trend_analysis')
    logger.setLevel(log_level)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # 添加处理器到日志器
    logger.addHandler(console_handler)
    
    return logger


# 创建日志器实例
logger = setup_logger()


def analyze_trend_intervals(trend_csv_path, original_data_path, output_path=None):
    """
    分析趋势区间的详细信息，添加最高点日期和最低点日期
    
    参数:
    trend_csv_path: 趋势分析CSV文件路径
    original_data_path: 原始数据CSV文件路径
    output_path: 输出文件路径，如果为None则覆盖原文件
    
    返回:
    更新后的趋势数据框
    """
    try:
        logger.info(f"正在分析趋势区间: {trend_csv_path}")
        logger.info(f"使用原始数据: {original_data_path}")
        
        # 检查文件是否存在
        if not os.path.exists(trend_csv_path):
            logger.error(f"趋势分析文件不存在: {trend_csv_path}")
            return None
        
        if not os.path.exists(original_data_path):
            logger.error(f"原始数据文件不存在: {original_data_path}")
            return None
        
        # 读取趋势分析CSV文件
        trends_df = pd.read_csv(trend_csv_path)
        logger.info(f"读取趋势分析文件成功，包含 {len(trends_df)} 个区间")
        
        # 尝试将日期列转换为日期类型，并格式化为yyyy-mm-dd
        for date_col in ['start_date', 'end_date']:
            if date_col in trends_df.columns:
                try:
                    # 转换为日期类型
                    trends_df[date_col] = pd.to_datetime(trends_df[date_col])
                    # 格式化为yyyy-mm-dd
                    trends_df[date_col] = trends_df[date_col].dt.strftime(
                        '%Y-%m-%d')
                except Exception as e:
                    logger.warning(f"无法将 {date_col} 列转换为日期类型: {e}")
        
        # 读取原始数据CSV文件
        try:
            original_df = pd.read_csv(original_data_path)
            logger.info(f"读取原始数据文件成功，包含 {len(original_df)} 行数据")
            
            # 尝试找到日期列
            date_col = 'date'
            if date_col not in original_df.columns:
                # 尝试其他可能的日期列名
                possible_date_cols = [
                    'time', 'timestamp', 'Date', 'Time', 'Timestamp'
                ]
                for col in possible_date_cols:
                    if col in original_df.columns:
                        date_col = col
                        break
                else:
                    # 如果没有找到日期列，使用第一列作为索引
                    date_col = original_df.columns[0]
                    logger.warning(f"未找到日期列，使用 '{date_col}' 列作为日期")
            
            # 将日期列转换为日期类型并设置为索引
            try:
                original_df[date_col] = pd.to_datetime(original_df[date_col])
                original_df = original_df.set_index(date_col)
                original_df = original_df.sort_index()
            except Exception as e:
                logger.warning(f"无法将 {date_col} 列转换为日期类型: {e}")
                # 如果无法转换为日期，尝试使用字符串比较
                original_df = original_df.set_index(date_col)
        except Exception as e:
            logger.error(f"无法读取原始数据文件: {e}")
            return trends_df
        
        # 确定价格列
        price_col = 'close'
        if price_col not in original_df.columns:
            # 尝试其他可能的价格列名
            possible_price_cols = ['value', 'price', 'Close', 'Price', 'Value']
            for col in possible_price_cols:
                if col in original_df.columns:
                    price_col = col
                    break
            else:
                # 如果没有找到价格列，使用第一列
                if len(original_df.columns) > 0:
                    price_col = original_df.columns[0]
                    logger.warning(
                        f"未找到价格列，使用 '{price_col}' 列作为价格数据")
                else:
                    logger.error("原始数据文件没有列")
                    return trends_df
        
        logger.info(f"使用 '{price_col}' 列作为价格数据")
        
        # 初始化新列
        trends_df['high_price_date'] = None
        trends_df['low_price_date'] = None
        
        # 对每个趋势区间进行分析
        for i, row in trends_df.iterrows():
            try:
                start_date = pd.to_datetime(row['start_date'])
                end_date = pd.to_datetime(row['end_date'])
                
                logger.info(
                    f"分析区间 {i+1}/{len(trends_df)}: {start_date} 到 {end_date}")
                
                # 获取区间内的数据
                try:
                    interval_data = original_df.loc[start_date:end_date]
                except Exception:
                    # 如果日期索引失败，尝试使用字符串比较
                    interval_data = original_df[
                        (original_df.index >= start_date) & 
                        (original_df.index <= end_date)
                    ]
                
                if not interval_data.empty:
                    logger.info(f"  区间内有 {len(interval_data)} 个数据点")
                    
                    # 找到最高价格和最低价格对应的日期
                    try:
                        # 确保价格列是数值类型
                        if interval_data[price_col].dtype == 'object':
                            # 如果是字符串类型，尝试转换为数值
                            # 先移除逗号等非数字字符
                            interval_data[price_col] = interval_data[
                                price_col].apply(
                                    lambda x: float(str(x).replace(',', '')) 
                                    if isinstance(x, str) else float(x)
                                )
                        
                        high_price_date = interval_data[price_col].idxmax()
                        low_price_date = interval_data[price_col].idxmin()
                        
                        high_price = interval_data.loc[
                            high_price_date, price_col]
                        low_price = interval_data.loc[
                            low_price_date, price_col]
                        
                        logger.info(
                            f"  最高价格: {high_price} 于 {high_price_date}")
                        logger.info(
                            f"  最低价格: {low_price} 于 {low_price_date}")
                        
                        # 将日期转换为yyyy-mm-dd格式
                        high_price_date_fmt = pd.to_datetime(
                            high_price_date).strftime('%Y-%m-%d')
                        low_price_date_fmt = pd.to_datetime(
                            low_price_date).strftime('%Y-%m-%d')
                        
                        # 更新趋势数据框
                        trends_df.at[i, 'high_price_date'] = high_price_date_fmt
                        trends_df.at[i, 'low_price_date'] = low_price_date_fmt
                    except Exception as e:
                        logger.warning(f"  无法找到区间的最高/最低价格日期: {e}")
                else:
                    logger.warning("  区间在原始数据中没有对应的数据点")
            except Exception as e:
                logger.warning(f"  处理区间时出错: {e}")
        
        # 保存更新后的文件
        if output_path is None:
            output_path = trend_csv_path
        
        # 使用自定义方式保存CSV，确保数值格式正确
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            # 创建CSV写入器，禁用引号
            writer = csv.writer(f, quoting=csv.QUOTE_NONE, escapechar='\\')
            
            # 写入表头
            writer.writerow(trends_df.columns)
            
            # 写入数据行
            for _, row in trends_df.iterrows():
                # 处理每一行数据
                row_data = []
                for col in trends_df.columns:
                    value = row[col]
                    
                    # 处理日期列
                    if col in ['start_date', 'end_date', 
                               'high_price_date', 'low_price_date']:
                        if pd.notna(value):
                            # 确保日期格式为yyyy-mm-dd
                            try:
                                date_value = pd.to_datetime(value).strftime(
                                    '%Y-%m-%d')
                                row_data.append(date_value)
                            except Exception:
                                row_data.append(value)
                        else:
                            row_data.append('')
                    
                    # 处理数值列
                    elif col in ['start_price', 'end_price', 'low_price', 
                                'high_price', 'pct_change']:
                        if pd.notna(value):
                            # 处理可能带有逗号的数值字符串
                            try:
                                if isinstance(value, str):
                                    # 移除逗号等非数字字符
                                    clean_value = value.replace(',', '')
                                    numeric_value = float(clean_value)
                                else:
                                    numeric_value = float(value)
                                # 格式化为数字，不使用千位分隔符
                                row_data.append(f"{numeric_value:.4f}")
                            except Exception:
                                # 如果转换失败，保留原值
                                row_data.append(value)
                        else:
                            row_data.append('')
                    
                    # 处理其他列
                    else:
                        if pd.isna(value):
                            row_data.append('')
                        else:
                            row_data.append(value)
                
                writer.writerow(row_data)
        
        logger.info(f"分析完成! 结果已保存到 {output_path}")
        
        return trends_df
    except Exception as e:
        logger.error(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """主函数，处理命令行参数并执行分析"""
    # 设置日志系统
    logger = setup_logger()
    
    parser = argparse.ArgumentParser(description='分析趋势区间的详细信息')
    parser.add_argument(
        '--trend', type=str, required=True, help='趋势分析CSV文件路径')
    parser.add_argument(
        '--data', type=str, required=True, help='原始数据CSV文件路径')
    parser.add_argument(
        '--output', type=str, help='输出文件路径，默认覆盖原文件')
    
    args = parser.parse_args()
    
    result = analyze_trend_intervals(args.trend, args.data, args.output)
    
    if result is None:
        sys.exit(1)
    
    logger.info("处理成功完成")


if __name__ == "__main__":
    main()
