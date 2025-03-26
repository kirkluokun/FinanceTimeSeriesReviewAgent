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
        """寻找价格序列中的关键转折点"""
        # 寻找局部极大值和极小值点
        max_idx = argrelextrema(prices, np.greater, order=order)[0]
        min_idx = argrelextrema(prices, np.less, order=order)[0]
        
        # 合并所有极值点
        swing_points = np.sort(np.concatenate((max_idx, min_idx)))
        
        # 如果没有找到任何极值点，至少使用起点和终点
        if len(swing_points) == 0:
            return np.array([0, len(prices) - 1])
        
        # 确保包含起点
        if swing_points[0] > 0:
            swing_points = np.insert(swing_points, 0, 0)
        
        # 确保包含终点
        if swing_points[-1] < len(prices) - 1:
            swing_points = np.append(swing_points, len(prices) - 1)
        
        return swing_points
    
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
                except:
                    # 如果无法转换为日期，则使用索引差作为持续时间
                    duration = end_idx - start_idx
            
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
        
        # 合并震荡区间
        merged_trends = self._merge_consolidation(trends)
        
        # 确保最后一段时间被处理，检查最后一个趋势的结束时间
        if len(merged_trends) > 0:
            last_trend = merged_trends[-1]
            last_date_idx = np.where(dates == last_trend['end_date'])[0][0]
            
            # 如果最后一个趋势没有覆盖到最后的数据点，添加一个新的趋势
            if last_date_idx < len(dates) - 1:
                print(f"添加最后一段未覆盖的时间: {dates[last_date_idx+1]} 到 {dates[-1]}")
                start_idx = last_date_idx + 1
                end_idx = len(dates) - 1
                
                segment = prices[start_idx:end_idx+1]
                trend_type = self._classify_segment(
                    prices[start_idx], prices[end_idx], 
                    atr[start_idx] if start_idx < len(atr) else atr[-1]
                )
                
                # 使用价格变动与起始价格绝对值的比值来计算百分比变化
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
                    except:
                        # 如果无法转换为日期，则使用索引差作为持续时间
                        duration = end_idx - start_idx
                
                merged_trends.append({
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
        
        return pd.DataFrame(merged_trends)
    
    def _merge_consolidation(self, trends, max_gap=5):
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
                        # 使用价格变动与起始价格绝对值的比值来计算百分比变化
                        price_change = t['end_price'] - temp['start_price']
                        # 计算持续时间(天数)
                        if isinstance(temp['start_date'], (datetime.datetime, datetime.date)) and isinstance(t['end_date'], (datetime.datetime, datetime.date)):
                            duration = (t['end_date'] - temp['start_date']).days
                        else:
                            # 尝试转换为日期
                            try:
                                start_date = pd.to_datetime(temp['start_date'])
                                end_date = pd.to_datetime(t['end_date'])
                                duration = (end_date - start_date).days
                            except:
                                # 如果无法转换，则保留原有duration或设为None
                                duration = t.get('duration', None)

                        temp['pct_change'] = round(
                            price_change / max(abs(temp['start_price']), 1e-10),
                            4
                        )
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
                return min(21, base_atr * 1.5)
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

def main(input_path, output_dir='results'):
    # 读取数据
    df = pd.read_csv(input_path, parse_dates=['date'], index_col='date')
    df = df.sort_index()
    
    # 打印列名，帮助调试
    print(f"CSV文件中的列: {df.columns.tolist()}")
    
    # 生成时间戳
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 获取输入文件名（不含扩展名）
    input_filename = pathlib.Path(input_path).stem
    
    # 创建固定的results输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 运行分析
    analyzer = TrendAnalyzer(atr_period=14, swing_threshold=0.618)
    trends = analyzer.analyze(df)
    
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
    
    return output_dir

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--input', type=str, required=True, 
        help='输入CSV文件路径'
    )
    parser.add_argument(
        '--output', type=str, default='results', 
        help='输出目录路径，默认为results'
    )
    args = parser.parse_args()
    
    main(args.input, args.output)