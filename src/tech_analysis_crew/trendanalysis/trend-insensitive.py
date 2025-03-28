import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import argrelextrema
from matplotlib.patches import Patch
import os
import datetime
import pathlib
from datetime import timedelta

# 设置matplotlib字体
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Helvetica', 'Lucida Grande', 'Verdana']
plt.rcParams['axes.unicode_minus'] = False

class TrendAnalyzer:
    def __init__(self, atr_period=14, swing_threshold=0.618, order=5):
        """
        参数:
        atr_period: 基础ATR周期（会根据数据特征自动调整）
        swing_threshold: 趋势判定阈值（ATR倍数）
        order: 基础swing点检测窗口（会根据数据特征自动调整）
        """
        self.base_atr_period = atr_period
        self.swing_threshold = swing_threshold
        self.base_order = order
        self.actual_atr_period = atr_period  # 实际使用的ATR周期
        self.actual_order = order  # 实际使用的swing点窗口
        
    def _detect_data_frequency(self, df):
        """自动检测数据频率和时间跨度"""
        # 计算时间间隔中位数
        time_diff = np.diff(df.index).astype('timedelta64[m]')
        median_interval = np.median(time_diff)
        
        # 判断数据频率
        if median_interval < 60:  # 分钟级数据
            freq_type = 'minute'
        elif 60 <= median_interval < 1440:  # 小时数据
            freq_type = 'hourly'
        else:  # 日级及以上数据
            freq_type = 'daily'
        
        # 计算时间跨度（年）
        timespan_years = (df.index[-1] - df.index[0]).days / 365
        
        return {
            'freq_type': freq_type,
            'timespan_years': timespan_years,
            'data_points': len(df)
        }
    
    def _calculate_atr(self, df, price_col='close'):
        # 检查列是否存在，如果不存在则尝试其他可能的列名
        if 'high' in df.columns and 'low' in df.columns:
            high = df['high'].values
            low = df['low'].values
        else:
            high = df[price_col].values
            low = df[price_col].values
        
        close = df[price_col].values
        
        tr = np.zeros(len(df))
        tr[0] = high[0] - low[0]
        for i in range(1, len(df)):
            hl = high[i] - low[i]
            hc = abs(high[i] - close[i-1])
            lc = abs(low[i] - close[i-1])
            tr[i] = max(hl, hc, lc)
            
        atr = pd.Series(tr).rolling(self.actual_atr_period).mean().bfill().values
        return atr
    
    def _find_swing_points(self, prices, order=5):
        """
        找出价格序列中的swing点（局部最高点和最低点）
        
        注意：这个函数总是会包含第一个和最后一个数据点，
        确保整个价格序列都被包含在分析中
        """
        # 安全检查：确保数据长度足够进行分析
        if len(prices) < order * 2 + 1:
            # 如果数据点太少，直接返回首尾点
            return np.array([0, len(prices) - 1])
            
        try:
            max_idx = argrelextrema(prices, np.greater, order=order)[0]
            min_idx = argrelextrema(prices, np.less, order=order)[0]
            
            # 合并极值点并排序
            swing_points = np.sort(np.concatenate((max_idx, min_idx)))
            
            # 确保包含第一个和最后一个点
            if len(swing_points) == 0:
                # 如果没有找到任何极值点，直接返回首尾点
                return np.array([0, len(prices) - 1])
                
            if 0 not in swing_points:
                swing_points = np.append([0], swing_points)
            
            if len(prices) - 1 not in swing_points:
                swing_points = np.append(swing_points, [len(prices) - 1])
            
            return np.sort(swing_points)
        except Exception as e:
            print(f"警告: 寻找swing点时出错: {e}, 使用简化方法")
            # 在出错的情况下，使用简化的方法
            # 简单地取首、尾和中间的几个点
            step = max(1, len(prices) // 10)
            indices = list(range(0, len(prices), step))
            if len(prices) - 1 not in indices:
                indices.append(len(prices) - 1)
            return np.array(indices)
    
    def _classify_segment(self, prev, curr, atr):
        price_change = curr - prev
        threshold = atr * self.swing_threshold
        
        if price_change > threshold:
            return 'up'
        elif price_change < -threshold:
            return 'down'
        else:
            return 'consolidation'
    
    def analyze(self, df, price_col='close'):
        df = df.sort_index()
        
        # 自动检测数据特征
        data_info = self._detect_data_frequency(df)
        print(f"检测到数据特征: {data_info}")
        
        # 动态调整参数
        adjusted_order = self._adjust_swing_order(data_info)
        adjusted_atr = self._adjust_atr_period(data_info)
        
        print(f"自适应参数: order={adjusted_order}, ATR周期={adjusted_atr}")
        
        # 使用调整后的参数
        self.actual_atr_period = adjusted_atr
        self.actual_order = adjusted_order
        
        # 确保价格列存在
        if price_col not in df.columns:
            # 尝试其他可能的列名
            possible_cols = ['value', 'price', 'close', 'adj_close', 'Close']
            for col in possible_cols:
                if col in df.columns:
                    price_col = col
                    break
            else:
                # 如果没有找到合适的列，使用第一列
                price_col = df.columns[0]
                print(f"警告: 未找到价格列，使用 '{price_col}' 列作为价格数据")
        
        prices = df[price_col].values
        dates = df.index
        
        # 寻找关键转折点时使用调整后的order
        swing_idx = self._find_swing_points(prices, order=self.actual_order)
        print(f"识别到的swing点数量: {len(swing_idx)}")
        if len(swing_idx) > 0:
            print(f"第一个swing点: {dates[swing_idx[0]]}，"
                  f"最后一个swing点: {dates[swing_idx[-1]]}")
        
        # 使用调整后的ATR周期重新计算ATR
        atr = self._calculate_atr(df, price_col)
        
        # 趋势分类
        trends = []
        for i in range(1, len(swing_idx)):
            start_idx = swing_idx[i-1]
            end_idx = swing_idx[i]
            
            segment = prices[start_idx:end_idx+1]
            trend_type = self._classify_segment(
                prices[start_idx], prices[end_idx], 
                atr[start_idx]
            )
            
            # 计算百分比变化并保留4位小数
            price_change = prices[end_idx] - prices[start_idx]
            pct_change = round(
                price_change / max(abs(prices[start_idx]), 1e-10), 
                4
            )
            
            # 计算持续时间(天数)
            if isinstance(dates[start_idx], (datetime.datetime, datetime.date)):
                duration = (dates[end_idx] - dates[start_idx]).days
            else:
                # 如果dates不是日期类型，尝试转换
                try:
                    start_date = pd.to_datetime(dates[start_idx])
                    end_date = pd.to_datetime(dates[end_idx])
                    duration = (end_date - start_date).days
                except Exception as e:
                    # 如果无法转换为日期，使用已有duration或默认值
                    print(f"日期转换失败: {e}")
                    duration = 30  # 使用默认值30天
            
            trends.append({
                'start_date': dates[start_idx],
                'end_date': dates[end_idx],
                'start_price': prices[start_idx],
                'end_price': prices[end_idx],
                'low_price': np.min(segment),
                'high_price': np.max(segment),
                'pct_change': pct_change,
                'duration': duration,
                'trend_type': trend_type
            })
        
        if not trends:
            print("警告: 未识别到任何趋势区间")
            # 如果没有识别到任何区间，创建一个覆盖整个数据集的基本区间
            if len(prices) > 0:
                start_price = prices[0]
                end_price = prices[-1]
                price_change = end_price - start_price
                pct_change = round(
                    price_change / max(abs(start_price), 1e-10), 
                    4
                ) if start_price != 0 else 0
                
                trend_type = 'consolidation'
                if pct_change > 0.1:
                    trend_type = 'up'
                elif pct_change < -0.1:
                    trend_type = 'down'

                # 计算持续时间(天数)
                if len(dates) > 1:
                    if isinstance(dates[0], (datetime.datetime, datetime.date)):
                        duration = (dates[-1] - dates[0]).days
                    else:
                        # 如果dates不是日期类型，尝试转换
                        try:
                            start_date = pd.to_datetime(dates[0])
                            end_date = pd.to_datetime(dates[-1])
                            duration = (end_date - start_date).days
                        except:
                            # 如果无法转换为日期，则使用索引差作为持续时间
                            duration = len(prices) - 1
                else:
                    duration = 0
                
                trends.append({
                    'start_date': dates[0],
                    'end_date': dates[-1],
                    'start_price': start_price,
                    'end_price': end_price,
                    'low_price': np.min(prices),
                    'high_price': np.max(prices),
                    'pct_change': pct_change,
                    'duration': duration,
                    'trend_type': trend_type
                })
        
        # 合并震荡区间
        merged_trends = self._merge_consolidation(trends)
        
        # 减少碎片化并处理反弹/回调行情
        refined_trends = self._refine_trends(merged_trends)
        
        # 检查是否包含所有数据
        data_coverage = self._check_data_coverage(df.index, refined_trends)
        if not data_coverage['complete']:
            print(f"警告: 有{data_coverage['missing']}个数据点未被包含在趋势分析中")
            if data_coverage['last_missing']:
                print("最近的数据没有被包含在趋势分析中，添加额外区间")
                # 添加额外的区间来覆盖最近的数据
                additional_trend = self._create_additional_segment(
                    df, price_col, refined_trends[-1], data_coverage
                )
                if additional_trend:
                    refined_trends.append(additional_trend)
        
        return pd.DataFrame(refined_trends)
    
    def _check_data_coverage(self, dates, trends):
        """检查趋势是否覆盖了所有数据点"""
        if not trends:
            return {
                'complete': False,
                'first_missing': True,
                'last_missing': True,
                'missing': len(dates)
            }
            
        start_date = dates[0]
        end_date = dates[-1]
        
        # 检查第一个趋势的开始日期
        first_trend_start = trends[0]['start_date']
        first_covered = first_trend_start <= start_date
        
        # 检查最后一个趋势的结束日期
        last_trend_end = trends[-1]['end_date']
        last_covered = last_trend_end >= end_date
        
        # 计算差距（天数）
        missing_days = 0
        if not last_covered:
            missing_days = (end_date - last_trend_end).days
        
        return {
            'complete': first_covered and last_covered,
            'first_missing': not first_covered,
            'last_missing': not last_covered,
            'missing': missing_days
        }
    
    def _create_additional_segment(self, df, price_col, last_trend, 
                                  coverage_info):
        """为未覆盖的最近数据创建额外区间"""
        last_date = last_trend['end_date']
        end_date = df.index[-1]
        
        # 如果差距很小，直接扩展最后一个区间
        if (end_date - last_date).days <= 30:
            # 获取最近数据段
            recent_data = df.loc[last_date:end_date]
            
            # 扩展最后一个区间
            extended_trend = last_trend.copy()
            extended_trend['end_date'] = end_date
            extended_trend['end_price'] = df.loc[end_date, price_col]
            
            # 更新高点和低点
            extended_trend['high_price'] = max(
                extended_trend['high_price'], 
                recent_data[price_col].max()
            )
            extended_trend['low_price'] = min(
                extended_trend['low_price'], 
                recent_data[price_col].min()
            )
            
            # 更新百分比变化
            price_change = extended_trend['end_price'] - extended_trend['start_price']
            extended_trend['pct_change'] = round(
                price_change / max(abs(extended_trend['start_price']), 1e-10),
                4
            )
            
            # 计算持续时间(天数)
            if isinstance(last_date, (datetime.datetime, datetime.date)) and isinstance(end_date, (datetime.datetime, datetime.date)):
                duration = (end_date - last_date).days
            else:
                # 如果dates不是日期类型，尝试转换
                try:
                    start_date = pd.to_datetime(last_date)
                    end_date = pd.to_datetime(end_date)
                    duration = (end_date - start_date).days
                except Exception as e:
                    # 如果无法转换为日期，使用估计值
                    print(f"日期转换失败: {e}")
                    duration = 30  # 使用默认值30天
            
            extended_trend['duration'] = duration
            
            return extended_trend
        else:
            # 创建新区间
            recent_data = df.loc[last_date:end_date]
            
            # 确定趋势类型
            start_price = df.loc[last_date, price_col]
            end_price = df.loc[end_date, price_col]
            price_change = end_price - start_price
            
            # 简单趋势判断
            if price_change > 0 and price_change / start_price > 0.03:
                trend_type = 'up'
            elif price_change < 0 and abs(price_change) / start_price > 0.03:
                trend_type = 'down'
            else:
                trend_type = 'consolidation'
            
            # 计算持续时间(天数)
            if isinstance(dates[start_idx], (datetime.datetime, datetime.date)):
                duration = (dates[end_idx] - dates[start_idx]).days
            else:
                # 如果dates不是日期类型，尝试转换
                try:
                    start_date = pd.to_datetime(dates[start_idx])
                    end_date = pd.to_datetime(dates[end_idx])
                    duration = (end_date - start_date).days
                except:
                    # 如果无法转换为日期，则使用索引差作为持续时间
                    duration = end_idx - start_idx
            
            return {
                'start_date': last_date,
                'end_date': end_date,
                'start_price': start_price,
                'end_price': end_price,
                'low_price': recent_data[price_col].min(),
                'high_price': recent_data[price_col].max(),
                'pct_change': round(
                    (end_price - start_price) / max(abs(start_price), 1e-10), 
                    4
                ),
                'duration': duration,
                'trend_type': trend_type
            }
    
    def _merge_consolidation(self, trends, max_gap=5):
        """合并相邻的震荡区间"""
        if not trends:
            return []
            
        merged = []
        temp = None
        
        for t in trends:
            if t['trend_type'] == 'consolidation':
                if temp is None:
                    temp = t
                else:
                    gap = (t['start_date'] - temp['end_date']).days
                    if gap <= max_gap:
                        temp['end_date'] = t['end_date']
                        temp['low_price'] = min(
                            temp['low_price'], t['low_price']
                        )
                        temp['high_price'] = max(
                            temp['high_price'], t['high_price']
                        )
                        # 计算百分比变化并保留4位小数
                        price_change = t['end_price'] - temp['start_price']
                        temp['pct_change'] = round(
                            price_change / max(abs(temp['start_price']), 1e-10),
                            4
                        )
                        # 计算持续时间
                        try:
                            start_date = pd.to_datetime(temp['start_date'])
                            end_date = pd.to_datetime(t['end_date'])
                            duration = (end_date - start_date).days
                        except Exception as e:
                            # 如果日期转换失败，累加duration或使用估计值
                            print(f"日期转换失败: {e}")
                            if temp.get('duration') is not None and t.get('duration') is not None:
                                duration = temp.get('duration', 0) + t.get('duration', 0)
                            else:
                                # 如果没有可用的duration，尝试估计
                                try:
                                    # 尝试从字符串形式的日期估计
                                    start_str = str(temp['start_date'])
                                    end_str = str(t['end_date'])
                                    start_date = pd.to_datetime(start_str)
                                    end_date = pd.to_datetime(end_str)
                                    duration = (end_date - start_date).days
                                except:
                                    # 如果仍然失败，使用默认值
                                    duration = 30  # 默认30天
                        
                        temp['duration'] = duration
                    else:
                        merged.append(temp)
                        temp = t
            else:
                if temp is not None:
                    merged.append(temp)
                    temp = None
                merged.append(t)
        
        if temp is not None:
            merged.append(temp)
            
        return merged
    
    def _refine_trends(self, trends):
        """
        减少区间碎片化并处理无效反弹/回调:
        1. 如果区间没有突破前一区间的高点/低点，且价格变动幅度不超过20%，归类为震荡
        2. 如果连续的上涨/下跌区间之间有反向的小区间，但整体突破，则合并为一个大区间
        """
        if len(trends) <= 1:
            return trends
            
        refined = [trends[0]]  # 初始化结果列表，保留第一个区间
        
        for i in range(1, len(trends)):
            current = trends[i]
            previous = refined[-1]
            
            # 计算当前区间的价格变动百分比（绝对值）
            price_change_pct = abs(current['pct_change']) * 100
            significant_move = price_change_pct >= 15  # 判断是否是显著变动（超过20%）
            
            # 如果当前区间是上涨
            if current['trend_type'] == 'up':
                # 检查是否突破前一区间的高点，如果没有突破且变动幅度不大，改为震荡
                if current['high_price'] <= previous['high_price'] and not significant_move:
                    # 未突破且幅度不大，改为震荡
                    current['trend_type'] = 'consolidation'
                # 检查是否是大趋势中的回调 - 安全检查列表长度   
                elif (len(refined) >= 2 and 
                      refined[-2]['trend_type'] == 'up' and 
                      previous['trend_type'] != 'up'):
                    # 检查是否是大趋势中的回调
                    if current['high_price'] > refined[-2]['high_price']:
                        # 当前区间突破了前面上涨区间的高点，说明回调结束，继续上涨
                        # 合并前面的回调区间到当前上涨区间
                        current['start_date'] = previous['start_date']
                        current['start_price'] = previous['start_price']
                        current['low_price'] = min(
                            current['low_price'], 
                            previous['low_price']
                        )
                        current['pct_change'] = round(
                            (current['end_price'] - current['start_price']) / 
                            max(abs(current['start_price']), 1e-10),
                            4
                        )
                        # 移除前一个区间（回调区间）
                        refined.pop()
            
            # 如果当前区间是下跌
            elif current['trend_type'] == 'down':
                # 检查是否突破前一区间的低点，如果没有突破且变动幅度不大，改为震荡
                if current['low_price'] >= previous['low_price'] and not significant_move:
                    # 未突破且幅度不大，改为震荡
                    current['trend_type'] = 'consolidation'
                # 检查是否是大趋势中的反弹 - 安全检查列表长度    
                elif (len(refined) >= 2 and 
                      refined[-2]['trend_type'] == 'down' and 
                      previous['trend_type'] != 'down'):
                    # 检查是否是大趋势中的反弹
                    if current['low_price'] < refined[-2]['low_price']:
                        # 当前区间突破了前面下跌区间的低点，说明反弹结束，继续下跌
                        # 合并前面的反弹区间到当前下跌区间
                        current['start_date'] = previous['start_date']
                        current['start_price'] = previous['start_price']
                        current['high_price'] = max(
                            current['high_price'], 
                            previous['high_price']
                        )
                        current['pct_change'] = round(
                            (current['end_price'] - current['start_price']) / 
                            max(abs(current['start_price']), 1e-10),
                            4
                        )
                        # 移除前一个区间（反弹区间）
                        refined.pop()
            
            # 合并相邻的相同类型区间
            if refined and refined[-1]['trend_type'] == current['trend_type']:
                previous = refined[-1]
                previous['end_date'] = current['end_date']
                previous['end_price'] = current['end_price']
                previous['high_price'] = max(
                    previous['high_price'], 
                    current['high_price']
                )
                previous['low_price'] = min(
                    previous['low_price'], 
                    current['low_price']
                )
                # 计算持续时间
                try:
                    start_date = pd.to_datetime(previous['start_date'])
                    end_date = pd.to_datetime(current['end_date'])
                    previous['duration'] = (end_date - start_date).days
                except Exception as e:
                    # 如果日期转换失败，累加duration或使用估计值
                    print(f"日期转换失败: {e}")
                    if previous.get('duration') is not None and current.get('duration') is not None:
                        duration = previous.get('duration', 0) + current.get('duration', 0)
                    else:
                        # 如果没有可用的duration，尝试估计
                        try:
                            # 尝试从字符串形式的日期估计
                            start_str = str(previous['start_date'])
                            end_str = str(current['end_date'])
                            start_date = pd.to_datetime(start_str)
                            end_date = pd.to_datetime(end_str)
                            duration = (end_date - start_date).days
                        except:
                            # 如果仍然失败，使用默认值
                            duration = 30  # 默认30天
                
                # 更新百分比变化
                price_change = previous['end_price'] - previous['start_price']
                previous['pct_change'] = round(
                    price_change / max(abs(previous['start_price']), 1e-10),
                    4
                )
            else:
                refined.append(current)
        
        # 最后一次检查：合并小震荡区间
        if len(refined) >= 3:
            result = []
            i = 0
            while i < len(refined):
                # 安全检查：确保不会索引越界
                if (i+2 < len(refined) and 
                    refined[i]['trend_type'] == refined[i+2]['trend_type'] and
                    refined[i+1]['trend_type'] == 'consolidation' and
                    (refined[i+1]['end_date'] - 
                     refined[i+1]['start_date']).days < 30):
                    
                    # 将三个区间合并为一个
                    merged = refined[i].copy()
                    merged['end_date'] = refined[i+2]['end_date']
                    merged['end_price'] = refined[i+2]['end_price']
                    merged['high_price'] = max(
                        refined[i]['high_price'], 
                        refined[i+1]['high_price'],
                        refined[i+2]['high_price']
                    )
                    merged['low_price'] = min(
                        refined[i]['low_price'],
                        refined[i+1]['low_price'],
                        refined[i+2]['low_price']
                    )
                    price_change = merged['end_price'] - merged['start_price']
                    # 计算持续时间
                    try:
                        start_date = pd.to_datetime(merged['start_date'])
                        end_date = pd.to_datetime(merged['end_date'])
                        duration = (end_date - start_date).days
                    except Exception as e:
                        # 如果日期转换失败，尝试其他方法
                        print(f"日期转换失败: {e}")
                        try:
                            # 尝试从字符串形式的日期估计
                            start_str = str(merged['start_date'])
                            end_str = str(merged['end_date'])
                            start_date = pd.to_datetime(start_str)
                            end_date = pd.to_datetime(end_str)
                            duration = (end_date - start_date).days
                        except:
                            # 如果仍然失败，累加已有duration
                            duration = 0
                            for idx in range(i, i+3):
                                if idx < len(refined) and refined[idx].get('duration') is not None:
                                    duration += refined[idx].get('duration', 0)
                            
                            # 如果累加结果为0，使用默认值
                            if duration == 0:
                                duration = 30 * 3  # 默认每个区间30天，共3个区间
                    
                    merged['pct_change'] = round(
                        price_change / max(abs(merged['start_price']), 1e-10),
                        4
                    )
                    merged['duration'] = duration
                    result.append(merged)
                    i += 3
                else:
                    result.append(refined[i])
                    i += 1
            
            # 确保所有剩余区间都被添加
            while i < len(refined):
                result.append(refined[i])
                i += 1
                
            refined = result
        
        print(f"区间优化: 原始区间数量 {len(trends)}, 优化后区间数量 {len(refined)}")
        return refined
    
    def _adjust_swing_order(self, data_info):
        """根据数据特征调整swing点检测窗口"""
        base_order = self.base_order
        
        # 时间跨度调整
        if data_info['timespan_years'] > 10:
            base_order *= 3
        elif data_info['timespan_years'] > 5:
            base_order *= 2
        elif data_info['timespan_years'] < 1:
            base_order = max(3, base_order // 2)
            
        # 数据频率调整
        if data_info['freq_type'] == 'minute':
            return max(3, base_order // 2)
        elif data_info['freq_type'] == 'hourly':
            return base_order
        else:  # daily
            if data_info['timespan_years'] > 3:
                return min(30, base_order * 2)
            return base_order
    
    def _adjust_atr_period(self, data_info):
        """根据数据特征调整ATR周期"""
        base_atr = self.base_atr_period
        
        # 高频数据使用较短周期
        if data_info['freq_type'] == 'minute':
            return max(5, base_atr // 2)
        elif data_info['freq_type'] == 'hourly':
            return base_atr
        else:  # daily
            if data_info['timespan_years'] > 5:
                return min(21, int(base_atr * 1.5))
            return base_atr

def plot_trends(df, trends, output_path, price_col='close', dpi=800):
    """
    绘制趋势分析图表
    
    参数:
    df: 数据框
    trends: 趋势数据框
    output_path: 输出路径
    price_col: 价格列名
    dpi: 图像分辨率
    """
    plt.figure(figsize=(16, 10))
    
    # 绘制价格曲线
    plt.plot(df.index, df[price_col], color='black', linewidth=1.5, 
             label='Price')
    
    # 绘制趋势区域
    color_map = {'up': 'red', 'down': 'green', 'consolidation': 'lightgrey'}
    
    for _, row in trends.iterrows():
        start = row['start_date']
        end = row['end_date']
        trend_type = row['trend_type']
        
        plt.fill_betweenx(
            y=[row['low_price'], row['high_price']],
            x1=start, x2=end,
            color=color_map[trend_type],
            alpha=0.3
        )
    
    # 添加图例
    legend_elements = [
        Patch(facecolor='red', alpha=0.3, label='Uptrend'),
        Patch(facecolor='green', alpha=0.3, label='Downtrend'),
        Patch(facecolor='lightgrey', alpha=0.3, label='Consolidation')
    ]
    plt.legend(handles=legend_elements, fontsize=12)
    
    plt.title('Price Trend Analysis', fontsize=16)
    plt.xlabel('Date', fontsize=14)
    plt.ylabel('Price', fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    
    # 保存高分辨率图片
    plt.savefig(output_path, dpi=dpi)
    plt.close()

def main(input_path, output_dir='crewai-agent/src/tech_analysis_crew/trendanalysis/results'):
    # 读取数据
    df = pd.read_csv(input_path, parse_dates=['date'], index_col='date')
    df = df.sort_index()
    
    # 打印列名，帮助调试
    print(f"CSV文件中的列: {df.columns.tolist()}")
    print(f"数据时间范围: {df.index[0]} 到 {df.index[-1]}")
    
    # 生成时间戳
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 获取输入文件名（不含扩展名）
    input_filename = pathlib.Path(input_path).stem
    
    # 创建固定的results输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # 运行分析
        analyzer = TrendAnalyzer(atr_period=14, swing_threshold=0.618)
        trends = analyzer.analyze(df)
        
        # 检查是否有结果
        if trends.empty:
            print("警告: 趋势分析未产生任何结果")
            return output_dir
        
        # 保存CSV，使用时间戳+文件名格式
        csv_filename = f"{timestamp}_{input_filename}-trend_analysis.csv"
        csv_path = os.path.join(output_dir, csv_filename)
        trends.to_csv(csv_path, index=False, float_format='%.4f')
        
        # 生成图表，使用时间戳+文件名格式
        png_filename = f"{timestamp}_{input_filename}-trend_visualization.png"
        plot_path = os.path.join(output_dir, png_filename)
        
        # 使用与analyze相同的价格列
        price_col = 'close'
        if price_col not in df.columns and len(df.columns) > 0:
            price_col = df.columns[0]
        plot_trends(df, trends, plot_path, price_col, dpi=800)
        
        print(f"分析完成! 结果保存到 {output_dir} 文件夹")
        print(f"CSV文件: {csv_filename}")
        print(f"图表文件: {png_filename}")
    
    except Exception as e:
        print(f"分析过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    return output_dir

def test_duration_calculation():
    """
    测试持续时间计算是否正确
    """
    # 创建测试数据
    test_data = {
        'date': pd.date_range(start='2018-01-01', end='2020-12-31', freq='D'),
        'close': np.random.rand(731) * 1000 + 3000  # 随机价格数据
    }
    df = pd.DataFrame(test_data)
    df.set_index('date', inplace=True)
    
    # 运行分析
    analyzer = TrendAnalyzer()
    trends = analyzer.analyze(df)
    
    # 验证每个区间的duration是否正确
    for i, row in trends.iterrows():
        start_date = pd.to_datetime(row['start_date'])
        end_date = pd.to_datetime(row['end_date'])
        expected_duration = (end_date - start_date).days
        actual_duration = row['duration']
        
        # 打印比较结果
        print(f"区间 {i+1}: {start_date} 到 {end_date}")
        print(f"  预期持续时间: {expected_duration} 天")
        print(f"  实际持续时间: {actual_duration} 天")
        print(f"  差异: {abs(expected_duration - actual_duration)} 天")
        print(f"  是否正确: {'是' if expected_duration == actual_duration else '否'}")
        print()
    
    return trends

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--input', type=str, required=True, 
        help='输入CSV文件路径'
    )
    parser.add_argument(
        '--output', type=str, default='crewai-agent/src/tech_analysis_crew/trendanalysis/results', 
        help='输出目录路径，默认为results'
    )
    parser.add_argument(
        '--test', action='store_true',
        help='运行测试以验证duration计算'
    )
    args = parser.parse_args()
    
    if args.test:
        test_duration_calculation()
    else:
        main(args.input, args.output)