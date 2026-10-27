"""
Main Agent — 主控 Agent
职责：接收用户指令，协调其他 Agent，汇报进度
task_type: reasoning → 火山引擎 volc-pro (primary)
"""
import logging
from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class MainAgent(BaseAgent):
    agent_name = "main_agent"
    prompt_file = "main_agent.md"
    task_type = "reasoning"
    default_temperature = 0.5
    default_max_tokens = 4000

    def build_messages(self, task_input: dict, system_prompt: str) -> list[dict]:
        messages = [{"role": "system", "content": system_prompt}]
        
        user_instruction = task_input.get("user_instruction", "")
        book_status = task_input.get("book_status", "")
        available_actions = task_input.get("available_actions", [])
        
        user_content = f"**用户指令**：{user_instruction}\n\n"
        if book_status:
            user_content += f"**当前书籍状态**：\n{book_status}\n\n"
        if available_actions:
            user_content += f"**可执行的操作**：{', '.join(available_actions)}\n\n"
        
        user_content += "请分析用户意图，给出执行计划或直接回复。\n"
        
        messages.append({"role": "user", "content": user_content})
        return messages

    def parse_response(self, response: str, task_input: dict) -> dict:
        return {
            "summary": "主控 Agent 响应完成",
            "response": response,
        }
