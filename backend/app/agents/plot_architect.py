"""
Plot Architect Agent — 情节架构师
职责：故事大纲、章节规划、伏笔管理、节奏控制
task_type: reasoning → 火山引擎 volc-pro (primary)
"""
import logging
from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class PlotArchitectAgent(BaseAgent):
    agent_name = "plot_architect"
    prompt_file = "plot_architect.md"
    task_type = "reasoning"
    default_temperature = 0.5
    default_max_tokens = 8000

    def build_messages(self, task_input: dict, system_prompt: str) -> list[dict]:
        messages = [{"role": "system", "content": system_prompt}]
        
        sub_task = task_input.get("sub_task", "outline")
        
        if sub_task == "outline":
            # 生成总大纲
            world_summary = task_input.get("world_summary", "")
            characters = task_input.get("characters_summary", "")
            genre = task_input.get("genre", "xuanhuan")
            
            user_content = f"基于以下设定生成故事大纲：\n\n"
            user_content += f"**题材**：{genre}\n"
            user_content += f"**世界设定**：\n{world_summary}\n\n"
            user_content += f"**核心角色**：\n{characters}\n\n"
            user_content += "请生成：\n"
            user_content += "1. 总大纲（master_outline.md）— 全书脉络\n"
            user_content += "2. 前 3 章细纲（chapter-0001.md ~ chapter-0003.md）\n"
            user_content += "3. 初始伏笔账本（hook_ledger.json 格式）\n"
            user_content += "4. 初始时间线（timeline.json 格式）\n"
            
        elif sub_task == "chapter_intent":
            # 生成单章意图
            chapter_number = task_input.get("chapter_number", 1)
            prev_summary = task_input.get("previous_summary", "")
            hook_ledger = task_input.get("hook_ledger", "")
            master_outline = task_input.get("master_outline", "")
            
            user_content = f"请为第 {chapter_number} 章生成章节意图（intent.md）：\n\n"
            user_content += f"**前情摘要**：\n{prev_summary}\n\n"
            user_content += f"**总大纲相关部分**：\n{master_outline}\n\n"
            user_content += f"**当前伏笔账本**：\n{hook_ledger}\n\n"
            user_content += "请明确：\n"
            user_content += "- 本章推进哪些伏笔\n"
            user_content += "- 引入哪些冲突\n"
            user_content += "- 节奏定位（铺垫/高潮/过渡/转折）\n"
            user_content += "- 章末钩子设计\n"
            
        else:
            user_content = task_input.get("task", "请帮助规划情节")
        
        messages.append({"role": "user", "content": user_content})
        return messages

    def parse_response(self, response: str, task_input: dict) -> dict:
        sections = response.split("===")
        parsed = {"output_files": [], "sections": {}, "raw": response}
        
        for section in sections:
            section = section.strip()
            if section:
                for keyword in ["master_outline", "chapter-", "hook_ledger", "timeline", "intent"]:
                    if keyword in section.lower()[:200]:
                        parsed["sections"][keyword] = section
                        parsed["output_files"].append(keyword)
                        break
                else:
                    parsed["sections"]["outline"] = section
        
        parsed["summary"] = f"完成情节规划，生成了 {len(parsed['sections'])} 个文件"
        return parsed
