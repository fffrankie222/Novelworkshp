"""
Consistency Checker Agent — 一致性审核员
职责：检查章节与世界设定、角色状态、时间线的一致性
task_type: reasoning → 火山引擎 volc-pro (primary)
支持三种模式：observer（事实提取）、reflector（状态 delta）、auditor（20维审核）
"""
import json
import logging
from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class ConsistencyCheckerAgent(BaseAgent):
    agent_name = "consistency_checker"
    prompt_file = "consistency_checker.md"
    task_type = "reasoning"
    default_temperature = 0.3  # 审核需要低温保证准确性
    default_max_tokens = 6000

    def build_messages(self, task_input: dict, system_prompt: str) -> list[dict]:
        messages = [{"role": "system", "content": system_prompt}]
        
        mode = task_input.get("mode", "auditor")
        
        if mode == "observer":
            # Observer 模式：从正文提取 9 类事实
            chapter_text = task_input.get("chapter_text", "")
            chapter_number = task_input.get("chapter_number", 1)
            
            user_content = f"请以 Observer 模式分析第 {chapter_number} 章正文，提取所有事实性陈述。\n\n"
            user_content += f"**正文内容**：\n{chapter_text}\n\n"
            user_content += "请按以下 9 个类别分类提取：\n"
            user_content += "1. 角色状态变更（HP、修为、情绪、位置）\n"
            user_content += "2. 人际关系变动\n"
            user_content += "3. 物品流转\n"
            user_content += "4. 地理/时间标记\n"
            user_content += "5. 世界观规则触发\n"
            user_content += "6. 伏笔相关事件\n"
            user_content += "7. 势力/阵营变动\n"
            user_content += "8. 秘密/信息传播\n"
            user_content += "9. 情感/心理转折\n\n"
            user_content += "请以 JSON 格式输出，结构为 {facts: [{category, description, characters_involved, evidence}]}\n"
            
        elif mode == "reflector":
            # Reflector 模式：基于事实生成状态 delta
            facts = task_input.get("facts", "")
            current_states = task_input.get("current_states", "")
            chapter_number = task_input.get("chapter_number", 1)
            
            user_content = f"请以 Reflector 模式，基于以下事实生成状态更新 delta。\n\n"
            user_content += f"**章节**：chapter-{chapter_number:04d}\n\n"
            user_content += f"**提取的事实**：\n{facts}\n\n"
            user_content += f"**当前状态**：\n{current_states}\n\n"
            user_content += "请输出 JSON delta，包含：\n"
            user_content += "- character_states: 角色状态变更\n"
            user_content += "- world_state: 世界状态变更\n"
            user_content += "- hook_updates: 伏笔更新（advance/upsert/resolve）\n"
            user_content += "- timeline_events: 时间线事件\n"
            
        elif mode == "auditor":
            # Auditor 模式：20 维度审核
            chapter_text = task_input.get("chapter_text", "")
            chapter_number = task_input.get("chapter_number", 1)
            world_rules = task_input.get("world_rules", "")
            character_states = task_input.get("character_states", "")
            timeline = task_input.get("timeline", "")
            hook_ledger = task_input.get("hook_ledger", "")
            
            user_content = f"请以 Auditor 模式对第 {chapter_number} 章进行 20 维度审核。\n\n"
            user_content += f"**待审核正文**：\n{chapter_text}\n\n"
            
            if world_rules:
                user_content += f"**世界规则**：\n{world_rules}\n\n"
            if character_states:
                user_content += f"**角色当前状态**：\n{character_states}\n\n"
            if timeline:
                user_content += f"**时间线**：\n{timeline}\n\n"
            if hook_ledger:
                user_content += f"**伏笔账本**：\n{hook_ledger}\n\n"
            
            user_content += "请对以下 20 个维度逐一审核，输出 JSON 格式的审核报告：\n"
            user_content += "1.时间线一致性 2.角色位置合理性 3.角色能力边界 4.人设言行一致\n"
            user_content += "5.称谓/称呼一致 6.伏笔回收状态 7.新伏笔合理性 8.情节逻辑自洽\n"
            user_content += "9.场景转换流畅度 10.对话自然度 11.描写详略得当 12.节奏控制\n"
            user_content += "13.信息密度 14.世界观规则遵守 15.力量体系一致 16.前文衔接\n"
            user_content += "17.章末钩子 18.重复用词/句式 19.AI味检测 20.整体可读性\n\n"
            user_content += "每个问题标记 severity: critical/warning/info\n"
            user_content += "输出 {critical_count, warning_count, issues: [{severity, type, location, description, fix_instruction}]}\n"
        
        else:
            user_content = task_input.get("task", "请审核一致性")
        
        messages.append({"role": "user", "content": user_content})
        return messages

    def parse_response(self, response: str, task_input: dict) -> dict:
        """解析审核响应"""
        mode = task_input.get("mode", "auditor")
        
        # 尝试解析 JSON
        try:
            json_str = response
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]
            parsed_data = json.loads(json_str.strip())
        except (json.JSONDecodeError, IndexError):
            parsed_data = {"raw": response}
        
        if mode == "auditor":
            critical_count = parsed_data.get("critical_count", 0)
            warning_count = parsed_data.get("warning_count", 0)
            summary = f"审核完成：{critical_count} 个关键问题，{warning_count} 个警告"
        elif mode == "observer":
            facts = parsed_data.get("facts", [])
            summary = f"事实提取完成：共 {len(facts)} 条事实"
        elif mode == "reflector":
            deltas = parsed_data.get("deltas", {})
            total = sum(len(v) if isinstance(v, list) else 1 for v in deltas.values())
            summary = f"状态 delta 生成完成：{total} 项更新"
        else:
            summary = "一致性检查完成"
        
        return {
            "summary": summary,
            "parsed_data": parsed_data,
            "raw": response,
            "output_file": task_input.get("output_path", ""),
        }
