#!/usr/bin/env python
import sys
import warnings
import os

from datetime import datetime

from research_crew.crews.testcrew.crew import ResearchAgent
from crewai import Agent, Crew, Process

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# This main file is intended to be a way for you to run your
# crew locally, so refrain from adding unnecess ary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information

# 在代码开头添加环境变量来禁用遥测
os.environ['CREWAI_DISABLE_TELEMETRY'] = 'true'

def run():
    """
    运行crew.
    """
    inputs = {
        'topic': '黄金价格为什么创新高了？',
        'current_date': str(datetime.now().strftime('%Y-%m-%d'))
    }
    
    try:
        ResearchAgent(topic=inputs['topic']).crew().kickoff(inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")


# def train():
#     """
#     Train the crew for a given number of iterations.
#     """
#     inputs = {
#         "topic": "AI LLMs"
#     }
#     try:
#         Infoai().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

#     except Exception as e:
#         raise Exception(f"An error occurred while training the crew: {e}")

# def replay():
#     """
#     Replay the crew execution from a specific task.
#     """
#     try:    
#         Infoai().crew().replay(task_id=sys.argv[1])

#     except Exception as e:
#         raise Exception(f"An error occurred while replaying the crew: {e}")

# def test():
#     """
#     Test the crew execution and returns the results.
#     """
#     inputs = {
#         "topic": "AI LLMs"
#     }
#     try:
#         Infoai().crew().test(n_iterations=int(sys.argv[1]), openai_model_name=sys.argv[2], inputs=inputs)

#     except Exception as e:
#         raise Exception(f"An error occurred while testing the crew: {e}")
