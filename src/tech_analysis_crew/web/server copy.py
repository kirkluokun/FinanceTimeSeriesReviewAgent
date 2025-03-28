#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
时间序列分析Web服务器
提供API接口和静态文件服务

使用方法：
cd crewAI-agent/src/tech_analysis_crew
python web/server.py

访问：
http://localhost:5000
"""

import os
import sys
import json
import uuid
import logging
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, render_template, abort

# 添加项目根目录到Python路径
current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file))))
if project_root not in sys.path:
    sys.path.append(project_root)

# 获取当前目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取tech_analysis_crew目录
tech_analysis_dir = os.path.dirname(current_dir)
# 获取tool目录
tool_dir = os.path.join(os.path.dirname(tech_analysis_dir), 'tool')
# 获取趋势分析工具目录
trend_analysis_dir = os.path.join(tool_dir, 'trendanalysis')

# 配置路径
INPUT_DIR = os.path.join(tech_analysis_dir, 'input')
OUTPUT_DIR = os.path.join(tech_analysis_dir, 'output')
RESULTS_DIR = os.path.join(trend_analysis_dir, 'results')
STATIC_DIR = os.path.join(current_dir, 'static')
IMAGES_DIR = os.path.join(STATIC_DIR, 'images')
FILES_DIR = os.path.join(STATIC_DIR, 'files')

# 确保目录存在
for directory in [INPUT_DIR, OUTPUT_DIR, RESULTS_DIR, STATIC_DIR, IMAGES_DIR, FILES_DIR]:
    os.makedirs(directory, exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("WebServer")

app = Flask(__name__)

@app.route('/')
def index():
    """首页路由，提供Web界面"""
    return send_from_directory(current_dir, 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """提供静态文件服务"""
    return send_from_directory(current_dir, filename)

@app.route('/static/images/<path:filename>')
def serve_images(filename):
    """提供图片文件服务"""
    logger.info(f"请求图片文件: {filename}")
    file_path = os.path.join(IMAGES_DIR, filename)
    
    if not os.path.exists(file_path):
        logger.error(f"图片文件不存在: {file_path}")
        
        # 检查文件名是否含有特殊字符，尝试匹配最接近的文件
        base_filename = os.path.basename(filename)
        logger.info(f"尝试查找与 {base_filename} 类似的文件")
        
        # 列出目录中的所有文件
        all_image_files = list(Path(IMAGES_DIR).glob("*.*"))
        for img_file in all_image_files:
            # 检查是否含有相同的关键字（敏感/不敏感，趋势可视化）
            if 'trend_visualization' in base_filename and 'trend_visualization' in img_file.name:
                if ('insensitive' in base_filename and 'insensitive' in img_file.name) or \
                   ('sensitive' in base_filename and 'sensitive' in img_file.name and 'insensitive' not in img_file.name):
                    logger.info(f"找到可能匹配的文件: {img_file.name}")
                    return send_from_directory(IMAGES_DIR, img_file.name)
        
        abort(404)
        
    try:
        logger.info(f"提供图片文件: {file_path}")
        return send_from_directory(IMAGES_DIR, filename)
    except Exception as e:
        logger.error(f"提供图片文件时出错: {e}")
        abort(500)

@app.route('/static/files/<path:filename>')
def serve_files(filename):
    """提供分析文件服务"""
    logger.info(f"请求文件: {filename}")
    file_path = os.path.join(FILES_DIR, filename)
    
    if not os.path.exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        abort(404)
        
    try:
        return send_from_directory(FILES_DIR, filename)
    except Exception as e:
        logger.error(f"提供文件时出错: {e}")
        abort(500)

@app.route('/api/process-csv', methods=['POST'])
def process_csv():
    """处理上传的CSV文件并运行趋势分析"""
    try:
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'error': '未找到文件'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'status': 'error', 'error': '未选择文件'}), 400
            
        if not file.filename.endswith('.csv'):
            return jsonify({'status': 'error', 'error': '请上传CSV文件'}), 400
            
        # 生成唯一的文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{uuid.uuid4().hex[:8]}.csv"
        input_path = os.path.join(INPUT_DIR, filename)
        
        # 保存上传的文件
        file.save(input_path)
        logger.info(f"保存上传文件: {input_path}")
        
        # 调用趋势分析脚本
        main_script = os.path.join(trend_analysis_dir, 'main.py')
        output_path = os.path.join(RESULTS_DIR)
        
        logger.info(f"运行趋势分析: {main_script} {input_path} --output-dir {output_path}")
        
        try:
            # 调用主分析脚本，执行趋势分析
            result = subprocess.run(
                [sys.executable, main_script, input_path, '--output-dir', output_path],
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info(f"趋势分析输出: {result.stdout}")
            
            if result.returncode != 0:
                logger.error(f"趋势分析错误: {result.stderr}")
                return jsonify({
                    'status': 'error',
                    'error': f"分析失败: {result.stderr}"
                }), 500
            
            # 确保静态目录存在并有正确权限
            for directory in [STATIC_DIR, IMAGES_DIR, FILES_DIR]:
                if not os.path.exists(directory):
                    logger.info(f"创建目录: {directory}")
                    os.makedirs(directory, exist_ok=True)
                try:
                    os.chmod(directory, 0o755)
                    logger.info(f"设置目录权限: {directory}")
                except Exception as e:
                    logger.warning(f"无法设置目录权限 {directory}: {e}")
            
            # 文件搜索参数
            file_stem = Path(input_path).stem
            logger.info(f"分析完成，搜索匹配文件，文件基名: {file_stem}")
            
            # 搜索最近生成的文件
            # 获取所有结果文件，按修改时间排序
            all_files = list(Path(output_path).glob("*"))
            files = sorted(all_files, key=lambda x: x.stat().st_mtime, reverse=True)
            recent_files = files[:20]  # 只考虑最近的20个文件
            
            # 筛选出可能属于本次处理的文件 - 优先考虑时间戳匹配
            matching_files = []
            for f in recent_files:
                if timestamp in f.name or file_stem in f.name:
                    matching_files.append(f)
            
            # 如果找不到匹配文件，使用最近的文件
            if not matching_files:
                logger.warning(f"找不到与时间戳{timestamp}或文件名{file_stem}匹配的文件，使用最近的文件")
                matching_files = recent_files[:8]  # 最多取8个文件
            
            if not matching_files:
                return jsonify({
                    'status': 'error',
                    'error': '分析完成，但未找到输出文件'
                }), 500
            
            # 处理文件
            logger.info(f"处理 {len(matching_files)} 个匹配文件")
            
            # 创建结果字典
            results_dict = {
                'timestamp': timestamp,
                'filename': Path(input_path).stem,
                'sensitive': {},
                'insensitive': {},
            }
            
            # 处理文件
            for i, file_path in enumerate(matching_files):
                file_name = file_path.name
                logger.info(f"处理文件 {i+1}/{len(matching_files)}: {file_name}")
                
                # 确定目标目录和路径
                is_image = file_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif']
                dest_dir = IMAGES_DIR if is_image else FILES_DIR
                dest_path = os.path.join(dest_dir, file_name)
                
                # 复制文件
                try:
                    logger.info(f"复制文件: {file_path} -> {dest_path}")
                    # 以二进制模式复制文件
                    with open(file_path, 'rb') as src_file:
                        content = src_file.read()
                        with open(dest_path, 'wb') as dest_file:
                            dest_file.write(content)
                    
                    # 设置文件权限确保可访问
                    try:
                        os.chmod(dest_path, 0o644)
                    except Exception as e:
                        logger.warning(f"无法设置文件权限 {dest_path}: {e}")
                    
                    # 验证文件复制是否成功
                    if os.path.exists(dest_path):
                        file_size = os.path.getsize(dest_path)
                        logger.info(f"复制成功: {dest_path} ({file_size} 字节)")
                        
                        # 更详细的文件内容判定，确保正确添加到结果字典
                        if is_image:
                            if 'sensitive-trend_visualization' in file_name and 'insensitive' not in file_name:
                                results_dict['sensitive']['visualization'] = file_name
                                logger.info(f"添加敏感版趋势图: {file_name}")
                            elif 'insensitive-trend_visualization' in file_name:
                                results_dict['insensitive']['visualization'] = file_name
                                logger.info(f"添加不敏感版趋势图: {file_name}")
                        else:
                            if 'sensitive-trend_analysis' in file_name and 'insensitive' not in file_name:
                                results_dict['sensitive']['analysis'] = file_name
                                logger.info(f"添加敏感版趋势分析: {file_name}")
                            elif 'insensitive-trend_analysis' in file_name:
                                results_dict['insensitive']['analysis'] = file_name
                                logger.info(f"添加不敏感版趋势分析: {file_name}")
                            elif 'sensitive-enhanced_analysis' in file_name and 'insensitive' not in file_name:
                                results_dict['sensitive']['enhanced_analysis'] = file_name
                                logger.info(f"添加敏感版增强分析: {file_name}")
                            elif 'insensitive-enhanced_analysis' in file_name:
                                results_dict['insensitive']['enhanced_analysis'] = file_name
                                logger.info(f"添加不敏感版增强分析: {file_name}")
                            elif 'comparison_report' in file_name:
                                results_dict['comparison_report'] = file_name
                                logger.info(f"添加比较报告: {file_name}")
                            elif 'detailed_report' in file_name:
                                results_dict['detailed_report'] = file_name
                                logger.info(f"添加详细报告: {file_name}")
                    else:
                        logger.error(f"复制失败: {dest_path} 不存在")
                except Exception as e:
                    logger.error(f"复制文件时出错: {e}")
                    continue  # 继续处理其他文件
            
            logger.info(f"分析结果: {json.dumps(results_dict)}")
            
            return jsonify({
                'status': 'success',
                'results': results_dict
            })
            
        except subprocess.CalledProcessError as e:
            logger.error(f"趋势分析执行错误: {e}")
            return jsonify({
                'status': 'error',
                'error': f"分析执行错误: {e.stderr}"
            }), 500
            
    except Exception as e:
        logger.exception(f"处理CSV错误: {e}")
        return jsonify({
            'status': 'error',
            'error': f"服务器错误: {str(e)}"
        }), 500

@app.route('/api/save-processed-csv', methods=['POST'])
def save_processed_csv():
    """保存已处理的CSV文件到input目录"""
    try:
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'error': '未找到文件'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'status': 'error', 'error': '未选择文件'}), 400
            
        if not file.filename.endswith('.csv'):
            return jsonify({'status': 'error', 'error': '请上传CSV文件'}), 400
            
        # 生成唯一的文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{Path(file.filename).stem}.csv"
        filepath = os.path.join(INPUT_DIR, filename)
        
        # 保存上传的文件
        file.save(filepath)
        logger.info(f"保存处理后的CSV文件: {filepath}")
        
        return jsonify({
            'status': 'success',
            'filepath': filepath
        })
        
    except Exception as e:
        logger.exception(f"保存处理后的CSV文件错误: {e}")
        return jsonify({
            'status': 'error',
            'error': f"服务器错误: {str(e)}"
        }), 500

@app.route('/api/run-analysis', methods=['POST'])
def run_analysis():
    """运行复盘分析"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'error': '缺少请求数据'}), 400
            
        input_file = data.get('file')
        query = data.get('query', '分析铜价走势')
        
        if not input_file:
            return jsonify({'status': 'error', 'error': '未指定输入文件'}), 400
            
        # 确认文件存在
        input_path = os.path.join(INPUT_DIR, input_file)
        if not os.path.exists(input_path):
            return jsonify({'status': 'error', 'error': f"文件不存在: {input_file}"}), 404
            
        # 调用backend.py脚本
        run_backend_script = os.path.join(tech_analysis_dir, 'run_backend.py')
        
        # 创建临时目录存放输出
        output_path = os.path.join(OUTPUT_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        os.makedirs(output_path, exist_ok=True)
        
        logger.info(f"运行复盘分析: {run_backend_script} --input {input_path} --query \"{query}\" --output-dir {output_path}")
        
        try:
            # 异步执行分析（使用subprocess.Popen）
            process = subprocess.Popen(
                [sys.executable, run_backend_script, '--input', input_path, 
                 '--query', query, '--output-dir', output_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            return jsonify({
                'status': 'success',
                'message': '分析已启动',
                'job_id': os.path.basename(output_path)
            })
            
        except Exception as e:
            logger.error(f"复盘分析执行错误: {e}")
            return jsonify({
                'status': 'error',
                'error': f"分析执行错误: {str(e)}"
            }), 500
            
    except Exception as e:
        logger.exception(f"运行复盘分析错误: {e}")
        return jsonify({
            'status': 'error',
            'error': f"服务器错误: {str(e)}"
        }), 500

@app.route('/api/analysis-status/<job_id>', methods=['GET'])
def analysis_status(job_id):
    """获取分析任务状态"""
    try:
        # 验证job_id格式，防止路径遍历
        if not job_id or '/' in job_id or '\\' in job_id or '..' in job_id:
            return jsonify({'status': 'error', 'error': '无效的作业ID'}), 400
            
        # 查找对应的输出目录
        output_path = os.path.join(OUTPUT_DIR, job_id)
        if not os.path.exists(output_path):
            return jsonify({'status': 'error', 'error': f"作业不存在: {job_id}"}), 404
            
        # 检查是否有结果文件
        files = list(Path(output_path).glob("*"))
        if not files:
            return jsonify({
                'status': 'running',
                'message': '分析正在进行中'
            })
            
        # 寻找summary文件
        summary_files = list(Path(output_path).glob("*summary*.md"))
        if summary_files:
            # 读取summary内容
            with open(summary_files[0], 'r', encoding='utf-8') as f:
                summary_content = f.read()
                
            return jsonify({
                'status': 'completed',
                'summary': summary_content,
                'files': [f.name for f in files]
            })
        else:
            return jsonify({
                'status': 'running',
                'message': '分析正在进行中，已生成部分文件',
                'files': [f.name for f in files]
            })
            
    except Exception as e:
        logger.exception(f"获取分析状态错误: {e}")
        return jsonify({
            'status': 'error',
            'error': f"服务器错误: {str(e)}"
        }), 500

def main():
    """主函数"""
    try:
        # 修改默认端口从5000到8080，避免与macOS的AirPlay服务冲突
        port = int(os.environ.get('PORT', 8080))
        app.run(host='0.0.0.0', port=port, debug=True)
    except Exception as e:
        logger.exception(f"服务器启动错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 