#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
运行时间序列分析后端的脚本
提供命令行接口和进度显示

使用方法：
cd crewAI-agent/src/tech_analysis_crew
python run_backend.py [选项]

选项:
  --input PATH      输入CSV文件路径 (相对于当前目录)
  --query TEXT      分析查询（默认：分析铜价走势）
  --output-dir DIR  输出目录路径
  --debug          启用调试模式

示例:
  # 基本用法
  python run_backend.py --input input/vlcc.csv --query "复盘vlcc price"
  
  # 指定输出目录
  python run_backend.py --input input/vlcc.csv --query "复盘vlcc price" --output-dir ./output

依赖安装:
  pip install rich
"""

import os
import sys
import time
import logging
import argparse
import warnings
import signal
from typing import Dict, Any
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TimeElapsedColumn
)

# 忽略 Pydantic 警告
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# 添加项目根目录到Python路径
current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入后端
try:
    from tech_analysis_crew.backend import (
        RunTechAnalysisBackend,
        IndicatorExtractionError
    )
except ImportError:
    from src.tech_analysis_crew.backend import (
        RunTechAnalysisBackend,
        IndicatorExtractionError
    )

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("RunBackend")
console = Console()


def display_header():
    """显示脚本头部信息"""
    console.print("\n[bold cyan]时间序列分析工具[/bold cyan]")
    console.print("=" * 50)
    console.print("\n[yellow]初始化分析环境...[/yellow]")


def display_result(result: Dict[str, Any]):
    """显示分析结果
    
    Args:
        result: 分析结果字典
    """
    if result["status"] == "success":
        console.print("\n[bold green]分析完成！[/bold green]")
        console.print(f"\n作业ID: [cyan]{result['job_id']}[/cyan]")
        console.print(f"分析指标: [cyan]{result['indicator']}[/cyan]")
        console.print(f"输入文件: [cyan]{result['input_file']}[/cyan]")

        # 如果有多个输出文件，显示所有文件
        console.print(f"输出文件: [cyan]{result['output_file']}[/cyan]")

        console.print(f"摘要文件: [cyan]{result['summary_file']}[/cyan]")
        console.print(f"总耗时: [cyan]{result['duration']:.2f}秒[/cyan]")
    else:
        console.print("\n[bold red]分析失败！[/bold red]")
        console.print(f"错误信息: [red]{result['error']}[/red]")


def display_progress(backend: RunTechAnalysisBackend):
    """显示分析进度
    
    Args:
        backend: 后端实例
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        task = progress.add_task(
            description="正在分析...",
            total=backend.progress["total_steps"]
        )
        
        last_status = ""
        
        while not progress.finished:
            try:
                current_status = backend.progress["status"]
                current_step = backend.progress["current_step"]
                current_index = backend.progress["current_step_index"]
                
                if current_status != last_status:
                    progress.update(
                        task,
                        description=f"[cyan]{current_step}[/cyan]",
                        completed=current_index
                    )
                    last_status = current_status
                
                if current_status in ["completed", "error"]:
                    progress.update(
                        task,
                        completed=backend.progress["total_steps"]
                    )
                    break
                
                time.sleep(0.1)
            except (KeyError, AttributeError) as e:
                logger.error(f"获取进度信息失败: {e}")
                break


def validate_args(args):
    """验证命令行参数
    
    Args:
        args: 解析后的命令行参数

    Raises:
        ValueError: 当参数无效时抛出
    """
    if args.input:
        # 转换为绝对路径
        input_path = os.path.abspath(args.input)
        if not os.path.exists(input_path):
            raise ValueError(f"输入文件不存在: {input_path}")
        args.input = input_path


def main():
    """主函数"""
    # 设置信号处理
    def signal_handler(sig, frame):
        console.print("\n\n[bold yellow]用户中断分析，正在安全退出...[/bold yellow]")
        sys.exit(0)
    
    # 注册SIGINT信号处理器（Ctrl+C）
    signal.signal(signal.SIGINT, signal_handler)
    
    parser = argparse.ArgumentParser(
        description="时间序列分析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--input", type=str, help="输入CSV文件路径")
    parser.add_argument(
        "--query",
        type=str,
        default="分析铜价走势",
        help="用户查询"
    )
    parser.add_argument("--output-dir", type=str, help="输出目录路径")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    
    try:
        args = parser.parse_args()
        validate_args(args)
    except Exception as e:
        console.print(f"\n[bold red]参数错误：[/bold red]{str(e)}")
        parser.print_help()
        sys.exit(1)
    
    display_header()
    
    try:
        backend = RunTechAnalysisBackend()
        
        if args.output_dir:
            output_dir = os.path.abspath(args.output_dir)
            backend.output_dir = output_dir
            os.makedirs(output_dir, exist_ok=True)
        
        console.print(
            f"\n输入文件: [cyan]{args.input or '使用默认文件'}[/cyan]"
        )
        console.print(f"用户查询: [cyan]{args.query}[/cyan]")
        console.print(f"输出目录: [cyan]{backend.output_dir}[/cyan]")
        
        os.environ["OTEL_SDK_DISABLED"] = "true"
        
        console.print("\n[yellow]开始分析...[/yellow]\n")
        
        try:
            # 直接执行分析，不使用多线程
            result = backend.analyze(args.input, args.query)
            
            # 显示分析进度（已完成）
            display_result(result)
            
        except Exception as e:
            console.print(f"\n[bold red]分析过程中出错：[/bold red]{str(e)}")
            if args.debug:
                import traceback
                console.print("\n[red]调试信息：[/red]")
                console.print(traceback.format_exc())
            sys.exit(1)
        
    except IndicatorExtractionError as e:
        console.print(f"\n[bold red]指标提取失败：[/bold red]{str(e)}")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n\n[yellow]用户中断分析[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]发生错误：[/bold red]{str(e)}")
        if args.debug:
            import traceback
            console.print("\n[red]调试信息：[/red]")
            console.print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()