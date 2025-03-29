#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
时间序列分析后端API服务
提供REST API接口供前端调用

使用方法：
cd crewAI-agent/src/tech_analysis_crew
python run_api.py

API文档:
http://localhost:8000/docs
"""

import os
import sys
import logging
import warnings
import uuid
import subprocess
import json
from typing import Optional, List
from datetime import datetime
from fastapi import (
    FastAPI, 
    BackgroundTasks, 
    HTTPException
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# 忽略 Pydantic 警告
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# 添加项目根目录到Python路径
current_file = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入后端
try:
    from src.tech_analysis_crew.backend import (
        RunTechAnalysisBackend
    )
except ImportError:
    from tech_analysis_crew.backend import (
        RunTechAnalysisBackend
    )

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("TechAnalysisAPI")

# 创建FastAPI应用
app = FastAPI(
    title="时间序列分析API",
    description="提供时间序列数据分析功能的REST API",
    version="1.0.0"
)

# 允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境中应该限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建全局后端实例
backend = RunTechAnalysisBackend()

# 存储任务状态的内存字典
analysis_tasks = {}

# Pydantic模型
class AnalysisRequest(BaseModel):
    input_file: Optional[str] = Field(None, description="输入CSV文件路径，为空则使用默认文件")
    query: str = Field(..., description="分析查询文本，例如：'分析铜价走势'")
    output_dir: Optional[str] = Field(None, description="输出目录路径")

class TaskStatus(BaseModel):
    job_id: str
    status: str
    current_step: str
    progress: int  # 0-100
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    error: Optional[str] = None

class AnalysisResult(BaseModel):
    job_id: str
    status: str
    indicator: Optional[str] = None
    input_file: Optional[str] = None
    output_file: Optional[str] = None
    summary_file: Optional[str] = None
    duration: Optional[float] = None
    error: Optional[str] = None

# 后台任务函数 - 使用子进程方式避免asyncio冲突
async def run_analysis_task(job_id: str, input_file: Optional[str], query: str, 
                           output_dir: Optional[str]):
    """
    执行分析并更新任务状态 - 使用子进程方式执行以避免asyncio冲突
    """
    try:
        # 更新状态为进行中
        analysis_tasks[job_id]["status"] = "running"
        analysis_tasks[job_id]["current_step"] = "正在启动分析流程"
        
        # 创建输出目录
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        else:
            output_dir = os.path.join(current_dir, "output", job_id)
            os.makedirs(output_dir, exist_ok=True)
        
        # 获取绝对路径
        input_file_path = os.path.abspath(input_file) if input_file else ""
        output_dir_path = os.path.abspath(output_dir)
        project_root_path = project_root
        current_dir_path = current_dir
        
        # 准备运行参数 - 使用单独的Python脚本
        temp_script = os.path.join(output_dir, f"task_{job_id}.py")
        
        # 创建临时脚本文件
        with open(temp_script, "w") as f:
            f.write(f"""#!/usr/bin/env python
# -*- coding: utf-8 -*-
\"\"\"
临时分析脚本 - 任务ID: {job_id}
\"\"\"
import os
import sys
import json
import io
import contextlib
from datetime import datetime

# 重定向标准输出，以过滤非JSON输出
class OutputFilter:
    def __init__(self):
        self.original_stdout = sys.stdout
        self.captured_output = []
        self.json_result = None
    
    def write(self, text):
        # 保存所有输出
        self.captured_output.append(text)
        # 尝试识别JSON输出
        if text.strip().startswith('{{') and text.strip().endswith('}}'):
            try:
                json.loads(text)
                self.json_result = text
            except:
                pass
        # 也写入到原始stdout用于调试
        self.original_stdout.write(text)
    
    def flush(self):
        self.original_stdout.flush()
    
    def get_json_result(self):
        # 如果找到了JSON结果，直接返回
        if self.json_result:
            return self.json_result
            
        # 尝试从全部输出中找出最长的有效JSON
        all_output = ''.join(self.captured_output)
        # 寻找最外层花括号对的位置
        start_pos = all_output.find('{{')
        if start_pos >= 0:
            depth = 1
            for i in range(start_pos + 2, len(all_output)):
                if all_output[i] == '{{':
                    depth += 1
                elif all_output[i] == '}}':
                    depth -= 1
                    if depth == 0:
                        # 找到完整的JSON
                        try:
                            json_text = all_output[start_pos:i+1]
                            json.loads(json_text)
                            return json_text
                        except:
                            pass
        
        # 如果上面的方法都失败了，尝试最后的措施
        try:
            # 构造一个fallback的JSON结果
            fallback = {{
                "status": "success",
                "raw_output": ''.join(self.captured_output[-1000:]) if self.captured_output else "",
                "output_file": os.path.join("{output_dir_path.replace('\\', '\\\\')}", "output.md")
            }}
            return json.dumps(fallback)
        except:
            return json.dumps({{"status": "error", "error": "无法获取有效的JSON结果"}})

# 设置Python路径
project_root = "{project_root_path.replace('\\', '\\\\')}"
current_dir = "{current_dir_path.replace('\\', '\\\\')}"
parent_dir = os.path.dirname(current_dir)
parent_parent_dir = os.path.dirname(parent_dir)

# 确保所有可能的路径都在sys.path中
sys.path.insert(0, project_root)
sys.path.insert(0, current_dir)
sys.path.insert(0, parent_dir)
sys.path.insert(0, parent_parent_dir)
sys.path.insert(0, os.path.dirname(os.path.dirname(project_root)))
sys.path.insert(0, os.path.join(project_root, "src"))

# 输出调试信息
print(json.dumps({{
    "debug_info": {{
        "sys_path": sys.path,
        "current_dir": current_dir,
        "project_root": project_root
    }}
}}), file=sys.stderr)

# 禁用OpenTelemetry
os.environ["OTEL_SDK_DISABLED"] = "true"

try:
    # 尝试多种导入路径
    backend_module = None
    import_errors = []
    
    # 尝试方法1：直接导入
    try:
        from tech_analysis_crew.backend import RunTechAnalysisBackend
        backend_module = "tech_analysis_crew.backend"
    except ImportError as e1:
        import_errors.append(f"方法1失败: {{e1}}")
        
        # 尝试方法2：从src导入
        try:
            from src.tech_analysis_crew.backend import RunTechAnalysisBackend
            backend_module = "src.tech_analysis_crew.backend"
        except ImportError as e2:
            import_errors.append(f"方法2失败: {{e2}}")
            
            # 尝试方法3：使用绝对路径导入
            try:
                sys.path.insert(0, os.path.dirname("{current_dir_path.replace('\\', '\\\\')}"))
                from tech_analysis_crew.backend import RunTechAnalysisBackend
                backend_module = "absolute:tech_analysis_crew.backend"
            except ImportError as e3:
                import_errors.append(f"方法3失败: {{e3}}")
                
                # 尝试方法4：直接从文件导入
                try:
                    backend_file = os.path.join(current_dir, "backend.py")
                    sys.path.insert(0, os.path.dirname(backend_file))
                    import backend
                    RunTechAnalysisBackend = backend.RunTechAnalysisBackend
                    backend_module = "direct:backend"
                except ImportError as e4:
                    import_errors.append(f"方法4失败: {{e4}}")
                    # 所有尝试都失败
                    print(json.dumps({{
                        "status": "error",
                        "error": f"无法导入RunTechAnalysisBackend: {{import_errors}}"
                    }}))
                    sys.exit(1)
    
    # 输出成功的导入路径
    print(f"成功导入后端模块: {{backend_module}}", file=sys.stderr)
    
    # 创建后端实例并执行分析
    backend = RunTechAnalysisBackend()
    backend.output_dir = "{output_dir_path.replace('\\', '\\\\')}"
    
    # 使用输出过滤器捕获输出
    output_filter = OutputFilter()
    sys.stdout = output_filter
    
    # 执行分析
    try:
        result = backend.analyze(
            "{input_file_path.replace('\\', '\\\\')}" if "{input_file_path}" else None, 
            "{query.replace('"', '\\"')}"
        )
        
        # 输出JSON结果
        try:
            # 确保结果是可序列化的
            if not isinstance(result, dict):
                result = {{"status": "success", "raw_output": str(result)}}
            
            # 转换结果中的所有非字符串键为字符串
            json_result = {{}}
            for k, v in result.items():
                # 确保键是字符串
                key = str(k)
                # 如果值是不可序列化的对象，转换为字符串
                if isinstance(v, (dict, list, str, int, float, bool, type(None))):
                    json_result[key] = v
                else:
                    json_result[key] = str(v)
            
            # 打印JSON格式的结果
            print(json.dumps(json_result))
        except Exception as e:
            print(json.dumps({{
                "status": "error",
                "error": f"结果序列化失败: {{str(e)}}",
                "raw_result": str(result)
            }}))
    except Exception as e:
        print(json.dumps({{
            "status": "error", 
            "error": f"分析执行失败: {{str(e)}}"
        }}))
    
    # 恢复原始stdout
    sys.stdout = output_filter.original_stdout
    
    # 获取最终的JSON结果
    final_result = output_filter.get_json_result()
    
    # 最后输出JSON结果到原始stdout
    print(final_result)
    
except Exception as e:
    # 处理异常
    import traceback
    error_trace = traceback.format_exc()
    print(json.dumps({{
        "status": "error",
        "error": str(e),
        "traceback": error_trace
    }}))
    sys.exit(1)
""")
        
        # 设置脚本权限
        os.chmod(temp_script, 0o755)
        
        # 执行脚本
        logger.info(f"启动分析子进程，任务ID: {job_id}, 脚本: {temp_script}")
        process = subprocess.Popen(
            [sys.executable, temp_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 等待进程完成
        stdout, stderr = process.communicate()
        
        # 记录调试信息
        logger.info(f"子进程返回码: {process.returncode}")
        if stderr:
            logger.info(f"子进程标准错误: {stderr}")
        
        # 处理结果
        try:
            # 尝试解析JSON结果
            if stdout.strip():
                # 尝试找出最长的有效JSON
                json_result = None
                
                # 检查输出是否包含有效的JSON
                start_pos = stdout.find('{')
                if start_pos >= 0:
                    depth = 1
                    for i in range(start_pos + 1, len(stdout)):
                        if stdout[i] == '{':
                            depth += 1
                        elif stdout[i] == '}':
                            depth -= 1
                            if depth == 0:
                                # 找到完整的JSON
                                try:
                                    json_text = stdout[start_pos:i+1]
                                    json_result = json.loads(json_text)
                                    logger.info("成功从输出中提取JSON结果")
                                    break
                                except:
                                    pass
                
                # 如果找到有效JSON
                if json_result:
                    # 检查json_result中的路径是否正确
                    output_file = json_result.get("output_file", "")
                    summary_file = json_result.get("summary_file", "")
                    
                    # 如果output_file不是目录路径，尝试获取reports目录
                    if output_file and not output_file.endswith("reports"):
                        # 检查是否包含CrewAI生成的job_id
                        for key, value in json_result.items():
                            if isinstance(value, str) and "job_" in value and "_2025" in value:
                                crew_job_id = value
                                # 寻找输出目录
                                if os.path.exists(output_dir):
                                    for item in os.listdir(output_dir):
                                        if crew_job_id in item and os.path.isdir(os.path.join(output_dir, item)):
                                            job_dir = os.path.join(output_dir, item)
                                            reports_dir = os.path.join(job_dir, "reports")
                                            if os.path.exists(reports_dir):
                                                output_file = reports_dir
                                                # 查找final_report.md
                                                final_report = os.path.join(reports_dir, "final_report.md")
                                                if os.path.exists(final_report):
                                                    summary_file = final_report
                                                logger.info(f"更新输出目录: {output_file}")
                                                logger.info(f"更新摘要文件: {summary_file}")
                                                break
                    
                    # 如果summary_file仍然为空，但output_file是reports目录，再次尝试查找final_report.md
                    if not summary_file and output_file and os.path.exists(output_file) and os.path.basename(output_file) == "reports":
                        final_report = os.path.join(output_file, "final_report.md")
                        if os.path.exists(final_report):
                            summary_file = final_report
                            logger.info(f"已找到最终报告: {summary_file}")
                    
                    # 确保duration是有效值
                    duration = json_result.get("duration", 0.0)
                    if not duration or duration <= 0:
                        try:
                            # 使用当前时间计算一个近似值
                            start_time = datetime.fromisoformat(analysis_tasks[job_id]["start_time"])
                            duration = (datetime.now() - start_time).total_seconds()
                        except Exception as e:
                            logger.error(f"计算持续时间时出错: {str(e)}")
                    
                    # 更新任务状态
                    analysis_tasks[job_id] = {
                        "job_id": job_id,
                        "status": json_result.get("status", "completed"),
                        "indicator": json_result.get("indicator", ""),
                        "input_file": json_result.get("input_file", ""),
                        "output_file": output_file,
                        "summary_file": summary_file,
                        "duration": duration,
                        "error": json_result.get("error", None),
                        "progress": json_result.get("progress", {})
                    }
                    
                    logger.info(f"分析任务 {job_id} 已完成")
                    
                    # 确保设置了summary_file（如果存在）
                    if os.path.exists(final_report) and not analysis_tasks[job_id].get("summary_file"):
                        analysis_tasks[job_id]["summary_file"] = final_report
                        logger.info(f"已更新摘要文件路径: {final_report}")
                else:
                    # 如果未找到有效JSON，尝试创建一个fallback结果
                    logger.error(f"无法从输出中提取有效JSON，创建fallback结果")
                    
                    # 提取关键信息
                    indicator = ""
                    if "comex copper price" in stdout.lower():
                        indicator = "comex copper price"
                    
                    # 查找CrewAI生成的作业ID和输出目录
                    job_folder = None
                    crew_job_id = None
                    for line in stdout.split('\n'):
                        if "作业ID:" in line:
                            try:
                                crew_job_id = line.split("作业ID:")[1].strip()
                                logger.info(f"从输出中提取到CrewAI作业ID: {crew_job_id}")
                                break
                            except:
                                pass
                    
                    # 查找输出目录路径
                    output_dir_path = None
                    for line in stdout.split('\n'):
                        if "输出目录:" in line:
                            try:
                                output_dir_path = line.split("输出目录:")[1].strip()
                                logger.info(f"从输出中提取到输出目录: {output_dir_path}")
                                break
                            except:
                                pass
                    
                    # 如果找到CrewAI作业ID和输出目录
                    reports_dir = None
                    final_report_path = None
                    if crew_job_id and output_dir_path and os.path.exists(output_dir_path):
                        # 设置正确的报告目录和最终报告路径
                        reports_dir = os.path.join(output_dir_path, "reports")
                        final_report_path = os.path.join(reports_dir, "final_report.md")
                    else:
                        # 创建自定义输出文件作为备用
                        output_dir_path = output_dir
                        reports_dir = os.path.join(output_dir, "reports")
                        os.makedirs(reports_dir, exist_ok=True)
                        final_report_path = os.path.join(reports_dir, "final_report.md")
                    
                    # 创建输出文件，将原始输出保存下来
                    output_file = os.path.join(output_dir, "output.md")
                    with open(output_file, "w") as f:
                        f.write(f"# 分析结果 - {job_id}\n\n")
                        f.write(f"## 查询\n{query}\n\n")
                        f.write(f"## 原始输出\n```\n{stdout[:2000]}\n```\n")
                    
                    # 计算持续时间
                    duration = 0.0
                    try:
                        start_time_str = None
                        end_time_str = None
                        for line in stdout.split('\n'):
                            if "开始时间:" in line:
                                start_time_str = line.split("开始时间:")[1].strip()
                            if "结束时间:" in line:
                                end_time_str = line.split("结束时间:")[1].strip()
                        
                        if start_time_str and end_time_str:
                            start_time = datetime.fromisoformat(start_time_str)
                            end_time = datetime.fromisoformat(end_time_str)
                            duration = (end_time - start_time).total_seconds()
                        else:
                            # 如果没有找到时间信息，使用当前时间计算一个近似值
                            duration = (datetime.now() - datetime.fromisoformat(analysis_tasks[job_id]["start_time"])).total_seconds()
                    except Exception as e:
                        logger.error(f"计算持续时间时出错: {str(e)}")
                    
                    # 更新任务状态
                    analysis_tasks[job_id] = {
                        "job_id": job_id,
                        "status": "success",
                        "indicator": indicator,
                        "input_file": input_file_path if input_file_path else "",
                        "output_file": reports_dir if reports_dir else output_file,
                        "summary_file": final_report_path if os.path.exists(final_report_path) else "",
                        "duration": duration,
                        "error": None,
                        "progress": {
                            "current_step": "已完成，但结果解析异常", 
                            "current_step_index": 7, 
                            "total_steps": 7
                        }
                    }
                    
                    logger.info(f"分析任务 {job_id} 已完成(fallback)，输出目录: {reports_dir}")
                    logger.info(f"最终报告路径: {final_report_path}, 持续时间: {duration:.2f}秒")
            else:
                # 输出为空，可能有错误
                error_info = stderr if stderr else "子进程没有输出"
                logger.error(f"分析任务 {job_id} 执行失败: {error_info}")
                
                analysis_tasks[job_id] = {
                    "job_id": job_id,
                    "status": "error",
                    "error": f"分析过程没有输出。错误信息: {error_info}",
                    "progress": {
                        "current_step": "执行失败", 
                        "current_step_index": 0, 
                        "total_steps": 1
                    }
                }
                
        except Exception as e:
            # 处理解析异常
            logger.error(f"处理分析结果时出错: {str(e)}")
            
            # 提取调试信息
            debug_info = []
            for line in stderr.splitlines():
                if "debug_info" in line or "成功导入后端模块" in line:
                    debug_info.append(line)
            
            error_msg = f"处理分析结果时出错: {str(e)}\n"
            error_msg += f"调试信息: {'; '.join(debug_info)}\n" if debug_info else ""
            error_msg += f"错误输出: {stderr}\n"
            error_msg += f"标准输出: {stdout[:500]}..." if len(stdout) > 500 else stdout
            
            analysis_tasks[job_id] = {
                "job_id": job_id,
                "status": "error",
                "error": error_msg,
                "progress": {
                    "current_step": "执行失败", 
                    "current_step_index": 0, 
                    "total_steps": 1
                }
            }
    except Exception as e:
        # 更新任务状态为错误
        analysis_tasks[job_id] = {
            "job_id": job_id,
            "status": "error",
            "error": str(e),
            "progress": {
                "current_step": "发生异常", 
                "current_step_index": 0, 
                "total_steps": 1
            }
        }
        logger.error(f"分析任务 {job_id} 执行失败: {str(e)}")

@app.post("/api/analysis", response_model=TaskStatus, summary="启动新的分析任务")
async def start_analysis(
    background_tasks: BackgroundTasks,
    request: AnalysisRequest
):
    """
    启动新的时间序列分析任务
    
    - **input_file**: 可选，输入CSV文件路径
    - **query**: 必填，分析查询文本
    - **output_dir**: 可选，输出目录路径
    
    返回任务ID和初始状态
    """
    # 验证输入文件是否存在
    if request.input_file and not os.path.exists(request.input_file):
        raise HTTPException(status_code=400, detail="输入文件不存在")
    
    # 生成任务ID
    job_id = str(uuid.uuid4())
    
    # 初始化任务状态
    analysis_tasks[job_id] = {
        "job_id": job_id,
        "status": "initialized",
        "current_step": "任务初始化",
        "progress": 0,
        "start_time": datetime.now().isoformat(),
        "end_time": None,
        "error": None
    }
    
    # 启动后台任务
    background_tasks.add_task(
        run_analysis_task, 
        job_id, 
        request.input_file, 
        request.query, 
        request.output_dir
    )
    
    logger.info(f"分析任务 {job_id} 已创建并启动")
    
    return TaskStatus(
        job_id=job_id,
        status="initialized",
        current_step="任务已创建，正在启动...",
        progress=0
    )
    
@app.get("/api/analysis/{job_id}", response_model=TaskStatus, summary="获取任务状态")
async def get_task_status(job_id: str):
    """
    获取指定分析任务的状态
    
    - **job_id**: 任务ID
    
    返回任务当前状态
    """
    if job_id not in analysis_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = analysis_tasks[job_id]
    progress = task.get("progress", {})
    
    # 计算进度百分比
    progress_percentage = 0
    if isinstance(progress, dict) and "current_step_index" in progress and "total_steps" in progress:
        total_steps = max(progress["total_steps"], 1)  # 避免除零错误
        current_step = progress["current_step_index"]
        progress_percentage = min(int(current_step * 100 / total_steps), 100)
    
    return TaskStatus(
        job_id=job_id,
        status=task["status"],
        current_step=progress.get("current_step", "") if isinstance(progress, dict) else "",
        progress=progress_percentage,
        start_time=progress.get("start_time", "") if isinstance(progress, dict) else "",
        end_time=progress.get("end_time", "") if isinstance(progress, dict) else "",
        error=task.get("error", None)
    )

@app.get("/api/analysis/{job_id}/result", response_model=AnalysisResult, summary="获取分析结果")
async def get_analysis_result(job_id: str):
    """
    获取指定分析任务的完整结果
    
    - **job_id**: 任务ID
    
    返回任务的完整分析结果，包括输出文件路径
    """
    if job_id not in analysis_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = analysis_tasks[job_id]
    
    # 检查任务是否完成
    if task["status"] not in ["completed", "success", "error"]:
        raise HTTPException(status_code=400, detail="任务尚未完成")
    
    # 再次检查summary_file
    output_file = task.get("output_file", "")
    if output_file and not task.get("summary_file") and os.path.exists(output_file) and os.path.isdir(output_file):
        final_report = os.path.join(output_file, "final_report.md")
        if os.path.exists(final_report):
            task["summary_file"] = final_report
            logger.info(f"在API调用时更新摘要文件: {final_report}")
    
    return AnalysisResult(
        job_id=job_id,
        status=task["status"],
        indicator=task.get("indicator", ""),
        input_file=task.get("input_file", ""),
        output_file=task.get("output_file", ""),
        summary_file=task.get("summary_file", ""),
        duration=task.get("duration", 0),
        error=task.get("error", None)
    )

@app.get("/api/tasks", response_model=List[TaskStatus], summary="获取所有任务")
async def list_tasks():
    """
    获取所有分析任务的状态列表
    
    返回所有任务的简要状态
    """
    result = []
    for job_id, task in analysis_tasks.items():
        progress = task.get("progress", {})
        
        # 计算进度百分比
        progress_percentage = 0
        if isinstance(progress, dict) and "current_step_index" in progress and "total_steps" in progress:
            total_steps = max(progress["total_steps"], 1)  # 避免除零错误
            current_step = progress["current_step_index"]
            progress_percentage = min(int(current_step * 100 / total_steps), 100)
            
        result.append(TaskStatus(
            job_id=job_id,
            status=task["status"],
            current_step=progress.get("current_step", "") if isinstance(progress, dict) else "",
            progress=progress_percentage,
            start_time=progress.get("start_time", "") if isinstance(progress, dict) else "",
            end_time=progress.get("end_time", "") if isinstance(progress, dict) else "",
            error=task.get("error", None)
        ))
    
    return result

@app.delete("/api/analysis/{job_id}", summary="删除任务")
async def delete_task(job_id: str):
    """
    删除指定的分析任务
    
    - **job_id**: 任务ID
    
    返回删除操作的结果
    """
    if job_id not in analysis_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    del analysis_tasks[job_id]
    
    return {"status": "success", "message": f"任务 {job_id} 已删除"}

@app.get("/", summary="API根路径")
async def root():
    """
    API根路径，返回服务信息
    """
    return {
        "name": "时间序列分析API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": [
            "/api/analysis",
            "/api/analysis/{job_id}",
            "/api/analysis/{job_id}/result",
            "/api/tasks"
        ]
    }

# 错误处理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理器"""
    logger.error(f"请求处理时发生错误: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": str(exc)}
    )

# 如果直接运行此脚本，启动API服务
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        workers=1  # 使用单进程模式
    )