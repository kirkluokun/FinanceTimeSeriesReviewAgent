#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
时间序列分析Web服务器
提供API接口和静态文件服务

使用方法：
cd crewAI-agent/src/tech_analysis_crew
python web/server.py

访问：
http://localhost:8080
"""

import os
import sys
import json
import uuid
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Any

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel

# 添加项目根目录到Python路径
current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(current_file))))
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入RunTechAnalysisBackend类
try:
    # 尝试使用绝对导入
    from src.tech_analysis_crew.backend import (
        RunTechAnalysisBackend
    )
except ModuleNotFoundError as e:
    print(f"绝对导入失败: {e}")
    try:
        # 尝试使用相对导入
        import os
        import sys
        # 添加当前目录的父目录到sys.path
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent_dir not in sys.path:
            sys.path.append(parent_dir)
        print(f"添加路径: {parent_dir}")
        
        # 尝试导入
        try:
            from backend import RunTechAnalysisBackend
        except ImportError:
            # 直接从本地导入（不使用crew.py中的类）
            # 这需要你创建一个简化版的backend.py，不依赖于crew.py
            print("警告: 无法导入backend模块，将使用本地实现")
            # 这里可以添加一个简化版的RunTechAnalysisBackend实现
    except Exception as e:
        print(f"导入错误: {e}")
        print(f"当前Python路径: {sys.path}")
        raise

# 获取当前目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取tech_analysis_crew目录
tech_analysis_dir = os.path.dirname(current_dir)
# 获取趋势分析工具目录 - 修正路径
trend_analysis_dir = os.path.join(tech_analysis_dir, 'trendanalysis')

# 配置路径
INPUT_DIR = os.path.join(tech_analysis_dir, 'input')
OUTPUT_DIR = os.path.join(tech_analysis_dir, 'output')


RESULTS_DIR = os.path.join(trend_analysis_dir, 'results')
CACHE_DIR = os.path.join(trend_analysis_dir, 'cache')
# 修改静态文件目录路径
STATIC_DIR = os.path.join(trend_analysis_dir, 'static')
IMAGES_DIR = os.path.join(STATIC_DIR, 'images')
FILES_DIR = os.path.join(STATIC_DIR, 'files')

# 确保目录存在
dirs_to_create = [
    INPUT_DIR, OUTPUT_DIR, RESULTS_DIR, CACHE_DIR, 
    STATIC_DIR, IMAGES_DIR, FILES_DIR
]
for directory in dirs_to_create:
    os.makedirs(directory, exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("WebServer")

app = FastAPI(title="金融时间序列分析平台")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 数据模型
class AnalysisRequest(BaseModel):
    """分析请求模型"""
    file: str
    query: str = "分析铜价走势"


class AnalysisResponse(BaseModel):
    """分析响应模型"""
    status: str
    message: str
    job_id: str


class ProcessResponse(BaseModel):
    """处理响应模型"""
    status: str
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# 挂载静态文件 - 确保静态文件目录存在
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index():
    """首页路由，提供Web界面"""
    return FileResponse(os.path.join(current_dir, 'index.html'))


@app.get("/api/check-output-files")
async def check_output_files():
    """检查输出目录中的最新文件"""
    try:
        logger.info(f"检查输出目录: {OUTPUT_DIR}")
        
        # 确保输出目录存在
        if not os.path.exists(OUTPUT_DIR):
            logger.warning(f"输出目录不存在: {OUTPUT_DIR}")
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            return {
                "status": "no_data",
                "message": "没有找到输出目录"
            }
            
        # 获取output目录中的所有目录
        output_dirs = []
        for item in os.listdir(OUTPUT_DIR):
            item_path = os.path.join(OUTPUT_DIR, item)
            if os.path.isdir(item_path):
                # 获取目录的修改时间
                mod_time = os.path.getmtime(item_path)
                output_dirs.append((item_path, item, mod_time))
                logger.info(f"找到输出目录: {item} (修改时间: {datetime.fromtimestamp(mod_time)})")
        
        # 按修改时间排序，最新的优先
        output_dirs.sort(key=lambda x: x[2], reverse=True)
        
        if not output_dirs:
            logger.warning("未找到任何输出目录")
            return {
                "status": "no_data",
                "message": "没有找到输出目录"
            }
        
        # 获取最新的目录
        latest_dir_path, latest_dir_name, _ = output_dirs[0]
        logger.info(f"使用最新目录: {latest_dir_name}")
        
        # 检查目录结构
        directories = {
            "cache": False,
            "reports": False,
            "serper": False
        }
        
        # 检查文件
        files = {
            "cache": [],
            "reports": [],
            "serper": []
        }
        
        # 检查是否存在final_report.md
        final_report_exists = False
        final_report_content = ""
        
        # 检查各个子目录
        for dir_name in directories.keys():
            dir_path = os.path.join(latest_dir_path, dir_name)
            if os.path.exists(dir_path) and os.path.isdir(dir_path):
                directories[dir_name] = True
                logger.info(f"子目录存在: {dir_name}")
                
                # 获取目录中的文件
                try:
                    for file in os.listdir(dir_path):
                        file_path = os.path.join(dir_path, file)
                        if os.path.isfile(file_path):
                            files[dir_name].append(file)
                            
                            # 检查是否是final_report.md
                            if dir_name == "reports" and file == "final_report.md":
                                final_report_exists = True
                                logger.info("发现final_report.md文件")
                                try:
                                    with open(file_path, 'r', encoding='utf-8') as f:
                                        final_report_content = f.read()
                                    logger.info(f"读取final_report.md成功，内容长度: {len(final_report_content)}")
                                except Exception as e:
                                    logger.error(f"读取final_report.md时出错: {e}")
                except Exception as e:
                    logger.error(f"列出目录 {dir_path} 中的文件时出错: {e}")
            else:
                logger.info(f"子目录不存在: {dir_name}")
        
        # 确定分析状态
        if final_report_exists:
            status = "completed"
        elif directories["reports"] and files["reports"]:
            status = "reports_generated"
        elif directories["serper"] and files["serper"]:
            status = "search_completed"
        elif directories["cache"] and files["cache"]:
            status = "cache_generated"
        else:
            status = "started"
            
        logger.info(f"分析状态: {status}")
            
        return {
            "status": status,
            "directory": latest_dir_name,
            "directory_path": latest_dir_path,
            "directories": directories,
            "files": files,
            "final_report_exists": final_report_exists,
            "final_report": final_report_content if final_report_exists else "",
            "is_complete": final_report_exists
        }
        
    except Exception as e:
        logger.exception(f"检查输出文件错误: {e}")
        return {
            "status": "error",
            "error": f"服务器错误: {str(e)}"
        }


@app.get("/{filename:path}")
async def serve_static(filename: str):
    """提供静态文件服务"""
    file_path = os.path.join(current_dir, filename)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    
    # 如果是API路径但不存在，记录更详细的错误信息
    if filename.startswith('api/'):
        logger.error(f"API路径不存在: {filename}")
        
    raise HTTPException(status_code=404, detail="文件不存在")


@app.post("/api/process-csv")
async def process_csv(file: UploadFile = File(...)):
    """处理上传的CSV文件并运行趋势分析"""
    try:
        if not file.filename:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "error": "未选择文件"}
            )
            
        if not file.filename.endswith('.csv'):
            return JSONResponse(
                status_code=400,
                content={"status": "error", "error": "请上传CSV文件"}
            )
            
        # 生成唯一的文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        user_id = uuid.uuid4().hex[:8]  # 模拟用户ID
        filename = f"{timestamp}_{user_id}_{file.filename}"
        
        # 保存到缓存目录
        cache_path = os.path.join(CACHE_DIR, filename)
        
        # 读取上传文件内容并保存
        content = await file.read()
        with open(cache_path, "wb") as f:
            f.write(content)
        
        logger.info(f"保存上传文件: {cache_path}")
        
        # 调用趋势分析脚本
        main_script = os.path.join(trend_analysis_dir, 'main.py')
        output_path = RESULTS_DIR
        
        logger.info(
            f"运行趋势分析: {main_script} {cache_path} --output-dir {output_path}"
        )
        
        # 使用数组方式传递参数，这更安全
        cmd = [
            sys.executable,
            main_script,
            cache_path,
            '--output-dir',
            output_path
        ]
        
        logger.info(f"执行命令: {cmd}")
        
        try:
            # 调用主分析脚本，执行趋势分析
            result = subprocess.run(
                cmd,
                shell=False,  # 不使用shell执行命令
                capture_output=True,
                text=True,
                check=False  # 改为False，手动检查返回值
            )
            
            logger.info(f"趋势分析输出: {result.stdout}")
            
            # 手动检查返回值
            if result.returncode != 0:
                logger.error(f"趋势分析错误: {result.stderr}")
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "error",
                        "error": f"分析失败: {result.stderr}"
                    }
                )
        except Exception as e:
            logger.error(f"趋势分析执行错误: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "error": f"分析执行错误: {str(e)}"
                }
            )
            
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
        file_stem = Path(cache_path).stem
        logger.info(f"分析完成，搜索匹配文件，文件基名: {file_stem}")
        
        # 搜索最近生成的文件
        # 获取所有结果文件，按修改时间排序
        all_files = list(Path(output_path).glob("*"))
        files = sorted(
            all_files, 
            key=lambda x: x.stat().st_mtime, 
            reverse=True
        )
        recent_files = files[:20]  # 只考虑最近的20个文件
        
        # 筛选出可能属于本次处理的文件 - 优先考虑时间戳匹配
        matching_files = []
        for f in recent_files:
            if timestamp in f.name or user_id in f.name or file_stem in f.name:
                matching_files.append(f)
        
        # 如果找不到匹配文件，使用最近的文件
        if not matching_files:
            logger.warning(
                f"找不到与时间戳{timestamp}或用户ID{user_id}或"
                f"文件名{file_stem}匹配的文件，使用最近的文件"
            )
            matching_files = recent_files[:8]  # 最多取8个文件
        
        if not matching_files:
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "error": "分析完成，但未找到输出文件"
                }
            )
        
        # 处理文件
        logger.info(f"处理 {len(matching_files)} 个匹配文件")
        
        # 创建结果字典
        results_dict = {
            "timestamp": timestamp,
            "filename": Path(cache_path).stem,
            "sensitive": {},
            "insensitive": {},
        }
        
        # 处理文件
        for i, file_path in enumerate(matching_files):
            file_name = file_path.name
            logger.info(f"处理文件 {i+1}/{len(matching_files)}: {file_name}")
            
            # 确定目标目录和路径
            is_image = file_path.suffix.lower() in [
                '.png', '.jpg', '.jpeg', '.gif'
            ]
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
                        if ('sensitive-trend_visualization' in file_name and 
                            'insensitive' not in file_name):
                            results_dict['sensitive']['visualization'] = file_name
                            logger.info(f"添加敏感版趋势图: {file_name}")
                        elif 'insensitive-trend_visualization' in file_name:
                            results_dict['insensitive']['visualization'] = file_name
                            logger.info(f"添加不敏感版趋势图: {file_name}")
                    else:
                        if ('sensitive-trend_analysis' in file_name and 
                            'insensitive' not in file_name):
                            results_dict['sensitive']['analysis'] = file_name
                            logger.info(f"添加敏感版趋势分析: {file_name}")
                        elif 'insensitive-trend_analysis' in file_name:
                            results_dict['insensitive']['analysis'] = file_name
                            logger.info(f"添加不敏感版趋势分析: {file_name}")
                        elif ('sensitive-enhanced_analysis' in file_name and 
                              'insensitive' not in file_name):
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
        
        return JSONResponse(
            content={
                "status": "success",
                "results": results_dict
            }
        )
        
    except Exception as e:
        logger.exception(f"处理CSV错误: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": f"服务器错误: {str(e)}"
            }
        )


@app.post("/api/save-processed-csv")
async def save_processed_csv(file: UploadFile = File(...)):
    """保存已处理的CSV文件到input目录"""
    try:
        if not file.filename:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "error": "未选择文件"}
            )
            
        if not file.filename.endswith('.csv'):
            return JSONResponse(
                status_code=400,
                content={"status": "error", "error": "请上传CSV文件"}
            )
            
        # 生成唯一的文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        user_id = uuid.uuid4().hex[:8]  # 模拟用户ID
        filename = f"{timestamp}_{user_id}_{Path(file.filename).stem}.csv"
        filepath = os.path.join(INPUT_DIR, filename)
        
        # 保存上传的文件
        content = await file.read()
        with open(filepath, "wb") as f:
            f.write(content)
            
        logger.info(f"保存处理后的CSV文件: {filepath}")
        
        return JSONResponse(
            content={
                "status": "success",
                "filepath": filepath
            }
        )
        
    except Exception as e:
        logger.exception(f"保存处理后的CSV文件错误: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": f"服务器错误: {str(e)}"
            }
        )


# 存储分析任务信息
ANALYSIS_JOBS = {}


@app.post("/api/run-analysis", response_model=AnalysisResponse)
async def run_analysis(
    request: AnalysisRequest, 
    background_tasks: BackgroundTasks
):
    """运行复盘分析"""
    try:
        input_file = request.file
        query = request.query
        
        if not input_file:
            raise HTTPException(status_code=400, detail="未指定输入文件")
            
        # 确认文件存在
        # 先检查INPUT_DIR
        input_path = os.path.join(INPUT_DIR, input_file)
        if not os.path.exists(input_path):
            # 如果不在INPUT_DIR，检查CACHE_DIR
            input_path = os.path.join(CACHE_DIR, input_file)
            if not os.path.exists(input_path):
                raise HTTPException(
                    status_code=404, 
                    detail=f"文件不存在: {input_file}"
                )
        
        # 创建job_id
        job_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        logger.info(f"运行复盘分析: 输入文件 {input_path}, 查询 \"{query}\", ID: {job_id}")
        
        # 定义后台任务执行函数
        def run_analysis_task():
            try:
                # 禁用遥测以避免SSL错误
                os.environ["OTEL_SDK_DISABLED"] = "true"
                
                # 创建RunTechAnalysisBackend实例
                backend = RunTechAnalysisBackend()
                
                # 调用analyze方法
                result = backend.analyze(input_path, query)
                
                # 获取output_dir
                output_dir = result.get("output_file", "").split("/reports/")[0] if result.get("output_file") else ""
                
                logger.info(f"分析任务启动，output_dir: {output_dir}")
                
                # 存储任务信息
                ANALYSIS_JOBS[job_id] = {
                    "output_dir": output_dir,
                    "status": result.get("status", ""),
                    "start_time": datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"分析任务执行错误: {e}")
        
        # 添加任务到后台执行
        background_tasks.add_task(run_analysis_task)
        
        return {
            "status": "success",
            "message": "分析已启动",
            "job_id": job_id
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"运行复盘分析错误: {e}")
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有请求"""
    logger.info(f"收到请求: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"响应: {response.status_code}")
    return response


def main():
    """主函数"""
    try:
        # 修改默认端口从5000到8080，避免与macOS的AirPlay服务冲突
        port = int(os.environ.get('PORT', 8080))
        uvicorn.run(app, host="0.0.0.0", port=port)
    except Exception as e:
        logger.exception(f"服务器启动错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 